#!/usr/bin/env python3
"""
Phase C (Jul 17 2026) Backend Security Testing
Focus: Rate limiting, Security headers, Regression sanity
"""

import requests
import json
import time
import uuid
from typing import Dict, List, Any

# Configuration
BASE_URL = "http://localhost:8001/api"
ADMIN_EMAIL = "admin@artyfex.in"
ADMIN_PASSWORD = "ArtyFex@2026"

# Test results storage
results = {
    "focus_1_rate_limiting": [],
    "focus_2_security_headers": [],
    "focus_3_regression": [],
    "summary": {
        "total": 0,
        "passed": 0,
        "failed": 0
    }
}

def log_test(focus: str, test_id: str, description: str, passed: bool, details: str = ""):
    """Log a test result"""
    result = {
        "test_id": test_id,
        "description": description,
        "passed": passed,
        "details": details
    }
    results[focus].append(result)
    results["summary"]["total"] += 1
    if passed:
        results["summary"]["passed"] += 1
        print(f"✅ {test_id}: {description}")
    else:
        results["summary"]["failed"] += 1
        print(f"❌ {test_id}: {description}")
    if details:
        print(f"   {details}")

def get_admin_token() -> str:
    """Get admin JWT token"""
    resp = requests.post(f"{BASE_URL}/admin/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if resp.status_code == 200:
        return resp.json()["token"]
    raise Exception(f"Admin login failed: {resp.status_code} {resp.text}")

# =============================================================================
# FOCUS 1 — RATE LIMITING (slowapi)
# =============================================================================

def test_1_1_admin_login_rate_limit():
    """Test 1.1: Admin login rate limit (10/min) - 11th request should return 429"""
    print("\n=== FOCUS 1.1: Admin login rate limiting ===")
    
    # Make 11 rapid requests with wrong credentials
    status_codes = []
    for i in range(11):
        resp = requests.post(f"{BASE_URL}/admin/login", json={
            "email": ADMIN_EMAIL,
            "password": "wrong_password_123"
        })
        status_codes.append(resp.status_code)
        time.sleep(0.1)  # Small delay to avoid overwhelming the server
    
    # First 10 should be 401 (unauthorized), 11th should be 429 (rate limited)
    first_10_all_401 = all(code == 401 for code in status_codes[:10])
    eleventh_is_429 = status_codes[10] == 429
    
    passed = first_10_all_401 and eleventh_is_429
    details = f"Status codes: {status_codes[:10]} + [{status_codes[10]}]. First 10 all 401: {first_10_all_401}, 11th is 429: {eleventh_is_429}"
    
    log_test("focus_1_rate_limiting", "1.1", 
             "Admin login rate limit: 10/min, 11th request returns 429",
             passed, details)

def test_1_2_signup_rate_limit():
    """Test 1.2: Signup rate limit (5/min) - 6th request should return 429"""
    print("\n=== FOCUS 1.2: Signup rate limiting ===")
    
    # Make 6 rapid signups with unique emails
    status_codes = []
    for i in range(6):
        unique_email = f"test_phase_c_{uuid.uuid4().hex[:8]}@example.com"
        resp = requests.post(f"{BASE_URL}/auth/signup", json={
            "name": f"Test User {i}",
            "email": unique_email,
            "password": "ValidPass123"
        })
        status_codes.append(resp.status_code)
        time.sleep(0.1)
    
    # First 5 should be 200 or 400 (if duplicate), 6th should be 429
    first_5_ok = all(code in [200, 400] for code in status_codes[:5])
    sixth_is_429 = status_codes[5] == 429
    
    passed = first_5_ok and sixth_is_429
    details = f"Status codes: {status_codes[:5]} + [{status_codes[5]}]. First 5 all 200/400: {first_5_ok}, 6th is 429: {sixth_is_429}"
    
    log_test("focus_1_rate_limiting", "1.2",
             "Signup rate limit: 5/min, 6th request returns 429",
             passed, details)

def test_1_3_coupon_validate_rate_limit():
    """Test 1.3: Coupon validate rate limit (20/min) - 21st request should return 429"""
    print("\n=== FOCUS 1.3: Coupon validate rate limiting ===")
    
    # Make 21 rapid coupon validation requests
    status_codes = []
    for i in range(21):
        resp = requests.post(f"{BASE_URL}/coupons/validate", json={
            "code": "NOPE",
            "cart_total_inr": 100
        })
        status_codes.append(resp.status_code)
        time.sleep(0.05)
    
    # First 20 should be 404 or 400 (invalid coupon), 21st should be 429
    first_20_ok = all(code in [404, 400] for code in status_codes[:20])
    twentyfirst_is_429 = status_codes[20] == 429
    
    passed = first_20_ok and twentyfirst_is_429
    details = f"First 20 codes: {set(status_codes[:20])}, 21st: {status_codes[20]}. First 20 all 404/400: {first_20_ok}, 21st is 429: {twentyfirst_is_429}"
    
    log_test("focus_1_rate_limiting", "1.3",
             "Coupon validate rate limit: 20/min, 21st request returns 429",
             passed, details)

def test_1_4_b2b_leads_rate_limit():
    """Test 1.4: B2B leads rate limit (5/min) - 6th request should return 429"""
    print("\n=== FOCUS 1.4: B2B leads rate limiting ===")
    
    # Make 6 rapid B2B lead submissions
    status_codes = []
    for i in range(6):
        resp = requests.post(f"{BASE_URL}/b2b/leads", json={
            "full_name": f"Test Lead {i}",
            "email": f"lead{i}@example.com",
            "phone": "1234567890",
            "company": "Test Co",
            "business_type": "Retail",
            "message": "Test message"
        })
        status_codes.append(resp.status_code)
        time.sleep(0.1)
    
    # First 5 should be 200, 6th should be 429
    first_5_ok = all(code == 200 for code in status_codes[:5])
    sixth_is_429 = status_codes[5] == 429
    
    passed = first_5_ok and sixth_is_429
    details = f"Status codes: {status_codes[:5]} + [{status_codes[5]}]. First 5 all 200: {first_5_ok}, 6th is 429: {sixth_is_429}"
    
    log_test("focus_1_rate_limiting", "1.4",
             "B2B leads rate limit: 5/min, 6th request returns 429",
             passed, details)

def test_1_5_no_rate_limit_on_public_endpoints():
    """Test 1.5: Public endpoints (products, homepage) should NOT be rate limited"""
    print("\n=== FOCUS 1.5: Public endpoints NOT rate limited ===")
    
    # Make 30 rapid requests to /api/products
    products_status_codes = []
    for i in range(30):
        resp = requests.get(f"{BASE_URL}/products")
        products_status_codes.append(resp.status_code)
    
    # Make 30 rapid requests to /api/homepage
    homepage_status_codes = []
    for i in range(30):
        resp = requests.get(f"{BASE_URL}/homepage")
        homepage_status_codes.append(resp.status_code)
    
    # All should be 200
    products_all_200 = all(code == 200 for code in products_status_codes)
    homepage_all_200 = all(code == 200 for code in homepage_status_codes)
    
    passed = products_all_200 and homepage_all_200
    details = f"Products: {len([c for c in products_status_codes if c == 200])}/30 returned 200. Homepage: {len([c for c in homepage_status_codes if c == 200])}/30 returned 200."
    
    log_test("focus_1_rate_limiting", "1.5",
             "Public endpoints (products, homepage) NOT rate limited - 30 rapid GETs all return 200",
             passed, details)

# =============================================================================
# FOCUS 2 — SECURITY RESPONSE HEADERS
# =============================================================================

def test_2_1_security_headers_on_get():
    """Test 2.1: Security headers present on GET /api/products"""
    print("\n=== FOCUS 2.1: Security headers on GET ===")
    
    resp = requests.get(f"{BASE_URL}/products")
    headers = resp.headers
    
    required_headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": None  # Just check it exists, value can vary
    }
    
    missing = []
    incorrect = []
    
    for header, expected_value in required_headers.items():
        if header not in headers:
            missing.append(header)
        elif expected_value is not None and headers[header] != expected_value:
            incorrect.append(f"{header}: expected '{expected_value}', got '{headers[header]}'")
    
    passed = len(missing) == 0 and len(incorrect) == 0
    
    details_parts = []
    if missing:
        details_parts.append(f"Missing: {missing}")
    if incorrect:
        details_parts.append(f"Incorrect: {incorrect}")
    if passed:
        details_parts.append(f"All headers present: X-Content-Type-Options={headers.get('X-Content-Type-Options')}, X-Frame-Options={headers.get('X-Frame-Options')}, Referrer-Policy={headers.get('Referrer-Policy')}, Permissions-Policy={headers.get('Permissions-Policy')[:50]}...")
    
    details = "; ".join(details_parts) if details_parts else "All security headers correct"
    
    log_test("focus_2_security_headers", "2.1",
             "Security headers present on GET /api/products",
             passed, details)

def test_2_2_security_headers_on_post():
    """Test 2.2: Security headers present on POST /api/coupons/validate"""
    print("\n=== FOCUS 2.2: Security headers on POST ===")
    
    resp = requests.post(f"{BASE_URL}/coupons/validate", json={
        "code": "",
        "cart_total_inr": 0
    })
    headers = resp.headers
    
    required_headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": None
    }
    
    missing = []
    incorrect = []
    
    for header, expected_value in required_headers.items():
        if header not in headers:
            missing.append(header)
        elif expected_value is not None and headers[header] != expected_value:
            incorrect.append(f"{header}: expected '{expected_value}', got '{headers[header]}'")
    
    passed = len(missing) == 0 and len(incorrect) == 0
    
    details_parts = []
    if missing:
        details_parts.append(f"Missing: {missing}")
    if incorrect:
        details_parts.append(f"Incorrect: {incorrect}")
    if passed:
        details_parts.append(f"All headers present on POST response")
    
    details = "; ".join(details_parts) if details_parts else "All security headers correct"
    
    log_test("focus_2_security_headers", "2.2",
             "Security headers present on POST /api/coupons/validate",
             passed, details)

# =============================================================================
# FOCUS 3 — REGRESSION SANITY CHECK
# =============================================================================

def test_3_1_products_endpoint():
    """Test 3.1: GET /api/products returns 200 with ≥ 1 product"""
    print("\n=== FOCUS 3.1: Products endpoint regression ===")
    
    resp = requests.get(f"{BASE_URL}/products")
    
    passed = resp.status_code == 200 and len(resp.json()) >= 1
    details = f"Status: {resp.status_code}, Products count: {len(resp.json()) if resp.status_code == 200 else 'N/A'}"
    
    log_test("focus_3_regression", "3.1",
             "GET /api/products returns 200 with ≥ 1 product",
             passed, details)

def test_3_2_admin_login_with_correct_creds():
    """Test 3.2: POST /api/admin/login with correct credentials returns 200 and token"""
    print("\n=== FOCUS 3.2: Admin login with correct credentials ===")
    
    # Note: This may fail if rate limit from test 1.1 hasn't reset (60s window)
    # Wait 60 seconds to ensure rate limit has reset
    print("   Waiting 60 seconds for rate limit to reset...")
    time.sleep(60)
    
    resp = requests.post(f"{BASE_URL}/admin/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    
    has_token = False
    if resp.status_code == 200:
        data = resp.json()
        has_token = "token" in data and len(data["token"]) > 0
    
    passed = resp.status_code == 200 and has_token
    details = f"Status: {resp.status_code}, Has token: {has_token}"
    if resp.status_code == 429:
        details += " (Rate limit not reset - this is expected if < 60s since test 1.1)"
    
    log_test("focus_3_regression", "3.2",
             "POST /api/admin/login with correct credentials returns 200 and token",
             passed, details)

def test_3_3_homepage_endpoint():
    """Test 3.3: GET /api/homepage returns 200 with all 12 keys"""
    print("\n=== FOCUS 3.3: Homepage endpoint regression ===")
    
    resp = requests.get(f"{BASE_URL}/homepage")
    
    required_keys = [
        "announcement", "hero", "sale_banner", "craft", "collection_section",
        "reviews_section", "important_note", "custom_css", "category_section",
        "why_section", "featured_section", "nav_default_links"
    ]
    
    has_all_keys = False
    missing_keys = []
    
    if resp.status_code == 200:
        data = resp.json()
        missing_keys = [key for key in required_keys if key not in data]
        has_all_keys = len(missing_keys) == 0
    
    passed = resp.status_code == 200 and has_all_keys
    details = f"Status: {resp.status_code}, Has all 12 keys: {has_all_keys}"
    if missing_keys:
        details += f", Missing: {missing_keys}"
    
    log_test("focus_3_regression", "3.3",
             "GET /api/homepage returns 200 with all 12 keys",
             passed, details)

def test_3_4_homepage_category_tiles_default():
    """Test 3.4: GET /api/homepage - category_section.tiles is empty by default (expected)"""
    print("\n=== FOCUS 3.4: Homepage category tiles default state ===")
    
    resp = requests.get(f"{BASE_URL}/homepage")
    
    tiles_empty = False
    if resp.status_code == 200:
        data = resp.json()
        if "category_section" in data and "tiles" in data["category_section"]:
            tiles_empty = len(data["category_section"]["tiles"]) == 0
    
    # This is EXPECTED behavior - tiles are empty by default (defaults live on frontend)
    passed = resp.status_code == 200 and tiles_empty
    details = f"Status: {resp.status_code}, category_section.tiles is empty: {tiles_empty} (EXPECTED - defaults live on frontend)"
    
    log_test("focus_3_regression", "3.4",
             "GET /api/homepage - category_section.tiles is empty by default (expected, not an issue)",
             passed, details)

def test_3_5_user_signup_validation():
    """Test 3.5: UserSignup validation - short password returns 422, valid password returns 200/400"""
    print("\n=== FOCUS 3.5: UserSignup validation ===")
    
    # Test 1: Short password (< 8 chars) should return 422
    resp1 = requests.post(f"{BASE_URL}/auth/signup", json={
        "name": "x",
        "email": "tiny@t.com",
        "password": "short"
    })
    
    short_pw_rejected = resp1.status_code == 422
    
    # Test 2: Valid password should return 200 or 400 (400 if duplicate email)
    unique_email = f"valid_test_{uuid.uuid4().hex[:8]}@example.com"
    resp2 = requests.post(f"{BASE_URL}/auth/signup", json={
        "name": "Valid User",
        "email": unique_email,
        "password": "ValidPass123"
    })
    
    valid_pw_accepted = resp2.status_code in [200, 400]
    
    passed = short_pw_rejected and valid_pw_accepted
    details = f"Short password (< 8 chars) returns 422: {short_pw_rejected} (status: {resp1.status_code}). Valid password returns 200/400: {valid_pw_accepted} (status: {resp2.status_code})"
    
    log_test("focus_3_regression", "3.5",
             "UserSignup validation: short password → 422, valid password → 200/400",
             passed, details)

# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def main():
    print("=" * 80)
    print("PHASE C (Jul 17 2026) BACKEND SECURITY TESTING")
    print("Focus: Rate limiting, Security headers, Regression sanity")
    print("=" * 80)
    
    try:
        # FOCUS 1: Rate limiting
        print("\n" + "=" * 80)
        print("FOCUS 1 — RATE LIMITING (slowapi)")
        print("=" * 80)
        test_1_1_admin_login_rate_limit()
        test_1_2_signup_rate_limit()
        test_1_3_coupon_validate_rate_limit()
        test_1_4_b2b_leads_rate_limit()
        test_1_5_no_rate_limit_on_public_endpoints()
        
        # FOCUS 2: Security headers
        print("\n" + "=" * 80)
        print("FOCUS 2 — SECURITY RESPONSE HEADERS")
        print("=" * 80)
        test_2_1_security_headers_on_get()
        test_2_2_security_headers_on_post()
        
        # FOCUS 3: Regression sanity
        print("\n" + "=" * 80)
        print("FOCUS 3 — REGRESSION SANITY CHECK")
        print("=" * 80)
        test_3_1_products_endpoint()
        test_3_2_admin_login_with_correct_creds()
        test_3_3_homepage_endpoint()
        test_3_4_homepage_category_tiles_default()
        test_3_5_user_signup_validation()
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        results["summary"]["fatal_error"] = str(e)
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total tests: {results['summary']['total']}")
    print(f"Passed: {results['summary']['passed']}")
    print(f"Failed: {results['summary']['failed']}")
    print(f"Success rate: {results['summary']['passed'] / results['summary']['total'] * 100:.1f}%")
    
    # Save results to JSON
    with open("/app/backend_test_phase_c_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to: /app/backend_test_phase_c_results.json")
    
    return results["summary"]["failed"] == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
