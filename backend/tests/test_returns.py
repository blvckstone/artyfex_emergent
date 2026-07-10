"""Backend tests for ArtyFex Returns Overhaul (Phase A)."""
import os
import uuid
import pytest
import requests
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://artyfex-main.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"

# Load backend env for MongoDB access
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

ADMIN_EMAIL = "admin@artyfex.in"
ADMIN_PW = "ArtyFex@2026"

TEST_EMAIL_PREFIX = "TEST_returns_"

mongo = MongoClient(MONGO_URL)[DB_NAME]


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/admin/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def user_token():
    email = f"{TEST_EMAIL_PREFIX}{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{API}/auth/signup", json={
        "name": "Test Returns User", "email": email, "password": "password123", "phone": "9999999999"
    })
    assert r.status_code == 200, r.text
    return r.json()["token"], email


@pytest.fixture(scope="module")
def product():
    r = requests.get(f"{API}/products")
    assert r.status_code == 200
    return r.json()[0]


def _create_order(email, product):
    payload = {
        "customer": {"name": "Test Returns User", "email": email, "phone": "9999999999",
                     "address": "1 Test St", "city": "Mumbai", "pincode": "400001"},
        "items": [{"product_id": product["id"], "variant_key": product["variants"][0]["key"], "quantity": 1}],
        "payment_method": "cod",
        "subtotal_inr": product["price_inr"], "shipping_inr": 0, "total_inr": product["price_inr"],
    }
    r = requests.post(f"{API}/orders", json=payload)
    assert r.status_code == 200, r.text
    return r.json()["order"]


def _admin_set_status(admin_token, order_number, status):
    r = requests.patch(f"{API}/admin/orders/{order_number}",
                       json={"status": status},
                       headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200, r.text


# --- Rejection scenarios ---

def test_return_rejected_when_order_not_delivered(user_token, product):
    token, email = user_token
    order = _create_order(email, product)  # confirmed status
    r = requests.post(f"{API}/me/returns",
                      json={"order_number": order["order_number"], "reason": "Damaged",
                            "packaging_confirmed": True, "damage_image_url": "http://x.com/i.jpg"},
                      headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400
    assert "delivered" in r.json()["detail"].lower()


def test_return_rejected_when_packaging_not_confirmed(user_token, product, admin_token):
    token, email = user_token
    order = _create_order(email, product)
    _admin_set_status(admin_token, order["order_number"], "delivered")
    r = requests.post(f"{API}/me/returns",
                      json={"order_number": order["order_number"], "reason": "Damaged",
                            "packaging_confirmed": False},
                      headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400
    assert "packaging" in r.json()["detail"].lower()


def test_return_rejected_when_window_closed(user_token, product, admin_token):
    token, email = user_token
    order = _create_order(email, product)
    _admin_set_status(admin_token, order["order_number"], "delivered")
    # Backdate delivered_at 10 days in the past via direct DB update
    past = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    mongo.orders.update_one({"order_number": order["order_number"]}, {"$set": {"delivered_at": past}})
    r = requests.post(f"{API}/me/returns",
                      json={"order_number": order["order_number"], "reason": "Damaged",
                            "packaging_confirmed": True},
                      headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400
    assert "window closed" in r.json()["detail"].lower() or "3 days" in r.json()["detail"]


# --- Valid return + admin flow ---

@pytest.fixture(scope="module")
def valid_return(user_token, product, admin_token):
    token, email = user_token
    order = _create_order(email, product)
    _admin_set_status(admin_token, order["order_number"], "delivered")
    # Confirm delivered_at set
    doc = mongo.orders.find_one({"order_number": order["order_number"]})
    assert doc.get("delivered_at"), "delivered_at not set by admin PATCH"
    payload = {
        "order_number": order["order_number"],
        "reason": "Product damaged in transit",
        "details": "Small scratch on frame",
        "damage_image_url": "https://example.com/damage.jpg",
        "packaging_confirmed": True,
    }
    r = requests.post(f"{API}/me/returns", json=payload,
                      headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "requested"
    assert data["damage_image_url"] == payload["damage_image_url"]
    assert data["packaging_confirmed"] is True
    return {"token": token, "email": email, "order_number": order["order_number"], "return": data}


def test_valid_return_created(valid_return):
    assert valid_return["return"]["id"]


def test_duplicate_return_rejected(valid_return):
    token = valid_return["token"]
    r = requests.post(f"{API}/me/returns",
                      json={"order_number": valid_return["order_number"], "reason": "again",
                            "packaging_confirmed": True},
                      headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400
    assert "already" in r.json()["detail"].lower()


def test_admin_list_returns_enriched(valid_return, admin_token):
    r = requests.get(f"{API}/admin/returns", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    returns = r.json()
    target = next((x for x in returns if x["id"] == valid_return["return"]["id"]), None)
    assert target is not None
    assert "order_customer_name" in target
    assert "order_customer_phone" in target
    assert "order_total_inr" in target
    assert "order_delivered_at" in target
    assert "order_status" in target


def test_admin_invalid_status_rejected(valid_return, admin_token):
    r = requests.patch(f"{API}/admin/returns/{valid_return['return']['id']}",
                       json={"status": "foobar"},
                       headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 400


def test_admin_approve_return(valid_return, admin_token):
    rid = valid_return["return"]["id"]
    r = requests.patch(f"{API}/admin/returns/{rid}",
                       json={"status": "approved", "is_genuine": True, "admin_notes": "Approved by atelier"},
                       headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    # Customer view
    r2 = requests.get(f"{API}/me/returns", headers={"Authorization": f"Bearer {valid_return['token']}"})
    assert r2.status_code == 200
    mine = next((x for x in r2.json() if x["id"] == rid), None)
    assert mine and mine["status"] == "approved"
    assert mine["is_genuine"] is True
    assert mine["admin_notes"] == "Approved by atelier"


def test_admin_reject_return(user_token, product, admin_token):
    """Separate return that we reject."""
    token, email = user_token
    order = _create_order(email, product)
    _admin_set_status(admin_token, order["order_number"], "delivered")
    r = requests.post(f"{API}/me/returns",
                      json={"order_number": order["order_number"], "reason": "Color mismatch",
                            "packaging_confirmed": True, "details": "not as pictured"},
                      headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    rid = r.json()["id"]
    r2 = requests.patch(f"{API}/admin/returns/{rid}",
                        json={"status": "rejected", "is_genuine": False, "admin_notes": "Packaging damaged"},
                        headers={"Authorization": f"Bearer {admin_token}"})
    assert r2.status_code == 200
    r3 = requests.get(f"{API}/me/returns", headers={"Authorization": f"Bearer {token}"})
    mine = next((x for x in r3.json() if x["id"] == rid), None)
    assert mine and mine["status"] == "rejected"
    assert mine["is_genuine"] is False


def teardown_module(module):
    """Cleanup TEST_ prefixed data."""
    users = list(mongo.users.find({"email": {"$regex": f"^{TEST_EMAIL_PREFIX}"}}))
    emails = [u["email"] for u in users]
    if emails:
        mongo.orders.delete_many({"customer.email": {"$in": emails}})
        mongo.returns.delete_many({"user_email": {"$in": emails}})
        mongo.users.delete_many({"email": {"$in": emails}})
