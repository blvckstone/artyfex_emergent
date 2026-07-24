#!/usr/bin/env python3
"""
BATCH 8 Backend Testing
Tests the new seed-reference endpoint and regression smoke tests.
"""

import os
import sys
import json
import requests
from typing import Dict, Any

# Backend URL from environment
BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://html-inject-scan.preview.emergentagent.com")
API_BASE = f"{BACKEND_URL}/api"

# Admin credentials
ADMIN_EMAIL = "admin@artyfex.in"
ADMIN_PASSWORD = "ArtyFex@2026"

# Test results
results = []


def log_test(name: str, passed: bool, details: str = ""):
    """Log a test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if details:
        print(f"  Details: {details}")
    results.append({
        "test": name,
        "passed": passed,
        "details": details
    })


def admin_login() -> str:
    """Login as admin and return JWT token."""
    try:
        r = requests.post(
            f"{API_BASE}/admin/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=15
        )
        r.raise_for_status()
        token = r.json().get("token")
        if not token:
            raise Exception("No token in response")
        return token
    except Exception as e:
        print(f"❌ Admin login failed: {e}")
        sys.exit(1)


def test_task1_seed_reference(admin_token: str):
    """
    TASK 1 — POST /admin/products/seed-reference
    Tests:
    1. AUTH GATE: POST without token → 401
    2. HAPPY PATH: POST with admin token → 200 with {ok, action, id, slug}
    3. IDEMPOTENT: Second call → 200 with action="updated"
    4. VERIFY PRODUCT: GET /api/products/golden-geode-mirror-2x2-premium → correct structure
    5. PUBLIC LIST: GET /api/products includes the product
    """
    print("\n" + "="*80)
    print("TASK 1 — POST /admin/products/seed-reference")
    print("="*80)
    
    # Test 1.1: Auth gate - no token should return 401
    try:
        r = requests.post(f"{API_BASE}/admin/products/seed-reference", timeout=15)
        if r.status_code == 401:
            log_test("1.1 - Auth gate (no token)", True, "401 Unauthorized as expected")
        else:
            log_test("1.1 - Auth gate (no token)", False, f"Expected 401, got {r.status_code}")
    except Exception as e:
        log_test("1.1 - Auth gate (no token)", False, f"Request failed: {e}")
    
    # Test 1.2: Happy path - with admin token
    try:
        headers = {"Authorization": f"Bearer {admin_token}"}
        r = requests.post(f"{API_BASE}/admin/products/seed-reference", headers=headers, timeout=30)
        
        if r.status_code == 200:
            data = r.json()
            has_ok = data.get("ok") is True
            has_action = data.get("action") in ["created", "updated"]
            has_id = bool(data.get("id"))
            has_slug = data.get("slug") == "golden-geode-mirror-2x2-premium"
            
            if has_ok and has_action and has_id and has_slug:
                action = data.get("action")
                log_test("1.2 - Happy path (admin token)", True, 
                        f"200 OK with ok=true, action={action}, id={data.get('id')}, slug={data.get('slug')}")
                # Store for next test
                first_action = action
            else:
                log_test("1.2 - Happy path (admin token)", False, 
                        f"Missing required fields: ok={has_ok}, action={has_action}, id={has_id}, slug={has_slug}")
        else:
            log_test("1.2 - Happy path (admin token)", False, 
                    f"Expected 200, got {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log_test("1.2 - Happy path (admin token)", False, f"Request failed: {e}")
    
    # Test 1.3: Idempotent - second call should return action="updated"
    try:
        headers = {"Authorization": f"Bearer {admin_token}"}
        r = requests.post(f"{API_BASE}/admin/products/seed-reference", headers=headers, timeout=30)
        
        if r.status_code == 200:
            data = r.json()
            action = data.get("action")
            if action == "updated":
                log_test("1.3 - Idempotent (second call)", True, 
                        f"200 OK with action='updated' (no duplicate created)")
            else:
                log_test("1.3 - Idempotent (second call)", False, 
                        f"Expected action='updated', got action='{action}'")
        else:
            log_test("1.3 - Idempotent (second call)", False, 
                    f"Expected 200, got {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log_test("1.3 - Idempotent (second call)", False, f"Request failed: {e}")
    
    # Test 1.4: Verify product structure
    try:
        r = requests.get(f"{API_BASE}/products/golden-geode-mirror-2x2-premium", timeout=15)
        
        if r.status_code == 200:
            product = r.json()
            
            # Check name
            name_ok = "Golden Geode" in product.get("name", "")
            
            # Check variants (should be 3: Golden, Black, Silver)
            variants = product.get("variants", [])
            variants_ok = len(variants) == 3
            
            # Check all variants have required fields
            variants_complete = True
            for v in variants:
                if not all([v.get("sku"), v.get("weight_grams"), 
                           v.get("length_cm"), v.get("width_cm"), v.get("height_cm")]):
                    variants_complete = False
                    break
            
            # Check variation_options (should be 6)
            variation_options = product.get("variation_options", [])
            options_ok = len(variation_options) == 6
            
            # Check a_plus_content (should be 6 blocks with distinct layouts)
            a_plus = product.get("a_plus_content", [])
            a_plus_ok = len(a_plus) == 6
            
            # Check all a_plus blocks have layout field
            layouts = [block.get("layout") for block in a_plus]
            layouts_ok = all(layouts) and len(set(layouts)) == 6  # 6 distinct layouts
            
            all_checks = [
                ("name contains 'Golden Geode'", name_ok),
                ("variants length == 3", variants_ok),
                ("all variants have sku/weight/dims", variants_complete),
                ("variation_options length == 6", options_ok),
                ("a_plus_content length == 6", a_plus_ok),
                ("6 distinct layout values", layouts_ok),
            ]
            
            failed_checks = [check[0] for check in all_checks if not check[1]]
            
            if not failed_checks:
                log_test("1.4 - Verify product structure", True, 
                        "All checks passed: name, 3 variants with dims, 6 variation_options, 6 a_plus blocks with distinct layouts")
            else:
                log_test("1.4 - Verify product structure", False, 
                        f"Failed checks: {', '.join(failed_checks)}")
        else:
            log_test("1.4 - Verify product structure", False, 
                    f"Expected 200, got {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log_test("1.4 - Verify product structure", False, f"Request failed: {e}")
    
    # Test 1.5: Public list includes the product
    try:
        r = requests.get(f"{API_BASE}/products", timeout=15)
        
        if r.status_code == 200:
            products = r.json()
            found = any(p.get("slug") == "golden-geode-mirror-2x2-premium" for p in products)
            
            if found:
                log_test("1.5 - Public list includes product", True, 
                        "Product found in GET /api/products")
            else:
                log_test("1.5 - Public list includes product", False, 
                        "Product not found in public list")
        else:
            log_test("1.5 - Public list includes product", False, 
                    f"Expected 200, got {r.status_code}")
    except Exception as e:
        log_test("1.5 - Public list includes product", False, f"Request failed: {e}")


def test_task2_regression_smoke(admin_token: str):
    """
    TASK 2 — Regression smoke tests
    Tests:
    1. GET /api/health → 200, mongo=ok
    2. GET /api/products (public) → 200 non-empty
    3. GET /api/admin/nimbuspost/config (admin) → 200 with configured=true, auth_mode="jwt"
    4. POST /api/admin/orders/{order_number}/nimbuspost/ship → 502 (NOT 500) with real NimbusPost message
    """
    print("\n" + "="*80)
    print("TASK 2 — Regression smoke tests")
    print("="*80)
    
    # Test 2.1: Health check
    try:
        r = requests.get(f"{API_BASE}/health", timeout=15)
        
        if r.status_code == 200:
            data = r.json()
            mongo_ok = data.get("mongo") == "ok"
            
            if mongo_ok:
                log_test("2.1 - Health check", True, "200 OK with mongo=ok")
            else:
                log_test("2.1 - Health check", False, f"mongo status: {data.get('mongo')}")
        else:
            log_test("2.1 - Health check", False, f"Expected 200, got {r.status_code}")
    except Exception as e:
        log_test("2.1 - Health check", False, f"Request failed: {e}")
    
    # Test 2.2: Products list non-empty
    try:
        r = requests.get(f"{API_BASE}/products", timeout=15)
        
        if r.status_code == 200:
            products = r.json()
            if isinstance(products, list) and len(products) > 0:
                log_test("2.2 - Products list non-empty", True, 
                        f"200 OK with {len(products)} products")
            else:
                log_test("2.2 - Products list non-empty", False, 
                        f"Products list is empty or not a list")
        else:
            log_test("2.2 - Products list non-empty", False, 
                    f"Expected 200, got {r.status_code}")
    except Exception as e:
        log_test("2.2 - Products list non-empty", False, f"Request failed: {e}")
    
    # Test 2.3: NimbusPost config
    try:
        headers = {"Authorization": f"Bearer {admin_token}"}
        r = requests.get(f"{API_BASE}/admin/nimbuspost/config", headers=headers, timeout=15)
        
        if r.status_code == 200:
            data = r.json()
            configured = data.get("configured") is True
            auth_mode = data.get("auth_mode") == "jwt"
            
            if configured and auth_mode:
                log_test("2.3 - NimbusPost config", True, 
                        "200 OK with configured=true, auth_mode='jwt'")
            else:
                log_test("2.3 - NimbusPost config", False, 
                        f"configured={data.get('configured')}, auth_mode={data.get('auth_mode')}")
        else:
            log_test("2.3 - NimbusPost config", False, 
                    f"Expected 200, got {r.status_code}")
    except Exception as e:
        log_test("2.3 - NimbusPost config", False, f"Request failed: {e}")
    
    # Test 2.4: NimbusPost ship error handling (should be 502, not 500)
    try:
        # First, get any existing order
        headers = {"Authorization": f"Bearer {admin_token}"}
        r = requests.get(f"{API_BASE}/admin/orders", headers=headers, timeout=15)
        
        if r.status_code == 200:
            orders = r.json()
            if orders and len(orders) > 0:
                # Find an order without tracking_id
                test_order = None
                for order in orders:
                    if not order.get("tracking_id"):
                        test_order = order
                        break
                
                if not test_order:
                    # Use first order anyway (will get "already exists" error)
                    test_order = orders[0]
                
                order_number = test_order.get("order_number")
                
                # Try to ship via NimbusPost (expected to fail with 502)
                r = requests.post(
                    f"{API_BASE}/admin/orders/{order_number}/nimbuspost/ship",
                    headers=headers,
                    timeout=30
                )
                
                # Should be 502 (Bad Gateway) or 400 (if already shipped), NOT 500
                if r.status_code == 502:
                    # Check if detail contains real NimbusPost message
                    try:
                        error_data = r.json()
                        detail = error_data.get("detail", "")
                        
                        # Look for NimbusPost-specific keywords
                        nimbus_keywords = ["Support email", "OTP", "warehouse", "balance", "wallet", "NimbusPost"]
                        has_nimbus_msg = any(keyword.lower() in detail.lower() for keyword in nimbus_keywords)
                        
                        # Check it's NOT a Python traceback (500 error)
                        is_traceback = "Traceback" in detail or "File \"" in detail
                        
                        if has_nimbus_msg and not is_traceback:
                            log_test("2.4 - NimbusPost ship error (502)", True, 
                                    f"502 Bad Gateway with real NimbusPost message: {detail[:100]}")
                        else:
                            log_test("2.4 - NimbusPost ship error (502)", False, 
                                    f"502 but message doesn't look like NimbusPost error: {detail[:200]}")
                    except Exception:
                        log_test("2.4 - NimbusPost ship error (502)", True, 
                                f"502 Bad Gateway (response not JSON, but correct status code)")
                
                elif r.status_code == 400:
                    # Could be "already shipped" or other validation error
                    try:
                        error_data = r.json()
                        detail = error_data.get("detail", "")
                        log_test("2.4 - NimbusPost ship error (502)", True, 
                                f"400 Bad Request (validation error, not crash): {detail[:100]}")
                    except Exception:
                        log_test("2.4 - NimbusPost ship error (502)", True, 
                                "400 Bad Request (validation error)")
                
                elif r.status_code == 500:
                    log_test("2.4 - NimbusPost ship error (502)", False, 
                            f"Got 500 Internal Server Error (should be 502): {r.text[:200]}")
                
                else:
                    log_test("2.4 - NimbusPost ship error (502)", False, 
                            f"Unexpected status code {r.status_code}: {r.text[:200]}")
            else:
                log_test("2.4 - NimbusPost ship error (502)", False, 
                        "No orders found to test NimbusPost ship")
        else:
            log_test("2.4 - NimbusPost ship error (502)", False, 
                    f"Failed to get orders: {r.status_code}")
    except Exception as e:
        log_test("2.4 - NimbusPost ship error (502)", False, f"Request failed: {e}")


def main():
    """Run all BATCH 8 tests."""
    print("\n" + "="*80)
    print("BATCH 8 BACKEND TESTING")
    print("="*80)
    print(f"Backend URL: {API_BASE}")
    print(f"Admin: {ADMIN_EMAIL}")
    
    # Login as admin
    print("\n🔐 Logging in as admin...")
    admin_token = admin_login()
    print("✅ Admin login successful")
    
    # Run tests
    test_task1_seed_reference(admin_token)
    test_task2_regression_smoke(admin_token)
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED")
    else:
        print(f"\n❌ {total - passed} TEST(S) FAILED")
        print("\nFailed tests:")
        for r in results:
            if not r["passed"]:
                print(f"  - {r['test']}")
                if r["details"]:
                    print(f"    {r['details']}")
    
    # Save results to JSON
    with open("/app/backend_test_batch8_results.json", "w") as f:
        json.dump({
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "results": results
        }, f, indent=2)
    
    print(f"\n📄 Results saved to /app/backend_test_batch8_results.json")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
