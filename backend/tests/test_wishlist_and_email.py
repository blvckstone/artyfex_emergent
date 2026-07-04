"""Backend tests for ArtyFex Phase B: Wishlist + Email notification on return update."""
import os
import time
import uuid
import pytest
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
BASE_URL = os.environ['REACT_APP_BACKEND_URL'].rstrip('/') if os.environ.get('REACT_APP_BACKEND_URL') else 'https://repo-digest-8.preview.emergentagent.com'
# Prefer frontend env for the public URL
fe_env = Path('/app/frontend/.env').read_text()
for line in fe_env.splitlines():
    if line.startswith('REACT_APP_BACKEND_URL='):
        BASE_URL = line.split('=', 1)[1].strip().rstrip('/')

API = f"{BASE_URL}/api"

MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']
mongo = MongoClient(MONGO_URL)[DB_NAME]

ADMIN_EMAIL = "admin@artyfex.in"
ADMIN_PW = "ArtyFex@2026"
TEST_EMAIL_PREFIX = "TEST_wish_"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/admin/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def user():
    email = f"{TEST_EMAIL_PREFIX}{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{API}/auth/signup", json={
        "name": "Wish Test", "email": email, "password": "password123", "phone": "9999999999",
    })
    assert r.status_code == 200, r.text
    return {"token": r.json()["token"], "email": email}


@pytest.fixture(scope="module")
def products():
    r = requests.get(f"{API}/products")
    assert r.status_code == 200
    return r.json()


# ---------- Wishlist auth ---------- #

def test_wishlist_get_requires_auth():
    r = requests.get(f"{API}/me/wishlist")
    assert r.status_code == 401


def test_wishlist_post_requires_auth(products):
    r = requests.post(f"{API}/me/wishlist/{products[0]['id']}")
    assert r.status_code == 401


def test_wishlist_delete_requires_auth(products):
    r = requests.delete(f"{API}/me/wishlist/{products[0]['id']}")
    assert r.status_code == 401


# ---------- Wishlist CRUD ---------- #

def test_wishlist_add_and_duplicate(user, products):
    p = products[0]
    h = {"Authorization": f"Bearer {user['token']}"}
    r = requests.post(f"{API}/me/wishlist/{p['id']}", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["action"] == "added"
    assert data["product_id"] == p["id"]

    # Duplicate
    r2 = requests.post(f"{API}/me/wishlist/{p['id']}", headers=h)
    assert r2.status_code == 200
    assert r2.json()["action"] == "already_saved"


def test_wishlist_add_nonexistent_product_404(user):
    h = {"Authorization": f"Bearer {user['token']}"}
    r = requests.post(f"{API}/me/wishlist/does-not-exist-xyz", headers=h)
    assert r.status_code == 404


def test_wishlist_list_enriched(user, products):
    p = products[0]
    h = {"Authorization": f"Bearer {user['token']}"}
    r = requests.get(f"{API}/me/wishlist", headers=h)
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list) and len(items) >= 1
    entry = next((x for x in items if x["product_id"] == p["id"]), None)
    assert entry is not None
    assert "added_at" in entry
    assert "product" in entry
    assert entry["product"]["id"] == p["id"]
    assert entry["product"]["slug"] == p["slug"]
    assert entry["product"]["name"] == p["name"]


def test_wishlist_remove(user, products):
    p = products[0]
    h = {"Authorization": f"Bearer {user['token']}"}
    r = requests.delete(f"{API}/me/wishlist/{p['id']}", headers=h)
    assert r.status_code == 200
    assert r.json()["action"] == "removed"
    # Verify gone
    r2 = requests.get(f"{API}/me/wishlist", headers=h)
    assert not any(x["product_id"] == p["id"] for x in r2.json())


# ---------- Email trigger on return approve/reject ---------- #

def _create_delivered_order_and_return(user, products, admin_token):
    p = products[0]
    payload = {
        "customer": {"name": "Wish Test", "email": user["email"], "phone": "9999999999",
                     "address": "1 Test St", "city": "Mumbai", "pincode": "400001"},
        "items": [{"product_id": p["id"], "variant_key": p["variants"][0]["key"], "quantity": 1}],
        "payment_method": "cod",
        "subtotal_inr": p["price_inr"], "shipping_inr": 0, "total_inr": p["price_inr"],
    }
    r = requests.post(f"{API}/orders", json=payload)
    assert r.status_code == 200
    order = r.json()["order"]
    # Deliver
    requests.patch(f"{API}/admin/orders/{order['order_number']}",
                   json={"status": "delivered"},
                   headers={"Authorization": f"Bearer {admin_token}"})
    # Request return
    rr = requests.post(f"{API}/me/returns",
                       json={"order_number": order["order_number"], "reason": "Damage",
                             "packaging_confirmed": True, "damage_image_url": "https://example.com/x.jpg"},
                       headers={"Authorization": f"Bearer {user['token']}"})
    assert rr.status_code == 200, rr.text
    return rr.json()


def _tail_backend_log():
    logs = ""
    for fp in ("/var/log/supervisor/backend.err.log", "/var/log/supervisor/backend.out.log"):
        try:
            with open(fp, "r") as f:
                logs += f.read()[-8000:]
        except Exception:
            pass
    return logs


def test_return_approval_returns_200_fast_and_triggers_email(user, products, admin_token):
    ret = _create_delivered_order_and_return(user, products, admin_token)
    t0 = time.time()
    r = requests.patch(f"{API}/admin/returns/{ret['id']}",
                       json={"status": "approved", "is_genuine": True, "admin_notes": "Phase B email test"},
                       headers={"Authorization": f"Bearer {admin_token}"})
    elapsed = time.time() - t0
    assert r.status_code == 200
    # Fire-and-forget: should return fast even if email is slow
    assert elapsed < 5.0, f"Response too slow ({elapsed}s) — email may be blocking"
    # Give background task a moment
    time.sleep(4)
    logs = _tail_backend_log()
    # Either success or graceful failure must be logged (silent-fail contract)
    assert (
        "Email sent to" in logs
        or "Email send failed" in logs
        or "RESEND_API_KEY not configured" in logs
    ), "No email attempt logged; expected either success or graceful failure line"


def test_return_rejection_triggers_email(user, products, admin_token):
    ret = _create_delivered_order_and_return(user, products, admin_token)
    r = requests.patch(f"{API}/admin/returns/{ret['id']}",
                       json={"status": "rejected", "is_genuine": False, "admin_notes": "Phase B reject test"},
                       headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    time.sleep(4)
    logs = _tail_backend_log()
    assert (
        "Email sent to" in logs
        or "Email send failed" in logs
        or "RESEND_API_KEY not configured" in logs
    )


def teardown_module(module):
    users = list(mongo.users.find({"email": {"$regex": f"^{TEST_EMAIL_PREFIX}"}}))
    emails = [u["email"] for u in users]
    if emails:
        mongo.orders.delete_many({"customer.email": {"$in": emails}})
        mongo.returns.delete_many({"user_email": {"$in": emails}})
        mongo.wishlist.delete_many({"user_email": {"$in": emails}})
        mongo.users.delete_many({"email": {"$in": emails}})
