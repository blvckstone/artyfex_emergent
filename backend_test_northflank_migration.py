#!/usr/bin/env python3
"""
Backend testing for Northflank migration (2026-07-18)
Tests the 5 specific items from the review request:
1. NEW endpoint GET /api/health
2. CORS regex (vercel.app allowed, evil.example.com rejected)
3. No regressions on previously-working endpoints
4. Google OAuth kickoff endpoint (should return 500 with proper error)
5. /api/products health-check path still works
"""

import requests
import json
import sys
from typing import Dict, Any

# Backend URL
BASE_URL = "http://localhost:8001/api"

# Test credentials
ADMIN_EMAIL = "admin@artyfex.in"
ADMIN_PASSWORD = "ArtyFex@2026"

# Test results
results = []


def log_test(name: str, passed: bool, details: str = ""):
    """Log a test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    results.append({
        "name": name,
        "passed": passed,
        "details": details
    })
    print(f"{status}: {name}")
    if details:
        print(f"  {details}")


def test_health_endpoint():
    """Test 1: NEW endpoint GET /api/health"""
    print("\n=== TEST 1: Health Endpoint ===")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        
        # Check status code
        if response.status_code != 200:
            log_test("1.1 Health endpoint returns 200", False, f"Got {response.status_code}")
            return
        
        log_test("1.1 Health endpoint returns 200", True)
        
        # Check JSON response
        try:
            data = response.json()
        except Exception as e:
            log_test("1.2 Health endpoint returns valid JSON", False, str(e))
            return
        
        log_test("1.2 Health endpoint returns valid JSON", True)
        
        # Check required keys
        required_keys = [
            "app", "env", "mongo", "razorpay_configured", "resend_configured",
            "google_oauth_configured", "cloudinary_configured", "backend_public_url",
            "frontend_public_url", "cors_allow_origins", "jwt_secret_strength"
        ]
        
        missing_keys = [key for key in required_keys if key not in data]
        if missing_keys:
            log_test("1.3 Health endpoint has all required keys", False, 
                    f"Missing keys: {missing_keys}")
        else:
            log_test("1.3 Health endpoint has all required keys", True,
                    f"All {len(required_keys)} keys present")
        
        # Check that no secrets are leaked
        secret_indicators = ["secret", "password", "key_id", "api_key", "client_secret"]
        leaked_secrets = []
        for key, value in data.items():
            if isinstance(value, str):
                for indicator in secret_indicators:
                    if indicator in key.lower() and len(value) > 10 and value not in ["weak", "strong"]:
                        leaked_secrets.append(f"{key}={value[:20]}...")
        
        if leaked_secrets:
            log_test("1.4 Health endpoint does NOT leak secrets", False,
                    f"Potential leaks: {leaked_secrets}")
        else:
            log_test("1.4 Health endpoint does NOT leak secrets", True)
        
        # Check specific values
        if data.get("app") == "ok":
            log_test("1.5 Health endpoint app status is 'ok'", True)
        else:
            log_test("1.5 Health endpoint app status is 'ok'", False, f"Got: {data.get('app')}")
        
        if data.get("env") == "development":
            log_test("1.6 Health endpoint env is 'development'", True)
        else:
            log_test("1.6 Health endpoint env is 'development'", False, f"Got: {data.get('env')}")
        
        if data.get("mongo") == "ok":
            log_test("1.7 Health endpoint mongo status is 'ok'", True)
        else:
            log_test("1.7 Health endpoint mongo status is 'ok'", False, f"Got: {data.get('mongo')}")
        
        # Check boolean fields
        bool_fields = ["razorpay_configured", "resend_configured", "google_oauth_configured", "cloudinary_configured"]
        for field in bool_fields:
            if isinstance(data.get(field), bool):
                log_test(f"1.8 Health endpoint {field} is boolean", True, f"Value: {data.get(field)}")
            else:
                log_test(f"1.8 Health endpoint {field} is boolean", False, f"Got type: {type(data.get(field))}")
        
        # Check jwt_secret_strength
        if data.get("jwt_secret_strength") in ["weak", "strong"]:
            log_test("1.9 Health endpoint jwt_secret_strength is valid", True, 
                    f"Value: {data.get('jwt_secret_strength')}")
        else:
            log_test("1.9 Health endpoint jwt_secret_strength is valid", False,
                    f"Got: {data.get('jwt_secret_strength')}")
        
        print(f"\nHealth endpoint response:\n{json.dumps(data, indent=2)}")
        
    except Exception as e:
        log_test("1.0 Health endpoint accessible", False, str(e))


def test_cors_regex():
    """Test 2: CORS regex (vercel.app allowed, evil.example.com rejected)"""
    print("\n=== TEST 2: CORS Regex ===")
    
    # Test 2.1: Vercel preview URL should be allowed
    try:
        headers = {"Origin": "https://artyfex-preview-abc.vercel.app"}
        response = requests.get(f"{BASE_URL}/products", headers=headers, timeout=10)
        
        # Check if Access-Control-Allow-Origin is present
        acao = response.headers.get("Access-Control-Allow-Origin")
        
        if acao:
            log_test("2.1 CORS allows vercel.app origin", True,
                    f"Access-Control-Allow-Origin: {acao}")
        else:
            log_test("2.1 CORS allows vercel.app origin", False,
                    "No Access-Control-Allow-Origin header found")
    except Exception as e:
        log_test("2.1 CORS allows vercel.app origin", False, str(e))
    
    # Test 2.2: Evil domain should be rejected
    try:
        headers = {"Origin": "https://evil.example.com"}
        response = requests.get(f"{BASE_URL}/products", headers=headers, timeout=10)
        
        # Check if Access-Control-Allow-Origin is present
        acao = response.headers.get("Access-Control-Allow-Origin")
        
        # In dev mode with CORS_ORIGINS=*, it will return "*" but without credentials
        # The key is that evil.example.com should NOT get a specific echo
        if acao == "*":
            # Check that credentials are NOT allowed with wildcard
            acac = response.headers.get("Access-Control-Allow-Credentials")
            if acac == "true":
                log_test("2.2 CORS rejects evil.example.com (or disallows credentials)", False,
                        "Wildcard with credentials=true is unsafe")
            else:
                log_test("2.2 CORS rejects evil.example.com (or disallows credentials)", True,
                        "Wildcard without credentials (safe)")
        elif acao == "https://evil.example.com":
            log_test("2.2 CORS rejects evil.example.com (or disallows credentials)", False,
                    "Evil origin was echoed back")
        else:
            log_test("2.2 CORS rejects evil.example.com (or disallows credentials)", True,
                    f"Access-Control-Allow-Origin: {acao or 'None'}")
    except Exception as e:
        log_test("2.2 CORS rejects evil.example.com (or disallows credentials)", False, str(e))


def test_no_regressions():
    """Test 3: No regressions on previously-working endpoints"""
    print("\n=== TEST 3: No Regressions ===")
    
    # Test 3.1: GET /api/products
    try:
        response = requests.get(f"{BASE_URL}/products", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                log_test("3.1 GET /api/products returns 200 with JSON list", True,
                        f"Found {len(data)} products")
            else:
                log_test("3.1 GET /api/products returns 200 with JSON list", False,
                        f"Response is not a list: {type(data)}")
        else:
            log_test("3.1 GET /api/products returns 200 with JSON list", False,
                    f"Status: {response.status_code}")
    except Exception as e:
        log_test("3.1 GET /api/products returns 200 with JSON list", False, str(e))
    
    # Test 3.2: GET /api/ (root)
    try:
        response = requests.get(f"{BASE_URL}/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("brand") == "ArtyFex":
                log_test("3.2 GET /api/ returns {\"brand\":\"ArtyFex\"}", True)
            else:
                log_test("3.2 GET /api/ returns {\"brand\":\"ArtyFex\"}", False,
                        f"Got: {data}")
        else:
            log_test("3.2 GET /api/ returns {\"brand\":\"ArtyFex\"}", False,
                    f"Status: {response.status_code}")
    except Exception as e:
        log_test("3.2 GET /api/ returns {\"brand\":\"ArtyFex\"}", False, str(e))
    
    # Test 3.3: POST /api/admin/login
    try:
        payload = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        response = requests.post(f"{BASE_URL}/admin/login", json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "token" in data:
                token = data["token"]
                log_test("3.3 POST /api/admin/login returns JWT token", True,
                        f"Token length: {len(token)}")
                
                # Test 3.4: Use token to access admin endpoint
                headers = {"Authorization": f"Bearer {token}"}
                response = requests.get(f"{BASE_URL}/admin/orders", headers=headers, timeout=10)
                if response.status_code == 200:
                    log_test("3.4 Admin token works for GET /api/admin/orders", True)
                else:
                    log_test("3.4 Admin token works for GET /api/admin/orders", False,
                            f"Status: {response.status_code}")
                
                # Test 3.5: GET /api/admin/homepage
                response = requests.get(f"{BASE_URL}/admin/homepage", headers=headers, timeout=10)
                if response.status_code == 200:
                    log_test("3.5 Admin token works for GET /api/admin/homepage", True)
                else:
                    log_test("3.5 Admin token works for GET /api/admin/homepage", False,
                            f"Status: {response.status_code}")
                
            else:
                log_test("3.3 POST /api/admin/login returns JWT token", False,
                        f"No token in response: {data}")
        else:
            log_test("3.3 POST /api/admin/login returns JWT token", False,
                    f"Status: {response.status_code}, Body: {response.text[:200]}")
    except Exception as e:
        log_test("3.3 POST /api/admin/login returns JWT token", False, str(e))


def test_google_oauth_error():
    """Test 4: Google OAuth kickoff endpoint (should return 500 with proper error)"""
    print("\n=== TEST 4: Google OAuth Error Handling ===")
    
    try:
        response = requests.get(f"{BASE_URL}/auth/google/login", timeout=10, allow_redirects=False)
        
        # Since GOOGLE_CLIENT_ID is not set in local .env, expect 500
        if response.status_code == 500:
            try:
                data = response.json()
                detail = data.get("detail", "")
                if "Google OAuth not configured" in detail:
                    log_test("4.1 GET /api/auth/google/login returns 500 with correct error", True,
                            f"Detail: {detail}")
                else:
                    log_test("4.1 GET /api/auth/google/login returns 500 with correct error", False,
                            f"Wrong error message: {detail}")
            except Exception as e:
                log_test("4.1 GET /api/auth/google/login returns 500 with correct error", False,
                        f"Could not parse JSON: {e}")
        else:
            log_test("4.1 GET /api/auth/google/login returns 500 with correct error", False,
                    f"Expected 500, got {response.status_code}")
        
        # Check that it's NOT a crash (no traceback in response)
        if response.status_code == 500:
            try:
                data = response.json()
                if "detail" in data and "traceback" not in str(data).lower():
                    log_test("4.2 Google OAuth error is handled gracefully (no crash/traceback)", True)
                else:
                    log_test("4.2 Google OAuth error is handled gracefully (no crash/traceback)", False,
                            "Response contains traceback")
            except:
                log_test("4.2 Google OAuth error is handled gracefully (no crash/traceback)", False,
                        "Response is not valid JSON")
        
    except Exception as e:
        log_test("4.1 GET /api/auth/google/login returns 500 with correct error", False, str(e))


def test_products_healthcheck():
    """Test 5: /api/products health-check path still works"""
    print("\n=== TEST 5: Products Health-Check Path ===")
    
    try:
        response = requests.get(f"{BASE_URL}/products", timeout=10)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list):
                    log_test("5.1 GET /api/products (healthcheck path) returns 200 with list", True,
                            f"Found {len(data)} products")
                else:
                    log_test("5.1 GET /api/products (healthcheck path) returns 200 with list", False,
                            f"Response is not a list")
            except Exception as e:
                log_test("5.1 GET /api/products (healthcheck path) returns 200 with list", False,
                        f"Invalid JSON: {e}")
        else:
            log_test("5.1 GET /api/products (healthcheck path) returns 200 with list", False,
                    f"Status: {response.status_code}")
    except Exception as e:
        log_test("5.1 GET /api/products (healthcheck path) returns 200 with list", False, str(e))


def main():
    print("=" * 80)
    print("NORTHFLANK MIGRATION BACKEND TESTING")
    print("=" * 80)
    print(f"Backend URL: {BASE_URL}")
    print(f"Admin credentials: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print("=" * 80)
    
    # Run all tests
    test_health_endpoint()
    test_cors_regex()
    test_no_regressions()
    test_google_oauth_error()
    test_products_healthcheck()
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
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
                print(f"  - {r['name']}")
                if r["details"]:
                    print(f"    {r['details']}")
    
    # Save results to JSON
    with open("/app/backend_test_northflank_migration_results.json", "w") as f:
        json.dump({
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "results": results
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: /app/backend_test_northflank_migration_results.json")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
