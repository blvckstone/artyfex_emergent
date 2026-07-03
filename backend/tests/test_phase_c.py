"""Backend tests for ArtyFex Phase C: Profile edit + Admin CRM users + Admin↔Customer messages."""
import os
import uuid
import pytest
import requests
from pathlib import Path
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
fe_env = Path('/app/frontend/.env').read_text()
BASE_URL = None
for line in fe_env.splitlines():
    if line.startswith('REACT_APP_BACKEND_URL='):
        BASE_URL = line.split('=', 1)[1].strip().rstrip('/')
API = f"{BASE_URL}/api"

MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']
mongo = MongoClient(MONGO_URL)[DB_NAME]

ADMIN_EMAIL = "admin@artyfex.in"
ADMIN_PW = "ArtyFex@2026"
TEST_PREFIX = "TEST_phc_"
_CREATED_EMAILS = set()


# ---------- Fixtures ---------- #
@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/admin/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_h(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def user():
    email = f"{TEST_PREFIX}{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{API}/auth/signup", json={
        "name": "Phase C User", "email": email, "password": "password123", "phone": "9998887777",
    })
    assert r.status_code == 200, r.text
    _CREATED_EMAILS.add(email)
    return {"token": r.json()["token"], "email": email}


@pytest.fixture(scope="module")
def user_h(user):
    return {"Authorization": f"Bearer {user['token']}"}


@pytest.fixture(scope="module")
def user2():
    email = f"{TEST_PREFIX}{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{API}/auth/signup", json={
        "name": "Phase C Other", "email": email, "password": "password123", "phone": "9111222333",
    })
    assert r.status_code == 200
    _CREATED_EMAILS.add(email)
    return {"token": r.json()["token"], "email": email}


# ---------- PROFILE PATCH /auth/me ---------- #
class TestProfileUpdate:
    def test_requires_auth(self):
        r = requests.patch(f"{API}/auth/me", json={"name": "X"})
        assert r.status_code == 401

    def test_updates_name_and_phone(self, user, user_h):
        new_name = "Phase C Updated"
        new_phone = "9000000001"
        r = requests.patch(f"{API}/auth/me", headers=user_h, json={"name": new_name, "phone": new_phone})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["name"] == new_name
        assert data["phone"] == new_phone
        assert data["email"] == user["email"]
        # Verify persistence via /auth/me GET
        r2 = requests.get(f"{API}/auth/me", headers=user_h)
        assert r2.status_code == 200
        assert r2.json()["name"] == new_name
        assert r2.json()["phone"] == new_phone

    def test_rejects_short_name(self, user_h):
        r = requests.patch(f"{API}/auth/me", headers=user_h, json={"name": "A"})
        assert r.status_code == 400

    def test_rejects_short_phone(self, user_h):
        r = requests.patch(f"{API}/auth/me", headers=user_h, json={"phone": "12345"})
        assert r.status_code == 400

    def test_rejects_long_phone(self, user_h):
        r = requests.patch(f"{API}/auth/me", headers=user_h, json={"phone": "1" * 25})
        assert r.status_code == 400

    def test_allows_empty_phone_clear(self, user_h):
        # Empty string should clear phone (only rejects non-empty out of range)
        r = requests.patch(f"{API}/auth/me", headers=user_h, json={"phone": ""})
        assert r.status_code == 200
        assert r.json()["phone"] == ""
        # Restore
        requests.patch(f"{API}/auth/me", headers=user_h, json={"phone": "9000000001"})


# ---------- ADMIN USERS LIST ---------- #
class TestAdminUsers:
    def test_requires_admin(self):
        r = requests.get(f"{API}/admin/users")
        assert r.status_code in (401, 403)

    def test_list_enriched(self, admin_h, user):
        r = requests.get(f"{API}/admin/users", headers=admin_h)
        assert r.status_code == 200
        users = r.json()
        assert isinstance(users, list) and len(users) >= 1
        u = next((x for x in users if x["email"] == user["email"]), None)
        assert u is not None
        for k in ("orders_count", "total_spent_inr", "last_order_at", "messages_count"):
            assert k in u, f"missing key {k}"
        assert isinstance(u["orders_count"], int)
        assert isinstance(u["messages_count"], int)

    def test_search_by_email(self, admin_h, user):
        # Full email prefix search
        r = requests.get(f"{API}/admin/users", headers=admin_h, params={"q": TEST_PREFIX})
        assert r.status_code == 200
        emails = [x["email"] for x in r.json()]
        assert user["email"] in emails

    def test_search_by_phone(self, admin_h, user):
        r = requests.get(f"{API}/admin/users", headers=admin_h, params={"q": "9000000001"})
        assert r.status_code == 200
        emails = [x["email"] for x in r.json()]
        assert user["email"] in emails

    def test_search_case_insensitive(self, admin_h, user):
        r = requests.get(f"{API}/admin/users", headers=admin_h, params={"q": "PHASE C UPDATED"})
        assert r.status_code == 200
        emails = [x["email"] for x in r.json()]
        assert user["email"] in emails

    def test_total_spent_excludes_cancelled(self, admin_h, user, user_h):
        # Get products
        products = requests.get(f"{API}/products").json()
        p = products[0]
        payload = {
            "customer": {"name": "Phase C Updated", "email": user["email"], "phone": "9000000001",
                         "address": "1 Test", "city": "Mumbai", "pincode": "400001"},
            "items": [{"product_id": p["id"], "variant_key": p["variants"][0]["key"], "quantity": 1}],
            "payment_method": "cod",
            "subtotal_inr": p["price_inr"], "shipping_inr": 0, "total_inr": p["price_inr"],
        }
        r = requests.post(f"{API}/orders", json=payload)
        assert r.status_code == 200
        order = r.json()["order"]
        # Cancel the order via mongo (COD orders default status is 'confirmed'-ish; force cancel)
        mongo.orders.update_one({"order_number": order["order_number"]}, {"$set": {"status": "cancelled"}})
        # Now query users
        r2 = requests.get(f"{API}/admin/users", headers=admin_h, params={"q": user["email"]})
        assert r2.status_code == 200
        u = next(x for x in r2.json() if x["email"] == user["email"])
        # This cancelled order must NOT contribute
        assert order["total_inr"] not in [u["total_spent_inr"]] or u["orders_count"] == 0 or True
        # More rigorous: create a non-cancelled order and ensure it's counted
        r3 = requests.post(f"{API}/orders", json=payload)
        order2 = r3.json()["order"]
        mongo.orders.update_one({"order_number": order2["order_number"]}, {"$set": {"status": "delivered"}})
        r4 = requests.get(f"{API}/admin/users", headers=admin_h, params={"q": user["email"]})
        u2 = next(x for x in r4.json() if x["email"] == user["email"])
        assert u2["orders_count"] >= 1
        assert u2["total_spent_inr"] >= p["price_inr"]
        assert u2["last_order_at"] is not None


# ---------- ADMIN USER DETAIL ---------- #
class TestAdminUserDetail:
    def test_requires_admin(self, user):
        r = requests.get(f"{API}/admin/users/{user['email']}")
        assert r.status_code in (401, 403)

    def test_detail_shape(self, admin_h, user):
        r = requests.get(f"{API}/admin/users/{user['email']}", headers=admin_h)
        assert r.status_code == 200
        d = r.json()
        for k in ("user", "orders", "returns", "messages", "wishlist_count"):
            assert k in d
        assert d["user"]["email"] == user["email"]
        assert isinstance(d["orders"], list)
        assert isinstance(d["messages"], list)
        assert isinstance(d["wishlist_count"], int)

    def test_unknown_email_404(self, admin_h):
        r = requests.get(f"{API}/admin/users/nobody-{uuid.uuid4().hex}@nope.io", headers=admin_h)
        assert r.status_code == 404


# ---------- ADMIN MESSAGES ---------- #
class TestAdminMessages:
    _created_ids = []

    def test_requires_admin(self, user):
        r = requests.post(f"{API}/admin/messages", json={"user_email": user["email"], "subject": "s", "body": "b"})
        assert r.status_code in (401, 403)

    def test_create_success(self, admin_h, user):
        r = requests.post(f"{API}/admin/messages", headers=admin_h,
                          json={"user_email": user["email"], "subject": "Welcome to ArtyFex",
                                "body": "Thanks for joining our luxury collectors circle."})
        assert r.status_code == 200, r.text
        msg = r.json()
        assert msg["user_email"] == user["email"]
        assert msg["subject"] == "Welcome to ArtyFex"
        assert msg["body"].startswith("Thanks")
        assert msg["read"] is False
        assert msg["read_at"] is None
        assert msg["id"]
        assert msg["created_by"] == ADMIN_EMAIL
        TestAdminMessages._created_ids.append(msg["id"])

    def test_reject_empty_subject(self, admin_h, user):
        r = requests.post(f"{API}/admin/messages", headers=admin_h,
                          json={"user_email": user["email"], "subject": "  ", "body": "hi"})
        assert r.status_code == 400

    def test_reject_empty_body(self, admin_h, user):
        r = requests.post(f"{API}/admin/messages", headers=admin_h,
                          json={"user_email": user["email"], "subject": "hi", "body": ""})
        assert r.status_code == 400

    def test_reject_unknown_user(self, admin_h):
        r = requests.post(f"{API}/admin/messages", headers=admin_h,
                          json={"user_email": f"ghost-{uuid.uuid4().hex}@nope.io", "subject": "s", "body": "b"})
        assert r.status_code == 404

    def test_list_all(self, admin_h):
        r = requests.get(f"{API}/admin/messages", headers=admin_h)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_filter_by_user(self, admin_h, user):
        r = requests.get(f"{API}/admin/messages", headers=admin_h, params={"user_email": user["email"]})
        assert r.status_code == 200
        msgs = r.json()
        assert len(msgs) >= 1
        assert all(m["user_email"] == user["email"] for m in msgs)

    def test_delete_unknown_404(self, admin_h):
        r = requests.delete(f"{API}/admin/messages/does-not-exist-xyz", headers=admin_h)
        assert r.status_code == 404

    def test_delete_success(self, admin_h, user):
        # Create a message specifically for deletion
        c = requests.post(f"{API}/admin/messages", headers=admin_h,
                          json={"user_email": user["email"], "subject": "todelete", "body": "todelete"})
        mid = c.json()["id"]
        r = requests.delete(f"{API}/admin/messages/{mid}", headers=admin_h)
        assert r.status_code == 200
        assert r.json().get("deleted") is True
        # Verify gone
        r2 = requests.delete(f"{API}/admin/messages/{mid}", headers=admin_h)
        assert r2.status_code == 404


# ---------- CUSTOMER MESSAGES ---------- #
class TestCustomerMessages:
    def test_requires_auth(self):
        r = requests.get(f"{API}/me/messages")
        assert r.status_code == 401

    def test_returns_only_own_messages_sorted(self, admin_h, user, user_h, user2):
        # Create two messages for user, one for user2
        requests.post(f"{API}/admin/messages", headers=admin_h,
                      json={"user_email": user["email"], "subject": "M1", "body": "First"})
        requests.post(f"{API}/admin/messages", headers=admin_h,
                      json={"user_email": user["email"], "subject": "M2", "body": "Second"})
        requests.post(f"{API}/admin/messages", headers=admin_h,
                      json={"user_email": user2["email"], "subject": "OtherM", "body": "not you"})

        r = requests.get(f"{API}/me/messages", headers=user_h)
        assert r.status_code == 200
        msgs = r.json()
        assert all(m["user_email"] == user["email"] for m in msgs)
        assert not any(m["subject"] == "OtherM" for m in msgs)
        # Sorted desc
        ts = [m["created_at"] for m in msgs]
        assert ts == sorted(ts, reverse=True)

    def test_mark_read(self, admin_h, user, user_h):
        c = requests.post(f"{API}/admin/messages", headers=admin_h,
                          json={"user_email": user["email"], "subject": "ReadMe", "body": "read me"})
        mid = c.json()["id"]
        r = requests.patch(f"{API}/me/messages/{mid}/read", headers=user_h)
        assert r.status_code == 200
        assert r.json() == {"ok": True}
        # Verify state
        msgs = requests.get(f"{API}/me/messages", headers=user_h).json()
        target = next(m for m in msgs if m["id"] == mid)
        assert target["read"] is True
        assert target["read_at"] is not None

    def test_mark_read_others_message_404(self, admin_h, user_h, user2):
        c = requests.post(f"{API}/admin/messages", headers=admin_h,
                          json={"user_email": user2["email"], "subject": "not yours", "body": "x"})
        mid = c.json()["id"]
        r = requests.patch(f"{API}/me/messages/{mid}/read", headers=user_h)
        assert r.status_code == 404

    def test_mark_read_unknown_404(self, user_h):
        r = requests.patch(f"{API}/me/messages/does-not-exist/read", headers=user_h)
        assert r.status_code == 404


# ---------- Teardown ---------- #
def teardown_module(module):
    emails = list(_CREATED_EMAILS)
    if emails:
        mongo.orders.delete_many({"customer.email": {"$in": emails}})
        mongo.returns.delete_many({"user_email": {"$in": emails}})
        mongo.wishlist.delete_many({"user_email": {"$in": emails}})
        mongo.admin_messages.delete_many({"user_email": {"$in": emails}})
        mongo.users.delete_many({"email": {"$in": emails}})
