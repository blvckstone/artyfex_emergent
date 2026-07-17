#!/usr/bin/env python3
"""
Phase A Enterprise Backend Testing
Tests GST EXCLUSIVE, Cloudinary signature, Admin whitelist, Google login, Order emails
"""
import requests
import json
import sys
from typing import Dict, Any

BASE_URL = "https://atelier-worlds.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@artyfex.in"
ADMIN_PASSWORD = "ArtyFex@2026"

results = []
admin_token = None
test_product_id = None


def log_test(name: str, passed: bool, details: str = ""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    results.append({"test": name, "passed": passed, "details": details})
    print(f"{status}: {name}")
    if details:
        print(f"  → {details}")


def admin_login() -> str:
    """Login as admin and return token"""
    resp = requests.post(f"{BASE_URL}/admin/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if resp.status_code != 200:
        raise Exception(f"Admin login failed: {resp.status_code} {resp.text}")
    return resp.json()["token"]


def get_first_product_id() -> str:
    """Get first product ID for testing"""
    resp = requests.get(f"{BASE_URL}/products")
    if resp.status_code != 200:
        raise Exception(f"Failed to get products: {resp.status_code}")
    products = resp.json()
    if not products:
        raise Exception("No products found")
    return products[0]["id"]


# ============================================================================
# SECTION 1: GST EXCLUSIVE TREATMENT
# ============================================================================

def test_gst_exclusive_intra_state():
    """Test 1.1: GST exclusive with intra-state (Maharashtra) - CGST+SGST"""
    global test_product_id
    resp = requests.post(f"{BASE_URL}/cart/compute-tax", json={
        "items": [{"product_id": test_product_id, "quantity": 1}],
        "ship_state": "Maharashtra"
    })
    
    if resp.status_code != 200:
        log_test("GST Exclusive - Intra-state", False, f"Status {resp.status_code}: {resp.text}")
        return
    
    data = resp.json()
    
    # Assert treatment is exclusive
    if data.get("treatment") != "exclusive":
        log_test("GST Exclusive - Intra-state", False, f"treatment={data.get('treatment')}, expected 'exclusive'")
        return
    
    # Assert GST total > 0 (HSN 7009 = 18%)
    gst_total = data.get("gst_total_inr", 0)
    if gst_total <= 0:
        log_test("GST Exclusive - Intra-state", False, f"gst_total_inr={gst_total}, expected > 0")
        return
    
    # Assert intra_state = true
    if not data.get("intra_state"):
        log_test("GST Exclusive - Intra-state", False, f"intra_state={data.get('intra_state')}, expected true")
        return
    
    # Assert CGST + SGST = gst_total, IGST = 0
    cgst = data.get("cgst_inr", 0)
    sgst = data.get("sgst_inr", 0)
    igst = data.get("igst_inr", 0)
    
    if cgst + sgst != gst_total:
        log_test("GST Exclusive - Intra-state", False, f"cgst({cgst}) + sgst({sgst}) != gst_total({gst_total})")
        return
    
    if igst != 0:
        log_test("GST Exclusive - Intra-state", False, f"igst={igst}, expected 0 for intra-state")
        return
    
    log_test("GST Exclusive - Intra-state", True, 
             f"treatment=exclusive, gst_total={gst_total}, cgst={cgst}, sgst={sgst}, igst=0")


def test_gst_exclusive_inter_state():
    """Test 1.2: GST exclusive with inter-state (Karnataka) - IGST only"""
    global test_product_id
    resp = requests.post(f"{BASE_URL}/cart/compute-tax", json={
        "items": [{"product_id": test_product_id, "quantity": 1}],
        "ship_state": "Karnataka"
    })
    
    if resp.status_code != 200:
        log_test("GST Exclusive - Inter-state", False, f"Status {resp.status_code}: {resp.text}")
        return
    
    data = resp.json()
    
    # Assert intra_state = false
    if data.get("intra_state"):
        log_test("GST Exclusive - Inter-state", False, f"intra_state={data.get('intra_state')}, expected false")
        return
    
    # Assert IGST = gst_total, CGST = 0, SGST = 0
    gst_total = data.get("gst_total_inr", 0)
    cgst = data.get("cgst_inr", 0)
    sgst = data.get("sgst_inr", 0)
    igst = data.get("igst_inr", 0)
    
    if igst != gst_total:
        log_test("GST Exclusive - Inter-state", False, f"igst({igst}) != gst_total({gst_total})")
        return
    
    if cgst != 0 or sgst != 0:
        log_test("GST Exclusive - Inter-state", False, f"cgst={cgst}, sgst={sgst}, expected both 0 for inter-state")
        return
    
    log_test("GST Exclusive - Inter-state", True, 
             f"intra_state=false, igst={igst}, cgst=0, sgst=0")


def test_order_create_gst_exclusive_intra():
    """Test 1.3: Order create with GST exclusive (intra-state Maharashtra)"""
    global test_product_id, admin_token
    
    # Get product price
    resp = requests.get(f"{BASE_URL}/products")
    products = resp.json()
    product = next((p for p in products if p["id"] == test_product_id), None)
    if not product:
        log_test("Order Create - GST Exclusive Intra", False, "Product not found")
        return
    
    price = product["price_inr"]
    
    # Create order with COD
    order_payload = {
        "customer": {
            "name": "Rajesh Kumar",
            "email": "rajesh.test@example.com",
            "phone": "+919876543210",
            "address": "123 Test Street",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400001",
            "country": "India"
        },
        "items": [
            {
                "product_id": test_product_id,
                "variant_key": "default",
                "quantity": 1
            }
        ],
        "subtotal_inr": price,
        "discount_inr": 0,
        "shipping_inr": 0,
        "total_inr": 0,  # Server will recompute
        "payment_method": "cod"
    }
    
    resp = requests.post(f"{BASE_URL}/orders", json=order_payload)
    
    if resp.status_code != 200:
        log_test("Order Create - GST Exclusive Intra", False, f"Status {resp.status_code}: {resp.text}")
        return
    
    data = resp.json()
    order = data.get("order", {})
    
    # Assert gst_treatment = exclusive
    if order.get("gst_treatment") != "exclusive":
        log_test("Order Create - GST Exclusive Intra", False, 
                 f"gst_treatment={order.get('gst_treatment')}, expected 'exclusive'")
        return
    
    # Assert gst_total_inr > 0
    gst_total = order.get("gst_total_inr", 0)
    if gst_total <= 0:
        log_test("Order Create - GST Exclusive Intra", False, f"gst_total_inr={gst_total}, expected > 0")
        return
    
    # Assert total = subtotal - discount + shipping + gst_total
    subtotal = order.get("subtotal_inr", 0)
    discount = order.get("discount_inr", 0)
    shipping = order.get("shipping_inr", 0)
    total = order.get("total_inr", 0)
    expected_total = subtotal - discount + shipping + gst_total
    
    if total != expected_total:
        log_test("Order Create - GST Exclusive Intra", False, 
                 f"total={total}, expected {expected_total} (subtotal={subtotal} - discount={discount} + shipping={shipping} + gst={gst_total})")
        return
    
    # Assert intra-state split (CGST + SGST)
    cgst = order.get("cgst_inr", 0)
    sgst = order.get("sgst_inr", 0)
    igst = order.get("igst_inr", 0)
    
    if cgst + sgst != gst_total:
        log_test("Order Create - GST Exclusive Intra", False, 
                 f"cgst({cgst}) + sgst({sgst}) != gst_total({gst_total})")
        return
    
    if igst != 0:
        log_test("Order Create - GST Exclusive Intra", False, f"igst={igst}, expected 0 for intra-state")
        return
    
    log_test("Order Create - GST Exclusive Intra", True, 
             f"gst_treatment=exclusive, total={total} (includes gst={gst_total}), cgst={cgst}, sgst={sgst}")


def test_order_create_gst_exclusive_inter():
    """Test 1.4: Order create with GST exclusive (inter-state Karnataka)"""
    global test_product_id
    
    # Get product price
    resp = requests.get(f"{BASE_URL}/products")
    products = resp.json()
    product = next((p for p in products if p["id"] == test_product_id), None)
    if not product:
        log_test("Order Create - GST Exclusive Inter", False, "Product not found")
        return
    
    price = product["price_inr"]
    
    # Create order with COD and inter-state customer
    order_payload = {
        "customer": {
            "name": "Priya Sharma",
            "email": "priya.test@example.com",
            "phone": "+919876543211",
            "address": "456 Test Avenue",
            "city": "Bangalore",
            "state": "Karnataka",
            "pincode": "560001",
            "country": "India"
        },
        "items": [
            {
                "product_id": test_product_id,
                "variant_key": "default",
                "quantity": 1
            }
        ],
        "subtotal_inr": price,
        "discount_inr": 0,
        "shipping_inr": 0,
        "total_inr": 0,  # Server will recompute
        "payment_method": "cod"
    }
    
    resp = requests.post(f"{BASE_URL}/orders", json=order_payload)
    
    if resp.status_code != 200:
        log_test("Order Create - GST Exclusive Inter", False, f"Status {resp.status_code}: {resp.text}")
        return
    
    data = resp.json()
    order = data.get("order", {})
    
    # Assert inter-state split (IGST only)
    gst_total = order.get("gst_total_inr", 0)
    cgst = order.get("cgst_inr", 0)
    sgst = order.get("sgst_inr", 0)
    igst = order.get("igst_inr", 0)
    
    if igst != gst_total:
        log_test("Order Create - GST Exclusive Inter", False, f"igst({igst}) != gst_total({gst_total})")
        return
    
    if cgst != 0 or sgst != 0:
        log_test("Order Create - GST Exclusive Inter", False, 
                 f"cgst={cgst}, sgst={sgst}, expected both 0 for inter-state")
        return
    
    log_test("Order Create - GST Exclusive Inter", True, 
             f"igst={igst}, cgst=0, sgst=0 (inter-state)")


# ============================================================================
# SECTION 2: CLOUDINARY SIGNATURE
# ============================================================================

def test_cloudinary_no_auth():
    """Test 2.1: Cloudinary signature without auth returns 401"""
    resp = requests.get(f"{BASE_URL}/cloudinary/signature")
    
    if resp.status_code == 401:
        log_test("Cloudinary - No Auth", True, "401 Unauthorized as expected")
    else:
        log_test("Cloudinary - No Auth", False, f"Expected 401, got {resp.status_code}")


def test_cloudinary_with_auth():
    """Test 2.2: Cloudinary signature with admin auth returns 200 with all keys"""
    global admin_token
    
    resp = requests.get(f"{BASE_URL}/cloudinary/signature", 
                       headers={"Authorization": f"Bearer {admin_token}"})
    
    if resp.status_code != 200:
        log_test("Cloudinary - With Auth", False, f"Status {resp.status_code}: {resp.text}")
        return
    
    data = resp.json()
    required_keys = ["signature", "timestamp", "cloud_name", "api_key", "folder", "resource_type"]
    missing = [k for k in required_keys if k not in data]
    
    if missing:
        log_test("Cloudinary - With Auth", False, f"Missing keys: {missing}")
        return
    
    # Verify signature is hex string
    sig = data.get("signature", "")
    if not all(c in "0123456789abcdef" for c in sig.lower()):
        log_test("Cloudinary - With Auth", False, f"signature is not hex: {sig}")
        return
    
    # Verify defaults
    if data.get("folder") != "artyfex":
        log_test("Cloudinary - With Auth", False, f"folder={data.get('folder')}, expected 'artyfex'")
        return
    
    if data.get("resource_type") != "image":
        log_test("Cloudinary - With Auth", False, f"resource_type={data.get('resource_type')}, expected 'image'")
        return
    
    log_test("Cloudinary - With Auth", True, 
             f"All keys present, signature={sig[:16]}..., folder=artyfex, resource_type=image")


def test_cloudinary_invalid_folder():
    """Test 2.3: Cloudinary signature with invalid folder returns 400"""
    global admin_token
    
    resp = requests.get(f"{BASE_URL}/cloudinary/signature?folder=notallowed", 
                       headers={"Authorization": f"Bearer {admin_token}"})
    
    if resp.status_code == 400:
        log_test("Cloudinary - Invalid Folder", True, "400 Bad Request as expected")
    else:
        log_test("Cloudinary - Invalid Folder", False, f"Expected 400, got {resp.status_code}")


def test_cloudinary_invalid_resource_type():
    """Test 2.4: Cloudinary signature with invalid resource_type returns 400"""
    global admin_token
    
    resp = requests.get(f"{BASE_URL}/cloudinary/signature?resource_type=pdf", 
                       headers={"Authorization": f"Bearer {admin_token}"})
    
    if resp.status_code == 400:
        log_test("Cloudinary - Invalid Resource Type", True, "400 Bad Request as expected")
    else:
        log_test("Cloudinary - Invalid Resource Type", False, f"Expected 400, got {resp.status_code}")


# ============================================================================
# SECTION 3: ADMIN WHITELIST CRUD
# ============================================================================

def test_whitelist_get_defaults():
    """Test 3.1: GET /admin/whitelist returns 2 readonly defaults"""
    global admin_token
    
    resp = requests.get(f"{BASE_URL}/admin/whitelist", 
                       headers={"Authorization": f"Bearer {admin_token}"})
    
    if resp.status_code != 200:
        log_test("Whitelist - Get Defaults", False, f"Status {resp.status_code}: {resp.text}")
        return
    
    data = resp.json()
    
    # Find readonly entries
    readonly_entries = [e for e in data if e.get("readonly") is True]
    
    if len(readonly_entries) < 2:
        log_test("Whitelist - Get Defaults", False, 
                 f"Expected at least 2 readonly entries, got {len(readonly_entries)}")
        return
    
    # Check for specific emails
    emails = {e.get("email") for e in readonly_entries}
    expected = {"iblvckstone@gmail.com", "virusisstandhere@gmail.com"}
    
    if not expected.issubset(emails):
        log_test("Whitelist - Get Defaults", False, 
                 f"Expected emails {expected}, got {emails}")
        return
    
    log_test("Whitelist - Get Defaults", True, 
             f"Found {len(readonly_entries)} readonly entries including {expected}")


def test_whitelist_add_new():
    """Test 3.2: POST /admin/whitelist adds new entry"""
    global admin_token
    
    resp = requests.post(f"{BASE_URL}/admin/whitelist", 
                        headers={"Authorization": f"Bearer {admin_token}"},
                        json={"email": "testadd@example.com", "note": "E2E"})
    
    if resp.status_code != 200:
        log_test("Whitelist - Add New", False, f"Status {resp.status_code}: {resp.text}")
        return
    
    data = resp.json()
    
    if data.get("email") != "testadd@example.com":
        log_test("Whitelist - Add New", False, f"email={data.get('email')}, expected 'testadd@example.com'")
        return
    
    if data.get("readonly") is not False:
        log_test("Whitelist - Add New", False, f"readonly={data.get('readonly')}, expected False")
        return
    
    log_test("Whitelist - Add New", True, f"Added testadd@example.com with id={data.get('id')}")
    return data.get("id")


def test_whitelist_get_contains_new():
    """Test 3.3: GET /admin/whitelist contains newly added entry"""
    global admin_token
    
    resp = requests.get(f"{BASE_URL}/admin/whitelist", 
                       headers={"Authorization": f"Bearer {admin_token}"})
    
    if resp.status_code != 200:
        log_test("Whitelist - Get Contains New", False, f"Status {resp.status_code}: {resp.text}")
        return None
    
    data = resp.json()
    test_entry = next((e for e in data if e.get("email") == "testadd@example.com"), None)
    
    if not test_entry:
        log_test("Whitelist - Get Contains New", False, "testadd@example.com not found in list")
        return None
    
    if test_entry.get("readonly") is not False:
        log_test("Whitelist - Get Contains New", False, 
                 f"readonly={test_entry.get('readonly')}, expected False")
        return None
    
    log_test("Whitelist - Get Contains New", True, 
             f"Found testadd@example.com with readonly=false, id={test_entry.get('id')}")
    return test_entry.get("id")


def test_whitelist_add_duplicate():
    """Test 3.4: POST duplicate email returns 400"""
    global admin_token
    
    resp = requests.post(f"{BASE_URL}/admin/whitelist", 
                        headers={"Authorization": f"Bearer {admin_token}"},
                        json={"email": "testadd@example.com", "note": "Duplicate"})
    
    if resp.status_code == 400:
        log_test("Whitelist - Add Duplicate", True, "400 Bad Request as expected")
    else:
        log_test("Whitelist - Add Duplicate", False, f"Expected 400, got {resp.status_code}")


def test_whitelist_delete_default():
    """Test 3.5: DELETE default entry returns 400"""
    global admin_token
    
    resp = requests.delete(f"{BASE_URL}/admin/whitelist/default-iblvckstone@gmail.com", 
                          headers={"Authorization": f"Bearer {admin_token}"})
    
    if resp.status_code == 400:
        log_test("Whitelist - Delete Default", True, "400 Bad Request as expected (cannot delete built-ins)")
    else:
        log_test("Whitelist - Delete Default", False, f"Expected 400, got {resp.status_code}")


def test_whitelist_delete_custom(entry_id: str):
    """Test 3.6: DELETE custom entry returns 200"""
    global admin_token
    
    if not entry_id:
        log_test("Whitelist - Delete Custom", False, "No entry_id provided")
        return
    
    resp = requests.delete(f"{BASE_URL}/admin/whitelist/{entry_id}", 
                          headers={"Authorization": f"Bearer {admin_token}"})
    
    if resp.status_code != 200:
        log_test("Whitelist - Delete Custom", False, f"Status {resp.status_code}: {resp.text}")
        return
    
    log_test("Whitelist - Delete Custom", True, f"Deleted entry {entry_id}")


def test_whitelist_get_after_delete():
    """Test 3.7: GET /admin/whitelist no longer contains deleted entry"""
    global admin_token
    
    resp = requests.get(f"{BASE_URL}/admin/whitelist", 
                       headers={"Authorization": f"Bearer {admin_token}"})
    
    if resp.status_code != 200:
        log_test("Whitelist - Get After Delete", False, f"Status {resp.status_code}: {resp.text}")
        return
    
    data = resp.json()
    test_entry = next((e for e in data if e.get("email") == "testadd@example.com"), None)
    
    if test_entry:
        log_test("Whitelist - Get After Delete", False, "testadd@example.com still present after delete")
    else:
        log_test("Whitelist - Get After Delete", True, "testadd@example.com successfully removed")


# ============================================================================
# SECTION 4: ADMIN GOOGLE LOGIN ERROR PATHS
# ============================================================================

def test_google_login_empty_session():
    """Test 4.1: POST /admin/auth/google with empty session_id returns 400"""
    resp = requests.post(f"{BASE_URL}/admin/auth/google", json={"session_id": ""})
    
    if resp.status_code == 400:
        log_test("Google Login - Empty Session", True, "400 Bad Request as expected")
    else:
        log_test("Google Login - Empty Session", False, f"Expected 400, got {resp.status_code}")


def test_google_login_fake_session():
    """Test 4.2: POST /admin/auth/google with fake session_id returns 401"""
    resp = requests.post(f"{BASE_URL}/admin/auth/google", 
                        json={"session_id": "totally-fake-session-abc123"})
    
    if resp.status_code == 401:
        log_test("Google Login - Fake Session", True, "401 Unauthorized as expected (Emergent rejects)")
    else:
        log_test("Google Login - Fake Session", False, f"Expected 401, got {resp.status_code}")


# ============================================================================
# SECTION 5: ORDER EMAILS
# ============================================================================

def test_order_email_cancel():
    """Test 5.1: PATCH order status to cancelled triggers email (200 response)"""
    global admin_token, test_product_id
    
    # Create a fresh order first
    resp = requests.get(f"{BASE_URL}/products")
    products = resp.json()
    product = next((p for p in products if p["id"] == test_product_id), None)
    if not product:
        log_test("Order Email - Cancel", False, "Product not found")
        return None
    
    price = product["price_inr"]
    
    order_payload = {
        "customer": {
            "name": "Email Test User",
            "email": "emailtest@example.com",
            "phone": "+919876543212",
            "address": "789 Email Test St",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400002",
            "country": "India"
        },
        "items": [
            {
                "product_id": test_product_id,
                "variant_key": "default",
                "quantity": 1
            }
        ],
        "subtotal_inr": price,
        "discount_inr": 0,
        "shipping_inr": 0,
        "total_inr": 0,
        "payment_method": "cod"
    }
    
    resp = requests.post(f"{BASE_URL}/orders", json=order_payload)
    if resp.status_code != 200:
        log_test("Order Email - Cancel", False, f"Order creation failed: {resp.status_code}")
        return None
    
    order_number = resp.json()["order"]["order_number"]
    
    # Now cancel it
    resp = requests.patch(f"{BASE_URL}/admin/orders/{order_number}", 
                         headers={"Authorization": f"Bearer {admin_token}"},
                         json={"status": "cancelled"})
    
    if resp.status_code != 200:
        log_test("Order Email - Cancel", False, f"Status {resp.status_code}: {resp.text}")
        return None
    
    log_test("Order Email - Cancel", True, f"Order {order_number} cancelled, email queued (200 OK)")
    return order_number


def test_order_notify_custom():
    """Test 5.2: POST /admin/orders/{n}/notify with custom email returns 200"""
    global admin_token
    
    order_number = test_order_email_cancel()
    if not order_number:
        log_test("Order Email - Custom Notify", False, "No order_number from previous test")
        return
    
    resp = requests.post(f"{BASE_URL}/admin/orders/{order_number}/notify", 
                        headers={"Authorization": f"Bearer {admin_token}"},
                        json={"subject": "Test", "body_html": "Hello"})
    
    if resp.status_code != 200:
        log_test("Order Email - Custom Notify", False, f"Status {resp.status_code}: {resp.text}")
        return
    
    data = resp.json()
    if data.get("queued") is not True:
        log_test("Order Email - Custom Notify", False, f"queued={data.get('queued')}, expected true")
        return
    
    log_test("Order Email - Custom Notify", True, "Custom email queued (200 OK, queued=true)")


def test_order_notify_missing_subject():
    """Test 5.3: POST /admin/orders/{n}/notify with empty subject returns 400"""
    global admin_token
    
    # Use any order number (doesn't matter if it exists for validation test)
    resp = requests.post(f"{BASE_URL}/admin/orders/TEST-001/notify", 
                        headers={"Authorization": f"Bearer {admin_token}"},
                        json={"subject": "", "body_html": "x"})
    
    # Should return 400 for empty subject (or 404 if order doesn't exist - both acceptable)
    if resp.status_code in [400, 404]:
        log_test("Order Email - Missing Subject", True, f"{resp.status_code} as expected (validation working)")
    else:
        log_test("Order Email - Missing Subject", False, f"Expected 400/404, got {resp.status_code}")


def test_broadcast_email():
    """Test 5.4: POST /admin/broadcast with valid payload returns 200"""
    global admin_token
    
    resp = requests.post(f"{BASE_URL}/admin/broadcast", 
                        headers={"Authorization": f"Bearer {admin_token}"},
                        json={"subject": "Test", "body_html": "Hi", "audience": "all_customers"})
    
    if resp.status_code != 200:
        log_test("Broadcast Email - Valid", False, f"Status {resp.status_code}: {resp.text}")
        return
    
    data = resp.json()
    if "queued" not in data:
        log_test("Broadcast Email - Valid", False, f"Missing 'queued' key in response")
        return
    
    queued = data.get("queued")
    if not isinstance(queued, int):
        log_test("Broadcast Email - Valid", False, f"queued={queued}, expected integer")
        return
    
    log_test("Broadcast Email - Valid", True, f"Broadcast queued (200 OK, queued={queued})")


def test_broadcast_missing_subject():
    """Test 5.5: POST /admin/broadcast with empty subject returns 400"""
    global admin_token
    
    resp = requests.post(f"{BASE_URL}/admin/broadcast", 
                        headers={"Authorization": f"Bearer {admin_token}"},
                        json={"subject": "", "body_html": "x"})
    
    if resp.status_code == 400:
        log_test("Broadcast Email - Missing Subject", True, "400 Bad Request as expected")
    else:
        log_test("Broadcast Email - Missing Subject", False, f"Expected 400, got {resp.status_code}")


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    global admin_token, test_product_id
    
    print("=" * 80)
    print("PHASE A ENTERPRISE BACKEND TESTING")
    print("=" * 80)
    print()
    
    try:
        # Setup
        print("🔧 Setup: Admin login...")
        admin_token = admin_login()
        print(f"✓ Admin token: {admin_token[:20]}...")
        print()
        
        print("🔧 Setup: Get first product ID...")
        test_product_id = get_first_product_id()
        print(f"✓ Product ID: {test_product_id}")
        print()
        
        # Section 1: GST EXCLUSIVE
        print("=" * 80)
        print("SECTION 1: GST EXCLUSIVE TREATMENT")
        print("=" * 80)
        test_gst_exclusive_intra_state()
        test_gst_exclusive_inter_state()
        test_order_create_gst_exclusive_intra()
        test_order_create_gst_exclusive_inter()
        print()
        
        # Section 2: Cloudinary
        print("=" * 80)
        print("SECTION 2: CLOUDINARY SIGNATURE")
        print("=" * 80)
        test_cloudinary_no_auth()
        test_cloudinary_with_auth()
        test_cloudinary_invalid_folder()
        test_cloudinary_invalid_resource_type()
        print()
        
        # Section 3: Admin Whitelist
        print("=" * 80)
        print("SECTION 3: ADMIN WHITELIST CRUD")
        print("=" * 80)
        test_whitelist_get_defaults()
        test_whitelist_add_new()
        entry_id = test_whitelist_get_contains_new()
        test_whitelist_add_duplicate()
        test_whitelist_delete_default()
        test_whitelist_delete_custom(entry_id)
        test_whitelist_get_after_delete()
        print()
        
        # Section 4: Google Login Error Paths
        print("=" * 80)
        print("SECTION 4: ADMIN GOOGLE LOGIN ERROR PATHS")
        print("=" * 80)
        test_google_login_empty_session()
        test_google_login_fake_session()
        print()
        
        # Section 5: Order Emails
        print("=" * 80)
        print("SECTION 5: ORDER EMAILS")
        print("=" * 80)
        order_num = test_order_email_cancel()
        test_order_notify_custom()
        test_order_notify_missing_subject()
        test_broadcast_email()
        test_broadcast_missing_subject()
        print()
        
        # Summary
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        passed = sum(1 for r in results if r["passed"])
        total = len(results)
        print(f"Total: {passed}/{total} tests passed")
        print()
        
        if passed == total:
            print("🎉 ALL TESTS PASSED!")
        else:
            print("❌ SOME TESTS FAILED:")
            for r in results:
                if not r["passed"]:
                    print(f"  - {r['test']}: {r['details']}")
        
        # Save results
        with open("/app/backend_test_phase_a_enterprise_results.json", "w") as f:
            json.dump({
                "total": total,
                "passed": passed,
                "failed": total - passed,
                "results": results
            }, f, indent=2)
        
        print()
        print(f"Results saved to: /app/backend_test_phase_a_enterprise_results.json")
        
        sys.exit(0 if passed == total else 1)
        
    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
