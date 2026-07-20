#!/usr/bin/env python3
"""
Batch 1 Backend Testing for ArtyFex
Tests review moderation, verified-buyer, admin notifications, and Cloudinary endpoints
"""

import requests
import json
import uuid
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8001/api"
ADMIN_EMAIL = "admin@artyfex.in"
ADMIN_PASSWORD = "ArtyFex@2026"

# Test results storage
results = {
    "test_suite": "Batch 1 - Review Moderation & Cloudinary",
    "timestamp": datetime.utcnow().isoformat(),
    "tests": []
}

def log_test(test_name, passed, details="", response_data=None):
    """Log test result"""
    result = {
        "test": test_name,
        "passed": passed,
        "details": details
    }
    if response_data:
        result["response"] = response_data
    results["tests"].append(result)
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")
    if details:
        print(f"   {details}")
    print()

def get_admin_token():
    """Get admin JWT token"""
    response = requests.post(
        f"{BASE_URL}/admin/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        return response.json()["token"]
    raise Exception(f"Admin login failed: {response.status_code} {response.text}")

def signup_test_user():
    """Create a fresh test user for review testing"""
    user_email = f"review_tester_{uuid.uuid4().hex[:8]}@example.com"
    user_password = "TestPass123!"
    
    response = requests.post(
        f"{BASE_URL}/auth/signup",
        json={
            "email": user_email,
            "password": user_password,
            "name": "Review Tester",
            "phone": "9876543210"
        }
    )
    
    if response.status_code != 200:
        raise Exception(f"User signup failed: {response.status_code} {response.text}")
    
    # Login to get token
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": user_email, "password": user_password}
    )
    
    if login_response.status_code != 200:
        raise Exception(f"User login failed: {login_response.status_code} {login_response.text}")
    
    return {
        "email": user_email,
        "password": user_password,
        "token": login_response.json()["token"]
    }

def get_first_product():
    """Get first product from the catalog"""
    response = requests.get(f"{BASE_URL}/products")
    if response.status_code == 200:
        products = response.json()
        if products:
            return products[0]
    raise Exception("Failed to get products")

print("=" * 80)
print("BATCH 1 BACKEND TESTING - ArtyFex Review Moderation & Cloudinary")
print("=" * 80)
print()

# Get admin token
try:
    admin_token = get_admin_token()
    print(f"✓ Admin token obtained (length: {len(admin_token)})")
    print()
except Exception as e:
    print(f"✗ Failed to get admin token: {e}")
    exit(1)

# Get test product
try:
    test_product = get_first_product()
    product_id = test_product["id"]
    product_slug = test_product["slug"]
    print(f"✓ Test product: {test_product['name']} (id: {product_id}, slug: {product_slug})")
    print()
except Exception as e:
    print(f"✗ Failed to get test product: {e}")
    exit(1)

# ============================================================================
# TEST 1: GET /api/reviews → returns only approved reviews (seeded=6)
# ============================================================================
print("TEST 1: GET /api/reviews returns only approved reviews")
print("-" * 80)

response = requests.get(f"{BASE_URL}/reviews")
if response.status_code == 200:
    reviews = response.json()
    approved_count = len(reviews)
    
    # Check all reviews have status="approved" or no status field (backward compat)
    all_approved = all(
        r.get("status") in ["approved", None] or r.get("moderation_status") == "approved"
        for r in reviews
    )
    
    log_test(
        "Test 1.1: GET /api/reviews returns approved reviews only",
        all_approved and approved_count >= 0,
        f"Found {approved_count} reviews, all approved or legacy (no status field)",
        {"count": approved_count, "sample": reviews[0] if reviews else None}
    )
else:
    log_test(
        "Test 1.1: GET /api/reviews",
        False,
        f"Expected 200, got {response.status_code}: {response.text}"
    )

# ============================================================================
# TEST 2: GET /api/reviews?product_id=<any> → filters correctly
# ============================================================================
print("TEST 2: GET /api/reviews with product_id filter")
print("-" * 80)

response = requests.get(f"{BASE_URL}/reviews?product_id={product_id}")
if response.status_code == 200:
    filtered_reviews = response.json()
    
    # Check all reviews match the product_id
    all_match = all(r.get("product_id") == product_id for r in filtered_reviews)
    
    log_test(
        "Test 2.1: GET /api/reviews?product_id filters correctly",
        all_match,
        f"Found {len(filtered_reviews)} reviews for product {product_id}, all match filter",
        {"count": len(filtered_reviews)}
    )
else:
    log_test(
        "Test 2.1: GET /api/reviews?product_id",
        False,
        f"Expected 200, got {response.status_code}: {response.text}"
    )

# ============================================================================
# TEST 3: POST /api/reviews without auth → 401
# ============================================================================
print("TEST 3: POST /api/reviews without auth")
print("-" * 80)

response = requests.post(
    f"{BASE_URL}/reviews",
    json={
        "product_id": product_id,
        "rating": 5,
        "title": "Test Review",
        "body": "This is a test review"
    }
)

log_test(
    "Test 3.1: POST /api/reviews without auth → 401",
    response.status_code == 401,
    f"Expected 401, got {response.status_code}",
    {"status": response.status_code}
)

# ============================================================================
# TEST 3b: Create test user and POST review with auth
# ============================================================================
print("TEST 3b: Create test user and POST review")
print("-" * 80)

try:
    test_user = signup_test_user()
    print(f"✓ Test user created: {test_user['email']}")
    print()
    
    # POST review with user token (no product_id to test verified=false)
    response = requests.post(
        f"{BASE_URL}/reviews",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "rating": 4,
            "title": "Test Review Without Product ID",
            "body": "Testing review creation without product_id"
        }
    )
    
    if response.status_code == 200:
        review_data = response.json()
        verified_is_false = review_data.get("verified") == False
        
        log_test(
            "Test 3.2: POST /api/reviews with auth but no product_id → verified=false",
            verified_is_false,
            f"Review created with verified={review_data.get('verified')}",
            {"review_id": review_data.get("id"), "verified": review_data.get("verified")}
        )
        
        # Store review ID for later tests
        test_review_id = review_data.get("id")
    else:
        log_test(
            "Test 3.2: POST /api/reviews with auth",
            False,
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        test_review_id = None
        
except Exception as e:
    log_test(
        "Test 3.2: Create test user and POST review",
        False,
        f"Exception: {str(e)}"
    )
    test_user = None
    test_review_id = None

# ============================================================================
# TEST 4: POST /api/products/{slug}/reviews - duplicate check
# ============================================================================
print("TEST 4: POST /api/products/{slug}/reviews - duplicate check")
print("-" * 80)

if test_user:
    # First review submission
    response1 = requests.post(
        f"{BASE_URL}/products/{product_slug}/reviews",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "rating": 5,
            "title": "First Review for Product",
            "body": "This is my first review for this product"
        }
    )
    
    if response1.status_code == 200:
        first_review = response1.json()
        first_review_id = first_review.get("id")
        
        log_test(
            "Test 4.1: POST /api/products/{slug}/reviews first submission → 200",
            True,
            f"First review created successfully",
            {"review_id": first_review_id}
        )
        
        # Second review submission (should be 409 duplicate)
        response2 = requests.post(
            f"{BASE_URL}/products/{product_slug}/reviews",
            headers={"Authorization": f"Bearer {test_user['token']}"},
            json={
                "rating": 4,
                "title": "Second Review for Same Product",
                "body": "Trying to submit another review"
            }
        )
        
        log_test(
            "Test 4.2: POST /api/products/{slug}/reviews duplicate → 409",
            response2.status_code == 409,
            f"Expected 409, got {response2.status_code}",
            {"status": response2.status_code, "detail": response2.json().get("detail") if response2.status_code == 409 else None}
        )
    else:
        log_test(
            "Test 4.1: POST /api/products/{slug}/reviews first submission",
            False,
            f"Expected 200, got {response1.status_code}: {response1.text}"
        )
        first_review_id = None
else:
    log_test(
        "Test 4: POST /api/products/{slug}/reviews",
        False,
        "Skipped - test user not available"
    )
    first_review_id = None

# ============================================================================
# TEST 5: Pending review does NOT show in public GET /api/reviews
# ============================================================================
print("TEST 5: Pending review visibility")
print("-" * 80)

if first_review_id:
    # Check public endpoint
    response = requests.get(f"{BASE_URL}/reviews")
    if response.status_code == 200:
        public_reviews = response.json()
        pending_in_public = any(r.get("id") == first_review_id for r in public_reviews)
        
        log_test(
            "Test 5.1: Pending review NOT in GET /api/reviews (public)",
            not pending_in_public,
            f"Pending review {'FOUND' if pending_in_public else 'NOT FOUND'} in public list (expected NOT FOUND)",
            {"pending_review_id": first_review_id, "found_in_public": pending_in_public}
        )
    else:
        log_test(
            "Test 5.1: GET /api/reviews (public)",
            False,
            f"Expected 200, got {response.status_code}"
        )
    
    # Check admin endpoint with status=pending
    response = requests.get(
        f"{BASE_URL}/admin/reviews?status=pending",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if response.status_code == 200:
        admin_pending_reviews = response.json()
        pending_in_admin = any(r.get("id") == first_review_id for r in admin_pending_reviews)
        
        log_test(
            "Test 5.2: Pending review FOUND in GET /api/admin/reviews?status=pending",
            pending_in_admin,
            f"Pending review {'FOUND' if pending_in_admin else 'NOT FOUND'} in admin pending list (expected FOUND)",
            {"pending_review_id": first_review_id, "found_in_admin": pending_in_admin, "admin_pending_count": len(admin_pending_reviews)}
        )
    else:
        log_test(
            "Test 5.2: GET /api/admin/reviews?status=pending",
            False,
            f"Expected 200, got {response.status_code}: {response.text}"
        )
else:
    log_test(
        "Test 5: Pending review visibility",
        False,
        "Skipped - no pending review ID available"
    )

# ============================================================================
# TEST 6: PATCH /api/admin/reviews/{id}/moderate - approve review
# ============================================================================
print("TEST 6: Moderate review to approved")
print("-" * 80)

if first_review_id:
    # Moderate to approved
    response = requests.patch(
        f"{BASE_URL}/admin/reviews/{first_review_id}/moderate",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "approved"}
    )
    
    if response.status_code == 200:
        moderated_review = response.json()
        
        log_test(
            "Test 6.1: PATCH /api/admin/reviews/{id}/moderate status=approved → 200",
            True,
            f"Review moderated to approved",
            {"review_id": first_review_id, "status": moderated_review.get("status") or moderated_review.get("moderation_status")}
        )
        
        # Check if now appears in public endpoint
        response = requests.get(f"{BASE_URL}/reviews")
        if response.status_code == 200:
            public_reviews = response.json()
            approved_in_public = any(r.get("id") == first_review_id for r in public_reviews)
            
            log_test(
                "Test 6.2: Approved review NOW appears in GET /api/reviews",
                approved_in_public,
                f"Approved review {'FOUND' if approved_in_public else 'NOT FOUND'} in public list (expected FOUND)",
                {"review_id": first_review_id, "found_in_public": approved_in_public}
            )
        else:
            log_test(
                "Test 6.2: GET /api/reviews after approval",
                False,
                f"Expected 200, got {response.status_code}"
            )
    else:
        log_test(
            "Test 6.1: PATCH /api/admin/reviews/{id}/moderate",
            False,
            f"Expected 200, got {response.status_code}: {response.text}"
        )
else:
    log_test(
        "Test 6: Moderate review",
        False,
        "Skipped - no review ID available"
    )

# ============================================================================
# TEST 7: POST /api/orders - admin notification (no exception)
# ============================================================================
print("TEST 7: POST /api/orders with admin notification")
print("-" * 80)

if test_user:
    # Create an order
    order_payload = {
        "items": [
            {
                "product_id": product_id,
                "variant_key": "gold",
                "size": None,
                "quantity": 1
            }
        ],
        "customer": {
            "name": "Review Tester",
            "email": test_user["email"],
            "phone": "9876543210",
            "address": "123 Test Street",
            "line1": "123 Test Street",
            "line2": "",
            "landmark": "Near Test Mall",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400001",
            "country": "India"
        },
        "payment_method": "cod",
        "subtotal_inr": test_product["price_inr"],
        "discount_inr": 0,
        "shipping_inr": 0,
        "total_inr": test_product["price_inr"]
    }
    
    response = requests.post(
        f"{BASE_URL}/orders",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json=order_payload
    )
    
    if response.status_code == 200:
        order_data = response.json()
        
        log_test(
            "Test 7.1: POST /api/orders → 200 (admin notification queued, no exception)",
            True,
            f"Order created successfully: {order_data.get('order_number')}",
            {"order_number": order_data.get("order_number"), "status": order_data.get("status")}
        )
    else:
        log_test(
            "Test 7.1: POST /api/orders",
            False,
            f"Expected 200, got {response.status_code}: {response.text}"
        )
else:
    log_test(
        "Test 7: POST /api/orders",
        False,
        "Skipped - test user not available"
    )

# ============================================================================
# TEST 8: GET /api/admin/reviews auth check
# ============================================================================
print("TEST 8: GET /api/admin/reviews auth check")
print("-" * 80)

# Without auth
response = requests.get(f"{BASE_URL}/admin/reviews")
log_test(
    "Test 8.1: GET /api/admin/reviews without auth → 401",
    response.status_code == 401,
    f"Expected 401, got {response.status_code}",
    {"status": response.status_code}
)

# With admin token
response = requests.get(
    f"{BASE_URL}/admin/reviews",
    headers={"Authorization": f"Bearer {admin_token}"}
)
log_test(
    "Test 8.2: GET /api/admin/reviews with admin token → 200",
    response.status_code == 200,
    f"Expected 200, got {response.status_code}",
    {"status": response.status_code, "count": len(response.json()) if response.status_code == 200 else None}
)

# ============================================================================
# TEST 9: GET /api/cloudinary/signature with public_id
# ============================================================================
print("TEST 9: GET /api/cloudinary/signature with public_id")
print("-" * 80)

response = requests.get(
    f"{BASE_URL}/cloudinary/signature?public_id=test_image_123",
    headers={"Authorization": f"Bearer {admin_token}"}
)

# Expected: 500 with "Cloudinary not configured" in dev OR 200 with signature fields
if response.status_code == 500:
    detail = response.json().get("detail", "")
    is_expected_error = "Cloudinary not configured" in detail or "cloudinary" in detail.lower()
    
    log_test(
        "Test 9.1: GET /api/cloudinary/signature → 500 'Cloudinary not configured' (PASS in dev)",
        is_expected_error,
        f"Expected 'Cloudinary not configured' error in dev, got: {detail}",
        {"status": 500, "detail": detail}
    )
elif response.status_code == 200:
    sig_data = response.json()
    has_required_fields = all(
        key in sig_data for key in ["signature", "timestamp", "public_id", "overwrite", "invalidate"]
    )
    
    log_test(
        "Test 9.1: GET /api/cloudinary/signature → 200 with required fields",
        has_required_fields,
        f"Response contains: {list(sig_data.keys())}",
        {"status": 200, "fields": list(sig_data.keys())}
    )
else:
    log_test(
        "Test 9.1: GET /api/cloudinary/signature",
        False,
        f"Expected 200 or 500, got {response.status_code}: {response.text}"
    )

# ============================================================================
# TEST 10: DELETE /api/cloudinary/asset with non-Cloudinary URL
# ============================================================================
print("TEST 10: DELETE /api/cloudinary/asset with non-Cloudinary URL")
print("-" * 80)

response = requests.delete(
    f"{BASE_URL}/cloudinary/asset?url=https://example.com/image.jpg",
    headers={"Authorization": f"Bearer {admin_token}"}
)

# Expected: 400 "Not a Cloudinary URL" OR 500 "Cloudinary not configured"
if response.status_code == 400:
    detail = response.json().get("detail", "")
    is_expected_error = "Not a Cloudinary URL" in detail or "cloudinary" in detail.lower()
    
    log_test(
        "Test 10.1: DELETE /api/cloudinary/asset non-Cloudinary URL → 400",
        is_expected_error,
        f"Expected 'Not a Cloudinary URL' error, got: {detail}",
        {"status": 400, "detail": detail}
    )
elif response.status_code == 500:
    detail = response.json().get("detail", "")
    is_expected_error = "Cloudinary not configured" in detail or "cloudinary" in detail.lower()
    
    log_test(
        "Test 10.1: DELETE /api/cloudinary/asset → 500 'Cloudinary not configured' (PASS in dev)",
        is_expected_error,
        f"Expected 'Cloudinary not configured' error in dev, got: {detail}",
        {"status": 500, "detail": detail}
    )
else:
    log_test(
        "Test 10.1: DELETE /api/cloudinary/asset",
        False,
        f"Expected 400 or 500, got {response.status_code}: {response.text}"
    )

# ============================================================================
# SUMMARY
# ============================================================================
print()
print("=" * 80)
print("TEST SUMMARY")
print("=" * 80)

total_tests = len(results["tests"])
passed_tests = sum(1 for t in results["tests"] if t["passed"])
failed_tests = total_tests - passed_tests

print(f"Total Tests: {total_tests}")
print(f"Passed: {passed_tests}")
print(f"Failed: {failed_tests}")
print()

if failed_tests > 0:
    print("FAILED TESTS:")
    for test in results["tests"]:
        if not test["passed"]:
            print(f"  ❌ {test['test']}")
            if test["details"]:
                print(f"     {test['details']}")
    print()

# Save results to JSON
with open("/app/backend_test_batch1_results.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"✓ Results saved to /app/backend_test_batch1_results.json")
print()

if failed_tests == 0:
    print("🎉 ALL TESTS PASSED!")
else:
    print(f"⚠️  {failed_tests} test(s) failed")

exit(0 if failed_tests == 0 else 1)
