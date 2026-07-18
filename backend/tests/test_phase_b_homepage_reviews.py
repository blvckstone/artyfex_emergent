"""Phase B: Homepage CMS expansion + featured-review toggle + variant list PUT.

Covers the new admin-editable homepage sections (craft, collection_section,
reviews_section, important_note) and the PATCH /admin/reviews/{id} featured
toggle, plus regression for products CRUD with an array-based variants payload.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://backend-migration-24.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@artyfex.in"
ADMIN_PASSWORD = "ArtyFex@2026"


# ---- fixtures ----
@pytest.fixture(scope="module")
def admin_token():
    resp = requests.post(f"{BASE_URL}/api/admin/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert resp.status_code == 200, f"Admin login failed: {resp.status_code} {resp.text[:200]}"
    return resp.json()["token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def original_homepage(admin_headers):
    """Snapshot current homepage so we can restore after mutating tests."""
    resp = requests.get(f"{BASE_URL}/api/homepage", timeout=15)
    assert resp.status_code == 200
    return resp.json()


@pytest.fixture(scope="module")
def sample_product():
    resp = requests.get(f"{BASE_URL}/api/products", timeout=15)
    assert resp.status_code == 200
    products = resp.json()
    assert products, "Expected seed products"
    return products[0]


@pytest.fixture(scope="module")
def sample_review():
    resp = requests.get(f"{BASE_URL}/api/reviews", timeout=15)
    assert resp.status_code == 200
    reviews = resp.json()
    assert reviews, "Expected seed reviews"
    return reviews[0]


# ---- Homepage schema tests ----
class TestHomepageSchema:
    def test_public_homepage_returns_all_keys(self):
        resp = requests.get(f"{BASE_URL}/api/homepage", timeout=15)
        assert resp.status_code == 200
        data = resp.json()
        for k in ["announcement", "hero", "sale_banner", "craft", "collection_section", "reviews_section", "important_note", "custom_css"]:
            assert k in data, f"Missing key {k}. Got: {list(data.keys())}"

    def test_craft_section_default_shape(self):
        data = requests.get(f"{BASE_URL}/api/homepage", timeout=15).json()
        craft = data["craft"]
        for k in ["eyebrow", "headline_line_1", "headline_italic", "body", "section_image", "image_overlay_label", "image_overlay_title", "steps"]:
            assert k in craft
        assert isinstance(craft["steps"], list)

    def test_collection_section_default_shape(self):
        data = requests.get(f"{BASE_URL}/api/homepage", timeout=15).json()
        cs = data["collection_section"]
        for k in ["eyebrow", "headline_line_1", "headline_italic", "subtitle", "featured_product_ids"]:
            assert k in cs
        assert isinstance(cs["featured_product_ids"], list)

    def test_reviews_section_default_shape(self):
        data = requests.get(f"{BASE_URL}/api/homepage", timeout=15).json()
        rs = data["reviews_section"]
        for k in ["eyebrow", "headline_line_1", "headline_italic", "average_rating", "featured_review_ids"]:
            assert k in rs
        assert isinstance(rs["featured_review_ids"], list)

    def test_important_note_default_shape(self):
        data = requests.get(f"{BASE_URL}/api/homepage", timeout=15).json()
        note = data["important_note"]
        for k in ["enabled", "label", "body"]:
            assert k in note


# ---- Homepage PATCH persistence tests ----
class TestHomepagePatch:
    def test_patch_craft_persists(self, admin_headers, original_homepage):
        payload = dict(original_homepage)
        payload["craft"] = {
            **original_homepage["craft"],
            "eyebrow": "TEST Craft eyebrow",
            "headline_line_1": "TEST headline",
            "headline_italic": "TEST italic",
            "body": "TEST body copy",
            "section_image": "https://example.com/craft-test.jpg",
            "image_overlay_label": "TEST label",
            "image_overlay_title": "TEST title",
        }
        r = requests.patch(f"{BASE_URL}/api/admin/homepage", json=payload, headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text[:300]
        # verify persistence via public GET
        got = requests.get(f"{BASE_URL}/api/homepage", timeout=15).json()
        c = got["craft"]
        assert c["eyebrow"] == "TEST Craft eyebrow"
        assert c["headline_line_1"] == "TEST headline"
        assert c["headline_italic"] == "TEST italic"
        assert c["body"] == "TEST body copy"
        assert c["section_image"] == "https://example.com/craft-test.jpg"
        assert c["image_overlay_label"] == "TEST label"
        assert c["image_overlay_title"] == "TEST title"

    def test_patch_collection_featured_products(self, admin_headers, sample_product):
        current = requests.get(f"{BASE_URL}/api/homepage", timeout=15).json()
        payload = dict(current)
        payload["collection_section"] = {
            **current["collection_section"],
            "featured_product_ids": [sample_product["id"]],
        }
        r = requests.patch(f"{BASE_URL}/api/admin/homepage", json=payload, headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text[:300]
        got = requests.get(f"{BASE_URL}/api/homepage", timeout=15).json()
        assert got["collection_section"]["featured_product_ids"] == [sample_product["id"]]

    def test_patch_important_note_disabled_and_body(self, admin_headers):
        current = requests.get(f"{BASE_URL}/api/homepage", timeout=15).json()
        payload = dict(current)
        payload["important_note"] = {
            **current["important_note"],
            "enabled": False,
            "body": "Test note",
        }
        r = requests.patch(f"{BASE_URL}/api/admin/homepage", json=payload, headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text[:300]
        got = requests.get(f"{BASE_URL}/api/homepage", timeout=15).json()
        assert got["important_note"]["enabled"] is False
        assert got["important_note"]["body"] == "Test note"


# ---- Reviews featured toggle tests ----
class TestReviewFeaturedToggle:
    def test_patch_review_featured_true(self, admin_headers, sample_review):
        rid = sample_review["id"]
        r = requests.patch(f"{BASE_URL}/api/admin/reviews/{rid}", json={"featured": True}, headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        assert body["id"] == rid
        assert body["featured"] is True
        # Verify visible on public GET
        reviews = requests.get(f"{BASE_URL}/api/reviews", timeout=15).json()
        matched = [x for x in reviews if x["id"] == rid]
        assert matched and matched[0]["featured"] is True

    def test_patch_review_featured_false(self, admin_headers, sample_review):
        rid = sample_review["id"]
        r = requests.patch(f"{BASE_URL}/api/admin/reviews/{rid}", json={"featured": False}, headers=admin_headers, timeout=15)
        assert r.status_code == 200
        assert r.json()["featured"] is False
        reviews = requests.get(f"{BASE_URL}/api/reviews", timeout=15).json()
        matched = [x for x in reviews if x["id"] == rid]
        assert matched and matched[0]["featured"] is False

    def test_patch_review_invalid_id_404(self, admin_headers):
        r = requests.patch(f"{BASE_URL}/api/admin/reviews/does-not-exist-id-xxx", json={"featured": True}, headers=admin_headers, timeout=15)
        assert r.status_code == 404


# ---- Products CRUD regression + variant array payload ----
class TestProductsVariantArrayPayload:
    _created_id = None

    def test_list_products(self):
        r = requests.get(f"{BASE_URL}/api/products", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list) and len(r.json()) >= 1

    def test_create_product_with_variant_array(self, admin_headers):
        payload = {
            "slug": "test-phase-b-mirror",
            "name": "TEST Phase B Mirror",
            "tagline": "Test only",
            "description": "Test product created by pytest.",
            "price_inr": 9999,
            "mrp_inr": 12999,
            "size": "1x2",
            "craft_hours": 40,
            "materials": ["resin", "glass"],
            "hero_image": "https://example.com/test.jpg",
            "gallery": ["https://example.com/g1.jpg"],
            "variants": [
                {"key": "default", "label": "Default", "hex": "#000000", "image": "https://example.com/v0.jpg",
                 "size": "1x2", "stock": 5, "price_inr": 9999, "mrp_inr": 12999},
                {"key": "gold", "label": "Gold", "hex": "#D4AF37", "image": "https://example.com/v1.jpg",
                 "size": "1x2", "stock": 2, "price_inr": 10999, "mrp_inr": 13999},
            ],
            "is_hero": False,
            "stock": 5,
        }
        r = requests.post(f"{BASE_URL}/api/admin/products", json=payload, headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text[:300]
        created = r.json()
        assert created["slug"] == payload["slug"]
        assert isinstance(created["variants"], list)
        assert len(created["variants"]) == 2
        assert created["variants"][1]["key"] == "gold"
        assert created["variants"][1]["hex"] == "#D4AF37"
        assert created["variants"][1]["stock"] == 2
        TestProductsVariantArrayPayload._created_id = created["id"]

    def test_put_update_product_adds_variant(self, admin_headers):
        pid = TestProductsVariantArrayPayload._created_id
        assert pid, "Depends on create test"
        payload = {
            "slug": "test-phase-b-mirror",
            "name": "TEST Phase B Mirror v2",
            "tagline": "Updated",
            "description": "Updated desc.",
            "price_inr": 9999,
            "mrp_inr": 12999,
            "size": "1x2",
            "craft_hours": 45,
            "materials": ["resin", "glass", "crystal"],
            "hero_image": "https://example.com/test.jpg",
            "gallery": ["https://example.com/g1.jpg"],
            "variants": [
                {"key": "default", "label": "Default", "hex": "#000000", "image": "https://example.com/v0.jpg",
                 "size": "1x2", "stock": 5, "price_inr": 9999, "mrp_inr": 12999},
                {"key": "gold", "label": "Gold", "hex": "#D4AF37", "image": "https://example.com/v1.jpg",
                 "size": "1x2", "stock": 2, "price_inr": 10999, "mrp_inr": 13999},
                {"key": "silver", "label": "Silver", "hex": "#C0C0C0", "image": "https://example.com/v2.jpg",
                 "size": "1x2", "stock": 3, "price_inr": 10499, "mrp_inr": 13499},
            ],
            "is_hero": False,
            "stock": 10,
        }
        r = requests.put(f"{BASE_URL}/api/admin/products/{pid}", json=payload, headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text[:300]
        updated = r.json()
        assert updated["name"] == "TEST Phase B Mirror v2"
        assert len(updated["variants"]) == 3
        assert updated["variants"][2]["key"] == "silver"
        # Verify persisted via GET /products/{slug}
        got = requests.get(f"{BASE_URL}/api/products/test-phase-b-mirror", timeout=15).json()
        assert len(got["variants"]) == 3
        assert got["variants"][2]["hex"] == "#C0C0C0"

    def test_delete_product(self, admin_headers):
        pid = TestProductsVariantArrayPayload._created_id
        assert pid
        r = requests.delete(f"{BASE_URL}/api/admin/products/{pid}", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        # verify removed
        got = requests.get(f"{BASE_URL}/api/products/test-phase-b-mirror", timeout=15)
        assert got.status_code == 404


# ---- Cleanup: restore original homepage ----
def teardown_module(module):
    try:
        token_resp = requests.post(f"{BASE_URL}/api/admin/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
        if token_resp.status_code != 200:
            return
        headers = {"Authorization": f"Bearer {token_resp.json()['token']}"}
        # Restore defaults (minimal: put empty featured lists and enabled note back)
        current = requests.get(f"{BASE_URL}/api/homepage", timeout=15).json()
        current["important_note"]["enabled"] = True
        current["collection_section"]["featured_product_ids"] = []
        current["reviews_section"]["featured_review_ids"] = []
        requests.patch(f"{BASE_URL}/api/admin/homepage", json=current, headers=headers, timeout=15)
    except Exception:
        pass
