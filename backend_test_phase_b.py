#!/usr/bin/env python3
"""
Phase B Backend Testing - ArtyFex E-commerce
Tests: Analytics, Live Analytics, RBAC + Employees
"""

import requests
import json
import time
from datetime import datetime, timedelta

# Configuration
BASE_URL = "https://admin-dashboard-v2-65.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@artyfex.in"
ADMIN_PASSWORD = "ArtyFex@2026"

# Test results
results = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "tests": []
}

def log_test(name, passed, details=""):
    """Log test result"""
    results["total"] += 1
    if passed:
        results["passed"] += 1
        print(f"✅ {name}")
    else:
        results["failed"] += 1
        print(f"❌ {name}")
        if details:
            print(f"   Details: {details}")
    results["tests"].append({
        "name": name,
        "passed": passed,
        "details": details
    })

def admin_login():
    """Login as admin owner and return token"""
    resp = requests.post(f"{BASE_URL}/admin/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if resp.status_code == 200:
        return resp.json().get("token")
    raise Exception(f"Admin login failed: {resp.status_code} {resp.text}")

print("=" * 80)
print("PHASE B BACKEND TESTING - ArtyFex E-commerce")
print("=" * 80)
print()

# ============================================================================
# SECTION 1: ANALYTICS OVERVIEW ENDPOINT
# ============================================================================
print("SECTION 1: Analytics Overview Endpoint")
print("-" * 80)

try:
    owner_token = admin_login()
    headers = {"Authorization": f"Bearer {owner_token}"}
    
    # Test 1.1: GET /api/admin/analytics/overview
    resp = requests.get(f"{BASE_URL}/admin/analytics/overview", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        
        # Check required top-level keys
        required_keys = ["orders", "returns", "financials", "top_products", "series_30d", "coupons_summary"]
        has_all_keys = all(k in data for k in required_keys)
        log_test("Analytics overview - has all required keys", has_all_keys, 
                 f"Missing: {[k for k in required_keys if k not in data]}" if not has_all_keys else "")
        
        # Check orders structure
        orders = data.get("orders", {})
        orders_keys = ["total", "active", "successful", "cancelled", "failed"]
        has_orders_keys = all(k in orders for k in orders_keys)
        all_numbers = all(isinstance(orders.get(k), int) for k in orders_keys)
        log_test("Analytics overview - orders structure valid", 
                 has_orders_keys and all_numbers,
                 f"Orders: {orders}")
        
        # Check returns structure
        returns = data.get("returns", {})
        returns_keys = ["total", "active", "completed"]
        has_returns_keys = all(k in returns for k in returns_keys)
        all_numbers_ret = all(isinstance(returns.get(k), int) for k in returns_keys)
        log_test("Analytics overview - returns structure valid",
                 has_returns_keys and all_numbers_ret,
                 f"Returns: {returns}")
        
        # Check financials structure
        financials = data.get("financials", {})
        fin_keys = ["revenue_inr", "products_total", "customers_total", "b2b_leads_new", "failed_transactions"]
        has_fin_keys = all(k in financials for k in fin_keys)
        all_numbers_fin = all(isinstance(financials.get(k), int) for k in fin_keys)
        log_test("Analytics overview - financials structure valid",
                 has_fin_keys and all_numbers_fin,
                 f"Financials: {financials}")
        
        # Check series_30d
        series = data.get("series_30d", [])
        has_30_entries = len(series) == 30
        if has_30_entries and series:
            first_entry = series[0]
            has_series_keys = all(k in first_entry for k in ["date", "orders", "revenue_inr"])
            log_test("Analytics overview - series_30d has 30 entries with correct structure",
                     has_series_keys,
                     f"Length: {len(series)}, Sample: {first_entry}")
        else:
            log_test("Analytics overview - series_30d has 30 entries", has_30_entries,
                     f"Got {len(series)} entries")
        
        # Check top_products
        top_products = data.get("top_products", [])
        log_test("Analytics overview - top_products is array",
                 isinstance(top_products, list),
                 f"Type: {type(top_products)}, Length: {len(top_products)}")
        
        # Check coupons_summary
        coupons = data.get("coupons_summary", [])
        log_test("Analytics overview - coupons_summary is array",
                 isinstance(coupons, list),
                 f"Type: {type(coupons)}, Length: {len(coupons)}")
    else:
        log_test("Analytics overview - GET request", False, 
                 f"Status: {resp.status_code}, Body: {resp.text[:200]}")
        
except Exception as e:
    log_test("Analytics overview - exception", False, str(e))

print()

# ============================================================================
# SECTION 2: ANALYTICS ALERTS ENDPOINT
# ============================================================================
print("SECTION 2: Analytics Alerts Endpoint")
print("-" * 80)

try:
    headers = {"Authorization": f"Bearer {owner_token}"}
    
    # Test 2.1: GET /api/admin/analytics/alerts
    resp = requests.get(f"{BASE_URL}/admin/analytics/alerts", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        
        # Check required keys
        required_keys = ["low_stock_products", "out_of_stock_count", "old_pending_returns", "recent_failed_payments_1h"]
        has_all_keys = all(k in data for k in required_keys)
        log_test("Analytics alerts - has all required keys", has_all_keys,
                 f"Keys: {list(data.keys())}")
        
        # Check types
        low_stock = data.get("low_stock_products", [])
        out_of_stock = data.get("out_of_stock_count", -1)
        old_returns = data.get("old_pending_returns", [])
        recent_failures = data.get("recent_failed_payments_1h", -1)
        
        types_valid = (isinstance(low_stock, list) and 
                      isinstance(out_of_stock, int) and
                      isinstance(old_returns, list) and
                      isinstance(recent_failures, int))
        
        log_test("Analytics alerts - response types valid", types_valid,
                 f"low_stock: {type(low_stock)}, out_of_stock: {type(out_of_stock)}, "
                 f"old_returns: {type(old_returns)}, recent_failures: {type(recent_failures)}")
    else:
        log_test("Analytics alerts - GET request", False,
                 f"Status: {resp.status_code}, Body: {resp.text[:200]}")
        
except Exception as e:
    log_test("Analytics alerts - exception", False, str(e))

print()

# ============================================================================
# SECTION 3: COUPON & WISHLIST USAGE ANALYTICS
# ============================================================================
print("SECTION 3: Coupon & Wishlist Usage Analytics")
print("-" * 80)

try:
    headers = {"Authorization": f"Bearer {owner_token}"}
    
    # Test 3.1: GET /api/admin/analytics/coupon-usage
    resp = requests.get(f"{BASE_URL}/admin/analytics/coupon-usage", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        
        has_keys = "codes" in data and "customers" in data
        codes_is_array = isinstance(data.get("codes", None), list)
        customers_is_array = isinstance(data.get("customers", None), list)
        
        log_test("Analytics coupon-usage - has codes[] and customers[]",
                 has_keys and codes_is_array and customers_is_array,
                 f"Keys: {list(data.keys())}, codes type: {type(data.get('codes'))}, "
                 f"customers type: {type(data.get('customers'))}")
    else:
        log_test("Analytics coupon-usage - GET request", False,
                 f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    
    # Test 3.2: GET /api/admin/analytics/wishlist-usage
    resp = requests.get(f"{BASE_URL}/admin/analytics/wishlist-usage", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        
        required_keys = ["total_wishlists", "by_customer", "by_product"]
        has_keys = all(k in data for k in required_keys)
        by_customer_is_array = isinstance(data.get("by_customer", None), list)
        by_product_is_array = isinstance(data.get("by_product", None), list)
        total_is_int = isinstance(data.get("total_wishlists", None), int)
        
        log_test("Analytics wishlist-usage - has total_wishlists, by_customer[], by_product[]",
                 has_keys and by_customer_is_array and by_product_is_array and total_is_int,
                 f"Keys: {list(data.keys())}, total: {data.get('total_wishlists')}")
    else:
        log_test("Analytics wishlist-usage - GET request", False,
                 f"Status: {resp.status_code}, Body: {resp.text[:200]}")
        
except Exception as e:
    log_test("Analytics coupon/wishlist - exception", False, str(e))

print()

# ============================================================================
# SECTION 4: LIVE ANALYTICS FLOW
# ============================================================================
print("SECTION 4: Live Analytics Flow")
print("-" * 80)

try:
    # Test 4.1: POST /api/analytics/heartbeat (no auth) - session 1
    resp = requests.post(f"{BASE_URL}/analytics/heartbeat", json={
        "session_id": "test_session_1",
        "path": "/"
    })
    log_test("Live analytics - heartbeat session 1", 
             resp.status_code == 200 and resp.json().get("ok") == True,
             f"Status: {resp.status_code}, Response: {resp.json() if resp.status_code == 200 else resp.text[:100]}")
    
    # Test 4.2: POST /api/analytics/heartbeat (no auth) - session 2
    resp = requests.post(f"{BASE_URL}/analytics/heartbeat", json={
        "session_id": "test_session_2",
        "path": "/shop"
    })
    log_test("Live analytics - heartbeat session 2",
             resp.status_code == 200 and resp.json().get("ok") == True,
             f"Status: {resp.status_code}, Response: {resp.json() if resp.status_code == 200 else resp.text[:100]}")
    
    # Wait a moment for data to be available
    time.sleep(1)
    
    # Test 4.3: GET /api/admin/analytics/live (auth required)
    headers = {"Authorization": f"Bearer {owner_token}"}
    resp = requests.get(f"{BASE_URL}/admin/analytics/live", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        
        active_users = data.get("active_users", 0)
        sessions_now = data.get("sessions_now_by_path", [])
        
        # Should have at least 2 active users from our heartbeats
        has_active_users = active_users >= 2
        has_sessions_array = isinstance(sessions_now, list)
        
        log_test("Live analytics - active_users >= 2",
                 has_active_users,
                 f"active_users: {active_users}, sessions_now_by_path: {sessions_now}")
        
        log_test("Live analytics - sessions_now_by_path is array",
                 has_sessions_array,
                 f"Type: {type(sessions_now)}, Length: {len(sessions_now)}")
    else:
        log_test("Live analytics - GET /admin/analytics/live", False,
                 f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    
    # Test 4.4: POST /api/analytics/pageview (no auth)
    resp = requests.post(f"{BASE_URL}/analytics/pageview", json={
        "path": "/shop",
        "session_id": "test_session_2"
    })
    log_test("Live analytics - pageview /shop",
             resp.status_code == 200 and resp.json().get("ok") == True,
             f"Status: {resp.status_code}, Response: {resp.json() if resp.status_code == 200 else resp.text[:100]}")
    
    # Test 4.5: GET /api/admin/analytics/live again to check top_pages_24h
    time.sleep(1)
    resp = requests.get(f"{BASE_URL}/admin/analytics/live", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        top_pages = data.get("top_pages_24h", [])
        
        # Check if /shop appears in top_pages_24h
        shop_in_top = any(p.get("path") == "/shop" for p in top_pages)
        
        log_test("Live analytics - top_pages_24h contains /shop",
                 shop_in_top,
                 f"top_pages_24h: {top_pages}")
    else:
        log_test("Live analytics - GET /admin/analytics/live (2nd call)", False,
                 f"Status: {resp.status_code}")
        
except Exception as e:
    log_test("Live analytics - exception", False, str(e))

print()

# ============================================================================
# SECTION 5: RBAC END-TO-END
# ============================================================================
print("SECTION 5: RBAC End-to-End Testing")
print("-" * 80)

try:
    # Test 5.1: Login as owner
    resp = requests.post(f"{BASE_URL}/admin/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if resp.status_code == 200:
        owner_token = resp.json().get("token")
        log_test("RBAC - owner login", True, "Token received")
    else:
        log_test("RBAC - owner login", False, f"Status: {resp.status_code}")
        raise Exception("Owner login failed")
    
    # Test 5.2: GET /api/admin/me with owner token
    headers = {"Authorization": f"Bearer {owner_token}"}
    resp = requests.get(f"{BASE_URL}/admin/me", headers=headers)
    if resp.status_code == 200:
        me_data = resp.json()
        role = me_data.get("role")
        permissions = me_data.get("permissions", [])
        
        is_owner = role == "owner"
        has_all_perms = len(permissions) == 11
        
        log_test("RBAC - owner has role='owner'", is_owner, f"Role: {role}")
        log_test("RBAC - owner has all 11 permissions", has_all_perms,
                 f"Permissions count: {len(permissions)}, Permissions: {permissions}")
    else:
        log_test("RBAC - GET /admin/me", False, f"Status: {resp.status_code}")
    
    # Test 5.3: GET /api/admin/permissions
    resp = requests.get(f"{BASE_URL}/admin/permissions", headers=headers)
    if resp.status_code == 200:
        perms_data = resp.json()
        all_perms = perms_data.get("all", [])
        
        is_array = isinstance(all_perms, list)
        has_11 = len(all_perms) == 11
        
        log_test("RBAC - GET /admin/permissions returns 11 keys", is_array and has_11,
                 f"Count: {len(all_perms)}, Permissions: {all_perms}")
    else:
        log_test("RBAC - GET /admin/permissions", False, f"Status: {resp.status_code}")
    
    # Test 5.4: GET /api/admin/employees (should be empty or have existing employees)
    resp = requests.get(f"{BASE_URL}/admin/employees", headers=headers)
    if resp.status_code == 200:
        employees = resp.json()
        log_test("RBAC - GET /admin/employees", True, f"Employees: {len(employees)}")
    else:
        log_test("RBAC - GET /admin/employees", False, f"Status: {resp.status_code}")
    
    # Test 5.5: POST /api/admin/employees - create employee
    emp_email = "emp1@artyfex.in"
    emp_password = "Password123!"
    resp = requests.post(f"{BASE_URL}/admin/employees", headers=headers, json={
        "email": emp_email,
        "password": emp_password,
        "display_name": "Emp 1",
        "permissions": ["view_analytics", "manage_orders"]
    })
    
    if resp.status_code in [200, 201]:
        emp_data = resp.json()
        emp_id = emp_data.get("id")
        emp_role = emp_data.get("role")
        emp_perms = emp_data.get("permissions", [])
        has_password_hash = "password_hash" in emp_data
        
        log_test("RBAC - create employee", True, f"Employee ID: {emp_id}")
        log_test("RBAC - employee has role='employee'", emp_role == "employee", f"Role: {emp_role}")
        log_test("RBAC - employee has correct permissions", 
                 set(emp_perms) == {"view_analytics", "manage_orders"},
                 f"Permissions: {emp_perms}")
        log_test("RBAC - employee response does NOT expose password_hash", not has_password_hash,
                 f"Has password_hash: {has_password_hash}")
    else:
        log_test("RBAC - create employee", False, 
                 f"Status: {resp.status_code}, Body: {resp.text[:200]}")
        raise Exception("Failed to create employee")
    
    # Test 5.6: Login as employee
    resp = requests.post(f"{BASE_URL}/admin/login", json={
        "email": emp_email,
        "password": emp_password
    })
    if resp.status_code == 200:
        emp_token = resp.json().get("token")
        log_test("RBAC - employee login", True, "Token received")
    else:
        log_test("RBAC - employee login", False, f"Status: {resp.status_code}")
        raise Exception("Employee login failed")
    
    # Test 5.7: GET /api/admin/me with employee token
    emp_headers = {"Authorization": f"Bearer {emp_token}"}
    resp = requests.get(f"{BASE_URL}/admin/me", headers=emp_headers)
    if resp.status_code == 200:
        emp_me = resp.json()
        emp_role = emp_me.get("role")
        emp_perms = emp_me.get("permissions", [])
        
        log_test("RBAC - employee GET /admin/me shows role='employee'",
                 emp_role == "employee", f"Role: {emp_role}")
        log_test("RBAC - employee GET /admin/me shows correct permissions",
                 set(emp_perms) == {"view_analytics", "manage_orders"},
                 f"Permissions: {emp_perms}")
    else:
        log_test("RBAC - employee GET /admin/me", False, f"Status: {resp.status_code}")
    
    # Test 5.8: Employee can access /admin/analytics/overview (has view_analytics)
    resp = requests.get(f"{BASE_URL}/admin/analytics/overview", headers=emp_headers)
    log_test("RBAC - employee can GET /admin/analytics/overview (has view_analytics)",
             resp.status_code == 200,
             f"Status: {resp.status_code}")
    
    # Test 5.9: Employee CANNOT access /admin/employees (missing manage_employees)
    resp = requests.get(f"{BASE_URL}/admin/employees", headers=emp_headers)
    log_test("RBAC - employee CANNOT GET /admin/employees (missing manage_employees)",
             resp.status_code == 403,
             f"Status: {resp.status_code}, Expected: 403")
    
    # Test 5.10: Employee CANNOT PATCH /admin/shipping-settings (missing manage_shipping)
    resp = requests.patch(f"{BASE_URL}/admin/shipping-settings", headers=emp_headers, json={
        "method": "flat",
        "flat_rate_inr": 999,
        "free_shipping_above_inr": 25000,
        "origin_city": "Mumbai",
        "origin_state": "Maharashtra",
        "origin_pincode": "400095",
        "zone_rates": [],
        "distance_base_fee_inr": 299,
        "distance_per_km_inr": 3,
        "distance_bands": []
    })
    log_test("RBAC - employee CANNOT PATCH /admin/shipping-settings (missing manage_shipping)",
             resp.status_code == 403,
             f"Status: {resp.status_code}, Expected: 403")
    
    # Test 5.11: Employee can change their own password
    new_emp_password = "NewPass9876!"
    resp = requests.patch(f"{BASE_URL}/admin/me/password", headers=emp_headers, json={
        "current_password": emp_password,
        "new_password": new_emp_password
    })
    log_test("RBAC - employee can change own password",
             resp.status_code == 200,
             f"Status: {resp.status_code}")
    
    # Test 5.12: Login with old password should fail
    resp = requests.post(f"{BASE_URL}/admin/login", json={
        "email": emp_email,
        "password": emp_password
    })
    log_test("RBAC - employee login with old password fails",
             resp.status_code == 401,
             f"Status: {resp.status_code}, Expected: 401")
    
    # Test 5.13: Login with new password should succeed
    resp = requests.post(f"{BASE_URL}/admin/login", json={
        "email": emp_email,
        "password": new_emp_password
    })
    if resp.status_code == 200:
        emp_token = resp.json().get("token")
        log_test("RBAC - employee login with new password succeeds", True, "Token received")
    else:
        log_test("RBAC - employee login with new password", False, f"Status: {resp.status_code}")
    
    # Test 5.14: Owner updates employee permissions (remove manage_orders)
    resp = requests.patch(f"{BASE_URL}/admin/employees/{emp_id}", headers=headers, json={
        "permissions": ["view_analytics"]
    })
    if resp.status_code == 200:
        updated_emp = resp.json()
        updated_perms = updated_emp.get("permissions", [])
        
        log_test("RBAC - owner can update employee permissions",
                 updated_perms == ["view_analytics"],
                 f"Updated permissions: {updated_perms}")
    else:
        log_test("RBAC - owner update employee permissions", False,
                 f"Status: {resp.status_code}")
    
    # Test 5.15: Owner deletes employee
    resp = requests.delete(f"{BASE_URL}/admin/employees/{emp_id}", headers=headers)
    log_test("RBAC - owner can delete employee",
             resp.status_code == 200,
             f"Status: {resp.status_code}")
    
    # Test 5.16: Verify employee is deleted
    resp = requests.get(f"{BASE_URL}/admin/employees", headers=headers)
    if resp.status_code == 200:
        employees = resp.json()
        emp_exists = any(e.get("id") == emp_id for e in employees)
        
        log_test("RBAC - deleted employee not in list",
                 not emp_exists,
                 f"Employee {emp_id} exists: {emp_exists}")
    else:
        log_test("RBAC - verify employee deleted", False, f"Status: {resp.status_code}")
    
    # Test 5.17: Owner password change with wrong current password
    resp = requests.patch(f"{BASE_URL}/admin/me/password", headers=headers, json={
        "current_password": "wrong_password",
        "new_password": "whatever12"
    })
    log_test("RBAC - owner password change with wrong current password fails",
             resp.status_code == 400,
             f"Status: {resp.status_code}, Expected: 400")
    
    # Test 5.18: Verify owner can still login with original password
    resp = requests.post(f"{BASE_URL}/admin/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    log_test("RBAC - owner can still login with original password",
             resp.status_code == 200,
             f"Status: {resp.status_code}")
    
except Exception as e:
    log_test("RBAC - exception", False, str(e))

print()

# ============================================================================
# SUMMARY
# ============================================================================
print("=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print(f"Total Tests: {results['total']}")
print(f"Passed: {results['passed']}")
print(f"Failed: {results['failed']}")
print(f"Success Rate: {(results['passed']/results['total']*100):.1f}%")
print()

# Save results to JSON
with open("/app/backend_test_phase_b_results.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"Detailed results saved to: /app/backend_test_phase_b_results.json")
print()

# Exit with appropriate code
exit(0 if results['failed'] == 0 else 1)
