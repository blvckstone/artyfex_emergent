from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header, Request, BackgroundTasks
from fastapi.responses import RedirectResponse, JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import hmac
import hashlib
import base64
import json
from urllib.parse import urlencode
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import io
import bcrypt
import jwt as pyjwt
import razorpay
import asyncio
import re
import httpx
import resend
import time
import cloudinary
import cloudinary.utils
import cloudinary.uploader

# Rate limiting (brute-force / abuse protection). In-memory backend — fine for
# single-instance Northflank. For multi-instance, swap in Redis storage_uri.
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

RZP_KEY = os.environ.get('RAZORPAY_KEY_ID', '')
RZP_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
RZP_WEBHOOK_SECRET = os.environ.get('RAZORPAY_WEBHOOK_SECRET', '')
JWT_SECRET = os.environ.get('JWT_SECRET', 'change-me')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@artyfex.in')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'ArtyFex@2026')

# --- SECURITY BOOTSTRAP WARNINGS ---------------------------------------------
# We WARN but don't crash so preview environments keep working. In production
# (ENV=production) we upgrade to a hard failure.
_env_name = os.environ.get('APP_ENV', 'development').lower()
_is_prod = _env_name in ('production', 'prod', 'live')
_log_boot = logging.getLogger("artyfex.security")
if not JWT_SECRET or JWT_SECRET in ('change-me', 'dev-secret', ''):
    msg = "JWT_SECRET is missing or default — tokens can be forged."
    if _is_prod:
        raise RuntimeError(msg + " Refusing to boot in production.")
    _log_boot.warning(msg)
if _is_prod and len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET must be at least 32 chars in production")
if _is_prod and not RZP_SECRET:
    _log_boot.warning("RAZORPAY_KEY_SECRET missing — payments will fail")
if _is_prod and not RZP_WEBHOOK_SECRET:
    _log_boot.warning("RAZORPAY_WEBHOOK_SECRET missing — webhook signature verification disabled")

# --- RATE LIMITER -------------------------------------------------------------
# Uses X-Forwarded-For / remote_addr. Northflank/Vercel forward the real IP via
# that header so per-IP limits actually differentiate real users.
limiter = Limiter(key_func=get_remote_address, default_limits=[])

# Google OAuth (custom, Phase B). If unset, /auth/google/login returns 500.
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
# Public URLs used to build OAuth redirect + final frontend hand-off.
# In production set BACKEND_PUBLIC_URL to the Northflank custom domain
# (e.g. https://api.artyfex.in) and FRONTEND_PUBLIC_URL to https://www.artyfex.in.
BACKEND_PUBLIC_URL = (os.environ.get('BACKEND_PUBLIC_URL', '') or 'http://localhost:8001').rstrip('/')
FRONTEND_PUBLIC_URL = (os.environ.get('FRONTEND_PUBLIC_URL', '') or 'http://localhost:3000').rstrip('/')

rzp_client = razorpay.Client(auth=(RZP_KEY, RZP_SECRET)) if RZP_KEY else None

# Resend email config
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')
SENDER_NAME = os.environ.get('SENDER_NAME', 'ArtyFex Atelier')
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# --- Cloudinary configuration (Phase A · admin image uploads) ---
CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME', '')
CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY', '')
CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET', '')
if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True,
    )

# --- Default admin whitelist (used by Google admin login) ---
DEFAULT_ADMIN_WHITELIST = {"iblvckstone@gmail.com", "virusisstandhere@gmail.com"}


async def send_email(to_email: str, subject: str, html: str):
    """Non-blocking send. Silent-fails so email issues never break API responses."""
    if not RESEND_API_KEY:
        logging.warning("RESEND_API_KEY not configured — skipping email")
        return
    try:
        params = {"from": f"{SENDER_NAME} <{SENDER_EMAIL}>", "to": [to_email], "subject": subject, "html": html}
        await asyncio.to_thread(resend.Emails.send, params)
        logging.info(f"Email sent to {to_email}: {subject}")
    except Exception as e:
        logging.error(f"Email send failed for {to_email}: {e}")


def _esc(s) -> str:
    """HTML-escape a value for safe interpolation into email templates.
    Used by notify_admins_event callers to prevent HTML-injection from any
    user-supplied string (customer name, review body, etc.). Added Jul 2025
    after security review."""
    import html as _html_mod
    if s is None:
        return ""
    return _html_mod.escape(str(s), quote=True)


async def notify_admins_event(kind: str, subject: str, html_body: str):
    """Fan-out an operational notification to every admin in db.admins (Task 6).

    Categories used across the codebase:
      order_new, order_returned, review_pending, low_stock, payment_failed, b2b_lead
    Silent-fails per recipient so one bad address never blocks the others.

    SECURITY: callers MUST html-escape any user-supplied fragment before
    interpolating into `subject` / `html_body`. Use the module-level helper
    `_esc()` below.
    """
    try:
        admins = await db.admins.find({}, {"_id": 0, "email": 1}).to_list(200)
    except Exception:
        admins = []
    seen: set = set()
    envelope = (
        f"<div style='font-family:Cormorant Garamond,Georgia,serif;padding:24px;background:#050505;color:#f5f1e8'>"
        f"<div style='font-size:11px;letter-spacing:.2em;color:#c9a15a;text-transform:uppercase;margin-bottom:8px'>ArtyFex · {kind.replace('_',' ').title()}</div>"
        f"<div style='font-size:22px;color:#f5f1e8;margin-bottom:16px'>{subject}</div>"
        f"<div style='font-family:Outfit,Arial,sans-serif;font-size:14px;color:#f5f1e8/70;line-height:1.6'>{html_body}</div>"
        f"<hr style='border:none;border-top:1px solid #333;margin:24px 0'/>"
        f"<div style='font-size:11px;color:#888'>Automated notification from ArtyFex Atelier · you receive these because you are an admin on the platform.</div>"
        f"</div>"
    )
    for a in admins:
        em = (a.get("email") or "").lower().strip()
        if not em or em in seen:
            continue
        seen.add(em)
        try:
            await send_email(em, f"[ArtyFex Admin] {subject}", envelope)
        except Exception as e:
            logging.error(f"admin notify failed for {em}: {e}")




def render_return_email(status: str, customer_name: str, order_number: str, admin_notes: Optional[str], is_genuine: Optional[bool]) -> tuple[str, str]:
    approved = status == "approved"
    accent = "#D4AF37" if approved else "#E37878"
    headline = "Your return has been approved" if approved else "Your return could not be approved"
    intro = (
        "Our atelier has reviewed your return request and approved it. Our reverse-pickup team will reach out within 24 hours to schedule the collection."
        if approved else
        "After careful inspection our atelier could not approve this return. See the note from our team below for details."
    )
    subject = f"[ArtyFex] Return {status} · {order_number}"
    genuine_line = ""
    if approved and is_genuine is True:
        genuine_line = '<p style="margin:16px 0 0 0;color:#4ade80;font-size:12px;letter-spacing:1.6px;text-transform:uppercase;">Verified genuine · full refund eligible</p>'
    elif approved and is_genuine is False:
        genuine_line = '<p style="margin:16px 0 0 0;color:#fbbf24;font-size:12px;letter-spacing:1.6px;text-transform:uppercase;">Restocking / repair fees may apply</p>'
    notes_block = ""
    if admin_notes:
        notes_block = f'''
        <div style="margin-top:28px;padding:20px;background:#141414;border-left:3px solid {accent};">
          <div style="font-size:10px;letter-spacing:1.8px;text-transform:uppercase;color:#888;margin-bottom:8px;">Note from atelier</div>
          <div style="color:#e8e2d5;font-size:14px;line-height:1.6;">{admin_notes}</div>
        </div>'''
    html = f'''<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#0a0a0a;font-family:Georgia,serif;color:#e8e2d5;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#0a0a0a;padding:48px 24px;">
    <tr><td align="center">
      <table role="presentation" width="560" cellspacing="0" cellpadding="0" style="max-width:560px;background:#111;border:1px solid #1f1f1f;">
        <tr><td style="padding:40px 40px 24px 40px;border-bottom:1px solid #1f1f1f;">
          <div style="font-size:11px;letter-spacing:2.4px;text-transform:uppercase;color:{accent};">ArtyFex · Atelier</div>
          <h1 style="margin:16px 0 0 0;font-size:28px;font-weight:normal;color:#f5efdf;font-family:Georgia,serif;">{headline}</h1>
          <div style="margin-top:8px;font-size:12px;color:#888;">Order · <span style="font-family:monospace;color:{accent};">{order_number}</span></div>
        </td></tr>
        <tr><td style="padding:32px 40px 40px 40px;">
          <p style="margin:0;font-size:15px;line-height:1.7;color:#e8e2d5;">Dear {customer_name},</p>
          <p style="margin:16px 0 0 0;font-size:15px;line-height:1.7;color:#c9c2b1;">{intro}</p>
          {genuine_line}
          {notes_block}
          <div style="margin-top:32px;padding-top:24px;border-top:1px solid #1f1f1f;font-size:12px;color:#888;line-height:1.8;">
            You can track this request anytime in <a href="https://artyfex.in/account" style="color:{accent};text-decoration:none;">your account → Returns</a>.
          </div>
          <p style="margin-top:32px;font-size:14px;color:#c9c2b1;">With care,<br/><span style="color:{accent};font-style:italic;">The ArtyFex Atelier</span></p>
        </td></tr>
      </table>
      <div style="margin-top:24px;font-size:10px;letter-spacing:1.8px;text-transform:uppercase;color:#555;">100% Handmade · Mumbai</div>
    </td></tr>
  </table>
</body></html>'''
    return subject, html


# ==== Phase A (Jul 2025): Order transactional emails ====
def _fmt_inr(amount) -> str:
    try:
        return "\u20b9" + f"{int(amount):,}"
    except Exception:
        return "\u20b9" + str(amount or 0)


def render_order_email(kind: str, order: dict, custom_subject: Optional[str] = None, custom_body_html: Optional[str] = None) -> tuple[str, str]:
    """Render transactional email for order lifecycle.

    kind in {"placed", "dispatched", "cancelled", "custom"}
    """
    MID = "\u00b7"
    ARROW = "\u2192"
    customer = order.get("customer") or {}
    name = customer.get("name") or "there"
    order_number = order.get("order_number") or ""
    items = order.get("items") or []
    accent = "#D4AF37"
    if kind == "placed":
        headline = "Thank you for your order"
        intro = "We have received your order and our atelier is preparing your piece with care. You will receive another note once it ships."
        subject = f"[ArtyFex] Order confirmed {MID} {order_number}"
    elif kind == "dispatched":
        headline = "Your order is on its way"
        intro = "Your piece has left our atelier. Tracking details are below \u2014 please allow 3\u20137 business days for delivery."
        subject = f"[ArtyFex] Order dispatched {MID} {order_number}"
    elif kind == "cancelled":
        headline = "Your order has been cancelled"
        intro = "As requested, we have cancelled your order. Any charge captured by our payment provider will be refunded within 5\u20137 business days."
        subject = f"[ArtyFex] Order cancelled {MID} {order_number}"
    else:  # custom
        headline = custom_subject or "A note from the ArtyFex atelier"
        intro = ""
        subject = f"[ArtyFex] {custom_subject or 'Update'} {MID} {order_number}" if order_number else f"[ArtyFex] {custom_subject or 'Update'}"

    # Items block
    item_rows = ""
    for it in items:
        pname = it.get("name") or it.get("product_name") or "Piece"
        variant = it.get("variant_label") or it.get("variant") or ""
        qty = it.get("quantity") or 1
        price = it.get("price_inr") or it.get("unit_price_inr") or 0
        line_total = int(price) * int(qty)
        variant_html = f' <span style="color:#888;">{MID} {variant}</span>' if variant else ''
        item_rows += f"""
        <tr>
          <td style="padding:10px 0;border-bottom:1px solid #1f1f1f;color:#e8e2d5;font-size:14px;">
            {pname}{variant_html}
            <div style="color:#888;font-size:11px;margin-top:2px;">Qty {qty}</div>
          </td>
          <td style="padding:10px 0;border-bottom:1px solid #1f1f1f;color:#e8e2d5;font-size:14px;text-align:right;font-family:monospace;">{_fmt_inr(line_total)}</td>
        </tr>"""

    # Totals block
    subtotal = int(order.get("subtotal_inr") or 0)
    discount = int(order.get("discount_inr") or 0)
    shipping = int(order.get("shipping_inr") or 0)
    gst = int(order.get("gst_total_inr") or 0)
    total = int(order.get("total_inr") or 0)
    coupon = order.get("coupon_code")

    coupon_row = ""
    if discount > 0:
        coupon_row = f'<tr><td style="color:{accent};font-size:13px;padding:4px 0;">Coupon ({coupon})</td><td style="color:{accent};font-size:13px;text-align:right;padding:4px 0;font-family:monospace;">- {_fmt_inr(discount)}</td></tr>'
    gst_row = ""
    if gst > 0:
        gst_row = f'<tr><td style="color:#888;font-size:13px;padding:4px 0;">GST</td><td style="color:#e8e2d5;font-size:13px;text-align:right;padding:4px 0;font-family:monospace;">{_fmt_inr(gst)}</td></tr>'

    totals_block = f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-top:24px;">
      <tr><td style="color:#888;font-size:13px;padding:4px 0;">Subtotal</td><td style="color:#e8e2d5;font-size:13px;text-align:right;padding:4px 0;font-family:monospace;">{_fmt_inr(subtotal)}</td></tr>
      {coupon_row}
      <tr><td style="color:#888;font-size:13px;padding:4px 0;">Shipping</td><td style="color:#e8e2d5;font-size:13px;text-align:right;padding:4px 0;font-family:monospace;">{_fmt_inr(shipping)}</td></tr>
      {gst_row}
      <tr><td style="color:{accent};font-size:15px;padding:12px 0 4px 0;border-top:1px solid #1f1f1f;text-transform:uppercase;letter-spacing:2px;">Total</td><td style="color:{accent};font-size:18px;text-align:right;padding:12px 0 4px 0;border-top:1px solid #1f1f1f;font-family:monospace;">{_fmt_inr(total)}</td></tr>
    </table>
    """

    tracking_block = ""
    if kind == "dispatched":
        t_id = order.get("tracking_id")
        t_url = order.get("tracking_url")
        t_car = order.get("tracking_carrier")
        if t_id or t_car:
            carrier_html = f'<div style="color:#e8e2d5;font-size:14px;">Carrier {MID} <span style="color:{accent};">{t_car}</span></div>' if t_car else ''
            id_html = f'<div style="color:#e8e2d5;font-size:14px;font-family:monospace;margin-top:4px;">{t_id}</div>' if t_id else ''
            url_html = f'<div style="margin-top:10px;"><a href="{t_url}" style="color:{accent};font-size:12px;text-decoration:underline;letter-spacing:1.5px;text-transform:uppercase;">Track your order {ARROW}</a></div>' if t_url else ''
            tracking_block = f"""
            <div style="margin-top:28px;padding:20px;background:#141414;border-left:3px solid {accent};">
              <div style="font-size:10px;letter-spacing:1.8px;text-transform:uppercase;color:#888;margin-bottom:8px;">Tracking</div>
              {carrier_html}
              {id_html}
              {url_html}
            </div>"""

    body_html = custom_body_html or ""
    if body_html:
        body_html = f'<div style="margin-top:24px;color:#c9c2b1;font-size:14px;line-height:1.7;">{body_html}</div>'

    order_number_line = ""
    if order_number:
        order_number_line = f'<div style="margin-top:8px;font-size:12px;color:#888;">Order {MID} <span style="font-family:monospace;color:{accent};">{order_number}</span></div>'
    intro_line = f'<p style="margin:16px 0 0 0;font-size:15px;line-height:1.7;color:#c9c2b1;">{intro}</p>' if intro else ''
    items_table = f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-top:28px;">{item_rows}</table>' if item_rows else ''
    totals_final = totals_block if items else ''

    html = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#0a0a0a;font-family:Georgia,serif;color:#e8e2d5;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#0a0a0a;padding:48px 24px;">
    <tr><td align="center">
      <table role="presentation" width="580" cellspacing="0" cellpadding="0" style="max-width:580px;background:#111;border:1px solid #1f1f1f;">
        <tr><td style="padding:40px 40px 24px 40px;border-bottom:1px solid #1f1f1f;">
          <div style="font-size:11px;letter-spacing:2.4px;text-transform:uppercase;color:{accent};">ArtyFex {MID} Atelier</div>
          <h1 style="margin:16px 0 0 0;font-size:28px;font-weight:normal;color:#f5efdf;font-family:Georgia,serif;">{headline}</h1>
          {order_number_line}
        </td></tr>
        <tr><td style="padding:32px 40px 40px 40px;">
          <p style="margin:0;font-size:15px;line-height:1.7;color:#e8e2d5;">Dear {name},</p>
          {intro_line}
          {body_html}
          {tracking_block}
          {items_table}
          {totals_final}
          <div style="margin-top:32px;padding-top:24px;border-top:1px solid #1f1f1f;font-size:12px;color:#888;line-height:1.8;">
            Track your order in <a href="https://artyfex.in/account" style="color:{accent};text-decoration:none;">your account</a>.
          </div>
          <p style="margin-top:32px;font-size:14px;color:#c9c2b1;">With care,<br/><span style="color:{accent};font-style:italic;">The ArtyFex Atelier</span></p>
        </td></tr>
      </table>
      <div style="margin-top:24px;font-size:10px;letter-spacing:1.8px;text-transform:uppercase;color:#555;">100% Handmade {MID} Mumbai</div>
    </td></tr>
  </table>
</body></html>"""
    return subject, html


async def send_order_email(order: dict, kind: str, custom_subject: Optional[str] = None, custom_body_html: Optional[str] = None):
    """Fire-and-forget order email; silent-fails."""
    to_email = (order.get("customer") or {}).get("email")
    if not to_email:
        return
    try:
        subject, html = render_order_email(kind, order, custom_subject=custom_subject, custom_body_html=custom_body_html)
        await send_email(to_email, subject, html)
    except Exception as _e:
        logging.error(f"Order email render/send failed ({kind}): {_e}")
app = FastAPI(
    title="ArtyFex API",
    # In production we hide /docs, /redoc and /openapi.json to reduce recon
    # surface. Preview / dev still gets them.
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_url=None if _is_prod else "/openapi.json",
)
api_router = APIRouter(prefix="/api")

# Wire slowapi into the app so decorators like @limiter.limit("5/minute") work.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# --- SECURITY HEADERS MIDDLEWARE ---------------------------------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds baseline security response headers on every API response.

    Notes:
    - We deliberately do NOT set a strict CSP here because the storefront is
      served by a different origin (Vercel) that owns its own CSP. This
      middleware guards the API responses so admin-panel tokens and payment
      flows aren't leaked via referrer/frame embedding/etc.
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=(), payment=(self \"https://api.razorpay.com\" \"https://checkout.razorpay.com\")")
        # Only send HSTS when the request came in over HTTPS (behind Render/Vercel proxy)
        if request.headers.get("x-forwarded-proto", request.url.scheme) == "https":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


app.add_middleware(SecurityHeadersMiddleware)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ---------- MODELS ---------- #
class VariationValue(BaseModel):
    """A single choice within a variation option group.

    Ex. For a "Shape" option: {"key":"round","label":"Round","price_delta_inr":0}
        For a "Frame" option: {"key":"bordered","label":"With Border","image":"...","price_delta_inr":2500}
    """
    model_config = ConfigDict(extra="ignore")
    key: str
    label: str
    hex: Optional[str] = None          # For colour swatches
    image: Optional[str] = None        # Optional preview image
    price_delta_inr: int = 0           # Added to product price if selected (₹)
    stock: Optional[int] = None        # Optional per-value stock override
    is_default: bool = False


class VariationOption(BaseModel):
    """A single option group on a product (Colour, Shape, Frame, Thickness,
    Gift-Wrap, Care Kit, Mounting Orientation, custom, …).

    UI presentation depends on `type`:
      - "swatch"  -> circular colour swatches (uses `hex`)
      - "image"   -> image tiles (uses `image`)
      - "select"  -> dropdown of labels
      - "toggle"  -> add-on style yes/no (Gift Wrap, Care Kit)
    """
    model_config = ConfigDict(extra="ignore")
    key: str                                    # canonical id, e.g. "shape"
    label: str                                  # human label, e.g. "Shape"
    type: str = "select"                        # swatch | image | select | toggle
    required: bool = False
    help_text: Optional[str] = None             # shown under the picker
    values: List[VariationValue] = Field(default_factory=list)


class Variant(BaseModel):
    model_config = ConfigDict(extra="ignore")
    key: str; label: str; hex: str; image: str
    # Optional per-variant overrides for size / stock / price
    size: Optional[str] = None
    stock: Optional[int] = None
    price_inr: Optional[int] = None
    mrp_inr: Optional[int] = None
    # Batch 5 (Jul 2026) — per-variation SKU, weight & dims so shipping cost
    # (NimbusPost / manual) is calculated per selected size/variant rather than
    # off a single product-level number. All fields optional → fallback to
    # product-level values on the parent Product.
    sku: Optional[str] = None
    weight_grams: Optional[int] = None
    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None

class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    slug: str; name: str; tagline: str; description: str
    price_inr: int; mrp_inr: int; size: str; craft_hours: int
    materials: List[str]; hero_image: str; gallery: List[str]
    variants: List[Variant]; is_hero: bool = False; stock: int = 5
    # --- Phase A (Jul 2025) — Commerce / GST / Logistics fields ---
    category: Optional[str] = None            # e-commerce category (matches Category.slug)
    hsn_code: Optional[str] = None            # HSN classification for GST lookup
    sku: Optional[str] = None                 # Stock Keeping Unit
    weight_grams: Optional[int] = None        # shipping weight
    length_cm: Optional[float] = None         # package L (for shipping logistics)
    width_cm: Optional[float] = None          # package W
    height_cm: Optional[float] = None         # package H
    tags: List[str] = Field(default_factory=list)  # custom product tags
    # Task 3 (Jul 2025) — Flexible variation options beyond legacy colour swatches.
    # variation_options is authoritative for NEW variation types (shape, frame,
    # thickness, gift-wrap, care-kit, mount…). The legacy `variants` array
    # continues to work for colour-only products; both can coexist.
    variation_options: List[VariationOption] = Field(default_factory=list)
    # Batch 6 (Jul 2026) — Amazon-style "A+ content" story blocks that render
    # BELOW the fold on the product page. Each block: {layout, heading, body,
    # image, secondary_image, features (newline-separated)}.
    # layout values: "image_left" | "image_right" | "centered" | "full_bleed"
    #              | "feature_grid" | "quote"  (default: "image_left")
    a_plus_content: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso)

class ProductIn(BaseModel):
    slug: str; name: str; tagline: str; description: str
    price_inr: int; mrp_inr: int; size: str; craft_hours: int
    materials: List[str]; hero_image: str; gallery: List[str]
    variants: List[Variant]; is_hero: bool = False; stock: int = 5
    # Optional Phase A commerce fields (all backward-compat)
    category: Optional[str] = None
    hsn_code: Optional[str] = None
    sku: Optional[str] = None
    weight_grams: Optional[int] = None
    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    tags: List[str] = Field(default_factory=list)
    variation_options: List[VariationOption] = Field(default_factory=list)
    a_plus_content: List[Dict[str, Any]] = Field(default_factory=list)

class OrderCustomer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str; email: EmailStr; phone: str
    address: str; city: str; pincode: str
    # New Amazon-style structured fields (all optional for backward compat)
    line1: Optional[str] = None      # House / Building / Flat
    line2: Optional[str] = None      # Area / Street / Colony
    landmark: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "India"

class OrderItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    product_id: str; variant_key: str; quantity: int = 1
    # ---- Snapshot fields (populated server-side on order create; backward-compat optional) ----
    product_name: Optional[str] = None
    product_slug: Optional[str] = None
    product_image: Optional[str] = None
    product_category: Optional[str] = None
    product_hsn_code: Optional[str] = None
    product_sku: Optional[str] = None
    variant_label: Optional[str] = None
    variant_hex: Optional[str] = None
    variant_image: Optional[str] = None
    size: Optional[str] = None
    price_inr: Optional[int] = None
    mrp_inr: Optional[int] = None
    line_total_inr: Optional[int] = None
    # Batch 5 (Jul 2026) — per-line shipping snapshot so couriers get the
    # RIGHT weight/dims of the actual size the customer picked, not the
    # generic product-level default.
    weight_grams: Optional[int] = None
    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    # Task 3 (Jul 2025) — free-form option selections beyond legacy colour swatches.
    selected_options: Dict[str, str] = Field(default_factory=dict)
    selected_options_labels: Dict[str, str] = Field(default_factory=dict)
    options_price_delta_inr: int = 0
    # Batch 6 — free-form per-line customer notes (e.g. gift-wrap recipient
    # name & message, engraving text, etc.). Kept as a flat string dict so
    # everything stays JSON-round-trippable and easy to display.
    notes: Dict[str, str] = Field(default_factory=dict)

class OrderIn(BaseModel):
    customer: OrderCustomer; items: List[OrderItem]
    payment_method: str  # razorpay | cod
    subtotal_inr: int; shipping_inr: int; total_inr: int
    coupon_code: Optional[str] = None
    discount_inr: int = 0
    # Phase A (Jul 2025) — GST (server recomputes authoritatively)
    gst_total_inr: int = 0
    cgst_inr: int = 0
    sgst_inr: int = 0
    igst_inr: int = 0

class Order(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_number: str = Field(default_factory=lambda: f"ARF-{uuid.uuid4().hex[:8].upper()}")
    customer: OrderCustomer; items: List[OrderItem]
    payment_method: str
    subtotal_inr: int; shipping_inr: int; total_inr: int
    coupon_code: Optional[str] = None
    discount_inr: int = 0
    # Phase A — GST breakdown (INR paise-safe integers)
    gst_total_inr: int = 0
    cgst_inr: int = 0
    sgst_inr: int = 0
    igst_inr: int = 0
    gst_lines: List[dict] = Field(default_factory=list)
    gst_treatment: str = "inclusive"  # inclusive | exclusive
    status: str = "pending_payment"  # pending_payment | confirmed | packed | shipped | delivered | cancelled | payment_failed
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    delivered_at: Optional[str] = None
    # Shipment tracking (Phase A)
    tracking_id: Optional[str] = None
    tracking_url: Optional[str] = None
    tracking_carrier: Optional[str] = None
    tracking_updated_at: Optional[str] = None
    # Task 8 — GST invoice metadata (assigned lazily on first PDF download)
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)

class Review(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    author: str; location: str; rating: int
    title: str; body: str; image: Optional[str] = None
    verified: bool = True; featured: bool = False
    # Task 5: moderation. "approved" reviews show publicly. "pending" wait for
    # admin to approve. "rejected" are archived. Admin-created reviews auto-
    # approve; user-submitted reviews start "pending".
    status: str = "approved"
    # Optional link to the product being reviewed (used for storefront filtering)
    product_id: Optional[str] = None
    # Author identity — used to gate "verified buyer" badge + prevent duplicate reviews.
    user_email: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)

class ReviewIn(BaseModel):
    author: str; location: str; rating: int
    title: str; body: str; image: Optional[str] = None
    featured: bool = False
    verified: bool = True
    status: str = "approved"
    product_id: Optional[str] = None

class B2BLeadIn(BaseModel):
    full_name: str; company: str; email: EmailStr; phone: str
    business_type: str
    dimensions: Optional[str] = None; quantity: Optional[int] = None; message: Optional[str] = None

class B2BLead(B2BLeadIn):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "new"; created_at: str = Field(default_factory=now_iso)

class AdminLogin(BaseModel):
    email: EmailStr; password: str

class OrderStatusUpdate(BaseModel):
    status: str

class B2BStatusUpdate(BaseModel):
    status: str

class RzpVerify(BaseModel):
    order_number: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class UserSignup(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128, description="8–128 chars")
    phone: Optional[str] = Field(default=None, max_length=20)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class GoogleSessionIn(BaseModel):
    session_id: str


class ReviewPromptDelay(BaseModel):
    review_prompt_days: int = Field(ge=0, le=90)


class ReviewSubmit(BaseModel):
    rating: int = Field(ge=1, le=5)
    title: str = Field(min_length=1, max_length=140)
    body: str = Field(min_length=1, max_length=4000)
    location: Optional[str] = None
    image: Optional[str] = None
    product_id: Optional[str] = None
    author_name: Optional[str] = None


class ReturnRequestIn(BaseModel):
    order_number: str
    reason: str
    details: Optional[str] = None
    damage_image_url: Optional[str] = None
    packaging_confirmed: bool = False


class ReturnRequest(ReturnRequestIn):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_email: str
    status: str = "requested"  # requested | approved | rejected | received | refunded
    is_genuine: Optional[bool] = None
    admin_notes: Optional[str] = None
    reviewed_at: Optional[str] = None
    reviewed_by: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)


class ReturnStatusUpdate(BaseModel):
    status: str  # approved | rejected | received | refunded
    is_genuine: Optional[bool] = None
    admin_notes: Optional[str] = None


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None


class AdminMessageIn(BaseModel):
    user_email: EmailStr
    subject: str
    body: str


class AdminMessage(AdminMessageIn):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=now_iso)
    created_by: str = ""
    read: bool = False
    read_at: Optional[str] = None


# ---------- COUPONS ----------
class CouponIn(BaseModel):
    code: str
    type: str  # "percentage" | "flat"
    value: float  # percentage (0-100) or flat amount (INR)
    min_cart_inr: int = 0
    max_uses: Optional[int] = None
    expires_at: Optional[str] = None  # ISO string
    active: bool = True
    description: Optional[str] = None


class Coupon(CouponIn):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    used_count: int = 0
    created_at: str = Field(default_factory=now_iso)


class CouponValidateIn(BaseModel):
    code: str
    cart_total_inr: int


# ---------- FAILED PAYMENTS ----------
class FailedPaymentIn(BaseModel):
    order_number: Optional[str] = None
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    error_code: Optional[str] = None
    error_description: Optional[str] = None
    error_source: Optional[str] = None
    error_step: Optional[str] = None
    error_reason: Optional[str] = None
    amount_inr: int = 0
    customer_email: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    attempt: int = 1


class FailedPayment(FailedPaymentIn):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=now_iso)


# Strict return window enforced from delivery date
RETURN_WINDOW_DAYS = 3


# ---------- CATEGORIES (Phase A · Jul 2025) ----------
class CategoryIn(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    active: bool = True


class Category(CategoryIn):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=now_iso)


# ---------- GST RULES (Phase A · Jul 2025) ----------
# A rule maps a product-attribute → tax rate.
# Priority: hsn_code match > category match. Only one of the two should
# typically be set on any rule.
class GstRuleIn(BaseModel):
    hsn_code: Optional[str] = None
    category: Optional[str] = None   # matches Category.slug (or free-text)
    rate_percent: float               # e.g. 5, 12, 18, 28
    description: Optional[str] = None
    active: bool = True


class GstRule(GstRuleIn):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=now_iso)


class CartTaxItem(BaseModel):
    product_id: str
    variant_key: Optional[str] = None
    quantity: int = 1


class CartTaxIn(BaseModel):
    items: List[CartTaxItem]
    ship_state: Optional[str] = None   # Indian state name, e.g. "Maharashtra"


# Business registered in Maharashtra → intra-state gets CGST + SGST split,
# inter-state gets a single IGST at the full rate.
BUSINESS_STATE = "MAHARASHTRA"


# ---------- COUPONS ----------


# ---------- SEED ---------- #
from server_seed import SEED_PRODUCTS, SEED_REVIEWS, SEED_COUPONS  # noqa: E402


async def seed_if_empty():
    if await db.products.count_documents({}) == 0:
        await db.products.insert_many([Product(**p).model_dump() for p in SEED_PRODUCTS])
        logging.info(f"Seeded {len(SEED_PRODUCTS)} products")
    if await db.reviews.count_documents({}) == 0:
        await db.reviews.insert_many([Review(**r).model_dump() for r in SEED_REVIEWS])
        logging.info(f"Seeded {len(SEED_REVIEWS)} reviews")
    if await db.coupons.count_documents({}) == 0:
        await db.coupons.insert_many([Coupon(**c).model_dump() for c in SEED_COUPONS])
        logging.info(f"Seeded {len(SEED_COUPONS)} coupons")
    # --- Phase A (Jul 2025): seed product categories on empty DB ---
    if await db.product_categories.count_documents({}) == 0:
        seed_cats = [
            {"name": "Mirrors", "slug": "mirrors", "description": "Statement & round crystal mirrors"},
            {"name": "Wall Art", "slug": "wall-art", "description": "Resin wall pieces & panels"},
            {"name": "Sculpture", "slug": "sculpture", "description": "Free-standing resin sculptures"},
            {"name": "Tabletop", "slug": "tabletop", "description": "Trays, coasters, table décor"},
            {"name": "Lighting", "slug": "lighting", "description": "Resin lamps & lighting"},
            {"name": "Companion", "slug": "companion", "description": "Smaller companion pieces"},
            {"name": "Gifting", "slug": "gifting", "description": "Curated gifting selections"},
            {"name": "Custom", "slug": "custom", "description": "Bespoke commissions"},
        ]
        await db.product_categories.insert_many([Category(**c).model_dump() for c in seed_cats])
        logging.info(f"Seeded {len(seed_cats)} product categories")
    # --- Phase A: seed GST rules mapping HSN + categories → tax slab ---
    if await db.gst_rules.count_documents({}) == 0:
        seed_rules = [
            {"hsn_code": "7009", "rate_percent": 18, "description": "Mirrors (glass) — HSN 7009"},
            {"hsn_code": "9701", "rate_percent": 12, "description": "Handmade paintings / art — HSN 9701"},
            {"hsn_code": "3926", "rate_percent": 18, "description": "Other articles of plastics/resin — HSN 3926"},
            {"category": "mirrors", "rate_percent": 18, "description": "Fallback for uncoded mirrors"},
            {"category": "wall-art", "rate_percent": 12, "description": "Fallback for wall art"},
            {"category": "sculpture", "rate_percent": 12, "description": "Fallback for sculpture"},
            {"category": "tabletop", "rate_percent": 18, "description": "Fallback for tabletop décor"},
            {"category": "lighting", "rate_percent": 18, "description": "Fallback for lighting"},
            {"category": "companion", "rate_percent": 12, "description": "Fallback for companion pieces"},
            {"category": "gifting", "rate_percent": 12, "description": "Fallback for gifting"},
            {"category": "custom", "rate_percent": 18, "description": "Fallback for bespoke"},
        ]
        await db.gst_rules.insert_many([GstRule(**r).model_dump() for r in seed_rules])
        logging.info(f"Seeded {len(seed_rules)} GST rules")
    # Backfill category/HSN on legacy products (idempotent — only sets if missing).
    # We assume all seed mirrors match HSN 7009 / category 'mirrors'. Admin can edit any product later.
    try:
        legacy = await db.products.find({"$or": [{"category": {"$in": [None, ""]}}, {"category": {"$exists": False}}]}, {"_id": 0, "id": 1, "slug": 1}).to_list(500)
        for lp in legacy:
            slug = lp.get("slug", "")
            # everything we ship right now is a mirror
            await db.products.update_one(
                {"id": lp["id"]},
                {"$set": {
                    "category": "mirrors",
                    "hsn_code": "7009",
                    "sku": f"ARF-{slug[:12].upper().replace('-','')}" if slug else None,
                    "tags": [],
                }},
            )
        if legacy:
            logging.info(f"Backfilled category/HSN on {len(legacy)} legacy products")
    except Exception as e:
        logging.warning(f"Product backfill skipped: {e}")
    # Seed admin (idempotent) - owner has all permissions
    if not await db.admins.find_one({"email": ADMIN_EMAIL}):
        pw_hash = bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode()
        await db.admins.insert_one({
            "id": str(uuid.uuid4()), "email": ADMIN_EMAIL,
            "password_hash": pw_hash, "created_at": now_iso(),
            "role": "owner", "permissions": ALL_PERMISSIONS,
            "display_name": "Atelier Owner",
        })
        logging.info(f"Seeded admin {ADMIN_EMAIL}")
    else:
        # Backfill owner role + permissions on existing owner doc
        await db.admins.update_one(
            {"email": ADMIN_EMAIL},
            {"$set": {"role": "owner", "permissions": ALL_PERMISSIONS}}
        )


# ---------- AUTH ---------- #
# Permission catalog — extend here when new admin capabilities are added.
ALL_PERMISSIONS = [
    "manage_products",
    "manage_orders",
    "manage_returns",
    "manage_customers",
    "manage_reviews",
    "manage_leads",
    "manage_coupons",
    "manage_homepage",
    "manage_shipping",
    "manage_gst",
    "view_analytics",
    "manage_employees",
]


def create_token(email: str, role: str = "admin") -> str:
    payload = {"sub": email, "role": role, "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")


async def _decode(authorization: Optional[str]):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return pyjwt.decode(authorization.split(" ", 1)[1], JWT_SECRET, algorithms=["HS256"])
    except pyjwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_admin(authorization: str = Header(None)):
    payload = await _decode(authorization)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    admin = await db.admins.find_one({"email": payload.get("sub")}, {"_id": 0, "password_hash": 0})
    if not admin:
        raise HTTPException(status_code=401, detail="Admin not found")
    # Ensure permissions field always exists (legacy docs)
    admin.setdefault("role", "owner")
    admin.setdefault("permissions", ALL_PERMISSIONS if admin.get("role") == "owner" else [])
    return admin


def require_permission(perm: str):
    """FastAPI dependency: only allows requests from an admin having `perm` (owner bypasses)."""
    async def _dep(admin=Depends(get_current_admin)):
        role = admin.get("role", "owner")
        perms = admin.get("permissions") or []
        if role == "owner" or perm in perms:
            return admin
        raise HTTPException(status_code=403, detail=f"Missing permission: {perm}")
    return _dep


def require_owner(admin=Depends(get_current_admin)):
    if admin.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Owner only")
    return admin


async def get_current_user(authorization: str = Header(None)):
    payload = await _decode(authorization)
    user = await db.users.find_one({"email": payload.get("sub")}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ---------- PUBLIC ROUTES ---------- #
@api_router.get("/")
async def root():
    return {"brand": "ArtyFex"}


@api_router.get("/health")
async def health():
    """Deep-health probe. Reports readiness of every 3rd-party dependency so we
    can spot which service is misconfigured after a deploy. Safe to expose — no
    secrets are returned, only booleans + short status strings."""
    checks = {
        "app": "ok",
        "env": _env_name,
    }
    # MongoDB
    try:
        await db.command("ping")
        checks["mongo"] = "ok"
    except Exception as e:
        checks["mongo"] = f"fail: {type(e).__name__}"
    # Razorpay
    checks["razorpay_configured"] = bool(RZP_KEY and RZP_SECRET)
    checks["razorpay_webhook_configured"] = bool(RZP_WEBHOOK_SECRET)
    # Resend email
    checks["resend_configured"] = bool(RESEND_API_KEY)
    checks["sender_email"] = SENDER_EMAIL if RESEND_API_KEY else None
    # Google OAuth
    checks["google_oauth_configured"] = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
    # Cloudinary (image uploads in admin)
    checks["cloudinary_configured"] = bool(
        CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET
    )
    # URL / CORS visibility
    checks["backend_public_url"] = BACKEND_PUBLIC_URL
    checks["frontend_public_url"] = FRONTEND_PUBLIC_URL
    checks["cors_allow_origins"] = _cors_allow_origins
    checks["cors_allow_credentials"] = _cors_allow_credentials
    # JWT secret sanity (no leaking the value)
    checks["jwt_secret_strength"] = "strong" if len(JWT_SECRET) >= 32 else "weak"
    return checks


# ---------- COUPON HELPERS ----------
def _coupon_availability_error(coupon: dict, cart_total_inr: int) -> Optional[str]:
    """Return an error message string if the coupon can NOT be applied, else None."""
    if not coupon.get("active", True):
        return "This coupon is no longer active."
    if coupon.get("expires_at"):
        try:
            exp = datetime.fromisoformat(coupon["expires_at"].replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > exp:
                return "This coupon has expired."
        except Exception:
            pass
    max_uses = coupon.get("max_uses")
    if max_uses is not None and coupon.get("used_count", 0) >= max_uses:
        return "This coupon has reached its usage limit."
    min_cart = coupon.get("min_cart_inr", 0) or 0
    if cart_total_inr < min_cart:
        return f"Minimum cart value ₹{min_cart:,} required for this code."
    return None


def _coupon_discount_inr(coupon: dict, cart_total_inr: int) -> int:
    """Compute the discount amount (INR, integer, floored) for a given cart total."""
    t = coupon.get("type", "flat")
    v = float(coupon.get("value", 0))
    if t == "percentage":
        raw = cart_total_inr * (v / 100.0)
    else:
        raw = v
    # Cap discount at cart_total (never negative totals)
    return int(max(0, min(raw, cart_total_inr)))


@api_router.post("/coupons/validate")
@limiter.limit("20/minute")
async def validate_coupon(request: Request, payload: CouponValidateIn):
    code = (payload.code or "").upper().strip()
    if not code:
        raise HTTPException(status_code=400, detail="Please enter a coupon code.")
    coupon = await db.coupons.find_one({"code": code}, {"_id": 0})
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found.")
    err = _coupon_availability_error(coupon, payload.cart_total_inr)
    if err:
        raise HTTPException(status_code=400, detail=err)
    discount = _coupon_discount_inr(coupon, payload.cart_total_inr)
    return {
        "valid": True,
        "code": coupon["code"],
        "type": coupon["type"],
        "value": coupon["value"],
        "discount_inr": discount,
        "description": coupon.get("description"),
    }


@api_router.post("/payments/failed", response_model=FailedPayment)
async def log_failed_payment(payload: FailedPaymentIn):
    fp = FailedPayment(**payload.model_dump())
    await db.failed_payments.insert_one(fp.model_dump())
    # Also mark order as payment_failed if we have the order number
    if payload.order_number:
        await db.orders.update_one(
            {"order_number": payload.order_number},
            {"$set": {"status": "payment_failed"}},
        )
    return fp


# ---------- GST / TAX ENGINE (Phase A · Jul 2025) ----------
async def _resolve_gst_rate(product: dict) -> tuple[float, str]:
    """Return (rate_percent, source) for a product using HSN > category priority.
    Only active rules are considered. Returns (0.0, "none") if no match.
    """
    if not product:
        return 0.0, "none"
    hsn = (product.get("hsn_code") or "").strip()
    cat = (product.get("category") or "").strip().lower()
    if hsn:
        rule = await db.gst_rules.find_one(
            {"hsn_code": hsn, "active": True}, {"_id": 0}, sort=[("created_at", -1)]
        )
        if rule:
            return float(rule.get("rate_percent") or 0), f"hsn:{hsn}"
    if cat:
        rule = await db.gst_rules.find_one(
            {"category": cat, "active": True}, {"_id": 0}, sort=[("created_at", -1)]
        )
        if rule:
            return float(rule.get("rate_percent") or 0), f"category:{cat}"
    return 0.0, "none"


def _price_for_variant(product: dict, variant_key: Optional[str]) -> int:
    """Resolve the effective per-unit price (variant override > product base)."""
    variants = product.get("variants") or []
    v = None
    if variant_key:
        v = next((x for x in variants if x.get("key") == variant_key), None)
    if v is None and variants:
        v = variants[0]
    if v and v.get("price_inr") is not None:
        try:
            return int(v.get("price_inr"))
        except Exception:
            pass
    return int(product.get("price_inr") or 0)


async def compute_taxes_for_cart(
    items: list[dict],
    ship_state: Optional[str] = None,
    treatment: str = "inclusive",
) -> dict:
    """Compute a per-line and aggregate GST breakdown for a cart payload.

    items: list of {product_id, variant_key?, quantity}
    treatment:
      - "inclusive": GST is baked into the shown INR price → tax extracted out
                     tax_line = line_total * rate / (100 + rate)
      - "exclusive": GST is added on top → tax_line = line_total * rate / 100

    ship_state controls CGST+SGST vs IGST split (business is Maharashtra).
    """
    gst_lines: list[dict] = []
    gst_total = 0
    for it in items:
        pid = it.get("product_id")
        qty = int(it.get("quantity") or 1)
        vk = it.get("variant_key")
        prod = await db.products.find_one({"id": pid}, {"_id": 0}) if pid else None
        if not prod or qty <= 0:
            continue
        unit_price = _price_for_variant(prod, vk)
        line_total = unit_price * qty
        rate, source = await _resolve_gst_rate(prod)
        if rate <= 0 or line_total <= 0:
            gst_lines.append({
                "product_id": pid,
                "variant_key": vk,
                "quantity": qty,
                "unit_price_inr": unit_price,
                "line_total_inr": line_total,
                "hsn_code": prod.get("hsn_code"),
                "category": prod.get("category"),
                "rate_percent": rate,
                "source": source,
                "tax_inr": 0,
                "taxable_value_inr": line_total,
            })
            continue
        if treatment == "exclusive":
            tax = int(round(line_total * rate / 100.0))
            taxable = line_total
        else:  # inclusive (default)
            tax = int(round(line_total * rate / (100.0 + rate)))
            taxable = line_total - tax
        gst_total += tax
        gst_lines.append({
            "product_id": pid,
            "variant_key": vk,
            "quantity": qty,
            "unit_price_inr": unit_price,
            "line_total_inr": line_total,
            "hsn_code": prod.get("hsn_code"),
            "category": prod.get("category"),
            "rate_percent": rate,
            "source": source,
            "tax_inr": tax,
            "taxable_value_inr": taxable,
        })

    # Split: intra-state (Maharashtra) → CGST + SGST, inter-state → IGST
    ss = (ship_state or "").strip().upper()
    if ss == BUSINESS_STATE:
        cgst = gst_total // 2
        sgst = gst_total - cgst  # keep rounding-safe sum
        igst = 0
    else:
        cgst = 0
        sgst = 0
        igst = gst_total
    return {
        "gst_total_inr": gst_total,
        "cgst_inr": cgst,
        "sgst_inr": sgst,
        "igst_inr": igst,
        "gst_lines": gst_lines,
        "treatment": treatment,
        "ship_state": ship_state or None,
        "business_state": BUSINESS_STATE.title(),
        "intra_state": ss == BUSINESS_STATE,
    }


@api_router.post("/cart/compute-tax")
async def cart_compute_tax(payload: CartTaxIn):
    """Public endpoint used by cart & checkout to preview the GST breakdown."""
    items = [it.model_dump() for it in payload.items]
    result = await compute_taxes_for_cart(items, ship_state=payload.ship_state, treatment="exclusive")
    return result


# ---------- CATEGORIES · public + admin ----------
@api_router.get("/product-categories", response_model=List[Category])
async def list_product_categories_public():
    return await db.product_categories.find({"active": True}, {"_id": 0}).sort("name", 1).to_list(200)


@api_router.get("/admin/product-categories", response_model=List[Category])
async def admin_list_categories(admin=Depends(get_current_admin)):
    return await db.product_categories.find({}, {"_id": 0}).sort("name", 1).to_list(200)


@api_router.post("/admin/product-categories", response_model=Category)
async def admin_create_category(payload: CategoryIn, admin=Depends(require_permission("manage_products"))):
    slug = (payload.slug or payload.name).strip().lower().replace(" ", "-")
    slug = "".join(ch for ch in slug if ch.isalnum() or ch == "-")
    if not slug:
        raise HTTPException(status_code=400, detail="Category slug is required.")
    if await db.product_categories.find_one({"slug": slug}):
        raise HTTPException(status_code=400, detail="A category with this slug already exists.")
    cat = Category(**{**payload.model_dump(), "slug": slug})
    await db.product_categories.insert_one(cat.model_dump())
    return cat


@api_router.patch("/admin/product-categories/{cat_id}", response_model=Category)
async def admin_update_category(cat_id: str, payload: CategoryIn, admin=Depends(require_permission("manage_products"))):
    existing = await db.product_categories.find_one({"id": cat_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found.")
    updates = payload.model_dump(exclude_unset=True)
    if "slug" in updates and updates["slug"]:
        s = updates["slug"].strip().lower().replace(" ", "-")
        s = "".join(ch for ch in s if ch.isalnum() or ch == "-")
        if s != existing.get("slug") and await db.product_categories.find_one({"slug": s}):
            raise HTTPException(status_code=400, detail="A category with this slug already exists.")
        updates["slug"] = s
    merged = {**existing, **updates}
    await db.product_categories.update_one({"id": cat_id}, {"$set": merged})
    return merged


@api_router.delete("/admin/product-categories/{cat_id}")
async def admin_delete_category(cat_id: str, admin=Depends(require_permission("manage_products"))):
    res = await db.product_categories.delete_one({"id": cat_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found.")
    return {"deleted": True}


# ---------- GST RULES · admin CRUD ----------
@api_router.get("/admin/gst-rules", response_model=List[GstRule])
async def admin_list_gst_rules(admin=Depends(require_permission("manage_gst"))):
    return await db.gst_rules.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)


@api_router.post("/admin/gst-rules", response_model=GstRule)
async def admin_create_gst_rule(payload: GstRuleIn, admin=Depends(require_permission("manage_gst"))):
    data = payload.model_dump()
    if not data.get("hsn_code") and not data.get("category"):
        raise HTTPException(status_code=400, detail="A rule must target either an HSN code or a category.")
    if data.get("rate_percent") is None or data["rate_percent"] < 0 or data["rate_percent"] > 100:
        raise HTTPException(status_code=400, detail="Rate must be between 0 and 100.")
    # normalize
    if data.get("hsn_code"):
        data["hsn_code"] = data["hsn_code"].strip()
    if data.get("category"):
        data["category"] = data["category"].strip().lower()
    # uniqueness on (hsn_code, category)
    q = {"hsn_code": data.get("hsn_code"), "category": data.get("category")}
    if await db.gst_rules.find_one(q):
        raise HTTPException(status_code=400, detail="A rule already exists for this target. Edit it instead.")
    rule = GstRule(**data)
    await db.gst_rules.insert_one(rule.model_dump())
    return rule


@api_router.patch("/admin/gst-rules/{rule_id}", response_model=GstRule)
async def admin_update_gst_rule(rule_id: str, payload: GstRuleIn, admin=Depends(require_permission("manage_gst"))):
    existing = await db.gst_rules.find_one({"id": rule_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="GST rule not found.")
    data = payload.model_dump(exclude_unset=True)
    if "hsn_code" in data and data["hsn_code"]:
        data["hsn_code"] = data["hsn_code"].strip()
    if "category" in data and data["category"]:
        data["category"] = data["category"].strip().lower()
    if "rate_percent" in data and data["rate_percent"] is not None:
        if data["rate_percent"] < 0 or data["rate_percent"] > 100:
            raise HTTPException(status_code=400, detail="Rate must be between 0 and 100.")
    merged = {**existing, **data}
    await db.gst_rules.update_one({"id": rule_id}, {"$set": merged})
    return merged


@api_router.delete("/admin/gst-rules/{rule_id}")
async def admin_delete_gst_rule(rule_id: str, admin=Depends(require_permission("manage_gst"))):
    res = await db.gst_rules.delete_one({"id": rule_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="GST rule not found.")
    return {"deleted": True}


@api_router.get("/products", response_model=List[Product])
async def list_products():
    return await db.products.find({}, {"_id": 0}).to_list(200)


@api_router.get("/products/{slug}", response_model=Product)
async def get_product(slug: str):
    doc = await db.products.find_one({"slug": slug}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    return doc


@api_router.get("/reviews", response_model=List[Review], response_model_exclude={"user_email"})
async def list_reviews(product_id: Optional[str] = None):
    """Public list of reviews. Only status=approved reviews are returned.
    Optional ?product_id=... filters to a single product (used by ProductPage).
    SECURITY: `user_email` is stripped from the response so PII does not leak
    to unauthenticated visitors (added Jul 2025 after security review)."""
    q: dict = {"status": {"$in": ["approved", None]}}
    # Back-compat: existing docs without a `status` field are treated as approved.
    if product_id:
        q["product_id"] = product_id
    # Also drop from Mongo projection as a defence-in-depth measure.
    docs = await db.reviews.find(q, {"_id": 0, "user_email": 0}).sort("created_at", -1).to_list(500)
    return docs


@api_router.post("/reviews", response_model=Review)
async def customer_submit_review(payload: ReviewSubmit, user=Depends(get_current_user)):
    """Logged-in customer submits a review. Starts as status=pending — admin
    must approve. If we can prove the user has a delivered order containing
    this product, we set verified=true (the storefront shows a badge)."""
    email = (user.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=401, detail="Login required to review")

    # Verified-buyer check: any order for this email that is delivered AND
    # contains the given product_id.
    is_verified = False
    if payload.product_id:
        q = {"customer.email": email, "status": "delivered", "items.product_id": payload.product_id}
        if await db.orders.count_documents(q) > 0:
            is_verified = True
        # Prevent duplicate review from same buyer on same product
        if await db.reviews.count_documents({"user_email": email, "product_id": payload.product_id, "status": {"$ne": "rejected"}}) > 0:
            raise HTTPException(status_code=409, detail="You have already reviewed this product")

    author = (payload.author_name or user.get("name") or email.split("@")[0]).strip()[:80]
    review = Review(
        author=author,
        location=(payload.location or "").strip()[:80] or "India",
        rating=int(payload.rating),
        title=payload.title.strip(),
        body=payload.body.strip(),
        image=payload.image,
        verified=is_verified,
        featured=False,
        status="pending",
        product_id=payload.product_id,
        user_email=email,
    )
    await db.reviews.insert_one(review.model_dump())
    # Fire-and-forget admin notification (see notify_admins helper defined below).
    try:
        asyncio.create_task(notify_admins_event(
            kind="review_pending",
            subject=f"New review pending approval — {review.rating}★ from {author}",
            html_body=(
                f"<p><strong>{_esc(author)}</strong> ({_esc(email)}) submitted a "
                f"{int(review.rating)}-star review titled <em>{_esc(review.title)}</em>.</p>"
                f"<p>{_esc(review.body[:500])}</p>"
                f"<p>Go to <b>Admin → Reviews → Pending</b> to approve or reject.</p>"
            ),
        ))
    except Exception:
        pass
    return review


class ReviewModerateIn(BaseModel):
    status: str  # approved | rejected


@api_router.patch("/admin/reviews/{review_id}/moderate", response_model=Review)
async def admin_moderate_review(review_id: str, payload: ReviewModerateIn, admin=Depends(get_current_admin)):
    """Approve or reject a pending customer review (Task 5)."""
    if payload.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="status must be approved or rejected")
    doc = await db.reviews.find_one({"id": review_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Review not found")
    await db.reviews.update_one({"id": review_id}, {"$set": {"status": payload.status}})
    doc["status"] = payload.status
    return Review(**doc)


@api_router.post("/orders", response_model=dict)
async def create_order(payload: OrderIn):
    # If coupon provided, validate on server too (defence in depth)
    if payload.coupon_code:
        coupon = await db.coupons.find_one({"code": payload.coupon_code.upper().strip(), "active": True}, {"_id": 0})
        if not coupon:
            raise HTTPException(status_code=400, detail="Invalid coupon code.")
        _err = _coupon_availability_error(coupon, payload.subtotal_inr)
        if _err:
            raise HTTPException(status_code=400, detail=_err)
    order = Order(**payload.model_dump())
    if payload.coupon_code:
        order.coupon_code = payload.coupon_code.upper().strip()

    # --- Phase A (Jul 2025 · pending fix): snapshot product + variant details into each order item ---
    # Ensures the Admin Orders detail view (and customer receipt) shows the exact product bought
    # even if the product is later renamed, re-priced, or removed.
    snapshotted_items = []
    _low_stock_events = []  # (product_name, remaining_stock) — for admin low-stock notify
    for it in order.items:
        prod = await db.products.find_one({"id": it.product_id}, {"_id": 0})
        variant = None
        if prod:
            for v in (prod.get("variants") or []):
                if v.get("key") == it.variant_key:
                    variant = v
                    break
        # Prefer variant-level overrides, else fall back to product-level
        v_price = (variant or {}).get("price_inr")
        v_mrp = (variant or {}).get("mrp_inr")
        v_image = (variant or {}).get("image") or None
        v_label = (variant or {}).get("label") or None
        v_hex = (variant or {}).get("hex") or None
        v_size = (variant or {}).get("size") or (prod or {}).get("size")
        price_inr = int(v_price if v_price is not None else (prod or {}).get("price_inr") or 0)
        mrp_inr = int(v_mrp if v_mrp is not None else (prod or {}).get("mrp_inr") or 0)
        # --- Task 3: resolve selected_options → labels + cumulative price delta ---
        opt_labels: Dict[str, str] = {}
        opt_delta_inr = 0
        variation_options = (prod or {}).get("variation_options") or []
        for opt in variation_options:
            okey = opt.get("key")
            selected_val_key = (it.selected_options or {}).get(okey) if it.selected_options else None
            if not selected_val_key:
                if opt.get("required"):
                    raise HTTPException(status_code=400, detail=f"Option '{opt.get('label') or okey}' is required for {(prod or {}).get('name')}")
                continue
            match = next((v for v in (opt.get("values") or []) if v.get("key") == selected_val_key), None)
            if match:
                opt_labels[opt.get("label") or okey] = match.get("label") or selected_val_key
                opt_delta_inr += int(match.get("price_delta_inr") or 0)
        it.selected_options_labels = opt_labels
        it.options_price_delta_inr = opt_delta_inr
        it.product_name = (prod or {}).get("name")
        it.product_slug = (prod or {}).get("slug")
        it.product_image = v_image or (prod or {}).get("hero_image")
        it.product_category = (prod or {}).get("category")
        it.product_hsn_code = (prod or {}).get("hsn_code")
        # Batch 5 — prefer variant-level SKU / weight / dims when set, else fall back to product-level
        it.product_sku = (variant or {}).get("sku") or (prod or {}).get("sku")
        it.weight_grams = (variant or {}).get("weight_grams") if (variant or {}).get("weight_grams") is not None else (prod or {}).get("weight_grams")
        it.length_cm = (variant or {}).get("length_cm") if (variant or {}).get("length_cm") is not None else (prod or {}).get("length_cm")
        it.width_cm = (variant or {}).get("width_cm") if (variant or {}).get("width_cm") is not None else (prod or {}).get("width_cm")
        it.height_cm = (variant or {}).get("height_cm") if (variant or {}).get("height_cm") is not None else (prod or {}).get("height_cm")
        it.variant_label = v_label
        it.variant_hex = v_hex
        it.variant_image = v_image
        it.size = v_size
        effective_unit_price = price_inr + opt_delta_inr
        it.price_inr = effective_unit_price
        it.mrp_inr = mrp_inr + opt_delta_inr if mrp_inr else mrp_inr
        it.line_total_inr = effective_unit_price * int(it.quantity or 1)
        snapshotted_items.append(it)
        # Track low-stock candidates for post-insert notification (Task 6)
        remaining = int((prod or {}).get("stock_count") or 0) - int(it.quantity or 1)
        if remaining <= 3 and (prod or {}).get("name"):
            _low_stock_events.append(((prod or {}).get("name"), max(remaining, 0)))
    order.items = snapshotted_items

    # --- Phase A (Jul 2025): compute GST authoritatively (server is source of truth) ---
    # Treatment = EXCLUSIVE — GST is added on top of the shown price (standard e-commerce behaviour).
    try:
        tax = await compute_taxes_for_cart(
            [i.model_dump() for i in payload.items],
            ship_state=(order.customer.state if getattr(order.customer, "state", None) else None),
            treatment="exclusive",
        )
        order.gst_total_inr = int(tax.get("gst_total_inr") or 0)
        order.cgst_inr = int(tax.get("cgst_inr") or 0)
        order.sgst_inr = int(tax.get("sgst_inr") or 0)
        order.igst_inr = int(tax.get("igst_inr") or 0)
        order.gst_lines = tax.get("gst_lines") or []
        order.gst_treatment = "exclusive"
    except Exception as e:
        logging.warning(f"GST computation failed on order create: {e}")
    if payload.payment_method == "razorpay":
        if not rzp_client:
            raise HTTPException(status_code=500, detail="Razorpay not configured")
        # --- Phase A (Jul 2025): recompute total server-side incl. GST (exclusive) ---
        # total = subtotal - discount + shipping + gst_total (GST is added on top)
        server_total = max(
            0,
            int(payload.subtotal_inr)
            - int(payload.discount_inr or 0)
            + int(payload.shipping_inr)
            + int(order.gst_total_inr or 0),
        )
        if abs(server_total - int(payload.total_inr)) > 1:
            logging.warning(
                f"Order total mismatch (client={payload.total_inr}, server={server_total}). Trusting server."
            )
            order.total_inr = server_total
        rzp_order = rzp_client.order.create({
            "amount": int(order.total_inr) * 100,
            "currency": "INR",
            "receipt": order.order_number[:40],
            "payment_capture": 1,
        })
        order.razorpay_order_id = rzp_order["id"]
    else:
        order.status = "confirmed"
        # For COD orders, also recompute total incl. GST
        server_total = max(
            0,
            int(payload.subtotal_inr)
            - int(payload.discount_inr or 0)
            + int(payload.shipping_inr)
            + int(order.gst_total_inr or 0),
        )
        order.total_inr = server_total
    await db.orders.insert_one(order.model_dump())
    # Fire "order placed" email (fire-and-forget)
    try:
        asyncio.create_task(send_order_email(order.model_dump(), "placed"))
    except Exception as _e:
        logging.warning(f"Order-placed email queue failed: {_e}")
    # Task 6: notify every admin of the new order.
    try:
        _od = order.model_dump()
        _cust = _od.get('customer') or {}
        asyncio.create_task(notify_admins_event(
            kind="order_new",
            subject=f"New order {_od.get('order_number')} — ₹{_od.get('total_inr', 0):,}",
            html_body=(
                f"<p><b>{_esc(_cust.get('name',''))}</b> "
                f"({_esc(_cust.get('email',''))}) placed an order.</p>"
                f"<p>Items: {len(_od.get('items', []))} · Payment: {_esc(_od.get('payment_method'))}</p>"
                f"<p>Open <b>Admin → Orders</b> to view and process.</p>"
            ),
        ))
    except Exception as _e:
        logging.warning(f"Admin new-order notify failed: {_e}")
    # Task 6: low-stock notifications (fire once per product per order)
    if _low_stock_events:
        try:
            lines = "".join(
                f"<li><b>{_esc(name)}</b> — {int(remaining)} left in stock</li>"
                for name, remaining in _low_stock_events
            )
            asyncio.create_task(notify_admins_event(
                kind="low_stock",
                subject=f"Low stock alert — {len(_low_stock_events)} product(s) at or below 3 units",
                html_body=(
                    f"<p>The following product(s) just crossed the low-stock threshold after order "
                    f"<b>{_esc(order.order_number)}</b>:</p><ul>{lines}</ul>"
                    f"<p>Open <b>Admin → Inventory</b> to top up.</p>"
                ),
            ))
        except Exception as _e:
            logging.warning(f"Admin low-stock notify failed: {_e}")
    return {
        "order": order.model_dump(),
        "razorpay_key_id": RZP_KEY if payload.payment_method == "razorpay" else None,
    }


@api_router.post("/orders/verify")
async def verify_order(payload: RzpVerify):
    order = await db.orders.find_one({"order_number": payload.order_number}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    # verify signature
    body = f"{payload.razorpay_order_id}|{payload.razorpay_payment_id}".encode()
    expected = hmac.new(RZP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, payload.razorpay_signature):
        await db.orders.update_one({"order_number": payload.order_number}, {"$set": {"status": "payment_failed"}})
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    await db.orders.update_one(
        {"order_number": payload.order_number},
        {"$set": {"status": "confirmed", "razorpay_payment_id": payload.razorpay_payment_id}},
    )
    # Phase B: decrement stock on successful client-side verification (idempotent guard via status change)
    if order.get("status") != "confirmed":
        for it in order.get("items", []):
            try:
                await db.products.update_one(
                    {"id": it.get("product_id")},
                    {"$inc": {"stock_count": -int(it.get("quantity", 1))}},
                )
            except Exception as _e:
                logging.warning(f"Stock decrement failed for {it}: {_e}")
    # Increment coupon usage counter on successful verification
    if order.get("coupon_code"):
        await db.coupons.update_one({"code": order["coupon_code"]}, {"$inc": {"used_count": 1}})
    return {"status": "confirmed", "order_number": payload.order_number}


# ---------- RAZORPAY WEBHOOK (Phase B) ---------- #
# Configure in Razorpay Dashboard → Settings → Webhooks:
#   URL:    https://<your-render-backend>/api/razorpay/webhook
#   Secret: whatever you paste into env var RAZORPAY_WEBHOOK_SECRET
#   Events: payment.captured, payment.failed
@api_router.post("/razorpay/webhook")
async def razorpay_webhook(request: Request):
    raw = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not RZP_WEBHOOK_SECRET:
        logging.error("Razorpay webhook received but RAZORPAY_WEBHOOK_SECRET is not set")
        raise HTTPException(status_code=500, detail="Webhook secret not configured on server")
    expected = hmac.new(RZP_WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    try:
        payload_json = json.loads(raw.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = payload_json.get("event", "")
    entity = ((payload_json.get("payload") or {}).get("payment") or {}).get("entity") or {}
    rzp_order_id = entity.get("order_id")
    rzp_payment_id = entity.get("id")

    if not rzp_order_id:
        return {"status": "ignored", "reason": "no order_id"}

    order = await db.orders.find_one({"razorpay_order_id": rzp_order_id}, {"_id": 0})
    if not order:
        # Webhook may arrive before order finishes writing OR for a stale order. Ack to prevent retries.
        return {"status": "ignored", "reason": "order not found", "razorpay_order_id": rzp_order_id}

    if event == "payment.captured":
        # Only apply stock/coupon side-effects once; guard via status change.
        was_confirmed = order.get("status") == "confirmed"
        await db.orders.update_one(
            {"razorpay_order_id": rzp_order_id},
            {"$set": {"status": "confirmed", "razorpay_payment_id": rzp_payment_id, "tracking_updated_at": now_iso()}},
        )
        if not was_confirmed:
            for it in order.get("items", []):
                try:
                    await db.products.update_one(
                        {"id": it.get("product_id")},
                        {"$inc": {"stock_count": -int(it.get("quantity", 1))}},
                    )
                except Exception as _e:
                    logging.warning(f"Webhook stock decrement failed for {it}: {_e}")
            if order.get("coupon_code"):
                await db.coupons.update_one({"code": order["coupon_code"]}, {"$inc": {"used_count": 1}})
    elif event == "payment.failed":
        await db.orders.update_one(
            {"razorpay_order_id": rzp_order_id},
            {"$set": {"status": "payment_failed"}},
        )
    else:
        # Unhandled events (order.paid, refunds, etc.) — ack without action for now.
        return {"status": "ok", "event": event, "handled": False}

    return {"status": "ok", "event": event, "handled": True, "order_number": order.get("order_number")}


@api_router.get("/orders/{order_number}", response_model=Order)
async def get_order(order_number: str):
    doc = await db.orders.find_one({"order_number": order_number}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Order not found")
    enriched = await _enrich_order_items([doc])
    return enriched[0]


@api_router.post("/b2b/leads", response_model=B2BLead)
@limiter.limit("5/minute")
async def create_b2b_lead(request: Request, payload: B2BLeadIn):
    lead = B2BLead(**payload.model_dump())
    await db.b2b_leads.insert_one(lead.model_dump())
    return lead


# ---------- ADMIN ROUTES ---------- #
@api_router.post("/admin/login")
@limiter.limit("10/minute")
async def admin_login(request: Request, payload: AdminLogin):
    admin = await db.admins.find_one({"email": payload.email})
    if not admin or not bcrypt.checkpw(payload.password.encode(), admin["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": create_token(payload.email, role="admin"), "email": payload.email}


@api_router.get("/admin/me")
async def admin_me(admin=Depends(get_current_admin)):
    return admin


@api_router.get("/admin/stats")
async def admin_stats(admin=Depends(get_current_admin)):
    orders = await db.orders.find({}, {"_id": 0}).to_list(1000)
    confirmed = [o for o in orders if o.get("status") not in ("pending_payment", "cancelled", "payment_failed")]
    revenue = sum(o["total_inr"] for o in confirmed)
    return {
        "orders_total": len(orders),
        "orders_confirmed": len(confirmed),
        "revenue_inr": revenue,
        "leads_new": await db.b2b_leads.count_documents({"status": "new"}),
        "products_total": await db.products.count_documents({}),
        "reviews_total": await db.reviews.count_documents({}),
    }


@api_router.post("/admin/products", response_model=Product)
async def create_product(payload: ProductIn, admin=Depends(get_current_admin)):
    prod = Product(**payload.model_dump())
    await db.products.insert_one(prod.model_dump())
    return prod


# ------------- Batch 8 · Reference-product seed (idempotent) -----------------
# One-click "load me a fully-filled template product" for the owner. Uses the
# same PRODUCT payload as backend/seed_reference_product.py so the CLI seed
# and the in-app button stay in sync — but runs against the CURRENT DB so it
# works on prod Atlas without any shell access.
@api_router.post("/admin/products/seed-reference")
async def admin_seed_reference_product(admin=Depends(get_current_admin)):
    try:
        from seed_reference_product import PRODUCT as REF_PRODUCT  # noqa: E402
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"reference template unavailable: {e}")
    existing = await db.products.find_one({"slug": REF_PRODUCT["slug"]}, {"_id": 0})
    if existing:
        merged = {**existing, **REF_PRODUCT, "id": existing["id"]}
        await db.products.update_one({"id": existing["id"]}, {"$set": merged})
        return {"ok": True, "action": "updated", "id": existing["id"], "slug": REF_PRODUCT["slug"]}
    prod = Product(**ProductIn(**REF_PRODUCT).model_dump())
    await db.products.insert_one(prod.model_dump())
    return {"ok": True, "action": "created", "id": prod.id, "slug": prod.slug}



@api_router.put("/admin/products/{product_id}", response_model=Product)
async def update_product(product_id: str, payload: ProductIn, background_tasks: BackgroundTasks, admin=Depends(get_current_admin)):
    existing = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    updated = {**existing, **payload.model_dump()}
    await db.products.update_one({"id": product_id}, {"$set": updated})
    # Batch 5 — clean up any Cloudinary assets the admin removed
    old_urls = _extract_cloudinary_urls(existing)
    new_urls = _extract_cloudinary_urls(updated)
    background_tasks.add_task(_destroy_url_diff, old_urls, new_urls)
    return updated


@api_router.delete("/admin/products/{product_id}")
async def delete_product(product_id: str, background_tasks: BackgroundTasks, admin=Depends(get_current_admin)):
    existing = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Not found")
    await db.products.delete_one({"id": product_id})
    # Batch 5 — nuke every Cloudinary asset attached to this product
    background_tasks.add_task(_destroy_url_diff, _extract_cloudinary_urls(existing), set())
    return {"deleted": True}


async def _enrich_order_items(orders: list) -> list:
    """Backfill snapshot fields onto legacy order items so admin/customer views always show
    a name + image + variant even for orders created before the snapshot logic existed.
    Purely read-only enrichment — does NOT mutate the DB.
    """
    # Collect unique product_ids to load once
    ids = set()
    for o in orders:
        for it in (o.get("items") or []):
            if not it.get("product_name") and it.get("product_id"):
                ids.add(it["product_id"])
    if not ids:
        return orders
    prods = {p["id"]: p for p in await db.products.find({"id": {"$in": list(ids)}}, {"_id": 0}).to_list(1000)}
    for o in orders:
        for it in (o.get("items") or []):
            if it.get("product_name"):
                continue
            prod = prods.get(it.get("product_id"))
            if not prod:
                continue
            variant = None
            for v in (prod.get("variants") or []):
                if v.get("key") == it.get("variant_key"):
                    variant = v
                    break
            v_price = (variant or {}).get("price_inr")
            v_mrp = (variant or {}).get("mrp_inr")
            v_image = (variant or {}).get("image") or None
            v_label = (variant or {}).get("label") or None
            v_hex = (variant or {}).get("hex") or None
            v_size = (variant or {}).get("size") or prod.get("size")
            price_inr = int(v_price if v_price is not None else prod.get("price_inr") or 0)
            mrp_inr = int(v_mrp if v_mrp is not None else prod.get("mrp_inr") or 0)
            qty = int(it.get("quantity") or 1)
            it["product_name"] = prod.get("name")
            it["product_slug"] = prod.get("slug")
            it["product_image"] = v_image or prod.get("hero_image")
            it["product_category"] = prod.get("category")
            it["product_hsn_code"] = prod.get("hsn_code")
            it["product_sku"] = prod.get("sku")
            it["variant_label"] = v_label
            it["variant_hex"] = v_hex
            it["variant_image"] = v_image
            it["size"] = v_size
            it["price_inr"] = price_inr
            it["mrp_inr"] = mrp_inr
            it["line_total_inr"] = price_inr * qty
    return orders


@api_router.get("/admin/orders", response_model=List[Order])
async def admin_list_orders(admin=Depends(get_current_admin)):
    orders = await db.orders.find({}, {"_id": 0}).sort("created_at", -1).to_list(2000)
    return await _enrich_order_items(orders)


@api_router.patch("/admin/orders/{order_number}")
async def admin_update_order(order_number: str, payload: OrderStatusUpdate, admin=Depends(get_current_admin)):
    prev = await db.orders.find_one({"order_number": order_number}, {"_id": 0})
    if not prev:
        raise HTTPException(status_code=404, detail="Not found")
    update = {"status": payload.status}
    if payload.status == "delivered":
        update["delivered_at"] = now_iso()
    await db.orders.update_one({"order_number": order_number}, {"$set": update})
    # Fire transactional emails on status transitions
    new = {**prev, **update}
    try:
        if payload.status == "shipped" and prev.get("status") != "shipped":
            asyncio.create_task(send_order_email(new, "dispatched"))
        elif payload.status == "cancelled" and prev.get("status") != "cancelled":
            asyncio.create_task(send_order_email(new, "cancelled"))
        # Task 6 — payment_failed is worth alerting admins on
        elif payload.status == "payment_failed" and prev.get("status") != "payment_failed":
            asyncio.create_task(notify_admins_event(
                kind="payment_failed",
                subject=f"Payment FAILED for order {order_number}",
                html_body=(
                    f"<p>Order <b>{_esc(order_number)}</b> flipped to payment_failed.</p>"
                    f"<p>Customer: {_esc((prev.get('customer') or {}).get('email',''))}</p>"
                    f"<p>Amount: ₹{int(prev.get('total_inr',0)):,}</p>"
                ),
            ))
    except Exception as _e:
        logging.warning(f"Order status email failed: {_e}")
    return {"ok": True}


# ============================================================================
# TASK 8 — GST BUSINESS SETTINGS + INVOICE PDF DOWNLOAD (single + bulk)
# ============================================================================
class BusinessSettings(BaseModel):
    """One-row settings doc for the ArtyFex business identity that appears on
    every GST tax invoice. Stored under db.settings with _key = 'business'.
    """
    model_config = ConfigDict(extra="ignore")
    legal_name: str = "ArtyFex Atelier"
    trade_name: str = "ArtyFex"
    gstin: str = ""              # 15-char GSTIN
    pan: str = ""
    address: str = "Mumbai, Maharashtra, India"
    state: str = "Maharashtra"   # supplier state — determines CGST/SGST vs IGST
    email: str = ""
    phone: str = ""
    website: str = "https://www.artyfex.in"
    hsn_default: str = ""
    updated_at: str = Field(default_factory=now_iso)


async def _get_business_settings() -> dict:
    doc = await db.settings.find_one({"_key": "business"}, {"_id": 0, "_key": 0})
    if not doc:
        doc = BusinessSettings().model_dump()
    return doc


@api_router.get("/admin/settings/business", response_model=BusinessSettings)
async def admin_get_business(admin=Depends(get_current_admin)):
    return BusinessSettings(**(await _get_business_settings()))


@api_router.put("/admin/settings/business", response_model=BusinessSettings)
async def admin_put_business(payload: BusinessSettings, admin=Depends(get_current_admin)):
    doc = payload.model_dump()
    doc["updated_at"] = now_iso()
    await db.settings.update_one({"_key": "business"}, {"$set": {"_key": "business", **doc}}, upsert=True)
    return BusinessSettings(**doc)


async def _ensure_invoice_number(order: dict) -> dict:
    """Assign a running invoice number when missing (idempotent).

    Format: ARF/FY24-25/000123 (Indian fiscal year Apr-Mar).
    Runs a per-fiscal-year counter kept in db.settings under _key='inv_counter_FY<yy-yy>'.
    """
    if order.get("invoice_number"):
        return order
    # Fiscal year (Apr 1 – Mar 31) — India
    now = datetime.now()
    if now.month >= 4:
        fy_key = f"{now.year % 100:02d}-{(now.year + 1) % 100:02d}"
    else:
        fy_key = f"{(now.year - 1) % 100:02d}-{now.year % 100:02d}"
    counter_key = f"inv_counter_FY{fy_key}"
    counter = await db.settings.find_one_and_update(
        {"_key": counter_key},
        {"$inc": {"seq": 1}, "$setOnInsert": {"_key": counter_key}},
        upsert=True,
        return_document=True,
    )
    seq = int(counter.get("seq") or 1)
    inv_number = f"ARF/FY{fy_key}/{seq:06d}"
    inv_date = now_iso()
    await db.orders.update_one(
        {"order_number": order["order_number"]},
        {"$set": {"invoice_number": inv_number, "invoice_date": inv_date}},
    )
    order["invoice_number"] = inv_number
    order["invoice_date"] = inv_date
    return order


@api_router.get("/admin/orders/{order_number}/invoice.pdf")
async def admin_download_invoice(order_number: str, admin=Depends(get_current_admin)):
    """Download the GST tax invoice for a single order as PDF."""
    order = await db.orders.find_one({"order_number": order_number}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order = await _ensure_invoice_number(order)
    business = await _get_business_settings()
    try:
        from invoice_pdf import build_invoice_pdf
        pdf_bytes = build_invoice_pdf(order, business)
    except Exception as e:
        logging.exception("Invoice PDF build failed")
        raise HTTPException(status_code=500, detail=f"Invoice generation failed: {e}")
    fname = f"{order.get('invoice_number','invoice').replace('/', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@api_router.get("/admin/orders/invoices.zip")
async def admin_download_invoices_zip(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    admin=Depends(get_current_admin),
):
    """Bulk-download every invoice matching the given date range / status as a zip.
    Query params (all optional):
      date_from  ISO date (inclusive)  e.g. 2025-04-01
      date_to    ISO date (inclusive)  e.g. 2026-03-31
      status     e.g. 'delivered' — restricts to a single status
    """
    import zipfile
    from invoice_pdf import build_invoice_pdf
    q: dict = {}
    if status:
        q["status"] = status
    if date_from or date_to:
        rng: dict = {}
        if date_from:
            rng["$gte"] = date_from
        if date_to:
            # date_to inclusive → append end-of-day
            rng["$lte"] = date_to + "T23:59:59.999Z"
        q["created_at"] = rng
    orders = await db.orders.find(q, {"_id": 0}).sort("created_at", -1).to_list(5000)
    if not orders:
        raise HTTPException(status_code=404, detail="No orders match those filters")
    business = await _get_business_settings()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for order in orders:
            order = await _ensure_invoice_number(order)
            try:
                pdf_bytes = build_invoice_pdf(order, business)
            except Exception as e:
                logging.warning(f"Skipping invoice for {order.get('order_number')}: {e}")
                continue
            safe = (order.get("invoice_number") or order.get("order_number") or "invoice").replace("/", "_")
            zf.writestr(f"{safe}.pdf", pdf_bytes)
    buf.seek(0)
    label = "invoices"
    if date_from or date_to:
        label += f"_{date_from or 'all'}_to_{date_to or 'all'}"
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{label}.zip"'},
    )


@api_router.get("/admin/leads", response_model=List[B2BLead])
async def admin_list_leads(admin=Depends(get_current_admin)):
    return await db.b2b_leads.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)


@api_router.patch("/admin/leads/{lead_id}")
async def admin_update_lead(lead_id: str, payload: B2BStatusUpdate, admin=Depends(get_current_admin)):
    res = await db.b2b_leads.update_one({"id": lead_id}, {"$set": {"status": payload.status}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@api_router.post("/admin/reviews", response_model=Review)
async def admin_create_review(payload: ReviewIn, admin=Depends(get_current_admin)):
    """Admin creates a review directly. Auto-approved (Task 5)."""
    r = Review(**payload.model_dump())
    r.status = "approved"
    await db.reviews.insert_one(r.model_dump())
    return r


@api_router.get("/admin/reviews", response_model=List[Review])
async def admin_list_reviews(status: Optional[str] = None, admin=Depends(get_current_admin)):
    """Admin listing — supports ?status=pending|approved|rejected. No filter = all."""
    q: dict = {}
    if status in ("pending", "approved", "rejected"):
        q["status"] = status
    return await db.reviews.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)


class ReviewFeaturedIn(BaseModel):
    featured: bool


@api_router.patch("/admin/reviews/{review_id}", response_model=Review)
async def admin_update_review_featured(review_id: str, payload: ReviewFeaturedIn, admin=Depends(get_current_admin)):
    res = await db.reviews.update_one({"id": review_id}, {"$set": {"featured": payload.featured}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Review not found")
    doc = await db.reviews.find_one({"id": review_id}, {"_id": 0})
    return doc


@api_router.delete("/admin/reviews/{review_id}")
async def admin_delete_review(review_id: str, admin=Depends(get_current_admin)):
    res = await db.reviews.delete_one({"id": review_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"deleted": True}


@api_router.get("/admin/returns")
async def admin_list_returns(admin=Depends(get_current_admin)):
    returns = await db.returns.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    # Enrich with basic order info
    for r in returns:
        order = await db.orders.find_one(
            {"order_number": r["order_number"]},
            {"_id": 0, "customer.name": 1, "customer.phone": 1, "total_inr": 1, "delivered_at": 1, "status": 1},
        )
        if order:
            r["order_customer_name"] = order.get("customer", {}).get("name")
            r["order_customer_phone"] = order.get("customer", {}).get("phone")
            r["order_total_inr"] = order.get("total_inr")
            r["order_delivered_at"] = order.get("delivered_at")
            r["order_status"] = order.get("status")
    return returns


@api_router.patch("/admin/returns/{return_id}")
async def admin_update_return(return_id: str, payload: ReturnStatusUpdate, admin=Depends(get_current_admin)):
    allowed = {"approved", "rejected", "received", "refunded"}
    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail=f"Status must be one of {sorted(allowed)}")
    update = {
        "status": payload.status,
        "reviewed_at": now_iso(),
        "reviewed_by": admin["email"],
    }
    if payload.is_genuine is not None:
        update["is_genuine"] = payload.is_genuine
    if payload.admin_notes is not None:
        update["admin_notes"] = payload.admin_notes
    res = await db.returns.update_one({"id": return_id}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Return not found")
    # Fire customer email on approved / rejected (fire-and-forget)
    if payload.status in ("approved", "rejected"):
        rr = await db.returns.find_one({"id": return_id}, {"_id": 0})
        if rr:
            order = await db.orders.find_one({"order_number": rr["order_number"]}, {"_id": 0})
            customer_name = (order or {}).get("customer", {}).get("name", "there")
            subject, html = render_return_email(
                status=payload.status,
                customer_name=customer_name,
                order_number=rr["order_number"],
                admin_notes=rr.get("admin_notes"),
                is_genuine=rr.get("is_genuine"),
            )
            asyncio.create_task(send_email(rr["user_email"], subject, html))
    return {"ok": True}


# ---------- WISHLIST ---------- #
class WishlistToggleOut(BaseModel):
    product_id: str
    action: str  # added | removed


@api_router.get("/me/wishlist")
async def my_wishlist(user=Depends(get_current_user)):
    items = await db.wishlist.find({"user_email": user["email"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    # Enrich with product data
    result = []
    for it in items:
        prod = await db.products.find_one({"id": it["product_id"]}, {"_id": 0})
        if prod:
            result.append({"product_id": it["product_id"], "added_at": it["created_at"], "product": prod})
    return result


@api_router.post("/me/wishlist/{product_id}")
async def add_to_wishlist(product_id: str, user=Depends(get_current_user)):
    prod = await db.products.find_one({"id": product_id}, {"_id": 0, "id": 1})
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    existing = await db.wishlist.find_one({"user_email": user["email"], "product_id": product_id})
    if existing:
        return {"product_id": product_id, "action": "already_saved"}
    await db.wishlist.insert_one({
        "id": str(uuid.uuid4()), "user_email": user["email"],
        "product_id": product_id, "created_at": now_iso(),
    })
    return {"product_id": product_id, "action": "added"}


@api_router.delete("/me/wishlist/{product_id}")
async def remove_from_wishlist(product_id: str, user=Depends(get_current_user)):
    await db.wishlist.delete_one({"user_email": user["email"], "product_id": product_id})
    return {"product_id": product_id, "action": "removed"}


# ---------- USER (CUSTOMER) ROUTES ---------- #
@api_router.post("/auth/signup")
@limiter.limit("5/minute")
async def user_signup(request: Request, payload: UserSignup):
    if await db.users.find_one({"email": payload.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    pw_hash = bcrypt.hashpw(payload.password.encode(), bcrypt.gensalt()).decode()
    user = {
        "id": str(uuid.uuid4()), "name": payload.name, "email": payload.email,
        "phone": payload.phone or "", "password_hash": pw_hash, "created_at": now_iso(),
    }
    await db.users.insert_one(user)
    return {"token": create_token(payload.email, role="user"),
            "user": {"name": user["name"], "email": user["email"], "phone": user["phone"]}}


@api_router.post("/auth/login")
@limiter.limit("10/minute")
async def user_login(request: Request, payload: UserLogin):
    user = await db.users.find_one({"email": payload.email})
    if not user or not bcrypt.checkpw(payload.password.encode(), user["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.get("blocked"):
        raise HTTPException(status_code=403, detail="This account has been blocked. Please contact ArtyFex support.")
    return {"token": create_token(payload.email, role="user"),
            "user": {"name": user["name"], "email": user["email"], "phone": user.get("phone", "")}}


@api_router.get("/auth/me")
async def user_me(user=Depends(get_current_user)):
    return {"name": user["name"], "email": user["email"], "phone": user.get("phone", ""), "picture": user.get("picture")}


# ---------- GOOGLE OAUTH (Custom, Phase B) ----------
# Server-side OAuth 2.0 code flow. redirect_uri is derived from the INCOMING request
# (honors X-Forwarded-Proto / X-Forwarded-Host that Northflank/Vercel add), so it
# works on prod, preview, and local WITHOUT setting BACKEND_PUBLIC_URL/FRONTEND_PUBLIC_URL.
# `BACKEND_PUBLIC_URL` remains an optional explicit override if you want to force one.
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

# Front-end origins we are allowed to redirect the browser back to after OAuth.
# Prevents open-redirect abuse; anything outside falls back to FRONTEND_PUBLIC_URL.
ALLOWED_FRONTEND_ORIGINS = {
    "https://www.artyfex.in",
    "https://artyfex.in",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
}


def _resolve_backend_base(request: Request) -> str:
    """Return the public base URL of THIS backend, e.g. https://api.artyfex.in.
    Priority: explicit env override → X-Forwarded-* (proxy) → request.url."""
    override = os.environ.get('BACKEND_PUBLIC_URL', '').strip()
    if override:
        return override.rstrip('/')
    proto = (request.headers.get('x-forwarded-proto') or request.url.scheme or 'http').split(',')[0].strip()
    host = (request.headers.get('x-forwarded-host') or request.headers.get('host') or request.url.netloc).split(',')[0].strip()
    return f"{proto}://{host}".rstrip('/')


def _resolve_frontend_base(origin_hint: Optional[str], referer: Optional[str]) -> str:
    """Pick the front-end base URL to bounce back to. Only allow known origins."""
    for candidate in (origin_hint, referer):
        if not candidate:
            continue
        # Strip any path from referer → keep only scheme+host
        try:
            from urllib.parse import urlparse
            u = urlparse(candidate)
            if u.scheme and u.netloc:
                origin = f"{u.scheme}://{u.netloc}"
                if origin in ALLOWED_FRONTEND_ORIGINS:
                    return origin
        except Exception:
            pass
    # Fallback to explicit env override, else the canonical prod domain
    return (os.environ.get('FRONTEND_PUBLIC_URL', '').strip() or "https://www.artyfex.in").rstrip('/')


def _google_redirect_uri(request: Request) -> str:
    return f"{_resolve_backend_base(request)}/api/auth/google/callback"


@api_router.get("/auth/google/login")
async def google_login(
    request: Request,
    next: Optional[str] = "/account",
    origin: Optional[str] = None,
):
    """Kick off Google OAuth. Redirects the browser to Google's consent screen."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth not configured on server")
    # Resolve the front-end origin now (from ?origin= query, Referer header, or Origin header).
    # We embed it in state so the callback knows where to bounce back to.
    frontend_base = _resolve_frontend_base(
        origin_hint=origin or request.headers.get('origin'),
        referer=request.headers.get('referer'),
    )
    state = pyjwt.encode(
        {
            "next": next or "/account",
            "fe": frontend_base,
            "nonce": uuid.uuid4().hex,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": _google_redirect_uri(request),
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "include_granted_scopes": "true",
        "prompt": "select_account",
        "state": state,
    }
    return RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{urlencode(params)}", status_code=302)


def _frontend_callback_redirect(frontend_base: str, hash_params: dict) -> RedirectResponse:
    return RedirectResponse(
        url=f"{frontend_base.rstrip('/')}/auth/callback#{urlencode(hash_params)}",
        status_code=302,
    )


@api_router.get("/auth/google/callback")
async def google_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
):
    """Google redirects back here. We exchange the code, upsert the user, issue our JWT."""
    # Decode state early so we know where to bounce (even on errors).
    frontend_base = "https://www.artyfex.in"
    next_path = "/account"
    state_valid = False
    try:
        st = pyjwt.decode(state or "", JWT_SECRET, algorithms=["HS256"])
        next_path = st.get("next") or "/account"
        fe = st.get("fe")
        if fe and fe in ALLOWED_FRONTEND_ORIGINS:
            frontend_base = fe
        state_valid = True
    except Exception:
        pass  # frontend_base stays at canonical prod fallback

    if error:
        return _frontend_callback_redirect(frontend_base, {"error": error})
    if not state_valid:
        return _frontend_callback_redirect(frontend_base, {"error": "invalid_state"})
    if not code:
        return _frontend_callback_redirect(frontend_base, {"error": "missing_code"})
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return _frontend_callback_redirect(frontend_base, {"error": "server_not_configured"})

    # Exchange authorization code for access token
    try:
        async with httpx.AsyncClient(timeout=15) as http:
            tok_resp = await http.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": _google_redirect_uri(request),
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if tok_resp.status_code != 200:
                logging.error(f"Google token exchange failed: {tok_resp.status_code} {tok_resp.text[:200]}")
                return _frontend_callback_redirect(frontend_base, {"error": "token_exchange_failed"})
            tok = tok_resp.json()
            access_token = tok.get("access_token")
            if not access_token:
                return _frontend_callback_redirect(frontend_base, {"error": "no_access_token"})

            ui_resp = await http.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if ui_resp.status_code != 200:
                logging.error(f"Google userinfo failed: {ui_resp.status_code} {ui_resp.text[:200]}")
                return _frontend_callback_redirect(frontend_base, {"error": "userinfo_failed"})
            info = ui_resp.json()
    except Exception:
        logging.exception("Google OAuth exchange error")
        return _frontend_callback_redirect(frontend_base, {"error": "exchange_error"})

    email = (info.get("email") or "").lower()
    name = info.get("name") or (email.split("@")[0] if email else "user")
    picture = info.get("picture")
    if not email:
        return _frontend_callback_redirect(frontend_base, {"error": "no_email"})

    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        upd = {"name": name or existing.get("name"), "auth_provider": "google"}
        if picture:
            upd["picture"] = picture
        await db.users.update_one({"email": email}, {"$set": upd})
        user_doc = {**existing, **upd}
    else:
        user_doc = {
            "id": str(uuid.uuid4()),
            "name": name,
            "email": email,
            "phone": "",
            "picture": picture,
            "auth_provider": "google",
            "created_at": now_iso(),
        }
        await db.users.insert_one(user_doc)

    token = create_token(email, role="user")
    return _frontend_callback_redirect(frontend_base, {
        "token": token,
        "email": email,
        "name": user_doc.get("name") or "",
        "picture": user_doc.get("picture") or "",
        "next": next_path,
    })


# ---------- GOOGLE (EMERGENT) AUTH ---------- #
# REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
@api_router.post("/auth/google/session")
async def auth_google_session(payload: GoogleSessionIn):
    """
    Exchange an Emergent-Auth session_id for our own JWT.

    Flow:
      1) Frontend received a `session_id` in the URL fragment after Google OAuth
      2) Frontend calls this endpoint with that session_id
      3) We call Emergent Auth server-side to fetch the authenticated profile
      4) We upsert the user in our users collection (linked by email) and issue our own JWT
    """
    sid = (payload.session_id or "").strip()
    if not sid:
        raise HTTPException(status_code=400, detail="session_id is required")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": sid},
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Google session invalid or expired")
        data = resp.json()
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Emergent auth session-data call failed")
        raise HTTPException(status_code=502, detail=f"Auth provider unreachable: {e}")

    email = (data.get("email") or "").lower()
    name = data.get("name") or email.split("@")[0]
    picture = data.get("picture")
    session_token = data.get("session_token")  # 7-day token from Emergent; stored for future cookie option
    if not email:
        raise HTTPException(status_code=400, detail="Google account did not return an email address")

    # Upsert by email
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        update = {"name": name or existing.get("name"), "auth_provider": "google"}
        if picture:
            update["picture"] = picture
        if session_token:
            update["emergent_session_token"] = session_token
        await db.users.update_one({"email": email}, {"$set": update})
        user = {**existing, **update}
    else:
        user = {
            "id": str(uuid.uuid4()),
            "name": name,
            "email": email,
            "phone": "",
            "picture": picture,
            "auth_provider": "google",
            "emergent_session_token": session_token,
            "created_at": now_iso(),
        }
        await db.users.insert_one(user)

    token = create_token(email, role="user")
    return {
        "token": token,
        "user": {"name": user["name"], "email": user["email"], "phone": user.get("phone", ""), "picture": user.get("picture")},
    }


@api_router.post("/auth/logout")
async def auth_logout():
    """No-op for JWT; frontend discards the token. Present for future cookie-based sessions."""
    return {"ok": True}


# ---------- APP SETTINGS ---------- #
DEFAULT_REVIEW_PROMPT_DAYS = 7


async def get_setting(key: str, default):
    doc = await db.app_settings.find_one({"key": key}, {"_id": 0})
    return doc["value"] if doc else default


@api_router.get("/admin/settings")
async def admin_get_settings(admin=Depends(get_current_admin)):
    days = await get_setting("review_prompt_days", DEFAULT_REVIEW_PROMPT_DAYS)
    return {"review_prompt_days": days}


@api_router.patch("/admin/settings")
async def admin_patch_settings(payload: ReviewPromptDelay, admin=Depends(get_current_admin)):
    await db.app_settings.update_one(
        {"key": "review_prompt_days"},
        {"$set": {"key": "review_prompt_days", "value": payload.review_prompt_days}},
        upsert=True,
    )
    return {"review_prompt_days": payload.review_prompt_days}


# ---------- REVIEW PROMPTS ---------- #
@api_router.get("/me/review-prompts")
async def my_review_prompts(user=Depends(get_current_user)):
    """
    Return a list of {order_number, product_id, product_slug, product_name, product_image, delivered_at}
    for products this user has NOT yet reviewed, where the order was delivered ≥ review_prompt_days ago.
    """
    days = int(await get_setting("review_prompt_days", DEFAULT_REVIEW_PROMPT_DAYS))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    delivered_orders = await db.orders.find(
        {"customer.email": user["email"], "status": "delivered"},
        {"_id": 0},
    ).to_list(500)

    prompts = []
    seen_pairs = set()
    for order in delivered_orders:
        delivered_iso = order.get("delivered_at") or order.get("created_at")
        try:
            dt = datetime.fromisoformat(delivered_iso.replace("Z", "+00:00")) if delivered_iso else None
        except Exception:
            dt = None
        if not dt:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt > cutoff:
            continue  # not old enough yet
        for it in order.get("items", []):
            pid = it.get("product_id")
            if not pid:
                continue
            pair = (order["order_number"], pid)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            prod = await db.products.find_one({"id": pid}, {"_id": 0})
            if not prod:
                continue
            # Skip if user has already reviewed this product
            already = await db.reviews.find_one({"user_email": user["email"], "product_slug": prod["slug"]}, {"_id": 0})
            if already:
                continue
            prompts.append({
                "order_number": order["order_number"],
                "product_id": pid,
                "product_slug": prod["slug"],
                "product_name": prod["name"],
                "product_image": prod.get("hero_image"),
                "delivered_at": dt.isoformat(),
                "days_since_delivery": (datetime.now(timezone.utc) - dt).days,
            })
    return prompts


@api_router.get("/me/orders", response_model=List[Order])
async def my_orders(user=Depends(get_current_user)):
    orders = await db.orders.find({"customer.email": user["email"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return await _enrich_order_items(orders)


@api_router.post("/products/{slug}/reviews", response_model=Review)
async def submit_review(slug: str, payload: ReviewSubmit, user=Depends(get_current_user)):
    """Legacy slug-based review submission. Kept for backward compat with the
    older ProductPage code. New callers should POST /reviews with product_id."""
    prod = await db.products.find_one({"slug": slug}, {"_id": 0})
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    if payload.rating < 1 or payload.rating > 5:
        raise HTTPException(status_code=400, detail="Rating 1-5")
    email = (user.get("email") or "").lower().strip()
    product_id = prod.get("id")
    # Verified-buyer check: any delivered order for this email containing this product.
    is_verified = False
    if await db.orders.count_documents({
        "customer.email": email, "status": "delivered", "items.product_id": product_id,
    }) > 0:
        is_verified = True
    if await db.reviews.count_documents({"user_email": email, "product_id": product_id, "status": {"$ne": "rejected"}}) > 0:
        raise HTTPException(status_code=409, detail="You have already reviewed this product")
    r = Review(
        author=(payload.author_name or user.get("name") or email.split("@")[0]).strip()[:80],
        location=(payload.location or "").strip()[:80] or "India",
        rating=payload.rating, title=payload.title.strip(), body=payload.body.strip(),
        image=payload.image, verified=is_verified, featured=False,
        status="pending", product_id=product_id, user_email=email,
    )
    await db.reviews.insert_one(r.model_dump())
    try:
        asyncio.create_task(notify_admins_event(
            kind="review_pending",
            subject=f"New review pending approval — {r.rating}★ from {r.author}",
            html_body=f"<p>Product: <b>{_esc(prod.get('name',''))}</b></p><p>{_esc(r.body[:500])}</p>",
        ))
    except Exception:
        pass
    return r


@api_router.post("/me/returns", response_model=ReturnRequest)
async def request_return(payload: ReturnRequestIn, user=Depends(get_current_user)):
    order = await db.orders.find_one({"order_number": payload.order_number, "customer.email": user["email"]})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.get("status") != "delivered":
        raise HTTPException(status_code=400, detail="Returns can only be requested for delivered orders.")
    # Enforce 3-day return window from delivery date
    delivered_iso = order.get("delivered_at") or order.get("created_at")
    try:
        delivered_dt = datetime.fromisoformat(delivered_iso)
    except Exception:
        raise HTTPException(status_code=400, detail="Order delivery date unavailable.")
    if delivered_dt.tzinfo is None:
        delivered_dt = delivered_dt.replace(tzinfo=timezone.utc)
    days_since = (datetime.now(timezone.utc) - delivered_dt).days
    if days_since > RETURN_WINDOW_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"Return window closed. Requests must be raised within {RETURN_WINDOW_DAYS} days of delivery (yours was {days_since} days ago).",
        )
    if not payload.packaging_confirmed:
        raise HTTPException(status_code=400, detail="Please confirm you can return the piece in its original packaging.")
    # Prevent duplicate open returns for same order
    existing = await db.returns.find_one({
        "order_number": payload.order_number,
        "user_email": user["email"],
        "status": {"$in": ["requested", "approved", "received"]},
    })
    if existing:
        raise HTTPException(status_code=400, detail="A return request is already open for this order.")
    rr = ReturnRequest(**payload.model_dump(), user_email=user["email"])
    await db.returns.insert_one(rr.model_dump())
    # Task 6: notify admins of the new return request
    try:
        asyncio.create_task(notify_admins_event(
            kind="order_returned",
            subject=f"Return requested for order {rr.order_number}",
            html_body=(
                f"<p><b>{_esc(user.get('name') or user.get('email'))}</b> requested a return.</p>"
                f"<p>Reason: <em>{_esc(rr.reason)}</em></p>"
                f"<p>Order: <b>{_esc(rr.order_number)}</b> · delivered {int(days_since)} days ago</p>"
                f"<p>Open <b>Admin → Returns</b> to review and process.</p>"
            ),
        ))
    except Exception as _e:
        logging.warning(f"Admin return notify failed: {_e}")
    return rr


@api_router.get("/me/returns", response_model=List[ReturnRequest])
async def my_returns(user=Depends(get_current_user)):
    return await db.returns.find({"user_email": user["email"]}, {"_id": 0}).sort("created_at", -1).to_list(100)


# ---------- PROFILE ---------- #
@api_router.patch("/auth/me")
async def update_profile(payload: ProfileUpdate, user=Depends(get_current_user)):
    updates = {}
    if payload.name is not None:
        name = payload.name.strip()
        if len(name) < 2:
            raise HTTPException(status_code=400, detail="Name must be at least 2 characters.")
        updates["name"] = name
    if payload.phone is not None:
        phone = payload.phone.strip()
        if phone and (len(phone) < 7 or len(phone) > 20):
            raise HTTPException(status_code=400, detail="Please enter a valid phone number.")
        updates["phone"] = phone
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided.")
    await db.users.update_one({"email": user["email"]}, {"$set": updates})
    fresh = await db.users.find_one({"email": user["email"]}, {"_id": 0, "password_hash": 0})
    return {"name": fresh["name"], "email": fresh["email"], "phone": fresh.get("phone", "")}


# ---------- CUSTOMER MESSAGES ---------- #
@api_router.get("/me/messages")
async def my_messages(user=Depends(get_current_user)):
    return await db.admin_messages.find({"user_email": user["email"]}, {"_id": 0}).sort("created_at", -1).to_list(100)


@api_router.patch("/me/messages/{msg_id}/read")
async def mark_message_read(msg_id: str, user=Depends(get_current_user)):
    res = await db.admin_messages.update_one(
        {"id": msg_id, "user_email": user["email"]},
        {"$set": {"read": True, "read_at": now_iso()}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"ok": True}


# ---------- ADMIN — USERS (CRM) ---------- #
@api_router.get("/admin/users")
async def admin_list_users(q: Optional[str] = None, admin=Depends(get_current_admin)):
    query = {}
    if q:
        query = {"$or": [{"email": {"$regex": q, "$options": "i"}}, {"name": {"$regex": q, "$options": "i"}}, {"phone": {"$regex": q, "$options": "i"}}]}
    users = await db.users.find(query, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(5000)
    # Enrich with order aggregates
    for u in users:
        orders = await db.orders.find({"customer.email": u["email"], "status": {"$nin": ["pending_payment", "cancelled", "payment_failed"]}}, {"_id": 0, "total_inr": 1, "created_at": 1}).to_list(500)
        u["orders_count"] = len(orders)
        u["total_spent_inr"] = sum(o.get("total_inr", 0) for o in orders)
        u["last_order_at"] = max((o["created_at"] for o in orders), default=None)
        u["messages_count"] = await db.admin_messages.count_documents({"user_email": u["email"]})
        u["blocked"] = bool(u.get("blocked", False))
    return users


@api_router.get("/admin/users/{email}")
async def admin_user_detail(email: str, admin=Depends(get_current_admin)):
    user = await db.users.find_one({"email": email}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    orders = await db.orders.find({"customer.email": email}, {"_id": 0}).sort("created_at", -1).to_list(200)
    returns = await db.returns.find({"user_email": email}, {"_id": 0}).sort("created_at", -1).to_list(100)
    messages = await db.admin_messages.find({"user_email": email}, {"_id": 0}).sort("created_at", -1).to_list(100)
    wishlist = await db.wishlist.count_documents({"user_email": email})
    return {"user": user, "orders": orders, "returns": returns, "messages": messages, "wishlist_count": wishlist}


# ---------- ADMIN — MESSAGES ---------- #
@api_router.post("/admin/messages", response_model=AdminMessage)
async def admin_create_message(payload: AdminMessageIn, admin=Depends(get_current_admin)):
    subject = payload.subject.strip()
    body = payload.body.strip()
    if not subject or not body:
        raise HTTPException(status_code=400, detail="Subject and message are required.")
    target = await db.users.find_one({"email": payload.user_email}, {"_id": 0, "name": 1, "email": 1})
    if not target:
        raise HTTPException(status_code=404, detail="Recipient user not found")
    msg = AdminMessage(user_email=payload.user_email, subject=subject, body=body, created_by=admin["email"])
    await db.admin_messages.insert_one(msg.model_dump())
    return msg


@api_router.get("/admin/messages")
async def admin_list_messages(user_email: Optional[str] = None, admin=Depends(get_current_admin)):
    query = {"user_email": user_email} if user_email else {}
    return await db.admin_messages.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)


@api_router.delete("/admin/messages/{msg_id}")
async def admin_delete_message(msg_id: str, admin=Depends(get_current_admin)):
    res = await db.admin_messages.delete_one({"id": msg_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"deleted": True}


# ---------- ADMIN: COUPONS ----------
@api_router.get("/admin/coupons", response_model=List[Coupon])
async def admin_list_coupons(admin=Depends(get_current_admin)):
    return await db.coupons.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)


@api_router.post("/admin/coupons", response_model=Coupon)
async def admin_create_coupon(payload: CouponIn, admin=Depends(get_current_admin)):
    code = (payload.code or "").upper().strip()
    if not code:
        raise HTTPException(status_code=400, detail="Code is required.")
    if payload.type not in ("percentage", "flat"):
        raise HTTPException(status_code=400, detail="Type must be 'percentage' or 'flat'.")
    if payload.value <= 0:
        raise HTTPException(status_code=400, detail="Value must be greater than zero.")
    if payload.type == "percentage" and payload.value > 100:
        raise HTTPException(status_code=400, detail="Percentage cannot exceed 100.")
    if await db.coupons.find_one({"code": code}):
        raise HTTPException(status_code=409, detail=f"Coupon '{code}' already exists.")
    data = payload.model_dump()
    data["code"] = code
    coupon = Coupon(**data)
    await db.coupons.insert_one(coupon.model_dump())
    return coupon


@api_router.patch("/admin/coupons/{coupon_id}", response_model=Coupon)
async def admin_update_coupon(coupon_id: str, payload: CouponIn, admin=Depends(get_current_admin)):
    existing = await db.coupons.find_one({"id": coupon_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Coupon not found")
    code = (payload.code or "").upper().strip()
    if payload.type not in ("percentage", "flat"):
        raise HTTPException(status_code=400, detail="Type must be 'percentage' or 'flat'.")
    if payload.value <= 0:
        raise HTTPException(status_code=400, detail="Value must be greater than zero.")
    if payload.type == "percentage" and payload.value > 100:
        raise HTTPException(status_code=400, detail="Percentage cannot exceed 100.")
    # If code changed, ensure new code isn't taken
    if code and code != existing["code"]:
        if await db.coupons.find_one({"code": code}):
            raise HTTPException(status_code=409, detail=f"Coupon '{code}' already exists.")
    update = payload.model_dump()
    update["code"] = code or existing["code"]
    await db.coupons.update_one({"id": coupon_id}, {"$set": update})
    merged = {**existing, **update}
    return Coupon(**merged)


@api_router.delete("/admin/coupons/{coupon_id}")
async def admin_delete_coupon(coupon_id: str, admin=Depends(get_current_admin)):
    res = await db.coupons.delete_one({"id": coupon_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Coupon not found")
    return {"deleted": True}


# ---------- ADMIN: FAILED PAYMENTS ----------
@api_router.get("/admin/failed-payments", response_model=List[FailedPayment])
async def admin_list_failed_payments(admin=Depends(get_current_admin)):
    return await db.failed_payments.find({}, {"_id": 0}).sort("created_at", -1).to_list(2000)


@api_router.delete("/admin/failed-payments/{fp_id}")
async def admin_delete_failed_payment(fp_id: str, admin=Depends(get_current_admin)):
    res = await db.failed_payments.delete_one({"id": fp_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Failed payment not found")
    return {"deleted": True}


@api_router.post("/admin/failed-payments/bulk-delete")
async def admin_bulk_delete_failed_payments(payload: dict, admin=Depends(get_current_admin)):
    ids = payload.get("ids") or []
    if not isinstance(ids, list) or not ids:
        raise HTTPException(status_code=400, detail="ids[] required")
    res = await db.failed_payments.delete_many({"id": {"$in": ids}})
    return {"deleted": res.deleted_count}


# ---------- ADMIN: CUSTOMER BLOCK / DELETE ----------
@api_router.patch("/admin/users/{email}")
async def admin_update_user(email: str, payload: dict, admin=Depends(require_permission("manage_customers"))):
    updates = {}
    if "blocked" in payload:
        updates["blocked"] = bool(payload.get("blocked"))
    if "note" in payload:
        updates["admin_note"] = (payload.get("note") or "").strip() or None
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    res = await db.users.update_one({"email": email}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"updated": True, **updates}


@api_router.delete("/admin/users/{email}")
async def admin_delete_user(email: str, admin=Depends(require_permission("manage_customers"))):
    res = await db.users.delete_one({"email": email})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    # Best-effort cleanup of related non-order data (keep orders for records)
    await db.admin_messages.delete_many({"user_email": email})
    await db.wishlist.delete_many({"user_email": email})
    return {"deleted": True}


# =============================================================================
# ---------- PHASE A: HOMEPAGE CMS + SHIPPING SETTINGS + TRACKING ----------
# =============================================================================

# ---------- MODELS ----------
class AnnouncementBar(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    text: str = "Complimentary delivery on all mirrors above ₹25,000 · Handpoured in Mumbai"
    bg_color: str = "#0a0a0a"
    text_color: str = "#D4AF37"
    link_url: Optional[str] = ""
    link_label: Optional[str] = ""


class HeroStat(BaseModel):
    model_config = ConfigDict(extra="ignore")
    k: str = ""
    v: str = ""


class HeroContent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    eyebrow: str = "ArtyFex Atelier · Est. 2020 · Mumbai"
    headline_line_1: str = "A mirror,"
    headline_italic: str = "poured"
    headline_line_2: str = "over one hundred"
    headline_line_3: str = "and twenty hours."
    subheadline: str = (
        "The Obsidian Aurora — a 2×3 ft statement mirror of black marbled resin, real crushed "
        "blue crystal, and a hand-brushed golden aluminum border. Signed by the artisan. One of one."
    )
    primary_cta_text: str = "Acquire the piece"
    primary_cta_link: str = "#product"
    secondary_cta_text: str = "Explore the craft"
    secondary_cta_link: str = "#craft"
    background_image: str = (
        "https://images.unsplash.com/photo-1688646953306-5ec93eab8c06?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxOTJ8MHwxfHNlYXJjaHwzfHxsdXh1cnklMjBwZW50aG91c2UlMjBsaXZpbmclMjByb29tfGVufDB8fHx8MTc4MzA2MjM3M3ww&ixlib=rb-4.1.0&q=85"
    )
    mirror_image: str = (
        "https://images.pexels.com/photos/8068653/pexels-photo-8068653.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
    )
    edition_label: str = "Edition"
    edition_text: str = "Obsidian Aurora №03"
    text_color: str = "#f5efdf"
    accent_color: str = "#D4AF37"
    stats: List[HeroStat] = Field(default_factory=lambda: [
        HeroStat(k="120", v="artisan hours"),
        HeroStat(k="1 of 1", v="unique piece"),
        HeroStat(k="24 mo", v="warranty"),
    ])


class SaleBanner(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = False
    title: str = "Festive Edit"
    subtitle: str = "Enjoy 10% off select statement pieces this season."
    cta_text: str = "Discover"
    cta_link: str = "/shop"
    bg_color: str = "#1a1208"
    text_color: str = "#f5efdf"
    accent_color: str = "#D4AF37"
    image: str = ""


class CraftStep(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str = ""
    body: str = ""


class CraftSection(BaseModel):
    model_config = ConfigDict(extra="ignore")
    eyebrow: str = "Craft & Materials"
    headline_line_1: str = "No two are alike."
    headline_italic: str = "That is the point."
    body: str = (
        "Each ArtyFex mirror is poured, inlaid and framed entirely by hand in our Mumbai atelier. "
        "No moulds. No stamps. No two identical currents of resin. What arrives at your door will never exist again."
    )
    section_image: str = "https://images.pexels.com/photos/18325786/pexels-photo-18325786.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
    image_overlay_label: str = "Atelier"
    image_overlay_title: str = "The 120-hour ritual"
    steps: List[CraftStep] = Field(default_factory=lambda: [
        CraftStep(title="01 · Design", body="A moodboard is composed with the collector. Dimensions, palette and crystal density are set."),
        CraftStep(title="02 · Pour", body="Anti-yellowing epoxy is poured in layered veins. Every current is directed by hand."),
        CraftStep(title="03 · Inlay", body="Real crushed crystal (5–10mm) is placed grain by grain into the wet resin surface."),
        CraftStep(title="04 · Frame", body="A 1-inch hand-brushed golden aluminum border is fitted over 5mm scatter-proof glass."),
    ])


class CollectionSection(BaseModel):
    model_config = ConfigDict(extra="ignore")
    eyebrow: str = "The Collection"
    headline_line_1: str = "Companion"
    headline_italic: str = "pieces"
    subtitle: str = "Smaller edits from the atelier — each still 100% handpoured, still one of one."
    # Which non-hero products to show on the homepage. Empty list = show all non-hero (backward compat).
    featured_product_ids: List[str] = Field(default_factory=list)


class ReviewsSection(BaseModel):
    model_config = ConfigDict(extra="ignore")
    eyebrow: str = "Verified Collectors"
    headline_line_1: str = "Voices from"
    headline_italic: str = "the collectors"
    average_rating: str = "4.98"
    # If empty, homepage falls back to showing all reviews (backward compat).
    featured_review_ids: List[str] = Field(default_factory=list)


class ImportantNote(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    label: str = "Important note"
    body: str = (
        "No inbuilt LED lighting is included with any ArtyFex piece. Ambient light shown in "
        "product and lifestyle imagery is for styling visualisation only. Every piece is 100% handmade "
        "and one of one — subtle organic variations in resin currents and crystal placement are the "
        "signature of the atelier."
    )


class CategoryTile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    slug: str = ""
    label: str = ""
    keyword: str = ""
    image: str = ""


class WhyStat(BaseModel):
    model_config = ConfigDict(extra="ignore")
    icon: str = "sparkles"  # sparkles | award | shield | truck
    value: int = 0
    suffix: str = ""
    label: str = ""
    note: str = ""


class WhyArtyFexSection(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    eyebrow: str = "Why ArtyFex"
    headline_line_1: str = "The Mumbai atelier"
    headline_italic: str = "obsessed"
    headline_line_2: str = " with detail."
    subtitle: str = "Modern art collectors, luxury interior designers and celebrities trust ArtyFex for one reason — each piece is a story of 120+ artisan hours, poured by hand, signed by the maker."
    stats: List[WhyStat] = Field(default_factory=lambda: [
        WhyStat(icon="sparkles", value=120, suffix="+", label="Artisan hours per piece", note="Every mirror, hand-poured"),
        WhyStat(icon="award", value=1, suffix=" / 1", label="One-of-one editions", note="No two pieces alike"),
        WhyStat(icon="shield", value=24, suffix=" mo", label="Signature warranty", note="Anti-yellowing epoxy"),
        WhyStat(icon="truck", value=500, suffix="+", label="Delivered pan-India", note="Insured white-glove"),
    ])


class CategorySection(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    eyebrow: str = "Explore the Atelier"
    headline_line_1: str = "Curated"
    headline_italic: str = "worlds"
    headline_line_2: str = " of luxury."
    subtitle: str = "From statement mirrors to bespoke furniture — every category, handpoured in Mumbai."
    tiles: List[CategoryTile] = Field(default_factory=list)


class FeaturedSection(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    eyebrow: str = "Featured"
    headline_line_1: str = "Editor's"
    headline_italic: str = "pick"


class NavDefaultLinks(BaseModel):
    model_config = ConfigDict(extra="ignore")
    show_shop: bool = True
    show_craft: bool = True
    show_reviews: bool = True
    show_b2b: bool = True


class HomepageContent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    announcement: AnnouncementBar = Field(default_factory=AnnouncementBar)
    hero: HeroContent = Field(default_factory=HeroContent)
    sale_banner: SaleBanner = Field(default_factory=SaleBanner)
    craft: CraftSection = Field(default_factory=CraftSection)
    collection_section: CollectionSection = Field(default_factory=CollectionSection)
    reviews_section: ReviewsSection = Field(default_factory=ReviewsSection)
    important_note: ImportantNote = Field(default_factory=ImportantNote)
    # New Phase-B homepage sections + navigation controls
    category_section: CategorySection = Field(default_factory=CategorySection)
    why_section: WhyArtyFexSection = Field(default_factory=WhyArtyFexSection)
    featured_section: FeaturedSection = Field(default_factory=FeaturedSection)
    nav_default_links: NavDefaultLinks = Field(default_factory=NavDefaultLinks)
    custom_css: str = ""


class ZoneRate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = "Rest of India"
    states: List[str] = Field(default_factory=list)
    rate_inr: int = 1499


class DistanceBand(BaseModel):
    model_config = ConfigDict(extra="ignore")
    max_km: int = 500
    rate_inr: int = 999


class ShippingSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    method: str = "flat"  # "flat" | "zone" | "distance"
    flat_rate_inr: int = 1499
    free_shipping_above_inr: int = 25000
    origin_city: str = "Mumbai"
    origin_state: str = "Maharashtra"
    origin_pincode: str = "400095"
    zone_rates: List[ZoneRate] = Field(default_factory=lambda: [
        ZoneRate(name="Maharashtra (Local)", states=["Maharashtra"], rate_inr=499),
        ZoneRate(name="Metro & West", states=["Gujarat", "Goa", "Karnataka", "Madhya Pradesh", "Telangana", "Andhra Pradesh"], rate_inr=999),
        ZoneRate(name="Rest of India", states=[], rate_inr=1499),
    ])
    distance_base_fee_inr: int = 299
    distance_per_km_inr: int = 3
    distance_bands: List[DistanceBand] = Field(default_factory=list)


class ShippingCalcIn(BaseModel):
    subtotal_inr: int
    state: Optional[str] = None
    pincode: Optional[str] = None
    country: Optional[str] = "India"


class TrackingUpdate(BaseModel):
    tracking_id: Optional[str] = None
    tracking_url: Optional[str] = None
    tracking_carrier: Optional[str] = None


# Static state→approx km distance table from Mumbai origin (Malad West, 400095)
# Used for the "distance" shipping method without needing Google Maps.
STATE_DISTANCE_KM_FROM_MUMBAI = {
    "maharashtra": 30,
    "goa": 600,
    "gujarat": 550,
    "karnataka": 980,
    "kerala": 1500,
    "tamil nadu": 1330,
    "telangana": 700,
    "andhra pradesh": 700,
    "rajasthan": 1200,
    "madhya pradesh": 850,
    "delhi": 1400,
    "uttar pradesh": 1500,
    "punjab": 1750,
    "haryana": 1400,
    "west bengal": 1900,
    "bihar": 1900,
    "odisha": 1700,
    "chhattisgarh": 1200,
    "jharkhand": 1800,
    "uttarakhand": 1600,
    "himachal pradesh": 1700,
    "jammu and kashmir": 2000,
    "ladakh": 2100,
    "assam": 2400,
    "meghalaya": 2500,
    "manipur": 2700,
    "mizoram": 2700,
    "nagaland": 2700,
    "tripura": 2600,
    "arunachal pradesh": 2800,
    "sikkim": 2200,
    "chandigarh": 1600,
    "puducherry": 1350,
    "andaman and nicobar islands": 2500,
    "dadra and nagar haveli and daman and diu": 200,
    "lakshadweep": 1400,
}


DEFAULT_HOMEPAGE = HomepageContent().model_dump()
DEFAULT_SHIPPING = ShippingSettings().model_dump()


async def load_site_setting(key: str, default_dict: dict) -> dict:
    doc = await db.site_settings.find_one({"key": key}, {"_id": 0})
    if not doc:
        return default_dict
    val = doc.get("value") or {}
    # Deep-merge: fill any missing keys from default so old rows stay valid
    def merge(base, override):
        if not isinstance(base, dict) or not isinstance(override, dict):
            return override if override is not None else base
        out = dict(base)
        for k, v in override.items():
            out[k] = merge(base.get(k), v) if isinstance(v, dict) else v
        return out
    return merge(default_dict, val)


async def save_site_setting(key: str, value: dict):
    await db.site_settings.update_one(
        {"key": key},
        {"$set": {"key": key, "value": value, "updated_at": now_iso()}},
        upsert=True,
    )


def calc_shipping(settings: dict, subtotal_inr: int, state: Optional[str], pincode: Optional[str]) -> dict:
    """Compute shipping cost for the given cart context and settings."""
    method = settings.get("method", "flat")
    free_above = int(settings.get("free_shipping_above_inr", 25000) or 0)
    result = {"method": method, "shipping_inr": 0, "free_shipping_applied": False, "notes": ""}
    if subtotal_inr <= 0:
        return result
    if free_above and subtotal_inr >= free_above:
        result["free_shipping_applied"] = True
        result["notes"] = f"Free shipping · order above ₹{free_above:,}"
        return result

    state_norm = (state or "").strip().lower()

    if method == "flat":
        result["shipping_inr"] = int(settings.get("flat_rate_inr", 1499) or 0)
        result["notes"] = "Flat rate shipping"
    elif method == "zone":
        zones = settings.get("zone_rates") or []
        chosen = None
        # Prefer explicit state match
        for z in zones:
            zs = [s.strip().lower() for s in (z.get("states") or [])]
            if state_norm and state_norm in zs:
                chosen = z
                break
        # Fallback: first zone with empty states list acts as "rest of India"
        if not chosen:
            for z in zones:
                if not (z.get("states") or []):
                    chosen = z
                    break
        if not chosen and zones:
            chosen = zones[-1]
        if chosen:
            result["shipping_inr"] = int(chosen.get("rate_inr", 0) or 0)
            result["notes"] = f"Zone · {chosen.get('name', '')}"
        else:
            result["shipping_inr"] = int(settings.get("flat_rate_inr", 1499) or 0)
            result["notes"] = "Zone unmatched — fallback flat rate"
    elif method == "distance":
        km = STATE_DISTANCE_KM_FROM_MUMBAI.get(state_norm)
        if km is None:
            # Fallback: median India distance ~1200km
            km = 1200
        # Prefer explicit distance bands if configured
        bands = settings.get("distance_bands") or []
        band = None
        for b in sorted(bands, key=lambda x: int(x.get("max_km", 0) or 0)):
            if km <= int(b.get("max_km", 0) or 0):
                band = b
                break
        if band:
            result["shipping_inr"] = int(band.get("rate_inr", 0) or 0)
            result["notes"] = f"Distance ~{km} km · {band.get('max_km', 0)} km band"
        else:
            base = int(settings.get("distance_base_fee_inr", 299) or 0)
            per_km = float(settings.get("distance_per_km_inr", 3) or 0)
            result["shipping_inr"] = int(base + per_km * km)
            result["notes"] = f"Distance ~{km} km · base ₹{base} + ₹{per_km:.1f}/km"
    else:
        result["shipping_inr"] = int(settings.get("flat_rate_inr", 1499) or 0)
        result["notes"] = "Unknown method — flat fallback"
    return result


# ---------- HOMEPAGE ROUTES ----------
@api_router.get("/homepage")
async def public_get_homepage():
    return await load_site_setting("homepage", DEFAULT_HOMEPAGE)


@api_router.get("/admin/homepage")
async def admin_get_homepage(admin=Depends(get_current_admin)):
    return await load_site_setting("homepage", DEFAULT_HOMEPAGE)


@api_router.patch("/admin/homepage")
async def admin_patch_homepage(payload: HomepageContent, background_tasks: BackgroundTasks, admin=Depends(require_permission("manage_homepage"))):
    old = await load_site_setting("homepage", DEFAULT_HOMEPAGE)
    data = payload.model_dump()
    await save_site_setting("homepage", data)
    # Batch 5 — clean up orphaned Cloudinary assets
    background_tasks.add_task(_destroy_url_diff, _extract_cloudinary_urls(old), _extract_cloudinary_urls(data))
    return data


# ---------- SHIPPING ROUTES ----------
@api_router.get("/admin/shipping-settings")
async def admin_get_shipping(admin=Depends(get_current_admin)):
    return await load_site_setting("shipping", DEFAULT_SHIPPING)


@api_router.patch("/admin/shipping-settings")
async def admin_patch_shipping(payload: ShippingSettings, admin=Depends(require_permission("manage_shipping"))):
    data = payload.model_dump()
    if data.get("method") not in ("flat", "zone", "distance"):
        raise HTTPException(status_code=400, detail="method must be one of flat|zone|distance")
    await save_site_setting("shipping", data)
    return data


@api_router.post("/shipping/calculate")
async def public_shipping_calculate(payload: ShippingCalcIn):
    settings = await load_site_setting("shipping", DEFAULT_SHIPPING)
    return calc_shipping(settings, payload.subtotal_inr, payload.state, payload.pincode)


# ---------- ADMIN: ORDER TRACKING ----------
@api_router.patch("/admin/orders/{order_number}/tracking")
async def admin_update_tracking(order_number: str, payload: TrackingUpdate, admin=Depends(get_current_admin)):
    update = {"tracking_updated_at": now_iso()}
    if payload.tracking_id is not None:
        update["tracking_id"] = payload.tracking_id.strip() or None
    if payload.tracking_url is not None:
        update["tracking_url"] = payload.tracking_url.strip() or None
    if payload.tracking_carrier is not None:
        update["tracking_carrier"] = payload.tracking_carrier.strip() or None
    res = await db.orders.update_one({"order_number": order_number}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    doc = await db.orders.find_one({"order_number": order_number}, {"_id": 0})
    return doc


# =============================================================================
# ------------------ TASK 7 (BATCH 4): NIMBUSPOST COURIER  --------------------
# =============================================================================
import nimbuspost_service as nimbus  # noqa: E402  (kept close to route defs)


class NimbusConfigIn(BaseModel):
    warehouse_name: str = ""
    origin_pincode: str = ""
    # Batch 9 — full pickup contact block (NimbusPost validates on every shipment)
    contact_name: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    pincode: str = ""
    phone: str = ""
    # Optional webhook secret so the shipment-status webhook signature can be verified
    webhook_secret: str = ""


DEFAULT_NIMBUS_CFG = {
    "warehouse_name": os.getenv("NIMBUSPOST_WAREHOUSE_NAME", "").strip(),
    "origin_pincode": os.getenv("NIMBUSPOST_ORIGIN_PINCODE", "").strip(),
    "contact_name": os.getenv("NIMBUSPOST_CONTACT_NAME", "").strip(),
    "address": os.getenv("NIMBUSPOST_PICKUP_ADDRESS", "").strip(),
    "city": os.getenv("NIMBUSPOST_PICKUP_CITY", "").strip(),
    "state": os.getenv("NIMBUSPOST_PICKUP_STATE", "").strip(),
    "pincode": os.getenv("NIMBUSPOST_PICKUP_PINCODE", "").strip(),
    "phone": os.getenv("NIMBUSPOST_PICKUP_PHONE", "").strip(),
    "webhook_secret": os.getenv("NIMBUSPOST_WEBHOOK_SECRET", "").strip(),
}


async def _nimbus_warehouse() -> str:
    cfg = await load_site_setting("nimbuspost", DEFAULT_NIMBUS_CFG)
    return (cfg.get("warehouse_name") or "").strip()


async def _nimbus_origin_pincode() -> str:
    cfg = await load_site_setting("nimbuspost", DEFAULT_NIMBUS_CFG)
    return (cfg.get("origin_pincode") or cfg.get("pincode") or "").strip()


async def _nimbus_pickup() -> dict:
    cfg = await load_site_setting("nimbuspost", DEFAULT_NIMBUS_CFG)
    return {
        "warehouse_name": (cfg.get("warehouse_name") or "").strip(),
        "contact_name": (cfg.get("contact_name") or "").strip(),
        "address": (cfg.get("address") or "").strip(),
        "city": (cfg.get("city") or "").strip(),
        "state": (cfg.get("state") or "").strip(),
        "pincode": (cfg.get("pincode") or "").strip(),
        "phone": (cfg.get("phone") or "").strip(),
    }


@api_router.get("/admin/nimbuspost/config")
async def admin_get_nimbus_config(admin=Depends(get_current_admin)):
    cfg = await load_site_setting("nimbuspost", DEFAULT_NIMBUS_CFG)
    # Compute webhook URL from BACKEND_PUBLIC_URL (fallback to relative /api path)
    base = os.getenv("BACKEND_PUBLIC_URL", "").strip().rstrip("/")
    webhook_url = f"{base}/api/nimbuspost/webhook" if base else "/api/nimbuspost/webhook"
    return {
        "configured": nimbus.is_configured(),
        "warehouse_name": cfg.get("warehouse_name") or "",
        "origin_pincode": cfg.get("origin_pincode") or "",
        "contact_name": cfg.get("contact_name") or "",
        "address": cfg.get("address") or "",
        "city": cfg.get("city") or "",
        "state": cfg.get("state") or "",
        "pincode": cfg.get("pincode") or "",
        "phone": cfg.get("phone") or "",
        "webhook_secret_set": bool(cfg.get("webhook_secret")),
        "webhook_url": webhook_url,
        "auth_mode": "jwt" if (os.getenv("NIMBUSPOST_EMAIL") and os.getenv("NIMBUSPOST_PASSWORD")) else ("legacy" if os.getenv("NIMBUSPOST_LEGACY_KEY") else "none"),
    }


@api_router.patch("/admin/nimbuspost/config")
async def admin_patch_nimbus_config(payload: NimbusConfigIn, admin=Depends(require_permission("manage_shipping"))):
    # Load existing so blank fields don't wipe out previously-saved secrets
    old = await load_site_setting("nimbuspost", DEFAULT_NIMBUS_CFG)
    new = payload.model_dump()
    # Only overwrite webhook_secret if a non-empty new value provided
    if not (new.get("webhook_secret") or "").strip():
        new["webhook_secret"] = old.get("webhook_secret", "")
    data = {k: (v or "").strip() if isinstance(v, str) else v for k, v in new.items()}
    await save_site_setting("nimbuspost", data)
    return {**{k: v for k, v in data.items() if k != "webhook_secret"},
            "webhook_secret_set": bool(data.get("webhook_secret")),
            "configured": nimbus.is_configured()}


@api_router.post("/admin/orders/{order_number}/nimbuspost/ship")
async def admin_nimbus_ship(order_number: str, admin=Depends(require_permission("manage_orders"))):
    order = await db.orders.find_one({"order_number": order_number}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.get("tracking_id"):
        raise HTTPException(status_code=400, detail=f"Shipment already exists (AWB {order['tracking_id']}). Cancel it first if you want to re-ship.")
    pickup = await _nimbus_pickup()
    result = await nimbus.create_shipment(order, pickup)
    if not result["ok"]:
        raise HTTPException(status_code=502 if result.get("status") in (None, 502) else 400, detail=result["error"] or "NimbusPost error")

    body = result["data"] or {}
    # NimbusPost's response envelope varies slightly across endpoints:
    d = body.get("data") if isinstance(body.get("data"), dict) else body
    awb = str(d.get("awb_number") or d.get("awb") or d.get("shipment_id") or "").strip()
    courier = str(d.get("courier_name") or d.get("courier") or "NimbusPost")
    tracking_url = str(d.get("tracking_url") or (f"https://nimbuspost.com/track/{awb}" if awb else ""))
    if not awb:
        # Store raw response for debugging but surface a friendly error
        raise HTTPException(status_code=502, detail=f"NimbusPost returned no AWB: {str(body)[:300]}")

    update = {
        "tracking_id": awb,
        "tracking_carrier": courier,
        "tracking_url": tracking_url,
        "tracking_updated_at": now_iso(),
        "nimbuspost_response": d,
    }
    await db.orders.update_one({"order_number": order_number}, {"$set": update})
    doc = await db.orders.find_one({"order_number": order_number}, {"_id": 0})
    return {"ok": True, "awb": awb, "courier": courier, "tracking_url": tracking_url, "order": doc}


@api_router.get("/admin/orders/{order_number}/nimbuspost/track")
async def admin_nimbus_track(order_number: str, admin=Depends(require_permission("manage_orders"))):
    order = await db.orders.find_one({"order_number": order_number}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    awb = (order.get("tracking_id") or "").strip()
    if not awb:
        raise HTTPException(status_code=400, detail="No AWB — create a NimbusPost shipment first")
    result = await nimbus.track_shipment(awb)
    if not result["ok"]:
        raise HTTPException(status_code=502, detail=result["error"] or "NimbusPost tracking failed")
    return {"ok": True, "awb": awb, "data": result["data"]}


@api_router.post("/admin/orders/{order_number}/nimbuspost/cancel")
async def admin_nimbus_cancel(order_number: str, admin=Depends(require_permission("manage_orders"))):
    order = await db.orders.find_one({"order_number": order_number}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    awb = (order.get("tracking_id") or "").strip()
    if not awb:
        raise HTTPException(status_code=400, detail="No AWB to cancel")
    result = await nimbus.cancel_shipment(awb)
    if not result["ok"]:
        raise HTTPException(status_code=502, detail=result["error"] or "NimbusPost cancel failed")
    await db.orders.update_one(
        {"order_number": order_number},
        {"$set": {"tracking_id": None, "tracking_url": None, "tracking_updated_at": now_iso()}},
    )
    return {"ok": True, "data": result["data"]}


class NimbusServiceCheckIn(BaseModel):
    pincode: str
    cod: bool = False
    weight_g: int = 500
    origin: str = ""  # optional — falls back to configured origin_pincode


@api_router.post("/admin/nimbuspost/serviceability")
async def admin_nimbus_serviceability(payload: NimbusServiceCheckIn, admin=Depends(require_permission("manage_shipping"))):
    origin = (payload.origin or "").strip() or await _nimbus_origin_pincode()
    if not origin:
        raise HTTPException(status_code=400, detail="Origin pincode not set — add it in Admin → Shipping → NimbusPost")
    result = await nimbus.check_serviceability(payload.pincode, payload.cod, payload.weight_g, origin=origin)
    if not result["ok"]:
        raise HTTPException(status_code=502, detail=result["error"] or "NimbusPost serviceability failed")
    return result["data"]


# ------------ Batch 9 · NimbusPost webhook receiver (public, HMAC-verified) --
# Docs: https://ship.nimbuspost.com/webhook/add  →  X-Hmac-SHA256 header is
# base64(hmac_sha256(secret, raw_body)). Any 2xx response ACKs the delivery;
# non-2xx makes NimbusPost retry (up to 50 failures → auto-paused).
@api_router.post("/nimbuspost/webhook")
async def nimbuspost_webhook(request: Request):
    raw = await request.body()
    cfg = await load_site_setting("nimbuspost", DEFAULT_NIMBUS_CFG)
    secret = (cfg.get("webhook_secret") or os.getenv("NIMBUSPOST_WEBHOOK_SECRET") or "").strip()

    if secret:
        provided = request.headers.get("x-hmac-sha256") or request.headers.get("X-Hmac-SHA256") or ""
        digest = hmac.new(secret.encode(), raw, hashlib.sha256).digest()
        expected = base64.b64encode(digest).decode()
        if not hmac.compare_digest(provided.strip(), expected.strip()):
            _log_boot.warning("nimbuspost webhook: signature mismatch")
            raise HTTPException(status_code=401, detail="invalid signature")

    try:
        body = json.loads(raw.decode() or "{}")
    except Exception:
        body = {}

    awb = str(body.get("awb_number") or body.get("awb") or "").strip()
    status = str(body.get("status") or "").strip().lower()
    message = str(body.get("message") or "").strip()
    location = str(body.get("location") or "").strip()
    event_time = str(body.get("event_time") or "").strip() or now_iso()

    if not awb:
        return {"ok": True, "ignored": "no_awb"}

    order = await db.orders.find_one({"tracking_id": awb}, {"_id": 0, "id": 1, "order_number": 1, "status": 1})
    if not order:
        _log_boot.info("nimbuspost webhook: no order for AWB %s", awb)
        return {"ok": True, "ignored": "no_order"}

    # Map NimbusPost status → our internal order.status. Free-form so we don't
    # accidentally overwrite manual admin changes for statuses NimbusPost
    # doesn't own (e.g. "confirmed" pre-ship, "refunded" post-ship).
    status_map = {
        "manifested": "shipped",
        "in transit": "shipped",
        "in_transit": "shipped",
        "out for delivery": "shipped",
        "delivered": "delivered",
        "returned": "returned",
        "rto delivered": "returned",
        "rto in transit": "returned",
        "cancelled": "cancelled",
    }
    update: dict = {
        "tracking_updated_at": event_time,
        "nimbuspost_last_event": {"status": status, "message": message, "location": location, "at": event_time},
    }
    new_status = status_map.get(status)
    if new_status and order.get("status") not in ("delivered", "cancelled", "refunded"):
        update["status"] = new_status
    await db.orders.update_one({"tracking_id": awb}, {"$set": update})
    return {"ok": True, "order_number": order.get("order_number"), "applied_status": update.get("status")}




# =============================================================================
# ------------------ PHASE B: ANALYTICS, LIVE, RBAC, EMPLOYEES ----------------
# =============================================================================

# ---------- MODELS ----------
class EmployeeCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str] = ""
    permissions: List[str] = Field(default_factory=list)


class EmployeeUpdate(BaseModel):
    display_name: Optional[str] = None
    permissions: Optional[List[str]] = None
    password: Optional[str] = None  # optional password change


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class HeartbeatIn(BaseModel):
    session_id: str
    path: Optional[str] = "/"
    user_agent: Optional[str] = None


class PageviewIn(BaseModel):
    path: str
    session_id: Optional[str] = None
    referrer: Optional[str] = None


# ---------- ENSURE TTL INDEXES ----------
async def ensure_live_indexes():
    try:
        await db.live_sessions.create_index("expire_at", expireAfterSeconds=0)
        await db.live_sessions.create_index("session_id", unique=True)
        await db.page_views.create_index([("path", 1), ("day", 1)])
    except Exception as e:
        logging.warning(f"index creation warning: {e}")


# =============================================================================
# ------------------ ANALYTICS: OVERVIEW + ALERTS + LIVE ---------------------
# =============================================================================
def _iso_date(d: datetime) -> str:
    return d.strftime("%Y-%m-%d")


@api_router.get("/admin/analytics/overview")
async def analytics_overview(admin=Depends(require_permission("view_analytics"))):
    now = datetime.now(timezone.utc)
    day_30_ago = now - timedelta(days=30)

    orders = await db.orders.find({}, {"_id": 0}).to_list(5000)
    returns = await db.returns.find({}, {"_id": 0}).to_list(5000)

    # Order KPIs
    def _s(o): return o.get("status") or ""
    active_states = {"pending_payment", "confirmed", "packed", "shipped"}
    orders_total = len(orders)
    orders_active = sum(1 for o in orders if _s(o) in active_states)
    orders_success = sum(1 for o in orders if _s(o) == "delivered")
    orders_cancelled = sum(1 for o in orders if _s(o) == "cancelled")
    orders_failed = sum(1 for o in orders if _s(o) == "payment_failed")

    # Return KPIs
    ret_active_states = {"requested", "approved", "received"}
    ret_completed_states = {"refunded", "rejected"}
    returns_total = len(returns)
    returns_active = sum(1 for r in returns if r.get("status") in ret_active_states)
    returns_completed = sum(1 for r in returns if r.get("status") in ret_completed_states)

    # Financials
    revenue = sum(int(o.get("total_inr") or 0) for o in orders if _s(o) in ("delivered", "confirmed", "packed", "shipped"))
    products_total = await db.products.count_documents({})
    customers_total = await db.users.count_documents({})
    b2b_new = await db.b2b_leads.count_documents({
        "status": "new",
        "created_at": {"$gte": _iso_date(day_30_ago)},
    })
    failed_tx_total = await db.failed_payments.count_documents({})

    # Top products (by order count and review score)
    product_order_counts = {}
    product_revenue = {}
    for o in orders:
        if _s(o) in ("cancelled", "payment_failed", "pending_payment"):
            continue
        for it in (o.get("items") or []):
            pid = it.get("product_id")
            if not pid: continue
            product_order_counts[pid] = product_order_counts.get(pid, 0) + int(it.get("quantity") or 1)
            product_revenue[pid] = product_revenue.get(pid, 0) + int(it.get("subtotal_inr") or 0)

    # Review avg per product
    reviews_by_product = {}
    async for r in db.reviews.find({}, {"_id": 0}):
        pid = r.get("product_id")
        if not pid: continue
        reviews_by_product.setdefault(pid, []).append(int(r.get("rating") or 0))

    products = await db.products.find({}, {"_id": 0}).to_list(500)
    top_products = []
    for p in products:
        pid = p.get("id")
        r_list = reviews_by_product.get(pid, [])
        top_products.append({
            "id": pid,
            "name": p.get("name"),
            "image": (p.get("images") or [None])[0],
            "slug": p.get("slug"),
            "orders": product_order_counts.get(pid, 0),
            "revenue_inr": product_revenue.get(pid, 0),
            "avg_rating": round(sum(r_list) / len(r_list), 2) if r_list else 0,
            "review_count": len(r_list),
            "stock_count": p.get("stock_count", 0),
        })
    top_products.sort(key=lambda x: (x["orders"], x["avg_rating"], x["review_count"]), reverse=True)

    # 30-day time series (orders & revenue per day)
    series_map = {}
    for i in range(30):
        d = (now - timedelta(days=29 - i)).date()
        series_map[d.isoformat()] = {"date": d.isoformat(), "orders": 0, "revenue_inr": 0}
    for o in orders:
        try:
            d = datetime.fromisoformat((o.get("created_at") or "").replace("Z", "+00:00")).date().isoformat()
        except Exception:
            continue
        if d in series_map:
            series_map[d]["orders"] += 1
            if _s(o) not in ("cancelled", "payment_failed", "pending_payment"):
                series_map[d]["revenue_inr"] += int(o.get("total_inr") or 0)
    series = list(series_map.values())

    # Coupons total uses (per code)
    coupon_uses = {}
    for o in orders:
        code = o.get("coupon_code")
        if code:
            coupon_uses[code] = coupon_uses.get(code, 0) + 1
    coupons_summary = [{"code": c, "uses": n} for c, n in sorted(coupon_uses.items(), key=lambda x: -x[1])]

    return {
        "orders": {
            "total": orders_total,
            "active": orders_active,
            "successful": orders_success,
            "cancelled": orders_cancelled,
            "failed": orders_failed,
        },
        "returns": {
            "total": returns_total,
            "active": returns_active,
            "completed": returns_completed,
        },
        "financials": {
            "revenue_inr": revenue,
            "products_total": products_total,
            "customers_total": customers_total,
            "b2b_leads_new": b2b_new,
            "failed_transactions": failed_tx_total,
        },
        "top_products": top_products[:8],
        "series_30d": series,
        "coupons_summary": coupons_summary,
    }


@api_router.get("/admin/analytics/alerts")
async def analytics_alerts(admin=Depends(require_permission("view_analytics"))):
    now = datetime.now(timezone.utc)
    hour_1_ago = now - timedelta(hours=1)
    day_2_ago = now - timedelta(days=2)

    low_stock = []
    async for p in db.products.find({"stock_count": {"$lte": 3}}, {"_id": 0, "id": 1, "name": 1, "slug": 1, "stock_count": 1, "images": 1}):
        low_stock.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "slug": p.get("slug"),
            "stock_count": p.get("stock_count", 0),
            "image": (p.get("images") or [None])[0],
        })

    out_of_stock = sum(1 for p in low_stock if p["stock_count"] <= 0)

    old_pending_returns = []
    pending_returns = await db.returns.find({"status": "requested"}, {"_id": 0}).to_list(500)
    for r in pending_returns:
        try:
            created = datetime.fromisoformat(r.get("created_at", "").replace("Z", "+00:00"))
            if created < day_2_ago:
                old_pending_returns.append({
                    "id": r.get("id"),
                    "order_number": r.get("order_number"),
                    "hours_old": int((now - created).total_seconds() / 3600),
                })
        except Exception:
            continue

    recent_failures = await db.failed_payments.count_documents({"created_at": {"$gte": hour_1_ago.isoformat().replace("+00:00", "Z")}})

    return {
        "low_stock_products": low_stock,
        "out_of_stock_count": out_of_stock,
        "old_pending_returns": old_pending_returns,
        "recent_failed_payments_1h": recent_failures,
    }


@api_router.get("/admin/analytics/coupon-usage")
async def analytics_coupon_usage(admin=Depends(require_permission("view_analytics"))):
    """Return per-code totals and per-customer usage breakdown."""
    per_code = {}
    per_customer = {}
    async for o in db.orders.find({"coupon_code": {"$ne": None}}, {"_id": 0, "coupon_code": 1, "customer.email": 1, "customer.name": 1, "total_inr": 1, "discount_inr": 1, "order_number": 1, "created_at": 1}):
        code = o.get("coupon_code")
        if not code: continue
        email = (o.get("customer") or {}).get("email") or "guest"
        name = (o.get("customer") or {}).get("name") or ""
        per_code[code] = per_code.get(code, 0) + 1
        key = f"{email}::{code}"
        entry = per_customer.get(key) or {"customer_email": email, "customer_name": name, "code": code, "uses": 0, "total_discount_inr": 0, "last_used_at": None, "orders": []}
        entry["uses"] += 1
        entry["total_discount_inr"] += int(o.get("discount_inr") or 0)
        entry["orders"].append(o.get("order_number"))
        # Track most-recent
        ca = o.get("created_at") or ""
        if not entry["last_used_at"] or ca > entry["last_used_at"]:
            entry["last_used_at"] = ca
        per_customer[key] = entry

    codes = [{"code": c, "uses": n} for c, n in sorted(per_code.items(), key=lambda x: -x[1])]
    customers = sorted(per_customer.values(), key=lambda x: -x["uses"])
    return {"codes": codes, "customers": customers}


@api_router.get("/admin/analytics/wishlist-usage")
async def analytics_wishlist_usage(admin=Depends(require_permission("view_analytics"))):
    """Return wishlist entries grouped by customer + by product."""
    entries = []
    per_customer = {}
    per_product = {}
    async for w in db.wishlist.find({}, {"_id": 0}):
        email = w.get("user_email") or w.get("email") or ""
        pid = w.get("product_id") or ""
        prod = await db.products.find_one({"id": pid}, {"_id": 0, "name": 1, "slug": 1, "images": 1, "price_inr": 1, "id": 1}) if pid else None
        row = {
            "user_email": email,
            "product_id": pid,
            "product_name": (prod or {}).get("name") or "(unknown)",
            "product_slug": (prod or {}).get("slug") or "",
            "product_image": ((prod or {}).get("images") or [None])[0],
            "created_at": w.get("created_at"),
        }
        entries.append(row)
        per_customer.setdefault(email, []).append(row)
        per_product.setdefault(pid, {"product_id": pid, "product_name": row["product_name"], "product_image": row["product_image"], "count": 0, "customers": []})
        per_product[pid]["count"] += 1
        per_product[pid]["customers"].append(email)

    customers = [{"user_email": e, "count": len(rows), "items": rows} for e, rows in per_customer.items()]
    customers.sort(key=lambda x: -x["count"])
    products = sorted(per_product.values(), key=lambda x: -x["count"])
    return {"total_wishlists": len(entries), "by_customer": customers, "by_product": products}


# =============================================================================
# ------------------ LIVE ANALYTICS -----------------------------------------
# =============================================================================
@api_router.post("/analytics/heartbeat")
async def analytics_heartbeat(payload: HeartbeatIn):
    """Public. Frontend calls every ~20s. Upserts a live_sessions doc with TTL."""
    now = datetime.now(timezone.utc)
    expire_at = now + timedelta(seconds=45)
    await db.live_sessions.update_one(
        {"session_id": payload.session_id},
        {"$set": {
            "session_id": payload.session_id,
            "path": payload.path or "/",
            "user_agent": (payload.user_agent or "")[:200],
            "last_seen": now,
            "expire_at": expire_at,
        }},
        upsert=True,
    )
    return {"ok": True}


@api_router.post("/analytics/pageview")
async def analytics_pageview(payload: PageviewIn):
    """Public. Counts a page-view for the day."""
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await db.page_views.update_one(
        {"path": payload.path, "day": day},
        {"$inc": {"count": 1}, "$setOnInsert": {"path": payload.path, "day": day}},
        upsert=True,
    )
    return {"ok": True}


@api_router.get("/admin/analytics/live")
async def analytics_live(admin=Depends(require_permission("view_analytics"))):
    """Active sessions (within TTL window) + top-visited paths."""
    now = datetime.now(timezone.utc)
    active_docs = await db.live_sessions.find({"expire_at": {"$gt": now}}, {"_id": 0}).to_list(2000)
    active_users = len(active_docs)

    # Top paths from active sessions
    page_counts = {}
    for d in active_docs:
        p = d.get("path") or "/"
        page_counts[p] = page_counts.get(p, 0) + 1
    top_now = sorted([{"path": p, "count": c} for p, c in page_counts.items()], key=lambda x: -x["count"])[:10]

    # Top pages in last 24h from page_views collection
    day_today = now.strftime("%Y-%m-%d")
    day_yest = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    day_totals = {}
    async for pv in db.page_views.find({"day": {"$in": [day_today, day_yest]}}, {"_id": 0}):
        p = pv.get("path") or "/"
        day_totals[p] = day_totals.get(p, 0) + int(pv.get("count") or 0)
    top_24h = sorted([{"path": p, "count": c} for p, c in day_totals.items()], key=lambda x: -x["count"])[:10]

    return {
        "active_users": active_users,
        "sessions_now_by_path": top_now,
        "top_pages_24h": top_24h,
        "as_of": now.isoformat().replace("+00:00", "Z"),
    }


# =============================================================================
# ------------------ RBAC: EMPLOYEES + PASSWORD -----------------------------
# =============================================================================
@api_router.get("/admin/permissions")
async def admin_list_permissions(admin=Depends(get_current_admin)):
    """Catalog of permission keys for the admin UI to render checkboxes."""
    return {"all": ALL_PERMISSIONS}


@api_router.get("/admin/employees")
async def admin_list_employees(admin=Depends(require_permission("manage_employees"))):
    """Only lists employees (not the owner)."""
    docs = await db.admins.find({"role": {"$ne": "owner"}}, {"_id": 0, "password_hash": 0}).to_list(500)
    return docs


@api_router.post("/admin/employees")
async def admin_create_employee(payload: EmployeeCreate, admin=Depends(require_permission("manage_employees"))):
    email = payload.email.lower()
    if await db.admins.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="An admin with this email already exists")
    invalid = [p for p in payload.permissions if p not in ALL_PERMISSIONS]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unknown permissions: {invalid}")
    pw_hash = bcrypt.hashpw(payload.password.encode(), bcrypt.gensalt()).decode()
    doc = {
        "id": str(uuid.uuid4()),
        "email": email,
        "password_hash": pw_hash,
        "display_name": payload.display_name or "",
        "role": "employee",
        "permissions": payload.permissions,
        "created_at": now_iso(),
    }
    await db.admins.insert_one(doc)
    doc.pop("password_hash", None)
    doc.pop("_id", None)
    return doc


@api_router.patch("/admin/employees/{employee_id}")
async def admin_update_employee(employee_id: str, payload: EmployeeUpdate, admin=Depends(require_permission("manage_employees"))):
    existing = await db.admins.find_one({"id": employee_id, "role": {"$ne": "owner"}})
    if not existing:
        raise HTTPException(status_code=404, detail="Employee not found")
    update = {}
    if payload.display_name is not None:
        update["display_name"] = payload.display_name
    if payload.permissions is not None:
        invalid = [p for p in payload.permissions if p not in ALL_PERMISSIONS]
        if invalid:
            raise HTTPException(status_code=400, detail=f"Unknown permissions: {invalid}")
        update["permissions"] = payload.permissions
    if payload.password:
        update["password_hash"] = bcrypt.hashpw(payload.password.encode(), bcrypt.gensalt()).decode()
    if not update:
        raise HTTPException(status_code=400, detail="Nothing to update")
    await db.admins.update_one({"id": employee_id}, {"$set": update})
    doc = await db.admins.find_one({"id": employee_id}, {"_id": 0, "password_hash": 0})
    return doc


@api_router.delete("/admin/employees/{employee_id}")
async def admin_delete_employee(employee_id: str, admin=Depends(require_permission("manage_employees"))):
    existing = await db.admins.find_one({"id": employee_id, "role": {"$ne": "owner"}})
    if not existing:
        raise HTTPException(status_code=404, detail="Employee not found")
    await db.admins.delete_one({"id": employee_id})
    return {"deleted": True}


@api_router.patch("/admin/me/password")
async def admin_change_password(payload: PasswordChange, admin=Depends(get_current_admin)):
    doc = await db.admins.find_one({"email": admin["email"]})
    if not doc or not bcrypt.checkpw(payload.current_password.encode(), doc["password_hash"].encode()):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    pw_hash = bcrypt.hashpw(payload.new_password.encode(), bcrypt.gensalt()).decode()
    await db.admins.update_one({"email": admin["email"]}, {"$set": {"password_hash": pw_hash, "password_changed_at": now_iso()}})
    return {"ok": True}


# ==== Phase A (Jul 2025) · Cloudinary + Admin Google Login + Whitelist + Notify ====

@api_router.get("/cloudinary/signature")
async def cloudinary_signature(
    folder: str = "artyfex",
    resource_type: str = "image",
    public_id: Optional[str] = None,
    admin=Depends(get_current_admin),
):
    """Generate signed upload params for direct browser-to-Cloudinary upload.

    If `public_id` is passed (e.g. a SHA-1 hash of file contents), we sign it
    with overwrite=false → Cloudinary will silently reuse an existing asset
    with the same public_id rather than storing a duplicate. This is our
    content-based dedup mechanism (Task 1)."""
    if not CLOUDINARY_CLOUD_NAME or not CLOUDINARY_API_KEY or not CLOUDINARY_API_SECRET:
        raise HTTPException(status_code=500, detail="Cloudinary not configured")
    if resource_type not in ("image", "video"):
        raise HTTPException(status_code=400, detail="resource_type must be image or video")
    # Whitelist folder prefixes to prevent free-form upload paths.
    if not folder.startswith("artyfex"):
        raise HTTPException(status_code=400, detail="Invalid folder path")
    ts = int(time.time())
    params_to_sign: dict = {"timestamp": ts, "folder": folder}
    if public_id:
        # Sanitise: only allow letters/digits/dashes/underscore
        clean_pid = re.sub(r"[^a-zA-Z0-9_-]", "", public_id)[:64]
        if clean_pid:
            params_to_sign["public_id"] = clean_pid
            params_to_sign["overwrite"] = "false"
            params_to_sign["invalidate"] = "true"
    signature = cloudinary.utils.api_sign_request(params_to_sign, CLOUDINARY_API_SECRET)
    return {
        "signature": signature,
        "timestamp": ts,
        "cloud_name": CLOUDINARY_CLOUD_NAME,
        "api_key": CLOUDINARY_API_KEY,
        "folder": folder,
        "resource_type": resource_type,
        "public_id": params_to_sign.get("public_id"),
        "overwrite": params_to_sign.get("overwrite"),
        "invalidate": params_to_sign.get("invalidate"),
    }


def _cloudinary_public_id_from_url(url: str) -> Optional[str]:
    """Extract the Cloudinary public_id (including folder path) from a secure_url.

    Ex: https://res.cloudinary.com/<cloud>/image/upload/v123456/artyfex/homepage/hash.jpg
       → "artyfex/homepage/hash"
    Returns None if the URL isn't a Cloudinary asset for our cloud.
    """
    if not url or "res.cloudinary.com" not in url:
        return None
    try:
        # After /upload/ (optionally /v<digits>/) the rest is <public_id>.<ext>
        parts = url.split("/upload/", 1)
        if len(parts) != 2:
            return None
        tail = parts[1]
        # Strip optional version prefix "v123456/"
        tail = re.sub(r"^v\d+/", "", tail)
        # Strip file extension
        tail = re.sub(r"\.[a-zA-Z0-9]+$", "", tail)
        # Strip any transformation prefix (rare, but just in case)
        return tail or None
    except Exception:
        return None


# ------------ Batch 5 (Jul 2026) — Orphan Cloudinary cleanup ---------------
# When a product / homepage / any document with image URLs is UPDATED or
# DELETED, we compute the set of Cloudinary URLs present BEFORE vs AFTER and
# fire-and-forget destroy() the ones removed. Runs off the request path via
# BackgroundTasks so callers stay fast.

def _extract_cloudinary_urls(node) -> set[str]:
    """Recursively walk a dict/list and return every Cloudinary secure_url found."""
    out: set[str] = set()
    if node is None:
        return out
    if isinstance(node, str):
        if "res.cloudinary.com" in node:
            out.add(node)
        return out
    if isinstance(node, dict):
        for v in node.values():
            out |= _extract_cloudinary_urls(v)
        return out
    if isinstance(node, (list, tuple, set)):
        for v in node:
            out |= _extract_cloudinary_urls(v)
        return out
    return out


def _destroy_cloudinary_url(url: str) -> None:
    """Best-effort Cloudinary destroy — never raises. Called from BackgroundTasks."""
    if not (CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET):
        return
    pid = _cloudinary_public_id_from_url(url)
    if not pid:
        return
    try:
        cloudinary.uploader.destroy(pid, invalidate=True)
    except Exception as e:  # pragma: no cover
        _log_boot.warning("cloudinary destroy failed for %s: %s", pid, e)


def _destroy_url_diff(old_urls: set[str], new_urls: set[str]) -> None:
    """Delete the URLs that were in `old_urls` but not in `new_urls`."""
    for url in (old_urls - new_urls):
        _destroy_cloudinary_url(url)
# ---------------------------------------------------------------------------


@api_router.delete("/cloudinary/asset")
async def cloudinary_destroy(url: str, admin=Depends(get_current_admin)):
    """Delete a Cloudinary asset by its secure_url. Called by the admin
    image-uploader when the user removes an image, so we don't accumulate
    dead assets (Task 1)."""
    if not CLOUDINARY_CLOUD_NAME or not CLOUDINARY_API_KEY or not CLOUDINARY_API_SECRET:
        raise HTTPException(status_code=500, detail="Cloudinary not configured")
    public_id = _cloudinary_public_id_from_url(url)
    if not public_id:
        raise HTTPException(status_code=400, detail="Not a Cloudinary URL")
    try:
        result = cloudinary.uploader.destroy(public_id, invalidate=True)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Cloudinary destroy failed: {e}")
    return {"public_id": public_id, "result": result.get("result", "unknown")}


# --- Admin whitelist (Google login access) ---
class AdminWhitelistIn(BaseModel):
    email: EmailStr
    note: Optional[str] = None


async def _get_admin_whitelist() -> set[str]:
    docs = await db.admin_whitelist.find({}, {"_id": 0}).to_list(500)
    emails = {(d.get("email") or "").lower().strip() for d in docs}
    emails.update(e.lower() for e in DEFAULT_ADMIN_WHITELIST)
    # Existing seeded admin (email/password owner) is always allowed.
    if ADMIN_EMAIL:
        emails.add(ADMIN_EMAIL.lower())
    return {e for e in emails if e}


@api_router.get("/admin/whitelist")
async def admin_list_whitelist(admin=Depends(get_current_admin)):
    docs = await db.admin_whitelist.find({}, {"_id": 0}).sort("created_at", 1).to_list(500)
    # Also surface the built-in defaults so admins see the full picture
    default_entries = [
        {"id": f"default-{e}", "email": e, "note": "Built-in owner", "created_at": None, "readonly": True}
        for e in sorted(DEFAULT_ADMIN_WHITELIST)
        if not any((d.get("email") or "").lower() == e for d in docs)
    ]
    return default_entries + docs


@api_router.post("/admin/whitelist")
async def admin_add_whitelist(payload: AdminWhitelistIn, admin=Depends(require_permission("manage_employees"))):
    email = payload.email.lower().strip()
    if await db.admin_whitelist.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already whitelisted")
    doc = {
        "id": str(uuid.uuid4()),
        "email": email,
        "note": payload.note or "",
        "created_at": now_iso(),
        "added_by": admin.get("email"),
        "readonly": False,
    }
    await db.admin_whitelist.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api_router.delete("/admin/whitelist/{wl_id}")
async def admin_delete_whitelist(wl_id: str, admin=Depends(require_permission("manage_employees"))):
    if wl_id.startswith("default-"):
        raise HTTPException(status_code=400, detail="Built-in owner emails cannot be removed")
    res = await db.admin_whitelist.delete_one({"id": wl_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"deleted": True}


# --- Admin Google Login (bridges Emergent session_id → admin JWT if whitelisted) ---
class AdminGoogleSessionIn(BaseModel):
    session_id: str


@api_router.post("/admin/auth/google")
@limiter.limit("10/minute")
async def admin_google_login(request: Request, payload: AdminGoogleSessionIn):
    if not payload.session_id or not payload.session_id.strip():
        raise HTTPException(status_code=400, detail="session_id is required")
    # Fetch profile from Emergent auth
    try:
        async with httpx.AsyncClient(timeout=15.0) as cx:
            r = await cx.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": payload.session_id.strip()},
            )
    except Exception as _e:
        raise HTTPException(status_code=502, detail="Auth provider unreachable")
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google session")
    data = r.json() or {}
    email = (data.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")
    allowed = await _get_admin_whitelist()
    if email not in allowed:
        raise HTTPException(status_code=403, detail="This Google account is not authorized for admin access")
    # Load or create an admin doc for this email (as owner if built-in default, else employee)
    admin_doc = await db.admins.find_one({"email": email})
    is_default_owner = email in {e.lower() for e in DEFAULT_ADMIN_WHITELIST} or email == ADMIN_EMAIL.lower()
    if not admin_doc:
        admin_doc = {
            "id": str(uuid.uuid4()),
            "email": email,
            "display_name": data.get("name") or email.split("@")[0],
            "auth_provider": "google",
            "password_hash": bcrypt.hashpw(str(uuid.uuid4()).encode(), bcrypt.gensalt()).decode(),
            "role": "owner" if is_default_owner else "employee",
            "permissions": list(ALL_PERMISSIONS) if is_default_owner else ["view_analytics"],
            "created_at": now_iso(),
        }
        await db.admins.insert_one(admin_doc)
    else:
        # Ensure owner status for built-in emails
        if is_default_owner and admin_doc.get("role") != "owner":
            await db.admins.update_one({"email": email}, {"$set": {"role": "owner", "permissions": list(ALL_PERMISSIONS)}})
            admin_doc = await db.admins.find_one({"email": email})
    admin_doc.pop("_id", None)
    admin_doc.pop("password_hash", None)
    token = create_token(email, role="admin")
    return {"token": token, "admin": admin_doc}


# --- Admin custom email notify (per-order + broadcast) ---
class OrderNotifyIn(BaseModel):
    subject: str
    body_html: str


@api_router.post("/admin/orders/{order_number}/notify")
async def admin_notify_order(order_number: str, payload: OrderNotifyIn, admin=Depends(require_permission("manage_orders"))):
    order = await db.orders.find_one({"order_number": order_number}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if not payload.subject.strip() or not payload.body_html.strip():
        raise HTTPException(status_code=400, detail="Subject and body are required")
    asyncio.create_task(send_order_email(order, "custom", custom_subject=payload.subject.strip(), custom_body_html=payload.body_html))
    return {"queued": True}


class BroadcastIn(BaseModel):
    subject: str
    body_html: str
    audience: str = "all_customers"  # future: filters


@api_router.post("/admin/broadcast")
async def admin_broadcast(payload: BroadcastIn, admin=Depends(require_permission("manage_customers"))):
    if not payload.subject.strip() or not payload.body_html.strip():
        raise HTTPException(status_code=400, detail="Subject and body are required")
    users = await db.users.find({"email": {"$exists": True}}, {"_id": 0, "email": 1, "name": 1}).to_list(5000)
    seen: set = set()
    queued = 0
    for u in users:
        em = (u.get("email") or "").lower().strip()
        if not em or em in seen:
            continue
        seen.add(em)
        fake_order = {
            "order_number": "",
            "customer": {"name": u.get("name") or em.split("@")[0], "email": em},
            "items": [],
        }
        asyncio.create_task(send_order_email(fake_order, "custom", custom_subject=payload.subject.strip(), custom_body_html=payload.body_html))
        queued += 1
    return {"queued": queued}


# --- CORS ---------------------------------------------------------------------
# Wildcard + credentials is unsafe because browsers will accept credentialed
# requests from *any* origin. We normalise the env to a strict allowlist in
# production. In dev/preview we keep the wildcard but strip credentials.
_raw_origins = [o.strip() for o in os.environ.get('CORS_ORIGINS', '*').split(',') if o.strip()]
_default_prod_origins = [
    "https://www.artyfex.in",
    "https://artyfex.in",
]
if _raw_origins == ['*'] and _is_prod:
    _log_boot.warning("CORS_ORIGINS='*' in production — narrowing to known ArtyFex domains only. Set CORS_ORIGINS to your real frontend origins to silence this.")
    _cors_allow_origins = list(_default_prod_origins)
    _cors_allow_credentials = True
elif _raw_origins == ['*']:
    # Dev / preview — allow all but forbid credentialed requests (per spec)
    _cors_allow_origins = ["*"]
    _cors_allow_credentials = False
else:
    _cors_allow_origins = _raw_origins
    _cors_allow_credentials = True

# Regex fallback: any Vercel preview deployment for this project should also work.
# Vercel preview URLs look like https://<project>-<hash>-<team>.vercel.app.
_cors_allow_origin_regex = r"https://.*\.vercel\.app$"

app.add_middleware(
    CORSMiddleware,
    allow_credentials=_cors_allow_credentials,
    allow_origins=_cors_allow_origins,
    allow_origin_regex=_cors_allow_origin_regex,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
    max_age=3600,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# =============================================================================
# ---------- PHASE B5: DYNAMIC-PAGE CMS + LEGAL COMPLIANCE ----------
# =============================================================================
# Admin-editable pages (Privacy, Terms, Shipping, Returns, About… anything).
# Each page is a list of "blocks" so a non-technical admin can drop in headings,
# paragraphs and Cloudinary-hosted images without writing HTML.
#
# Public endpoints:
#   GET /api/pages              → published pages, minimal fields (for header/footer)
#   GET /api/pages/{slug}       → single published page (full body)
# Admin endpoints (permission: manage_homepage):
#   GET /api/admin/pages, POST, GET/PATCH/DELETE /admin/pages/{id}
#   POST /api/admin/pages/reorder {ids:[...]}

class PageBlock(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # type: heading | paragraph | image | cta | divider | quote | list
    type: str
    # Free-form fields — different block types use different subsets.
    text: Optional[str] = None      # heading, paragraph, cta label, quote, list item joiner
    html: Optional[str] = None      # rich paragraph (safe HTML)
    level: Optional[int] = 2        # heading level 1-4
    url: Optional[str] = None       # image src, cta href
    alt: Optional[str] = None       # image alt text
    caption: Optional[str] = None   # image caption
    items: Optional[List[str]] = None  # bullet-list items
    align: Optional[str] = None     # left | center | right


class PageIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    slug: str
    title: str
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    blocks: List[PageBlock] = Field(default_factory=list)
    published: bool = True
    show_in_header: bool = False
    show_in_footer: bool = True
    header_order: int = 100


class Page(PageIn):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


DEFAULT_PAGES = [
    {
        "slug": "privacy-policy",
        "title": "Privacy Policy",
        "meta_title": "Privacy Policy · ArtyFex",
        "meta_description": "How ArtyFex collects, uses and protects your personal data. GDPR-aligned. PCI-DSS compliant checkout via Razorpay.",
        "show_in_header": False,
        "show_in_footer": True,
        "header_order": 10,
        "blocks": [
            {"type": "paragraph", "html": "<em>Last updated: July 2025.</em> ArtyFex Atelier (\"ArtyFex\", \"we\", \"our\") respects your privacy. This policy explains what we collect, why, and your rights."},
            {"type": "heading", "level": 2, "text": "1. Data we collect"},
            {"type": "paragraph", "html": "When you register or place an order we collect your name, email, phone, shipping address, and (via Razorpay) payment metadata. We never store your full card or UPI details on our servers."},
            {"type": "heading", "level": 2, "text": "2. How we use it"},
            {"type": "list", "items": [
                "To fulfil your order — payment, packaging, shipping, and post-delivery support.",
                "To personalise your account (wishlist, saved addresses, order history).",
                "To send transactional emails (Order Placed / Dispatched / Delivered) via Resend.",
                "For internal analytics (aggregated, anonymised — no advertising cookies).",
            ]},
            {"type": "heading", "level": 2, "text": "3. Cookies"},
            {"type": "paragraph", "html": "We use minimal, first-party cookies to keep you logged in and remember your cart. No third-party advertising trackers are used."},
            {"type": "heading", "level": 2, "text": "4. Data sharing"},
            {"type": "paragraph", "html": "We share order details only with our payment processor (Razorpay), shipping carrier, and email provider (Resend) — all bound by their own privacy commitments. We never sell your data."},
            {"type": "heading", "level": 2, "text": "5. Your rights"},
            {"type": "paragraph", "html": "You may request access, correction, or deletion of your data at any time by emailing <a class=\"text-gold underline\" href=\"mailto:privacy@artyfex.in\">privacy@artyfex.in</a>. We respond within 7 working days."},
            {"type": "heading", "level": 2, "text": "6. Contact"},
            {"type": "paragraph", "html": "For any privacy question: <a class=\"text-gold underline\" href=\"mailto:privacy@artyfex.in\">privacy@artyfex.in</a>. Postal: ArtyFex Atelier, Mumbai, Maharashtra, India."},
        ],
    },
    {
        "slug": "terms-and-conditions",
        "title": "Terms & Conditions",
        "meta_title": "Terms & Conditions · ArtyFex",
        "meta_description": "The rules that govern your use of ArtyFex.in and the pieces we sell. Please read before placing an order.",
        "show_in_header": False,
        "show_in_footer": True,
        "header_order": 20,
        "blocks": [
            {"type": "paragraph", "html": "<em>Last updated: July 2025.</em> By accessing artyfex.in or placing an order, you agree to these Terms."},
            {"type": "heading", "level": 2, "text": "1. Bespoke, made-to-order nature"},
            {"type": "paragraph", "html": "Every ArtyFex mirror is poured by hand. Because each piece is one-of-a-kind, minor variations in colour depth, crystal placement and grain are part of the craft — never a defect."},
            {"type": "heading", "level": 2, "text": "2. Pricing & GST"},
            {"type": "paragraph", "html": "All prices are in Indian Rupees (₹) and exclusive of GST. GST (as per current HSN classification) is added at checkout and shown on your final invoice."},
            {"type": "heading", "level": 2, "text": "3. Payment"},
            {"type": "paragraph", "html": "We accept UPI, Cards, Netbanking and Wallets through Razorpay (PCI-DSS compliant). Cash-on-Delivery is available in select pincodes."},
            {"type": "heading", "level": 2, "text": "4. Cancellations"},
            {"type": "paragraph", "html": "Orders may be cancelled free of charge within 12 hours of placement. Once production has started, cancellations attract a 20% studio-time fee. Cancelled orders are refunded to the original payment method within 7 working days."},
            {"type": "heading", "level": 2, "text": "5. Governing law"},
            {"type": "paragraph", "html": "These terms are governed by the laws of India. Disputes fall under the exclusive jurisdiction of the courts of Mumbai, Maharashtra."},
        ],
    },
    {
        "slug": "shipping-policy",
        "title": "Shipping Policy",
        "meta_title": "Shipping & Delivery · ArtyFex",
        "meta_description": "White-glove insured delivery across India. Lead times, carriers, and free-shipping thresholds explained.",
        "show_in_header": False,
        "show_in_footer": True,
        "header_order": 30,
        "blocks": [
            {"type": "paragraph", "html": "Every ArtyFex mirror is shipped in custom-built triple-wall crating, fully insured, and (in most metros) hand-delivered by our white-glove partners."},
            {"type": "heading", "level": 2, "text": "Lead time"},
            {"type": "list", "items": [
                "In-stock signature editions: dispatch within 3–5 working days.",
                "Made-to-order & custom sizes: 4–6 weeks of studio time, then dispatch.",
                "You'll receive live tracking as soon as the crate leaves our atelier.",
            ]},
            {"type": "heading", "level": 2, "text": "Where we ship"},
            {"type": "paragraph", "html": "Across all Indian pincodes. International shipping is available on request — please <a class=\"text-gold underline\" href=\"/contact\">contact us</a> for a bespoke quote."},
            {"type": "heading", "level": 2, "text": "Shipping charges"},
            {"type": "paragraph", "html": "Live rates are calculated at checkout based on your pincode, weight and packaging dimensions. Orders above ₹25,000 ship free anywhere in India."},
        ],
    },
    {
        "slug": "refund-and-return-policy",
        "title": "Refund & Return Policy",
        "meta_title": "Refunds & Returns · ArtyFex",
        "meta_description": "Our transparent 3-day return window for damage-in-transit, plus refund timelines and process.",
        "show_in_header": False,
        "show_in_footer": True,
        "header_order": 40,
        "blocks": [
            {"type": "paragraph", "html": "Because each piece is hand-poured, returns are limited to <strong>damage in transit</strong> only. We do not accept change-of-mind returns."},
            {"type": "heading", "level": 2, "text": "Return window"},
            {"type": "paragraph", "html": "You have <strong>3 days from delivery</strong> to raise a damage claim. After 3 days the sale is considered final."},
            {"type": "heading", "level": 2, "text": "How to claim"},
            {"type": "list", "items": [
                "Log in and open your Account → Returns tab.",
                "Choose the affected order and describe the damage.",
                "Attach clear photos showing the damage AND the original packaging.",
                "Our team reviews within 24h and confirms next steps.",
            ]},
            {"type": "heading", "level": 2, "text": "Refunds"},
            {"type": "paragraph", "html": "Once a return is approved and the piece is received back at the atelier, refunds are issued to the original payment method within 7 working days. For Razorpay payments, credit may take 3–5 additional business days to reflect on your statement."},
        ],
    },
    {
        "slug": "cookie-policy",
        "title": "Cookie Policy",
        "meta_title": "Cookie Policy · ArtyFex",
        "meta_description": "The minimal cookies we use to keep you logged in, remember your cart, and understand aggregate site health.",
        "show_in_header": False,
        "show_in_footer": True,
        "header_order": 50,
        "blocks": [
            {"type": "paragraph", "html": "We use only what's strictly necessary."},
            {"type": "heading", "level": 2, "text": "What we set"},
            {"type": "list", "items": [
                "Session cookie (keeps you logged in — expires when you log out).",
                "Cart cookie (remembers your bag between visits).",
                "Anonymous session-id (local storage, live-analytics only — never sold or shared).",
            ]},
            {"type": "heading", "level": 2, "text": "What we DO NOT do"},
            {"type": "list", "items": [
                "No third-party advertising trackers.",
                "No cross-site behavioural profiling.",
                "No selling of usage data to data brokers.",
            ]},
            {"type": "paragraph", "html": "Cookies can be cleared any time from your browser settings without affecting your account."},
        ],
    },
]


async def _seed_default_pages():
    for pg in DEFAULT_PAGES:
        exists = await db.pages.find_one({"slug": pg["slug"]}, {"_id": 0})
        if exists:
            continue
        doc = Page(**pg).model_dump()
        await db.pages.insert_one(doc)
    # Unique index on slug
    try:
        await db.pages.create_index("slug", unique=True)
    except Exception:
        pass


# ---------- PUBLIC PAGE ENDPOINTS ----------
@api_router.get("/pages")
async def public_list_pages():
    """Published pages — lightweight listing for header/footer link rendering."""
    docs = await db.pages.find(
        {"published": True},
        {"_id": 0, "slug": 1, "title": 1, "show_in_header": 1, "show_in_footer": 1, "header_order": 1, "meta_title": 1, "meta_description": 1},
    ).sort("header_order", 1).to_list(200)
    return docs


@api_router.get("/pages/{slug}")
async def public_get_page(slug: str):
    doc = await db.pages.find_one({"slug": slug, "published": True}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Page not found")
    return doc


# ---------- ADMIN PAGE ENDPOINTS ----------
@api_router.get("/admin/pages")
async def admin_list_pages(admin=Depends(require_permission("manage_homepage"))):
    return await db.pages.find({}, {"_id": 0}).sort("header_order", 1).to_list(500)


@api_router.get("/admin/pages/{page_id}")
async def admin_get_page(page_id: str, admin=Depends(require_permission("manage_homepage"))):
    doc = await db.pages.find_one({"id": page_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Page not found")
    return doc


def _slugify(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "untitled"


@api_router.post("/admin/pages", response_model=Page)
async def admin_create_page(payload: PageIn, admin=Depends(require_permission("manage_homepage"))):
    slug = _slugify(payload.slug or payload.title)
    if await db.pages.find_one({"slug": slug}):
        raise HTTPException(status_code=400, detail=f"A page with slug '{slug}' already exists.")
    data = payload.model_dump()
    data["slug"] = slug
    page = Page(**data)
    await db.pages.insert_one(page.model_dump())
    return page


@api_router.patch("/admin/pages/{page_id}", response_model=Page)
async def admin_update_page(page_id: str, payload: PageIn, admin=Depends(require_permission("manage_homepage"))):
    existing = await db.pages.find_one({"id": page_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Page not found")
    slug = _slugify(payload.slug or payload.title)
    if slug != existing.get("slug"):
        if await db.pages.find_one({"slug": slug, "id": {"$ne": page_id}}):
            raise HTTPException(status_code=400, detail=f"A page with slug '{slug}' already exists.")
    data = payload.model_dump()
    data["slug"] = slug
    data["updated_at"] = now_iso()
    await db.pages.update_one({"id": page_id}, {"$set": data})
    merged = {**existing, **data}
    return Page(**merged)


@api_router.delete("/admin/pages/{page_id}")
async def admin_delete_page(page_id: str, admin=Depends(require_permission("manage_homepage"))):
    res = await db.pages.delete_one({"id": page_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Page not found")
    return {"deleted": True}


@api_router.post("/admin/pages/reorder")
async def admin_reorder_pages(payload: dict, admin=Depends(require_permission("manage_homepage"))):
    ids = payload.get("ids") or []
    if not isinstance(ids, list):
        raise HTTPException(status_code=400, detail="ids[] required")
    for idx, pid in enumerate(ids):
        await db.pages.update_one({"id": pid}, {"$set": {"header_order": idx * 10, "updated_at": now_iso()}})
    return {"reordered": len(ids)}


# =============================================================================
# ---------- PHASE B4: SEO ENDPOINTS (sitemap.xml + robots.txt) ----------
# =============================================================================
# Build a valid, dynamic sitemap from products + pages + static routes.
# Public URLs (no /api prefix here — served through the frontend proxy path).

def _get_site_origin() -> str:
    return (os.environ.get("SITE_URL") or "https://www.artyfex.in").rstrip("/")


@api_router.get("/seo/sitemap.xml")
async def seo_sitemap():
    from fastapi.responses import Response
    origin = _get_site_origin()
    urls = []
    now = now_iso().split("T")[0]
    # Static
    for path in ["/", "/shop", "/about", "/contact"]:
        urls.append((path, now, "weekly", "0.9" if path == "/" else "0.7"))
    # Products
    for p in await db.products.find({}, {"_id": 0, "slug": 1, "updated_at": 1}).to_list(500):
        slug = p.get("slug")
        if not slug:
            continue
        lastmod = (p.get("updated_at") or now).split("T")[0]
        urls.append((f"/product/{slug}", lastmod, "weekly", "0.8"))
    # Dynamic CMS pages
    for pg in await db.pages.find({"published": True}, {"_id": 0, "slug": 1, "updated_at": 1}).to_list(200):
        lastmod = (pg.get("updated_at") or now).split("T")[0]
        urls.append((f"/p/{pg['slug']}", lastmod, "monthly", "0.5"))
    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, lastmod, freq, prio in urls:
        body.append(
            f"  <url><loc>{origin}{path}</loc><lastmod>{lastmod}</lastmod>"
            f"<changefreq>{freq}</changefreq><priority>{prio}</priority></url>"
        )
    body.append("</urlset>")
    return Response(content="\n".join(body), media_type="application/xml")


@api_router.get("/seo/robots.txt")
async def seo_robots():
    from fastapi.responses import PlainTextResponse
    origin = _get_site_origin()
    text = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /account\n"
        "Disallow: /api/\n\n"
        f"Sitemap: {origin}/api/seo/sitemap.xml\n"
    )
    return PlainTextResponse(text)


# Register ALL routes (including the CMS + SEO block above) on the app
app.include_router(api_router)


@app.on_event("startup")
async def on_startup():
    await seed_if_empty()
    await ensure_live_indexes()
    # Seed default site settings if missing (idempotent)
    if not await db.site_settings.find_one({"key": "homepage"}):
        await save_site_setting("homepage", DEFAULT_HOMEPAGE)
        logging.info("Seeded default homepage content")
    if not await db.site_settings.find_one({"key": "shipping"}):
        await save_site_setting("shipping", DEFAULT_SHIPPING)
        logging.info("Seeded default shipping settings")
    # Phase B5 — seed default legal / policy pages if the collection is empty
    await _seed_default_pages()


@app.on_event("shutdown")
async def shutdown():
    client.close()
