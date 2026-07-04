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
    created_at: str = Field(default_factory=now_iso)

class ProductIn(BaseModel):
    slug: str; name: str; tagline: str; description: str
    price_inr: int; mrp_inr: int; size: str; craft_hours: int
    materials: List[str]; hero_image: str; gallery: List[str]
    variants: List[Variant]; is_hero: bool = False; stock: int = 5

class OrderCustomer(BaseModel):
    name: str; email: EmailStr; phone: str
    address: str; city: str; pincode: str

class OrderItem(BaseModel):
    product_id: str; variant_key: str; quantity: int = 1

class OrderIn(BaseModel):
    customer: OrderCustomer; items: List[OrderItem]
    payment_method: str  # razorpay | cod
    subtotal_inr: int; shipping_inr: int; total_inr: int
    coupon_code: Optional[str] = None
    discount_inr: int = 0

class Order(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_number: str = Field(default_factory=lambda: f"ARF-{uuid.uuid4().hex[:8].upper()}")
    customer: OrderCustomer; items: List[OrderItem]
    payment_method: str
    subtotal_inr: int; shipping_inr: int; total_inr: int
    coupon_code: Optional[str] = None
    discount_inr: int = 0
    status: str = "pending_payment"  # pending_payment | confirmed | packed | shipped | delivered | cancelled | payment_failed
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    delivered_at: Optional[str] = None
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
    # Seed admin (idempotent)
    if not await db.admins.find_one({"email": ADMIN_EMAIL}):
        pw_hash = bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode()
        await db.admins.insert_one({
            "id": str(uuid.uuid4()), "email": ADMIN_EMAIL,
            "password_hash": pw_hash, "created_at": now_iso(),
        })
        logging.info(f"Seeded admin {ADMIN_EMAIL}")


# ---------- AUTH ---------- #
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


@app.on_event("shutdown")
async def shutdown():
    client.close()
