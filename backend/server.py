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

app = FastAPI(title="ArtyFex API")
api_router = APIRouter(prefix="/api")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ---------- MODELS ---------- #
class Variant(BaseModel):
    key: str; label: str; hex: str; image: str

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

class Order(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_number: str = Field(default_factory=lambda: f"ARF-{uuid.uuid4().hex[:8].upper()}")
    customer: OrderCustomer; items: List[OrderItem]
    payment_method: str
    subtotal_inr: int; shipping_inr: int; total_inr: int
    status: str = "pending_payment"  # pending_payment | confirmed | packed | shipped | delivered | cancelled
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
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


# ---------- SEED ---------- #
from server_seed import SEED_PRODUCTS, SEED_REVIEWS  # noqa: E402


async def seed_if_empty():
    if await db.products.count_documents({}) == 0:
        await db.products.insert_many([Product(**p).model_dump() for p in SEED_PRODUCTS])
        logging.info(f"Seeded {len(SEED_PRODUCTS)} products")
    if await db.reviews.count_documents({}) == 0:
        await db.reviews.insert_many([Review(**r).model_dump() for r in SEED_REVIEWS])
        logging.info(f"Seeded {len(SEED_REVIEWS)} reviews")
    # Seed admin (idempotent)
    if not await db.admins.find_one({"email": ADMIN_EMAIL}):
        pw_hash = bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode()
        await db.admins.insert_one({
            "id": str(uuid.uuid4()), "email": ADMIN_EMAIL,
            "password_hash": pw_hash, "created_at": now_iso(),
        })
        logging.info(f"Seeded admin {ADMIN_EMAIL}")


# ---------- AUTH ---------- #
def create_token(email: str) -> str:
    payload = {"sub": email, "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")


async def get_current_admin(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    try:
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except pyjwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    admin = await db.admins.find_one({"email": payload.get("sub")}, {"_id": 0, "password_hash": 0})
    if not admin:
        raise HTTPException(status_code=401, detail="Admin not found")
    return admin


# ---------- PUBLIC ROUTES ---------- #
@api_router.get("/")
async def root():
    return {"brand": "ArtyFex"}


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
    order = Order(**payload.model_dump())
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
    return {"token": create_token(payload.email), "email": payload.email}


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
    res = await db.orders.update_one({"order_number": order_number}, {"$set": {"status": payload.status}})
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
