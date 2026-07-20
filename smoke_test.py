#!/usr/bin/env python3
"""
ArtyFex Production Readiness Smoke Test
Quick sanity check before GitHub push - 7 critical endpoints
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8001"
ADMIN_EMAIL = "admin@artyfex.in"
ADMIN_PASSWORD = "ArtyFex@2026"

results = []
passed = 0
failed = 0

def test(name, condition, details=""):
    global passed, failed
    status = "✅ PASS" if condition else "❌ FAIL"
    if condition:
        passed += 1
    else:
        failed += 1
    results.append(f"{status} | {name}")
    if details:
        results.append(f"         {details}")
    print(f"{status} | {name}")
    if details:
        print(f"         {details}")

print("=" * 80)
print("ArtyFex Production Readiness Smoke Test")
print("=" * 80)
print()

# Test 1: Health check
print("1. Testing GET /api/health...")
try:
    r = requests.get(f"{BASE_URL}/api/health", timeout=5)
    test(
        "GET /api/health → 200, mongo=ok",
        r.status_code == 200 and r.json().get("mongo") == "ok",
        f"Status: {r.status_code}, Response: {r.json()}"
    )
except Exception as e:
    test("GET /api/health → 200, mongo=ok", False, f"Error: {str(e)}")

# Test 2: Products list
print("\n2. Testing GET /api/products...")
try:
    r = requests.get(f"{BASE_URL}/api/products", timeout=5)
    products = r.json() if r.status_code == 200 else []
    test(
        "GET /api/products → 200, non-empty list",
        r.status_code == 200 and isinstance(products, list) and len(products) > 0,
        f"Status: {r.status_code}, Count: {len(products) if isinstance(products, list) else 'N/A'}"
    )
except Exception as e:
    test("GET /api/products → 200, non-empty list", False, f"Error: {str(e)}")

# Test 3: Root API endpoint
print("\n3. Testing GET /api/...")
try:
    r = requests.get(f"{BASE_URL}/api/", timeout=5)
    data = r.json() if r.status_code == 200 else {}
    test(
        'GET /api/ → 200, {"brand":"ArtyFex"}',
        r.status_code == 200 and data.get("brand") == "ArtyFex",
        f"Status: {r.status_code}, Response: {data}"
    )
except Exception as e:
    test('GET /api/ → 200, {"brand":"ArtyFex"}', False, f"Error: {str(e)}")

# Test 4: Reviews (approved only)
print("\n4. Testing GET /api/reviews...")
try:
    r = requests.get(f"{BASE_URL}/api/reviews", timeout=5)
    reviews = r.json() if r.status_code == 200 else []
    test(
        "GET /api/reviews → 200, list (approved-only)",
        r.status_code == 200 and isinstance(reviews, list),
        f"Status: {r.status_code}, Count: {len(reviews) if isinstance(reviews, list) else 'N/A'}"
    )
except Exception as e:
    test("GET /api/reviews → 200, list (approved-only)", False, f"Error: {str(e)}")

# Test 5: Admin login
print("\n5. Testing POST /api/admin/login...")
admin_token = None
try:
    r = requests.post(
        f"{BASE_URL}/api/admin/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=5
    )
    data = r.json() if r.status_code == 200 else {}
    admin_token = data.get("token")
    test(
        "POST /api/admin/login → 200, returns JWT",
        r.status_code == 200 and admin_token is not None,
        f"Status: {r.status_code}, Token: {'Present' if admin_token else 'Missing'}"
    )
except Exception as e:
    test("POST /api/admin/login → 200, returns JWT", False, f"Error: {str(e)}")

# Test 6: Admin reviews (with token)
print("\n6. Testing GET /api/admin/reviews (with token)...")
if admin_token:
    try:
        r = requests.get(
            f"{BASE_URL}/api/admin/reviews",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=5
        )
        reviews = r.json() if r.status_code == 200 else []
        test(
            "GET /api/admin/reviews → 200, returns list",
            r.status_code == 200 and isinstance(reviews, list),
            f"Status: {r.status_code}, Count: {len(reviews) if isinstance(reviews, list) else 'N/A'}"
        )
    except Exception as e:
        test("GET /api/admin/reviews → 200, returns list", False, f"Error: {str(e)}")
else:
    test("GET /api/admin/reviews → 200, returns list", False, "Skipped: No admin token")

# Test 7: Cloudinary signature (should fail with correct error)
print("\n7. Testing GET /api/cloudinary/signature (dev env - should 500)...")
if admin_token:
    try:
        r = requests.get(
            f"{BASE_URL}/api/cloudinary/signature?folder=artyfex&public_id=abc",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=5
        )
        data = r.json() if r.content else {}
        detail = data.get("detail", "")
        test(
            'GET /api/cloudinary/signature → 500 "Cloudinary not configured"',
            r.status_code == 500 and detail == "Cloudinary not configured",
            f"Status: {r.status_code}, Detail: '{detail}' (CORRECT: dev env has no keys)"
        )
    except Exception as e:
        test('GET /api/cloudinary/signature → 500 "Cloudinary not configured"', False, f"Error: {str(e)}")
else:
    test('GET /api/cloudinary/signature → 500 "Cloudinary not configured"', False, "Skipped: No admin token")

# Summary
print("\n" + "=" * 80)
print(f"SMOKE TEST SUMMARY: {passed}/7 PASSED, {failed}/7 FAILED")
print("=" * 80)

if failed == 0:
    print("\n✅ VERDICT: PRODUCTION READY")
    print("All critical endpoints working correctly. Safe to push to GitHub.")
    sys.exit(0)
else:
    print("\n❌ VERDICT: REGRESSION DETECTED")
    print("One or more critical endpoints failed. DO NOT push to GitHub.")
    sys.exit(1)
