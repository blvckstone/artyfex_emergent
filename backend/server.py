from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import hmac
import hashlib
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt as pyjwt
import razorpay
import asyncio
import httpx
import resend

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

RZP_KEY = os.environ.get('RAZORPAY_KEY_ID', '')
RZP_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
JWT_SECRET = os.environ.get('JWT_SECRET', 'change-me')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@artyfex.in')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'ArtyFex@2026')

rzp_client = razorpay.Client(auth=(RZP_KEY, RZP_SECRET)) if RZP_KEY else None

# Resend email config
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')
SENDER_NAME = os.environ.get('SENDER_NAME', 'ArtyFex Atelier')
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


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

app = FastAPI(title="ArtyFex API")
api_router = APIRouter(prefix="/api")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ---------- MODELS ---------- #
class Variant(BaseModel):
    model_config = ConfigDict(extra="ignore")
    key: str; label: str; hex: str; image: str
    # Optional per-variant overrides for size / stock / price
    size: Optional[str] = None
    stock: Optional[int] = None
    price_inr: Optional[int] = None
    mrp_inr: Optional[int] = None

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
    product_id: str; variant_key: str; quantity: int = 1

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
    created_at: str = Field(default_factory=now_iso)

class Review(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    author: str; location: str; rating: int
    title: str; body: str; image: Optional[str] = None
    verified: bool = True; featured: bool = False
    created_at: str = Field(default_factory=now_iso)

class ReviewIn(BaseModel):
    author: str; location: str; rating: int
    title: str; body: str; image: Optional[str] = None
    featured: bool = False

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
    name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class GoogleSessionIn(BaseModel):
    session_id: str


class ReviewPromptDelay(BaseModel):
    review_prompt_days: int = Field(ge=0, le=90)


class ReviewSubmit(BaseModel):
    rating: int
    title: str
    body: str
    location: Optional[str] = None
    image: Optional[str] = None


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
async def validate_coupon(payload: CouponValidateIn):
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
    result = await compute_taxes_for_cart(items, ship_state=payload.ship_state, treatment="inclusive")
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


@api_router.get("/reviews", response_model=List[Review])
async def list_reviews():
    return await db.reviews.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)


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
    # --- Phase A (Jul 2025): compute GST authoritatively (server is source of truth) ---
    try:
        tax = await compute_taxes_for_cart(
            [i.model_dump() for i in payload.items],
            ship_state=(order.customer.state if getattr(order.customer, "state", None) else None),
            treatment="inclusive",
        )
        order.gst_total_inr = int(tax.get("gst_total_inr") or 0)
        order.cgst_inr = int(tax.get("cgst_inr") or 0)
        order.sgst_inr = int(tax.get("sgst_inr") or 0)
        order.igst_inr = int(tax.get("igst_inr") or 0)
        order.gst_lines = tax.get("gst_lines") or []
        order.gst_treatment = "inclusive"
    except Exception as e:
        logging.warning(f"GST computation failed on order create: {e}")
    if payload.payment_method == "razorpay":
        if not rzp_client:
            raise HTTPException(status_code=500, detail="Razorpay not configured")
        rzp_order = rzp_client.order.create({
            "amount": order.total_inr * 100,
            "currency": "INR",
            "receipt": order.order_number[:40],
            "payment_capture": 1,
        })
        order.razorpay_order_id = rzp_order["id"]
    else:
        order.status = "confirmed"
    await db.orders.insert_one(order.model_dump())
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
    # Increment coupon usage counter on successful verification
    if order.get("coupon_code"):
        await db.coupons.update_one({"code": order["coupon_code"]}, {"$inc": {"used_count": 1}})
    return {"status": "confirmed", "order_number": payload.order_number}


@api_router.get("/orders/{order_number}", response_model=Order)
async def get_order(order_number: str):
    doc = await db.orders.find_one({"order_number": order_number}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Order not found")
    return doc


@api_router.post("/b2b/leads", response_model=B2BLead)
async def create_b2b_lead(payload: B2BLeadIn):
    lead = B2BLead(**payload.model_dump())
    await db.b2b_leads.insert_one(lead.model_dump())
    return lead


# ---------- ADMIN ROUTES ---------- #
@api_router.post("/admin/login")
async def admin_login(payload: AdminLogin):
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


@api_router.put("/admin/products/{product_id}", response_model=Product)
async def update_product(product_id: str, payload: ProductIn, admin=Depends(get_current_admin)):
    existing = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    updated = {**existing, **payload.model_dump()}
    await db.products.update_one({"id": product_id}, {"$set": updated})
    return updated


@api_router.delete("/admin/products/{product_id}")
async def delete_product(product_id: str, admin=Depends(get_current_admin)):
    res = await db.products.delete_one({"id": product_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"deleted": True}


@api_router.get("/admin/orders", response_model=List[Order])
async def admin_list_orders(admin=Depends(get_current_admin)):
    return await db.orders.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)


@api_router.patch("/admin/orders/{order_number}")
async def admin_update_order(order_number: str, payload: OrderStatusUpdate, admin=Depends(get_current_admin)):
    update = {"status": payload.status}
    if payload.status == "delivered":
        update["delivered_at"] = now_iso()
    res = await db.orders.update_one({"order_number": order_number}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


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
    r = Review(**payload.model_dump())
    await db.reviews.insert_one(r.model_dump())
    return r


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
async def user_signup(payload: UserSignup):
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
async def user_login(payload: UserLogin):
    user = await db.users.find_one({"email": payload.email})
    if not user or not bcrypt.checkpw(payload.password.encode(), user["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": create_token(payload.email, role="user"),
            "user": {"name": user["name"], "email": user["email"], "phone": user.get("phone", "")}}


@api_router.get("/auth/me")
async def user_me(user=Depends(get_current_user)):
    return {"name": user["name"], "email": user["email"], "phone": user.get("phone", ""), "picture": user.get("picture")}


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
    return await db.orders.find({"customer.email": user["email"]}, {"_id": 0}).sort("created_at", -1).to_list(200)


@api_router.post("/products/{slug}/reviews", response_model=Review)
async def submit_review(slug: str, payload: ReviewSubmit, user=Depends(get_current_user)):
    prod = await db.products.find_one({"slug": slug}, {"_id": 0})
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    if payload.rating < 1 or payload.rating > 5:
        raise HTTPException(status_code=400, detail="Rating 1-5")
    r = Review(
        author=user["name"], location=payload.location or "",
        rating=payload.rating, title=payload.title, body=payload.body,
        image=payload.image, verified=True,
    )
    doc = r.model_dump()
    doc["product_slug"] = slug
    doc["user_email"] = user["email"]
    await db.reviews.insert_one(doc)
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
    users = await db.users.find(query, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(500)
    # Enrich with order aggregates
    for u in users:
        orders = await db.orders.find({"customer.email": u["email"], "status": {"$nin": ["pending_payment", "cancelled", "payment_failed"]}}, {"_id": 0, "total_inr": 1, "created_at": 1}).to_list(500)
        u["orders_count"] = len(orders)
        u["total_spent_inr"] = sum(o.get("total_inr", 0) for o in orders)
        u["last_order_at"] = max((o["created_at"] for o in orders), default=None)
        u["messages_count"] = await db.admin_messages.count_documents({"user_email": u["email"]})
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
    return await db.failed_payments.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)


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


class HomepageContent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    announcement: AnnouncementBar = Field(default_factory=AnnouncementBar)
    hero: HeroContent = Field(default_factory=HeroContent)
    sale_banner: SaleBanner = Field(default_factory=SaleBanner)
    craft: CraftSection = Field(default_factory=CraftSection)
    collection_section: CollectionSection = Field(default_factory=CollectionSection)
    reviews_section: ReviewsSection = Field(default_factory=ReviewsSection)
    important_note: ImportantNote = Field(default_factory=ImportantNote)
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
async def admin_patch_homepage(payload: HomepageContent, admin=Depends(require_permission("manage_homepage"))):
    data = payload.model_dump()
    await save_site_setting("homepage", data)
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
    async for w in db.wishlists.find({}, {"_id": 0}):
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


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware, allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"], allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


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


@app.on_event("shutdown")
async def shutdown():
    client.close()
