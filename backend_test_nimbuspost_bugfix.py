#!/usr/bin/env python3
"""
NimbusPost Bug Fix Verification Test
=====================================
Bug: "Origin is required" error on serviceability check
Fix: Added origin_pincode field to config + auto-fallback in serviceability endpoint

Test Scenarios:
1. CONFIG now includes origin_pincode field
2. SERVICEABILITY with configured origin (the bug fix - should return real courier list)
3. SERVICEABILITY with explicit origin override
4. SERVICEABILITY with NO origin anywhere (should return 400)
5. SERVICEABILITY with invalid destination pincode (should return 502 with NimbusPost error)
6. AUTH GATE unchanged (401 without token)
"""

import os
import sys
import json
import requests
from typing import Dict, Any

# Backend URL from environment
BACKEND_URL = os.getenv("REACT_APP_BACKEND_URL", "http://localhost:8001")
API_BASE = f"{BACKEND_URL}/api"

# Admin credentials
ADMIN_EMAIL = "admin@artyfex.in"
ADMIN_PASSWORD = "ArtyFex@2026"

# Test results
results = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "tests": []
}

def log_test(name: str, passed: bool, details: str = ""):
    """Log test result"""
    results["total"] += 1
    if passed:
        results["passed"] += 1
        print(f"✅ {name}")
    else:
        results["failed"] += 1
        print(f"❌ {name}")
    if details:
        print(f"   {details}")
    results["tests"].append({
        "name": name,
        "passed": passed,
        "details": details
    })

def admin_login() -> str:
    """Login as admin and return token"""
    r = requests.post(f"{API_BASE}/admin/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if r.status_code != 200:
        print(f"❌ Admin login failed: {r.status_code} {r.text}")
        sys.exit(1)
    return r.json()["token"]

def main():
    print("=" * 80)
    print("NIMBUSPOST BUG FIX VERIFICATION TEST")
    print("Bug: 'Origin is required' error on serviceability check")
    print("Fix: Added origin_pincode field to config + auto-fallback")
    print("=" * 80)
    print()

    # Login
    print("Logging in as admin...")
    token = admin_login()
    headers = {"Authorization": f"Bearer {token}"}
    print(f"✅ Admin login successful\n")

    # =========================================================================
    # TEST 1: CONFIG now includes origin_pincode field
    # =========================================================================
    print("TEST 1: CONFIG includes origin_pincode field")
    print("-" * 80)
    
    # 1.1 - GET config should have origin_pincode key
    r = requests.get(f"{API_BASE}/admin/nimbuspost/config", headers=headers)
    log_test(
        "1.1 - GET /admin/nimbuspost/config → 200 with origin_pincode key",
        r.status_code == 200 and "origin_pincode" in r.json(),
        f"Status: {r.status_code}, Keys: {list(r.json().keys())}"
    )
    
    # 1.2 - PATCH config with both warehouse_name and origin_pincode
    r = requests.patch(f"{API_BASE}/admin/nimbuspost/config", headers=headers, json={
        "warehouse_name": "ArtyFex Warehouse",
        "origin_pincode": "400095"
    })
    log_test(
        "1.2 - PATCH config with warehouse_name + origin_pincode → 200",
        r.status_code == 200,
        f"Status: {r.status_code}, Response: {r.json()}"
    )
    
    # 1.3 - GET config again to verify persistence
    r = requests.get(f"{API_BASE}/admin/nimbuspost/config", headers=headers)
    config = r.json()
    log_test(
        "1.3 - GET config → origin_pincode persisted as '400095'",
        r.status_code == 200 and config.get("origin_pincode") == "400095",
        f"origin_pincode: {config.get('origin_pincode')}"
    )
    
    print()

    # =========================================================================
    # TEST 2: SERVICEABILITY with configured origin (THE BUG FIX)
    # =========================================================================
    print("TEST 2: SERVICEABILITY with configured origin (THE BUG FIX)")
    print("-" * 80)
    
    # Ensure origin_pincode is set to 400095
    requests.patch(f"{API_BASE}/admin/nimbuspost/config", headers=headers, json={
        "warehouse_name": "ArtyFex Warehouse",
        "origin_pincode": "400095"
    })
    
    # 2.1 - POST serviceability WITHOUT origin in body (should use configured origin_pincode)
    r = requests.post(f"{API_BASE}/admin/nimbuspost/serviceability", headers=headers, json={
        "pincode": "110001",  # Delhi
        "cod": False,
        "weight_g": 500
    })
    
    # Should return 200 with real courier list (not "Origin is required" error)
    if r.status_code == 200:
        data = r.json()
        # Check if we got a real courier list
        has_couriers = False
        courier_names = []
        
        if isinstance(data, dict):
            # NimbusPost returns {"status": true, "data": [...couriers...]}
            if data.get("status") is True and isinstance(data.get("data"), list):
                couriers = data.get("data", [])
                has_couriers = len(couriers) > 0
                courier_names = [c.get("courier_name", "Unknown") for c in couriers[:3]]
            # Or it might return the courier list directly
            elif isinstance(data.get("data"), list):
                couriers = data.get("data", [])
                has_couriers = len(couriers) > 0
                courier_names = [c.get("courier_name", "Unknown") for c in couriers[:3]]
        
        log_test(
            "2.1 - POST serviceability (no origin in body) → 200 with courier list",
            has_couriers,
            f"Couriers found: {len(couriers) if has_couriers else 0}, Examples: {courier_names[:3]}"
        )
    else:
        log_test(
            "2.1 - POST serviceability (no origin in body) → 200 with courier list",
            False,
            f"Status: {r.status_code}, Response: {r.text[:200]}"
        )
    
    print()

    # =========================================================================
    # TEST 3: SERVICEABILITY with explicit origin (override)
    # =========================================================================
    print("TEST 3: SERVICEABILITY with explicit origin override")
    print("-" * 80)
    
    # 3.1 - POST serviceability WITH origin in body (should override config)
    r = requests.post(f"{API_BASE}/admin/nimbuspost/serviceability", headers=headers, json={
        "pincode": "560001",  # Bangalore
        "origin": "400095",   # Mumbai (explicit override)
        "cod": False,
        "weight_g": 1000
    })
    
    if r.status_code == 200:
        data = r.json()
        has_couriers = False
        
        if isinstance(data, dict):
            if data.get("status") is True and isinstance(data.get("data"), list):
                has_couriers = len(data.get("data", [])) > 0
            elif isinstance(data.get("data"), list):
                has_couriers = len(data.get("data", [])) > 0
        
        log_test(
            "3.1 - POST serviceability with explicit origin → 200 with courier list",
            has_couriers,
            f"Mumbai → Bangalore route working"
        )
    else:
        log_test(
            "3.1 - POST serviceability with explicit origin → 200 with courier list",
            False,
            f"Status: {r.status_code}, Response: {r.text[:200]}"
        )
    
    print()

    # =========================================================================
    # TEST 4: SERVICEABILITY with NO origin anywhere
    # =========================================================================
    print("TEST 4: SERVICEABILITY with NO origin anywhere")
    print("-" * 80)
    
    # 4.1 - Clear origin_pincode in config
    r = requests.patch(f"{API_BASE}/admin/nimbuspost/config", headers=headers, json={
        "warehouse_name": "ArtyFex Warehouse",
        "origin_pincode": ""
    })
    log_test(
        "4.1 - PATCH config to clear origin_pincode → 200",
        r.status_code == 200,
        f"Status: {r.status_code}"
    )
    
    # 4.2 - POST serviceability without origin in body and no config origin
    r = requests.post(f"{API_BASE}/admin/nimbuspost/serviceability", headers=headers, json={
        "pincode": "110001"
    })
    log_test(
        "4.2 - POST serviceability (no origin anywhere) → 400 'Origin pincode not set'",
        r.status_code == 400 and "Origin pincode not set" in r.text,
        f"Status: {r.status_code}, Detail: {r.json().get('detail', '')}"
    )
    
    # 4.3 - Restore origin_pincode for remaining tests
    r = requests.patch(f"{API_BASE}/admin/nimbuspost/config", headers=headers, json={
        "warehouse_name": "ArtyFex Warehouse",
        "origin_pincode": "400095"
    })
    log_test(
        "4.3 - Restore origin_pincode to '400095' → 200",
        r.status_code == 200,
        f"Status: {r.status_code}"
    )
    
    print()

    # =========================================================================
    # TEST 5: SERVICEABILITY with invalid destination pincode
    # =========================================================================
    print("TEST 5: SERVICEABILITY with invalid destination pincode")
    print("-" * 80)
    
    # 5.1 - POST serviceability with invalid pincode
    r = requests.post(f"{API_BASE}/admin/nimbuspost/serviceability", headers=headers, json={
        "pincode": "000000",  # Invalid pincode
        "cod": False,
        "weight_g": 500
    })
    
    # Should return 502 with NimbusPost error message (NOT 500 crash)
    log_test(
        "5.1 - POST serviceability with invalid pincode → 502 with NimbusPost error",
        r.status_code == 502,
        f"Status: {r.status_code}, Detail: {r.json().get('detail', '')[:100]}"
    )
    
    print()

    # =========================================================================
    # TEST 6: AUTH GATE unchanged
    # =========================================================================
    print("TEST 6: AUTH GATE unchanged")
    print("-" * 80)
    
    # 6.1 - PATCH config without token
    r = requests.patch(f"{API_BASE}/admin/nimbuspost/config", json={
        "warehouse_name": "Test",
        "origin_pincode": "400001"
    })
    log_test(
        "6.1 - PATCH config WITHOUT token → 401",
        r.status_code == 401,
        f"Status: {r.status_code}"
    )
    
    print()

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total: {results['total']}")
    print(f"Passed: {results['passed']} ✅")
    print(f"Failed: {results['failed']} ❌")
    print()
    
    if results['failed'] > 0:
        print("FAILED TESTS:")
        for test in results['tests']:
            if not test['passed']:
                print(f"  ❌ {test['name']}")
                if test['details']:
                    print(f"     {test['details']}")
        print()
    
    # Save results to JSON
    with open("/app/backend_test_nimbuspost_bugfix_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to: /app/backend_test_nimbuspost_bugfix_results.json")
    print()
    
    # Exit with appropriate code
    sys.exit(0 if results['failed'] == 0 else 1)

if __name__ == "__main__":
    main()
