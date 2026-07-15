#!/usr/bin/env python3
"""
ArtyFex Phase C Backend Testing - Comprehensive Test Suite
Tests Google Auth error paths, Admin settings, Review prompts, and Regression
"""

import requests
import json
import time
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
import uuid
import os

# Configuration
BACKEND_URL = "https://artyfex-phase-a.preview.emergentagent.com/api"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "artyfex"

# Admin credentials
ADMIN_EMAIL = "admin@artyfex.in"
ADMIN_PASSWORD = "ArtyFex@2026"

# Test results tracking
test_results = []
test_user_email = None
test_user_token = None
admin_token = None
test_orders = []
test_reviews = []


def log_test(section, test_name, passed, details=""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    result = {
        "section": section,
        "test": test_name,
        "passed": passed,
        "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    test_results.append(result)
    print(f"{status} | {section} | {test_name}")
    if details and not passed:
        print(f"   Details: {details}")


def print_section(title):
    """Print section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")


def admin_login():
    """Login as admin and get token"""
    global admin_token
    print_section("ADMIN LOGIN")
    try:
        resp = requests.post(f"{BACKEND_URL}/admin/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }, timeout=10)
        if resp.status_code == 200:
            admin_token = resp.json()["token"]
            log_test("Setup", "Admin login", True, f"Token: {admin_token[:20]}...")
            return True
        else:
            log_test("Setup", "Admin login", False, f"Status {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        log_test("Setup", "Admin login", False, str(e))
        return False


def test_section_1_google_auth_errors():
    """Section 1 - Emergent Google Auth error paths"""
    print_section("SECTION 1: Google Auth Error Paths")
    
    # Test 1: Empty session_id string
    try:
        resp = requests.post(f"{BACKEND_URL}/auth/google/session", json={"session_id": ""}, timeout=10)
        passed = resp.status_code == 400 and "session_id is required" in resp.text.lower()
        log_test("Section 1", "Empty session_id → 400", passed, 
                f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    except Exception as e:
        log_test("Section 1", "Empty session_id → 400", False, str(e))
    
    # Test 2: Missing session_id field (empty body)
    try:
        resp = requests.post(f"{BACKEND_URL}/auth/google/session", json={}, timeout=10)
        passed = resp.status_code in [400, 422]
        log_test("Section 1", "Missing session_id → 400/422", passed,
                f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    except Exception as e:
        log_test("Section 1", "Missing session_id → 400/422", False, str(e))
    
    # Test 3: Invalid session_id
    try:
        resp = requests.post(f"{BACKEND_URL}/auth/google/session", 
                           json={"session_id": "definitely-not-a-real-session-abc123"}, 
                           timeout=15)
        passed = resp.status_code in [401, 502] and len(resp.text) > 0
        log_test("Section 1", "Invalid session_id → 401/502", passed,
                f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    except Exception as e:
        log_test("Section 1", "Invalid session_id → 401/502", False, str(e))


def test_section_2_admin_settings():
    """Section 2 - Admin settings CRUD"""
    print_section("SECTION 2: Admin Settings")
    
    if not admin_token:
        log_test("Section 2", "Admin settings tests", False, "No admin token available")
        return
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Test 1: GET settings with token
    try:
        resp = requests.get(f"{BACKEND_URL}/admin/settings", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            current_value = data.get("review_prompt_days")
            passed = "review_prompt_days" in data
            log_test("Section 2", "GET /admin/settings → 200", passed,
                    f"Current value: {current_value}")
        else:
            log_test("Section 2", "GET /admin/settings → 200", False,
                    f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    except Exception as e:
        log_test("Section 2", "GET /admin/settings → 200", False, str(e))
    
    # Test 2: PATCH settings to 10
    try:
        resp = requests.patch(f"{BACKEND_URL}/admin/settings", 
                            headers=headers,
                            json={"review_prompt_days": 10},
                            timeout=10)
        passed = resp.status_code == 200 and resp.json().get("review_prompt_days") == 10
        log_test("Section 2", "PATCH review_prompt_days=10 → 200", passed,
                f"Response: {resp.json() if resp.status_code == 200 else resp.text[:200]}")
    except Exception as e:
        log_test("Section 2", "PATCH review_prompt_days=10 → 200", False, str(e))
    
    # Test 3: GET again to verify
    try:
        resp = requests.get(f"{BACKEND_URL}/admin/settings", headers=headers, timeout=10)
        passed = resp.status_code == 200 and resp.json().get("review_prompt_days") == 10
        log_test("Section 2", "GET again → review_prompt_days=10", passed,
                f"Value: {resp.json().get('review_prompt_days') if resp.status_code == 200 else 'N/A'}")
    except Exception as e:
        log_test("Section 2", "GET again → review_prompt_days=10", False, str(e))
    
    # Test 4: PATCH with invalid value > 90
    try:
        resp = requests.patch(f"{BACKEND_URL}/admin/settings",
                            headers=headers,
                            json={"review_prompt_days": 200},
                            timeout=10)
        passed = resp.status_code == 422
        log_test("Section 2", "PATCH review_prompt_days=200 → 422", passed,
                f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    except Exception as e:
        log_test("Section 2", "PATCH review_prompt_days=200 → 422", False, str(e))
    
    # Test 5: PATCH with invalid value < 0
    try:
        resp = requests.patch(f"{BACKEND_URL}/admin/settings",
                            headers=headers,
                            json={"review_prompt_days": -1},
                            timeout=10)
        passed = resp.status_code == 422
        log_test("Section 2", "PATCH review_prompt_days=-1 → 422", passed,
                f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    except Exception as e:
        log_test("Section 2", "PATCH review_prompt_days=-1 → 422", False, str(e))
    
    # Test 6: GET without token
    try:
        resp = requests.get(f"{BACKEND_URL}/admin/settings", timeout=10)
        passed = resp.status_code == 401
        log_test("Section 2", "GET without token → 401", passed,
                f"Status: {resp.status_code}")
    except Exception as e:
        log_test("Section 2", "GET without token → 401", False, str(e))
    
    # Test 7: Restore to default (7)
    try:
        resp = requests.patch(f"{BACKEND_URL}/admin/settings",
                            headers=headers,
                            json={"review_prompt_days": 7},
                            timeout=10)
        passed = resp.status_code == 200 and resp.json().get("review_prompt_days") == 7
        log_test("Section 2", "PATCH restore to 7 → 200", passed,
                f"Response: {resp.json() if resp.status_code == 200 else resp.text[:200]}")
    except Exception as e:
        log_test("Section 2", "PATCH restore to 7 → 200", False, str(e))


def test_section_3_review_prompts():
    """Section 3 - Review prompts flow"""
    print_section("SECTION 3: Review Prompts")
    
    global test_user_email, test_user_token, test_orders, test_reviews
    
    # Create fresh test user
    timestamp = int(time.time())
    test_user_email = f"reviewer_{timestamp}@example.com"
    
    try:
        resp = requests.post(f"{BACKEND_URL}/auth/signup", json={
            "name": "Review Tester",
            "email": test_user_email,
            "password": "TestPassword123",
            "phone": "9999999999"
        }, timeout=10)
        
        if resp.status_code == 200:
            test_user_token = resp.json()["token"]
            log_test("Section 3", "Create test user", True, f"Email: {test_user_email}")
        else:
            log_test("Section 3", "Create test user", False, 
                    f"Status: {resp.status_code}, Body: {resp.text[:200]}")
            return
    except Exception as e:
        log_test("Section 3", "Create test user", False, str(e))
        return
    
    user_headers = {"Authorization": f"Bearer {test_user_token}"}
    
    # Test 1: GET review-prompts (should be empty)
    try:
        resp = requests.get(f"{BACKEND_URL}/me/review-prompts", headers=user_headers, timeout=10)
        passed = resp.status_code == 200 and resp.json() == []
        log_test("Section 3", "GET /me/review-prompts → empty []", passed,
                f"Response: {resp.json() if resp.status_code == 200 else resp.text[:200]}")
    except Exception as e:
        log_test("Section 3", "GET /me/review-prompts → empty []", False, str(e))
    
    # Get products to use in test order
    try:
        resp = requests.get(f"{BACKEND_URL}/products", timeout=10)
        products = resp.json()
        if not products:
            log_test("Section 3", "Get products for test", False, "No products available")
            return
        
        test_product = products[0]
        product_id = test_product["id"]
        product_slug = test_product["slug"]
        variant_key = test_product["variants"][0]["key"] if test_product.get("variants") else "default"
        
        log_test("Section 3", "Get products for test", True, 
                f"Using product: {product_slug} (id: {product_id})")
    except Exception as e:
        log_test("Section 3", "Get products for test", False, str(e))
        return
    
    # Insert backdated order via MongoDB
    try:
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        order_id = str(uuid.uuid4())
        order_number = f"TEST-REV-{timestamp}"
        delivered_at = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        created_at = (datetime.now(timezone.utc) - timedelta(days=12)).isoformat()
        
        order_doc = {
            "id": order_id,
            "order_number": order_number,
            "customer": {
                "name": "Review Tester",
                "email": test_user_email,
                "phone": "9999999999",
                "address": "1 A",
                "city": "Mumbai",
                "pincode": "400001"
            },
            "items": [{
                "product_id": product_id,
                "variant_key": variant_key,
                "quantity": 1
            }],
            "payment_method": "razorpay",
            "subtotal_inr": 10000,
            "shipping_inr": 0,
            "total_inr": 10000,
            "discount_inr": 0,
            "status": "delivered",
            "delivered_at": delivered_at,
            "created_at": created_at
        }
        
        db.orders.insert_one(order_doc)
        test_orders.append(order_number)
        
        log_test("Section 3", "Insert backdated order (10 days ago)", True,
                f"Order: {order_number}, Product: {product_slug}")
        
        client.close()
    except Exception as e:
        log_test("Section 3", "Insert backdated order (10 days ago)", False, str(e))
        return
    
    # Test 2: GET review-prompts (should have 1 item)
    try:
        resp = requests.get(f"{BACKEND_URL}/me/review-prompts", headers=user_headers, timeout=10)
        if resp.status_code == 200:
            prompts = resp.json()
            passed = len(prompts) == 1
            if passed and prompts:
                prompt = prompts[0]
                details = (f"Order: {prompt.get('order_number')}, "
                          f"Product: {prompt.get('product_slug')}, "
                          f"Days: {prompt.get('days_since_delivery')}")
                # Verify structure
                has_required = all(k in prompt for k in 
                                 ['order_number', 'product_id', 'product_slug', 
                                  'product_name', 'product_image', 'delivered_at', 'days_since_delivery'])
                passed = passed and has_required and prompt['days_since_delivery'] >= 10
            else:
                details = f"Expected 1 prompt, got {len(prompts)}"
            log_test("Section 3", "GET /me/review-prompts → 1 item", passed, details)
        else:
            log_test("Section 3", "GET /me/review-prompts → 1 item", False,
                    f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    except Exception as e:
        log_test("Section 3", "GET /me/review-prompts → 1 item", False, str(e))
    
    # Test 3: Submit review for the product
    try:
        resp = requests.post(f"{BACKEND_URL}/products/{product_slug}/reviews",
                           headers=user_headers,
                           json={
                               "rating": 5,
                               "title": "Test Review Title",
                               "body": "This is a test review body content for automated testing."
                           },
                           timeout=10)
        
        if resp.status_code == 200:
            review = resp.json()
            # Track review for cleanup
            if "id" in review:
                test_reviews.append(review["id"])
            passed = True
            log_test("Section 3", "POST review → 200", passed,
                    f"Review created for {product_slug}")
        else:
            log_test("Section 3", "POST review → 200", False,
                    f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    except Exception as e:
        log_test("Section 3", "POST review → 200", False, str(e))
    
    # Test 4: GET review-prompts again (should be empty)
    try:
        resp = requests.get(f"{BACKEND_URL}/me/review-prompts", headers=user_headers, timeout=10)
        passed = resp.status_code == 200 and resp.json() == []
        log_test("Section 3", "GET /me/review-prompts → empty [] after review", passed,
                f"Response: {resp.json() if resp.status_code == 200 else resp.text[:200]}")
    except Exception as e:
        log_test("Section 3", "GET /me/review-prompts → empty [] after review", False, str(e))


def test_section_4_threshold():
    """Section 4 - Threshold adjustment"""
    print_section("SECTION 4: Threshold Works")
    
    if not test_user_token or not admin_token:
        log_test("Section 4", "Threshold tests", False, "Missing tokens")
        return
    
    user_headers = {"Authorization": f"Bearer {test_user_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Get a different product for second order
    try:
        resp = requests.get(f"{BACKEND_URL}/products", timeout=10)
        products = resp.json()
        # Try to get second product, fallback to first
        test_product = products[1] if len(products) > 1 else products[0]
        product_id = test_product["id"]
        product_slug = test_product["slug"]
        variant_key = test_product["variants"][0]["key"] if test_product.get("variants") else "default"
        
        log_test("Section 4", "Get second product", True, f"Using: {product_slug}")
    except Exception as e:
        log_test("Section 4", "Get second product", False, str(e))
        return
    
    # Insert order backdated 3 days
    try:
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        timestamp = int(time.time())
        order_id = str(uuid.uuid4())
        order_number = f"TEST-REV-{timestamp}-3D"
        delivered_at = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        created_at = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        
        order_doc = {
            "id": order_id,
            "order_number": order_number,
            "customer": {
                "name": "Review Tester",
                "email": test_user_email,
                "phone": "9999999999",
                "address": "1 A",
                "city": "Mumbai",
                "pincode": "400001"
            },
            "items": [{
                "product_id": product_id,
                "variant_key": variant_key,
                "quantity": 1
            }],
            "payment_method": "razorpay",
            "subtotal_inr": 10000,
            "shipping_inr": 0,
            "total_inr": 10000,
            "discount_inr": 0,
            "status": "delivered",
            "delivered_at": delivered_at,
            "created_at": created_at
        }
        
        db.orders.insert_one(order_doc)
        test_orders.append(order_number)
        
        log_test("Section 4", "Insert order backdated 3 days", True,
                f"Order: {order_number}")
        
        client.close()
    except Exception as e:
        log_test("Section 4", "Insert order backdated 3 days", False, str(e))
        return
    
    # Test 1: GET review-prompts (should be empty, 3 < 7)
    try:
        resp = requests.get(f"{BACKEND_URL}/me/review-prompts", headers=user_headers, timeout=10)
        passed = resp.status_code == 200 and resp.json() == []
        log_test("Section 4", "GET prompts with 3-day order (threshold=7) → []", passed,
                f"Response: {resp.json() if resp.status_code == 200 else resp.text[:200]}")
    except Exception as e:
        log_test("Section 4", "GET prompts with 3-day order (threshold=7) → []", False, str(e))
    
    # Test 2: PATCH threshold to 2
    try:
        resp = requests.patch(f"{BACKEND_URL}/admin/settings",
                            headers=admin_headers,
                            json={"review_prompt_days": 2},
                            timeout=10)
        passed = resp.status_code == 200 and resp.json().get("review_prompt_days") == 2
        log_test("Section 4", "PATCH review_prompt_days=2 → 200", passed,
                f"Response: {resp.json() if resp.status_code == 200 else resp.text[:200]}")
    except Exception as e:
        log_test("Section 4", "PATCH review_prompt_days=2 → 200", False, str(e))
    
    # Test 3: GET review-prompts (should have 1 item, 3 > 2)
    try:
        resp = requests.get(f"{BACKEND_URL}/me/review-prompts", headers=user_headers, timeout=10)
        if resp.status_code == 200:
            prompts = resp.json()
            passed = len(prompts) == 1
            details = f"Expected 1 prompt, got {len(prompts)}"
            if passed and prompts:
                details = f"Product: {prompts[0].get('product_slug')}, Days: {prompts[0].get('days_since_delivery')}"
            log_test("Section 4", "GET prompts with threshold=2 → 1 item", passed, details)
        else:
            log_test("Section 4", "GET prompts with threshold=2 → 1 item", False,
                    f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    except Exception as e:
        log_test("Section 4", "GET prompts with threshold=2 → 1 item", False, str(e))
    
    # Test 4: Restore threshold to 7
    try:
        resp = requests.patch(f"{BACKEND_URL}/admin/settings",
                            headers=admin_headers,
                            json={"review_prompt_days": 7},
                            timeout=10)
        passed = resp.status_code == 200 and resp.json().get("review_prompt_days") == 7
        log_test("Section 4", "PATCH restore to 7 → 200", passed,
                f"Response: {resp.json() if resp.status_code == 200 else resp.text[:200]}")
    except Exception as e:
        log_test("Section 4", "PATCH restore to 7 → 200", False, str(e))


def test_section_5_regression():
    """Section 5 - Regression tests"""
    print_section("SECTION 5: Regression Tests")
    
    # Test 1: Signup fresh user
    timestamp = int(time.time())
    reg_email = f"regression_{timestamp}@example.com"
    
    try:
        resp = requests.post(f"{BACKEND_URL}/auth/signup", json={
            "name": "Regression Tester",
            "email": reg_email,
            "password": "RegTest123",
            "phone": "8888888888"
        }, timeout=10)
        
        passed = resp.status_code == 200 and "token" in resp.json()
        reg_token = resp.json().get("token") if passed else None
        log_test("Section 5", "POST /auth/signup → 200", passed,
                f"Email: {reg_email}")
    except Exception as e:
        log_test("Section 5", "POST /auth/signup → 200", False, str(e))
        reg_token = None
    
    # Test 2: Login with same creds
    try:
        resp = requests.post(f"{BACKEND_URL}/auth/login", json={
            "email": reg_email,
            "password": "RegTest123"
        }, timeout=10)
        
        passed = resp.status_code == 200 and "token" in resp.json()
        log_test("Section 5", "POST /auth/login → 200", passed,
                f"Token received: {bool(passed)}")
    except Exception as e:
        log_test("Section 5", "POST /auth/login → 200", False, str(e))
    
    # Test 3: GET /auth/me
    if reg_token:
        try:
            resp = requests.get(f"{BACKEND_URL}/auth/me",
                              headers={"Authorization": f"Bearer {reg_token}"},
                              timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                # picture should be null or omitted for email/password users
                passed = "email" in data and data["email"] == reg_email
                picture_status = f"picture: {data.get('picture', 'omitted')}"
                log_test("Section 5", "GET /auth/me → 200", passed, picture_status)
            else:
                log_test("Section 5", "GET /auth/me → 200", False,
                        f"Status: {resp.status_code}")
        except Exception as e:
            log_test("Section 5", "GET /auth/me → 200", False, str(e))
    
    # Test 4: GET /products
    try:
        resp = requests.get(f"{BACKEND_URL}/products", timeout=10)
        passed = resp.status_code == 200 and len(resp.json()) == 4
        log_test("Section 5", "GET /products → 4 products", passed,
                f"Count: {len(resp.json()) if resp.status_code == 200 else 'N/A'}")
    except Exception as e:
        log_test("Section 5", "GET /products → 4 products", False, str(e))
    
    # Test 5: POST /coupons/validate
    try:
        resp = requests.post(f"{BACKEND_URL}/coupons/validate", json={
            "code": "WELCOME10",
            "cart_total_inr": 20000
        }, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            passed = data.get("discount_inr") == 2000
            log_test("Section 5", "POST /coupons/validate WELCOME10 → 2000", passed,
                    f"Discount: {data.get('discount_inr')}")
        else:
            log_test("Section 5", "POST /coupons/validate WELCOME10 → 2000", False,
                    f"Status: {resp.status_code}")
    except Exception as e:
        log_test("Section 5", "POST /coupons/validate WELCOME10 → 2000", False, str(e))


def cleanup():
    """Cleanup test data"""
    print_section("CLEANUP")
    
    try:
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Delete test orders
        if test_orders:
            result = db.orders.delete_many({"order_number": {"$regex": "^TEST-REV-"}})
            log_test("Cleanup", f"Delete test orders", True,
                    f"Deleted {result.deleted_count} orders")
        
        # Delete test reviews
        result = db.reviews.delete_many({"user_email": {"$regex": "^reviewer_"}})
        log_test("Cleanup", f"Delete test reviews", True,
                f"Deleted {result.deleted_count} reviews")
        
        # Verify review_prompt_days is set to 7
        if admin_token:
            resp = requests.patch(f"{BACKEND_URL}/admin/settings",
                                headers={"Authorization": f"Bearer {admin_token}"},
                                json={"review_prompt_days": 7},
                                timeout=10)
            log_test("Cleanup", "Restore review_prompt_days=7", 
                    resp.status_code == 200,
                    f"Status: {resp.status_code}")
        
        client.close()
        
    except Exception as e:
        log_test("Cleanup", "Cleanup operations", False, str(e))


def print_summary():
    """Print test summary"""
    print_section("TEST SUMMARY")
    
    total = len(test_results)
    passed = sum(1 for r in test_results if r["passed"])
    failed = total - passed
    
    print(f"\nTotal Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(passed/total*100):.1f}%\n")
    
    if failed > 0:
        print("FAILED TESTS:")
        print("-" * 80)
        for r in test_results:
            if not r["passed"]:
                print(f"❌ [{r['section']}] {r['test']}")
                if r["details"]:
                    print(f"   {r['details']}")
        print()
    
    # Group by section
    sections = {}
    for r in test_results:
        section = r["section"]
        if section not in sections:
            sections[section] = {"passed": 0, "failed": 0}
        if r["passed"]:
            sections[section]["passed"] += 1
        else:
            sections[section]["failed"] += 1
    
    print("BY SECTION:")
    print("-" * 80)
    for section, counts in sections.items():
        total_section = counts["passed"] + counts["failed"]
        print(f"{section}: {counts['passed']}/{total_section} passed")
    print()


def main():
    """Main test execution"""
    print("\n" + "="*80)
    print("  ArtyFex Phase C Backend Testing")
    print("  Backend URL:", BACKEND_URL)
    print("="*80)
    
    # Setup
    if not admin_login():
        print("\n❌ CRITICAL: Admin login failed. Cannot proceed with tests.")
        return
    
    # Run test sections
    test_section_1_google_auth_errors()
    test_section_2_admin_settings()
    test_section_3_review_prompts()
    test_section_4_threshold()
    test_section_5_regression()
    
    # Cleanup
    cleanup()
    
    # Summary
    print_summary()
    
    # Save results to file
    with open("/app/backend_test_results.json", "w") as f:
        json.dump(test_results, f, indent=2)
    print(f"Detailed results saved to: /app/backend_test_results.json\n")


if __name__ == "__main__":
    main()
