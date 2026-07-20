#!/usr/bin/env python3
"""
Backend test suite for NimbusPost courier integration (Batch 4 / Task 7)

Test scenarios per review request:
1. AUTH GATE - endpoints require admin token
2. CONFIG - GET/PATCH config with persistence
3. SHIP - real API call (expect NimbusPost error since warehouse not registered)
4. SHIP with empty warehouse - validation
5. TRACK/CANCEL on order with no AWB - validation
6. SERVICEABILITY - real API call
7. PERMISSION CHECK (RBAC) - employee without permissions gets 403
"""

import json
import os
import sys
import requests
from typing import Dict, Any

# Configuration
BACKEND_URL = os.getenv("REACT_APP_BACKEND_URL", "https://05776882-06fb-4022-a391-47e76ae8f55a.preview.emergentagent.com")
API_BASE = f"{BACKEND_URL}/api"

# Admin credentials from test_credentials.md
ADMIN_EMAIL = "admin@artyfex.in"
ADMIN_PASSWORD = "ArtyFex@2026"

# Test results
results = []


def log_test(name: str, passed: bool, details: str = ""):
    """Log a test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if details:
        print(f"  → {details}")
    results.append({"test": name, "passed": passed, "details": details})


def admin_login() -> str:
    """Login as admin and return JWT token."""
    r = requests.post(f"{API_BASE}/admin/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if r.status_code != 200:
        raise Exception(f"Admin login failed: {r.status_code} {r.text}")
    return r.json()["token"]


def get_any_order(token: str) -> Dict[str, Any]:
    """Get any existing order from the database."""
    r = requests.get(f"{API_BASE}/admin/orders", headers={"Authorization": f"Bearer {token}"})
    if r.status_code != 200:
        raise Exception(f"Failed to fetch orders: {r.status_code}")
    orders = r.json()
    if not orders:
        raise Exception("No orders found in database")
    return orders[0]


def create_temp_employee(token: str) -> Dict[str, Any]:
    """Create a temporary employee with view_analytics permission only."""
    payload = {
        "email": f"temp_test_{os.urandom(4).hex()}@artyfex.in",
        "password": "TempPass123!",
        "display_name": "Temp Test Employee",
        "permissions": ["view_analytics"]  # NO manage_shipping or manage_orders
    }
    r = requests.post(f"{API_BASE}/admin/employees", json=payload, headers={"Authorization": f"Bearer {token}"})
    if r.status_code != 200:
        raise Exception(f"Failed to create employee: {r.status_code} {r.text}")
    emp = r.json()
    emp["_test_password"] = payload["password"]
    return emp


def employee_login(email: str, password: str) -> str:
    """Login as employee and return JWT token."""
    r = requests.post(f"{API_BASE}/admin/login", json={"email": email, "password": password})
    if r.status_code != 200:
        raise Exception(f"Employee login failed: {r.status_code}")
    return r.json()["token"]


def delete_employee(token: str, emp_id: str):
    """Delete an employee."""
    requests.delete(f"{API_BASE}/admin/employees/{emp_id}", headers={"Authorization": f"Bearer {token}"})


# =============================================================================
# TEST SCENARIOS
# =============================================================================

def test_1_auth_gate():
    """Test 1: All NimbusPost endpoints require admin token (401 without token)."""
    print("\n=== TEST 1: AUTH GATE ===")
    
    # 1.1: GET config without token
    r = requests.get(f"{API_BASE}/admin/nimbuspost/config")
    log_test(
        "1.1 - GET /admin/nimbuspost/config WITHOUT token → 401",
        r.status_code == 401,
        f"Status: {r.status_code}"
    )
    
    # 1.2: PATCH config without token
    r = requests.patch(f"{API_BASE}/admin/nimbuspost/config", json={"warehouse_name": "Test"})
    log_test(
        "1.2 - PATCH /admin/nimbuspost/config WITHOUT token → 401",
        r.status_code == 401,
        f"Status: {r.status_code}"
    )
    
    # 1.3: POST ship without token
    r = requests.post(f"{API_BASE}/admin/orders/FAKE-ORDER/nimbuspost/ship")
    log_test(
        "1.3 - POST /admin/orders/*/nimbuspost/ship WITHOUT token → 401",
        r.status_code == 401,
        f"Status: {r.status_code}"
    )


def test_2_config_crud(token: str):
    """Test 2: GET/PATCH config with persistence."""
    print("\n=== TEST 2: CONFIG CRUD ===")
    
    # 2.1: GET config
    r = requests.get(f"{API_BASE}/admin/nimbuspost/config", headers={"Authorization": f"Bearer {token}"})
    log_test(
        "2.1 - GET /admin/nimbuspost/config (admin token) → 200",
        r.status_code == 200,
        f"Status: {r.status_code}"
    )
    
    if r.status_code == 200:
        data = r.json()
        # 2.2: Check required keys
        has_keys = all(k in data for k in ["configured", "warehouse_name", "auth_mode"])
        log_test(
            "2.2 - Response has keys {configured, warehouse_name, auth_mode}",
            has_keys,
            f"Keys: {list(data.keys())}"
        )
        
        # 2.3: Check configured is TRUE (JWT creds are set in .env)
        log_test(
            "2.3 - configured=True (JWT creds set in .env)",
            data.get("configured") is True,
            f"configured={data.get('configured')}"
        )
        
        # 2.4: Check auth_mode is "jwt"
        log_test(
            "2.4 - auth_mode='jwt'",
            data.get("auth_mode") == "jwt",
            f"auth_mode={data.get('auth_mode')}"
        )
    
    # 2.5: PATCH config with new warehouse name
    new_warehouse = "ArtyFex Test Mumbai"
    r = requests.patch(
        f"{API_BASE}/admin/nimbuspost/config",
        json={"warehouse_name": new_warehouse},
        headers={"Authorization": f"Bearer {token}"}
    )
    log_test(
        "2.5 - PATCH /admin/nimbuspost/config with warehouse_name → 200",
        r.status_code == 200,
        f"Status: {r.status_code}"
    )
    
    if r.status_code == 200:
        data = r.json()
        log_test(
            "2.6 - Response echoes warehouse_name back",
            data.get("warehouse_name") == new_warehouse,
            f"warehouse_name={data.get('warehouse_name')}"
        )
    
    # 2.7: GET config again to verify persistence
    r = requests.get(f"{API_BASE}/admin/nimbuspost/config", headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 200:
        data = r.json()
        log_test(
            "2.7 - GET config again → warehouse_name persisted",
            data.get("warehouse_name") == new_warehouse,
            f"warehouse_name={data.get('warehouse_name')}"
        )


def test_3_ship_real_api(token: str):
    """Test 3: POST ship with real NimbusPost API call (expect 400/502 NimbusPost error)."""
    print("\n=== TEST 3: SHIP (real API call) ===")
    
    # Get any existing order
    try:
        order = get_any_order(token)
        order_number = order["order_number"]
        print(f"  Using order: {order_number}")
    except Exception as e:
        log_test("3.1 - Get existing order", False, str(e))
        return
    
    # 3.1: POST ship (expect NimbusPost error since warehouse not registered)
    r = requests.post(
        f"{API_BASE}/admin/orders/{order_number}/nimbuspost/ship",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Expected: 400 or 502 with NimbusPost error message (NOT 500 Python crash)
    is_expected_error = r.status_code in (400, 502)
    log_test(
        "3.1 - POST ship → 400/502 with NimbusPost error (NOT 500 crash)",
        is_expected_error,
        f"Status: {r.status_code}, Detail: {r.json().get('detail', '')[:200] if r.status_code != 500 else 'CRASH'}"
    )
    
    # 3.2: Verify error message contains NimbusPost-related keywords
    if is_expected_error:
        detail = r.json().get("detail", "").lower()
        has_nimbus_error = any(kw in detail for kw in ["warehouse", "balance", "nimbuspost", "invalid", "error", "support", "email", "phone", "otp", "verified", "provided"])
        log_test(
            "3.2 - Error detail contains NimbusPost error message",
            has_nimbus_error,
            f"Detail: {r.json().get('detail', '')[:200]}"
        )
    
    # 3.3: POST ship with nonexistent order → 404
    r = requests.post(
        f"{API_BASE}/admin/orders/NOPE-FAKE-ORDER/nimbuspost/ship",
        headers={"Authorization": f"Bearer {token}"}
    )
    log_test(
        "3.3 - POST ship with nonexistent order → 404 'Order not found'",
        r.status_code == 404 and "not found" in r.json().get("detail", "").lower(),
        f"Status: {r.status_code}, Detail: {r.json().get('detail', '')}"
    )


def test_4_ship_empty_warehouse(token: str):
    """Test 4: POST ship with empty warehouse → 400."""
    print("\n=== TEST 4: SHIP with empty warehouse ===")
    
    # 4.1: Clear warehouse name
    r = requests.patch(
        f"{API_BASE}/admin/nimbuspost/config",
        json={"warehouse_name": ""},
        headers={"Authorization": f"Bearer {token}"}
    )
    log_test(
        "4.1 - PATCH config with empty warehouse_name → 200",
        r.status_code == 200,
        f"Status: {r.status_code}"
    )
    
    # 4.2: Try to ship with empty warehouse
    try:
        order = get_any_order(token)
        order_number = order["order_number"]
    except Exception as e:
        log_test("4.2 - Get existing order", False, str(e))
        return
    
    r = requests.post(
        f"{API_BASE}/admin/orders/{order_number}/nimbuspost/ship",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    try:
        detail = r.json().get("detail", "") if r.status_code != 500 else ""
    except Exception:
        detail = r.text
    is_warehouse_error = r.status_code in (400, 502) and "warehouse" in detail.lower()
    log_test(
        "4.2 - POST ship with empty warehouse → 400 with 'warehouse not set'",
        is_warehouse_error,
        f"Status: {r.status_code}, Detail: {detail}"
    )
    
    # 4.3: Restore warehouse for subsequent tests
    r = requests.patch(
        f"{API_BASE}/admin/nimbuspost/config",
        json={"warehouse_name": "ArtyFex Test Mumbai"},
        headers={"Authorization": f"Bearer {token}"}
    )
    log_test(
        "4.3 - Restore warehouse to 'ArtyFex Test Mumbai' → 200",
        r.status_code == 200,
        f"Status: {r.status_code}"
    )


def test_5_track_cancel_no_awb(token: str):
    """Test 5: TRACK/CANCEL on order with no AWB → 400."""
    print("\n=== TEST 5: TRACK/CANCEL on order with no AWB ===")
    
    # Get any existing order (should not have AWB yet)
    try:
        order = get_any_order(token)
        order_number = order["order_number"]
        print(f"  Using order: {order_number}")
    except Exception as e:
        log_test("5.1 - Get existing order", False, str(e))
        return
    
    # 5.1: POST cancel before AWB exists → 400
    r = requests.post(
        f"{API_BASE}/admin/orders/{order_number}/nimbuspost/cancel",
        headers={"Authorization": f"Bearer {token}"}
    )
    is_no_awb_error = r.status_code == 400 and "awb" in r.json().get("detail", "").lower()
    log_test(
        "5.1 - POST cancel (before AWB) → 400 'No AWB to cancel'",
        is_no_awb_error,
        f"Status: {r.status_code}, Detail: {r.json().get('detail', '')}"
    )
    
    # 5.2: GET track before AWB exists → 400
    r = requests.get(
        f"{API_BASE}/admin/orders/{order_number}/nimbuspost/track",
        headers={"Authorization": f"Bearer {token}"}
    )
    is_no_awb_error = r.status_code == 400 and "awb" in r.json().get("detail", "").lower()
    log_test(
        "5.2 - GET track (before AWB) → 400 'No AWB — create a NimbusPost shipment first'",
        is_no_awb_error,
        f"Status: {r.status_code}, Detail: {r.json().get('detail', '')}"
    )


def test_6_serviceability(token: str):
    """Test 6: POST serviceability (real API call)."""
    print("\n=== TEST 6: SERVICEABILITY (real API call) ===")
    
    # 6.1: POST serviceability with valid pincode
    r = requests.post(
        f"{API_BASE}/admin/nimbuspost/serviceability",
        json={"pincode": "110001", "cod": False, "weight_g": 500},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Expected: 200 with courier list OR 502 with NimbusPost error (NOT 500 crash)
    is_valid_response = r.status_code in (200, 502)
    log_test(
        "6.1 - POST serviceability → 200 with data OR 502 with NimbusPost error (NOT 500 crash)",
        is_valid_response,
        f"Status: {r.status_code}, Response: {str(r.json())[:200] if r.status_code != 500 else 'CRASH'}"
    )


def test_7_rbac_permissions(token: str):
    """Test 7: RBAC - employee without permissions gets 403."""
    print("\n=== TEST 7: PERMISSION CHECK (RBAC) ===")
    
    # 7.1: Create temp employee with view_analytics only
    try:
        emp = create_temp_employee(token)
        emp_email = emp["email"]
        emp_password = emp["_test_password"]
        emp_id = emp["id"]
        print(f"  Created temp employee: {emp_email}")
    except Exception as e:
        log_test("7.1 - Create temp employee", False, str(e))
        return
    
    # 7.2: Login as employee
    try:
        emp_token = employee_login(emp_email, emp_password)
        log_test("7.2 - Employee login successful", True, f"Token: {emp_token[:20]}...")
    except Exception as e:
        log_test("7.2 - Employee login", False, str(e))
        delete_employee(token, emp_id)
        return
    
    # 7.3: Employee tries to PATCH config (missing manage_shipping) → 403
    r = requests.patch(
        f"{API_BASE}/admin/nimbuspost/config",
        json={"warehouse_name": "Hacker Warehouse"},
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    log_test(
        "7.3 - Employee PATCH config (missing manage_shipping) → 403",
        r.status_code == 403,
        f"Status: {r.status_code}"
    )
    
    # 7.4: Employee tries to POST ship (missing manage_orders) → 403
    try:
        order = get_any_order(token)
        order_number = order["order_number"]
    except Exception as e:
        log_test("7.4 - Get existing order", False, str(e))
        delete_employee(token, emp_id)
        return
    
    r = requests.post(
        f"{API_BASE}/admin/orders/{order_number}/nimbuspost/ship",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    log_test(
        "7.4 - Employee POST ship (missing manage_orders) → 403",
        r.status_code == 403,
        f"Status: {r.status_code}"
    )
    
    # 7.5: Clean up - delete temp employee
    delete_employee(token, emp_id)
    log_test("7.5 - Cleanup: Delete temp employee", True, f"Deleted {emp_email}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 80)
    print("NIMBUSPOST COURIER INTEGRATION TEST SUITE (Batch 4 / Task 7)")
    print("=" * 80)
    
    try:
        # Login as admin
        print("\n🔐 Logging in as admin...")
        token = admin_login()
        print(f"✅ Admin login successful (token: {token[:20]}...)")
        
        # Run all test scenarios
        test_1_auth_gate()
        test_2_config_crud(token)
        test_3_ship_real_api(token)
        test_4_ship_empty_warehouse(token)
        test_5_track_cancel_no_awb(token)
        test_6_serviceability(token)
        test_7_rbac_permissions(token)
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    
    print(f"\n✅ PASSED: {passed}/{total}")
    print(f"❌ FAILED: {total - passed}/{total}")
    
    if total - passed > 0:
        print("\nFailed tests:")
        for r in results:
            if not r["passed"]:
                print(f"  - {r['test']}: {r['details']}")
    
    # Save results to JSON
    output_file = "/app/backend_test_nimbuspost_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "results": results
        }, f, indent=2)
    print(f"\n📄 Results saved to: {output_file}")
    
    # Exit with appropriate code
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
