#!/usr/bin/env python3
"""
ArtyFex Phase B Backend Testing Suite
Tests coupon validation, admin coupon CRUD, order creation with coupons, and failed payment logging.
"""

import requests
import json
import sys
from typing import Dict, Any, Optional

# Backend URL from frontend/.env
BASE_URL = "https://repo-digest-8.preview.emergentagent.com/api"

# Admin credentials
ADMIN_EMAIL = "admin@artyfex.in"
ADMIN_PASSWORD = "ArtyFex@2026"

# Test results tracking
test_results = []
admin_token = None


def log_test(name: str, passed: bool, details: str = ""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    test_results.append({"name": name, "passed": passed, "details": details})
    print(f"{status} | {name}")
    if details and not passed:
        print(f"   Details: {details}")


def admin_login() -> Optional[str]:
    """Login as admin and return JWT token"""
    try:
        resp = requests.post(
            f"{BASE_URL}/admin/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10
        )
        if resp.status_code == 200:
            token = resp.json().get("token")
            log_test("Admin login", True, f"Token obtained")
            return token
        else:
            log_test("Admin login", False, f"Status {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        log_test("Admin login", False, f"Exception: {str(e)}")
        return None


def test_coupon_validation():
    """Test POST /api/coupons/validate - public endpoint"""
    print("\n=== Testing Coupon Validation (Public) ===")
    
    # Test 1: Happy path - WELCOME10 on ₹20,000 cart
    try:
        resp = requests.post(
            f"{BASE_URL}/coupons/validate",
            json={"code": "WELCOME10", "cart_total_inr": 20000},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            expected_discount = 2000  # 10% of 20000
            if (data.get("valid") == True and 
                data.get("discount_inr") == expected_discount and
                data.get("type") == "percentage" and
                data.get("value") == 10 and
                data.get("code") == "WELCOME10"):
                log_test("Coupon validate: WELCOME10 on ₹20k", True)
            else:
                log_test("Coupon validate: WELCOME10 on ₹20k", False, 
                        f"Response mismatch: {json.dumps(data)}")
        else:
            log_test("Coupon validate: WELCOME10 on ₹20k", False, 
                    f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_test("Coupon validate: WELCOME10 on ₹20k", False, f"Exception: {str(e)}")
    
    # Test 2: Happy path - ATELIER500 on ₹15,000 cart
    try:
        resp = requests.post(
            f"{BASE_URL}/coupons/validate",
            json={"code": "ATELIER500", "cart_total_inr": 15000},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("discount_inr") == 500:
                log_test("Coupon validate: ATELIER500 on ₹15k", True)
            else:
                log_test("Coupon validate: ATELIER500 on ₹15k", False, 
                        f"Expected discount 500, got {data.get('discount_inr')}")
        else:
            log_test("Coupon validate: ATELIER500 on ₹15k", False, 
                    f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_test("Coupon validate: ATELIER500 on ₹15k", False, f"Exception: {str(e)}")
    
    # Test 3: Min-cart failure - SIGNATURE15 on ₹10,000 (requires ₹25k)
    try:
        resp = requests.post(
            f"{BASE_URL}/coupons/validate",
            json={"code": "SIGNATURE15", "cart_total_inr": 10000},
            timeout=10
        )
        if resp.status_code == 400:
            detail = resp.json().get("detail", "")
            if "Minimum cart" in detail or "minimum" in detail.lower():
                log_test("Coupon validate: SIGNATURE15 min-cart failure", True)
            else:
                log_test("Coupon validate: SIGNATURE15 min-cart failure", False, 
                        f"Expected 'Minimum cart' in detail, got: {detail}")
        else:
            log_test("Coupon validate: SIGNATURE15 min-cart failure", False, 
                    f"Expected 400, got {resp.status_code}")
    except Exception as e:
        log_test("Coupon validate: SIGNATURE15 min-cart failure", False, f"Exception: {str(e)}")
    
    # Test 4: Not found - invalid code
    try:
        resp = requests.post(
            f"{BASE_URL}/coupons/validate",
            json={"code": "NOPE", "cart_total_inr": 20000},
            timeout=10
        )
        if resp.status_code == 404:
            log_test("Coupon validate: invalid code NOPE", True)
        else:
            log_test("Coupon validate: invalid code NOPE", False, 
                    f"Expected 404, got {resp.status_code}")
    except Exception as e:
        log_test("Coupon validate: invalid code NOPE", False, f"Exception: {str(e)}")
    
    # Test 5: Empty code
    try:
        resp = requests.post(
            f"{BASE_URL}/coupons/validate",
            json={"code": "", "cart_total_inr": 20000},
            timeout=10
        )
        if resp.status_code == 400:
            log_test("Coupon validate: empty code", True)
        else:
            log_test("Coupon validate: empty code", False, 
                    f"Expected 400, got {resp.status_code}")
    except Exception as e:
        log_test("Coupon validate: empty code", False, f"Exception: {str(e)}")
    
    # Test 6: Case insensitivity - lowercase "welcome10"
    try:
        resp = requests.post(
            f"{BASE_URL}/coupons/validate",
            json={"code": "welcome10", "cart_total_inr": 20000},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == "WELCOME10":  # Server should uppercase
                log_test("Coupon validate: case insensitivity", True)
            else:
                log_test("Coupon validate: case insensitivity", False, 
                        f"Expected code 'WELCOME10', got {data.get('code')}")
        else:
            log_test("Coupon validate: case insensitivity", False, 
                    f"Expected 200, got {resp.status_code}")
    except Exception as e:
        log_test("Coupon validate: case insensitivity", False, f"Exception: {str(e)}")


def test_admin_coupon_crud():
    """Test admin coupon CRUD endpoints"""
    print("\n=== Testing Admin Coupon CRUD ===")
    
    if not admin_token:
        log_test("Admin coupon CRUD", False, "No admin token available")
        return
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Test 1: GET /api/admin/coupons - list coupons
    try:
        resp = requests.get(f"{BASE_URL}/admin/coupons", headers=headers, timeout=10)
        if resp.status_code == 200:
            coupons = resp.json()
            if isinstance(coupons, list) and len(coupons) >= 3:
                codes = [c.get("code") for c in coupons]
                if all(code in codes for code in ["WELCOME10", "ATELIER500", "SIGNATURE15"]):
                    log_test("Admin GET coupons: list with seeded coupons", True)
                else:
                    log_test("Admin GET coupons: list with seeded coupons", False, 
                            f"Missing seeded coupons. Found: {codes}")
            else:
                log_test("Admin GET coupons: list with seeded coupons", False, 
                        f"Expected list with >=3 coupons, got {len(coupons) if isinstance(coupons, list) else 'not a list'}")
        else:
            log_test("Admin GET coupons: list with seeded coupons", False, 
                    f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_test("Admin GET coupons: list with seeded coupons", False, f"Exception: {str(e)}")
    
    # Test 2: POST /api/admin/coupons - create new coupon
    test_coupon_id = None
    try:
        resp = requests.post(
            f"{BASE_URL}/admin/coupons",
            headers=headers,
            json={
                "code": "TESTX",
                "type": "percentage",
                "value": 20,
                "min_cart_inr": 0,
                "max_uses": 5,
                "active": True,
                "description": "Test coupon"
            },
            timeout=10
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            test_coupon_id = data.get("id")
            if data.get("code") == "TESTX":
                log_test("Admin POST coupon: create TESTX", True)
            else:
                log_test("Admin POST coupon: create TESTX", False, 
                        f"Expected code TESTX, got {data.get('code')}")
        else:
            log_test("Admin POST coupon: create TESTX", False, 
                    f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_test("Admin POST coupon: create TESTX", False, f"Exception: {str(e)}")
    
    # Test 3: POST duplicate - should return 409
    try:
        resp = requests.post(
            f"{BASE_URL}/admin/coupons",
            headers=headers,
            json={
                "code": "TESTX",
                "type": "percentage",
                "value": 20,
                "min_cart_inr": 0,
                "max_uses": 5,
                "active": True,
                "description": "Duplicate"
            },
            timeout=10
        )
        if resp.status_code == 409:
            log_test("Admin POST coupon: duplicate code 409", True)
        else:
            log_test("Admin POST coupon: duplicate code 409", False, 
                    f"Expected 409, got {resp.status_code}")
    except Exception as e:
        log_test("Admin POST coupon: duplicate code 409", False, f"Exception: {str(e)}")
    
    # Test 4: POST invalid - percentage > 100
    try:
        resp = requests.post(
            f"{BASE_URL}/admin/coupons",
            headers=headers,
            json={
                "code": "BAD1",
                "type": "percentage",
                "value": 150,
                "min_cart_inr": 0,
                "active": True
            },
            timeout=10
        )
        if resp.status_code == 400:
            log_test("Admin POST coupon: percentage > 100 validation", True)
        else:
            log_test("Admin POST coupon: percentage > 100 validation", False, 
                    f"Expected 400, got {resp.status_code}")
    except Exception as e:
        log_test("Admin POST coupon: percentage > 100 validation", False, f"Exception: {str(e)}")
    
    # Test 5: POST invalid - value <= 0
    try:
        resp = requests.post(
            f"{BASE_URL}/admin/coupons",
            headers=headers,
            json={
                "code": "BAD2",
                "type": "flat",
                "value": -100,
                "min_cart_inr": 0,
                "active": True
            },
            timeout=10
        )
        if resp.status_code == 400:
            log_test("Admin POST coupon: value <= 0 validation", True)
        else:
            log_test("Admin POST coupon: value <= 0 validation", False, 
                    f"Expected 400, got {resp.status_code}")
    except Exception as e:
        log_test("Admin POST coupon: value <= 0 validation", False, f"Exception: {str(e)}")
    
    # Test 6: POST invalid type
    try:
        resp = requests.post(
            f"{BASE_URL}/admin/coupons",
            headers=headers,
            json={
                "code": "BAD3",
                "type": "weird",
                "value": 10,
                "min_cart_inr": 0,
                "active": True
            },
            timeout=10
        )
        if resp.status_code == 400:
            log_test("Admin POST coupon: invalid type validation", True)
        else:
            log_test("Admin POST coupon: invalid type validation", False, 
                    f"Expected 400, got {resp.status_code}")
    except Exception as e:
        log_test("Admin POST coupon: invalid type validation", False, f"Exception: {str(e)}")
    
    # Test 7: PATCH /api/admin/coupons/{id} - update description
    if test_coupon_id:
        try:
            resp = requests.patch(
                f"{BASE_URL}/admin/coupons/{test_coupon_id}",
                headers=headers,
                json={
                    "code": "TESTX",
                    "type": "percentage",
                    "value": 20,
                    "min_cart_inr": 0,
                    "max_uses": 5,
                    "active": True,
                    "description": "Updated description"
                },
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("description") == "Updated description":
                    log_test("Admin PATCH coupon: update description", True)
                else:
                    log_test("Admin PATCH coupon: update description", False, 
                            f"Description not updated: {data.get('description')}")
            else:
                log_test("Admin PATCH coupon: update description", False, 
                        f"Status {resp.status_code}: {resp.text}")
        except Exception as e:
            log_test("Admin PATCH coupon: update description", False, f"Exception: {str(e)}")
    
    # Test 8: DELETE /api/admin/coupons/{id}
    if test_coupon_id:
        try:
            resp = requests.delete(
                f"{BASE_URL}/admin/coupons/{test_coupon_id}",
                headers=headers,
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("deleted") == True:
                    # Verify it's gone
                    resp2 = requests.get(f"{BASE_URL}/admin/coupons", headers=headers, timeout=10)
                    if resp2.status_code == 200:
                        coupons = resp2.json()
                        codes = [c.get("code") for c in coupons]
                        if "TESTX" not in codes:
                            log_test("Admin DELETE coupon: verify deleted", True)
                        else:
                            log_test("Admin DELETE coupon: verify deleted", False, 
                                    "TESTX still in list after delete")
                    else:
                        log_test("Admin DELETE coupon: verify deleted", False, 
                                "Could not verify deletion")
                else:
                    log_test("Admin DELETE coupon: verify deleted", False, 
                            f"Expected deleted:true, got {data}")
            else:
                log_test("Admin DELETE coupon: verify deleted", False, 
                        f"Status {resp.status_code}: {resp.text}")
        except Exception as e:
            log_test("Admin DELETE coupon: verify deleted", False, f"Exception: {str(e)}")
    
    # Test 9: Unauthorized access - no token
    try:
        resp = requests.get(f"{BASE_URL}/admin/coupons", timeout=10)
        if resp.status_code == 401:
            log_test("Admin coupon endpoint: 401 without token", True)
        else:
            log_test("Admin coupon endpoint: 401 without token", False, 
                    f"Expected 401, got {resp.status_code}")
    except Exception as e:
        log_test("Admin coupon endpoint: 401 without token", False, f"Exception: {str(e)}")


def test_order_with_coupon():
    """Test order creation with coupon code"""
    print("\n=== Testing Order Creation with Coupon ===")
    
    # First, get a product to order
    try:
        resp = requests.get(f"{BASE_URL}/products", timeout=10)
        if resp.status_code != 200:
            log_test("Order with coupon: get products", False, 
                    f"Could not fetch products: {resp.status_code}")
            return
        
        products = resp.json()
        if not products:
            log_test("Order with coupon: get products", False, "No products available")
            return
        
        product = products[0]
        product_id = product.get("id")
        variant_key = product.get("variants", [{}])[0].get("key", "default")
        
        # Test 1: Create order with valid coupon WELCOME10
        order_payload = {
            "customer": {
                "name": "Priya Sharma",
                "email": "priya.test@example.com",
                "phone": "9876543210",
                "address": "123 Marine Drive",
                "city": "Mumbai",
                "pincode": "400020"
            },
            "items": [
                {
                    "product_id": product_id,
                    "variant_key": variant_key,
                    "quantity": 1
                }
            ],
            "payment_method": "razorpay",
            "subtotal_inr": 20000,
            "shipping_inr": 0,
            "total_inr": 18000,
            "coupon_code": "WELCOME10",
            "discount_inr": 2000
        }
        
        resp = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            order = data.get("order", {})
            if (order.get("coupon_code") == "WELCOME10" and 
                order.get("discount_inr") == 2000):
                log_test("Order creation: with valid coupon WELCOME10", True)
            else:
                log_test("Order creation: with valid coupon WELCOME10", False, 
                        f"Coupon data mismatch: {order.get('coupon_code')}, {order.get('discount_inr')}")
        else:
            log_test("Order creation: with valid coupon WELCOME10", False, 
                    f"Status {resp.status_code}: {resp.text}")
        
        # Test 2: Create order with invalid coupon
        invalid_payload = order_payload.copy()
        invalid_payload["coupon_code"] = "EXPIRED"
        invalid_payload["customer"]["email"] = "test2@example.com"
        
        resp = requests.post(f"{BASE_URL}/orders", json=invalid_payload, timeout=10)
        if resp.status_code == 400:
            log_test("Order creation: with invalid coupon", True)
        else:
            log_test("Order creation: with invalid coupon", False, 
                    f"Expected 400, got {resp.status_code}")
        
        # Test 3: Create order with coupon not meeting min_cart
        low_cart_payload = order_payload.copy()
        low_cart_payload["coupon_code"] = "SIGNATURE15"
        low_cart_payload["subtotal_inr"] = 5000
        low_cart_payload["total_inr"] = 5000
        low_cart_payload["discount_inr"] = 0
        low_cart_payload["customer"]["email"] = "test3@example.com"
        
        resp = requests.post(f"{BASE_URL}/orders", json=low_cart_payload, timeout=10)
        if resp.status_code == 400:
            detail = resp.json().get("detail", "")
            if "Minimum" in detail or "minimum" in detail.lower():
                log_test("Order creation: coupon min_cart validation", True)
            else:
                log_test("Order creation: coupon min_cart validation", False, 
                        f"Expected min_cart error, got: {detail}")
        else:
            log_test("Order creation: coupon min_cart validation", False, 
                    f"Expected 400, got {resp.status_code}")
        
    except Exception as e:
        log_test("Order with coupon tests", False, f"Exception: {str(e)}")


def test_failed_payment_logging():
    """Test failed payment logging endpoints"""
    print("\n=== Testing Failed Payment Logging ===")
    
    # Test 1: POST /api/payments/failed - basic logging
    failed_payment_id = None
    try:
        payload = {
            "error_code": "BAD_CARD",
            "error_description": "Card declined",
            "amount_inr": 19999,
            "customer_email": "failed@example.com",
            "customer_name": "Test User"
        }
        
        resp = requests.post(f"{BASE_URL}/payments/failed", json=payload, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("id") and data.get("created_at"):
                failed_payment_id = data.get("id")
                log_test("Failed payment: POST basic logging", True)
            else:
                log_test("Failed payment: POST basic logging", False, 
                        f"Missing id or created_at: {data}")
        else:
            log_test("Failed payment: POST basic logging", False, 
                    f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_test("Failed payment: POST basic logging", False, f"Exception: {str(e)}")
    
    # Test 2: POST with order_number - should mark order as payment_failed
    try:
        # First create an order
        resp = requests.get(f"{BASE_URL}/products", timeout=10)
        if resp.status_code == 200:
            products = resp.json()
            if products:
                product = products[0]
                product_id = product.get("id")
                variant_key = product.get("variants", [{}])[0].get("key", "default")
                
                order_payload = {
                    "customer": {
                        "name": "Failed Payment Test",
                        "email": "failtest@example.com",
                        "phone": "9999999999",
                        "address": "1 Test Lane",
                        "city": "Mumbai",
                        "pincode": "400001"
                    },
                    "items": [{"product_id": product_id, "variant_key": variant_key, "quantity": 1}],
                    "payment_method": "razorpay",
                    "subtotal_inr": 20000,
                    "shipping_inr": 0,
                    "total_inr": 20000
                }
                
                resp = requests.post(f"{BASE_URL}/orders", json=order_payload, timeout=10)
                if resp.status_code == 200:
                    order_number = resp.json().get("order", {}).get("order_number")
                    
                    # Now log a failed payment with this order_number
                    fail_payload = {
                        "order_number": order_number,
                        "error_code": "PAYMENT_TIMEOUT",
                        "error_description": "Payment timed out",
                        "amount_inr": 20000,
                        "customer_email": "failtest@example.com",
                        "customer_name": "Failed Payment Test"
                    }
                    
                    resp = requests.post(f"{BASE_URL}/payments/failed", json=fail_payload, timeout=10)
                    if resp.status_code == 200:
                        # Verify order status changed to payment_failed
                        resp = requests.get(f"{BASE_URL}/orders/{order_number}", timeout=10)
                        if resp.status_code == 200:
                            order = resp.json()
                            if order.get("status") == "payment_failed":
                                log_test("Failed payment: order status update", True)
                            else:
                                log_test("Failed payment: order status update", False, 
                                        f"Expected status 'payment_failed', got {order.get('status')}")
                        else:
                            log_test("Failed payment: order status update", False, 
                                    f"Could not fetch order: {resp.status_code}")
                    else:
                        log_test("Failed payment: order status update", False, 
                                f"Failed payment POST failed: {resp.status_code}")
                else:
                    log_test("Failed payment: order status update", False, 
                            f"Could not create test order: {resp.status_code}")
    except Exception as e:
        log_test("Failed payment: order status update", False, f"Exception: {str(e)}")
    
    # Test 3: GET /api/admin/failed-payments with admin token
    if admin_token:
        try:
            headers = {"Authorization": f"Bearer {admin_token}"}
            resp = requests.get(f"{BASE_URL}/admin/failed-payments", headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    # Check if our logged payment is in the list
                    if failed_payment_id:
                        ids = [fp.get("id") for fp in data]
                        if failed_payment_id in ids:
                            log_test("Admin GET failed-payments: list contains logged entry", True)
                        else:
                            log_test("Admin GET failed-payments: list contains logged entry", False, 
                                    f"Failed payment {failed_payment_id} not in list")
                    else:
                        log_test("Admin GET failed-payments: returns list", True)
                else:
                    log_test("Admin GET failed-payments: returns list", False, 
                            f"Expected list, got {type(data)}")
            else:
                log_test("Admin GET failed-payments: returns list", False, 
                        f"Status {resp.status_code}: {resp.text}")
        except Exception as e:
            log_test("Admin GET failed-payments: returns list", False, f"Exception: {str(e)}")
    
    # Test 4: GET /api/admin/failed-payments without token - should be 401
    try:
        resp = requests.get(f"{BASE_URL}/admin/failed-payments", timeout=10)
        if resp.status_code == 401:
            log_test("Admin failed-payments: 401 without token", True)
        else:
            log_test("Admin failed-payments: 401 without token", False, 
                    f"Expected 401, got {resp.status_code}")
    except Exception as e:
        log_test("Admin failed-payments: 401 without token", False, f"Exception: {str(e)}")


def test_regression():
    """Test that existing endpoints still work"""
    print("\n=== Testing Regression (Existing Endpoints) ===")
    
    # Test 1: GET /api/products should return 4 products
    try:
        resp = requests.get(f"{BASE_URL}/products", timeout=10)
        if resp.status_code == 200:
            products = resp.json()
            if len(products) == 4:
                log_test("Regression: GET /api/products returns 4 products", True)
            else:
                log_test("Regression: GET /api/products returns 4 products", False, 
                        f"Expected 4 products, got {len(products)}")
        else:
            log_test("Regression: GET /api/products returns 4 products", False, 
                    f"Status {resp.status_code}")
    except Exception as e:
        log_test("Regression: GET /api/products returns 4 products", False, f"Exception: {str(e)}")
    
    # Test 2: GET /api/products/moon-crystal-24 - check variants
    try:
        resp = requests.get(f"{BASE_URL}/products/moon-crystal-24", timeout=10)
        if resp.status_code == 200:
            product = resp.json()
            variants = product.get("variants", [])
            if len(variants) == 4:
                # Check for distinct sizes
                sizes = [v.get("size") for v in variants if v.get("size")]
                size_24_count = sum(1 for s in sizes if "24" in str(s))
                size_30_count = sum(1 for s in sizes if "30" in str(s))
                
                # Check for distinct prices
                prices = [v.get("price_inr") for v in variants if v.get("price_inr")]
                has_18999 = 18999 in prices
                has_24999 = 24999 in prices
                
                if size_24_count == 2 and size_30_count == 2 and has_18999 and has_24999:
                    log_test("Regression: moon-crystal-24 variants structure", True)
                else:
                    log_test("Regression: moon-crystal-24 variants structure", False, 
                            f"Variant structure mismatch. Sizes: {sizes}, Prices: {prices}")
            else:
                log_test("Regression: moon-crystal-24 variants structure", False, 
                        f"Expected 4 variants, got {len(variants)}")
        else:
            log_test("Regression: moon-crystal-24 variants structure", False, 
                    f"Status {resp.status_code}")
    except Exception as e:
        log_test("Regression: moon-crystal-24 variants structure", False, f"Exception: {str(e)}")
    
    # Test 3: GET /api/reviews should return 6 reviews
    try:
        resp = requests.get(f"{BASE_URL}/reviews", timeout=10)
        if resp.status_code == 200:
            reviews = resp.json()
            if len(reviews) == 6:
                log_test("Regression: GET /api/reviews returns 6 reviews", True)
            else:
                log_test("Regression: GET /api/reviews returns 6 reviews", False, 
                        f"Expected 6 reviews, got {len(reviews)}")
        else:
            log_test("Regression: GET /api/reviews returns 6 reviews", False, 
                    f"Status {resp.status_code}")
    except Exception as e:
        log_test("Regression: GET /api/reviews returns 6 reviews", False, f"Exception: {str(e)}")
    
    # Test 4: POST /api/admin/login with correct creds
    try:
        resp = requests.post(
            f"{BASE_URL}/admin/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("token"):
                log_test("Regression: admin login returns token", True)
            else:
                log_test("Regression: admin login returns token", False, "No token in response")
        else:
            log_test("Regression: admin login returns token", False, 
                    f"Status {resp.status_code}")
    except Exception as e:
        log_test("Regression: admin login returns token", False, f"Exception: {str(e)}")
    
    # Test 5: GET /api/admin/stats with token
    if admin_token:
        try:
            headers = {"Authorization": f"Bearer {admin_token}"}
            resp = requests.get(f"{BASE_URL}/admin/stats", headers=headers, timeout=10)
            if resp.status_code == 200:
                stats = resp.json()
                required_keys = ["orders_total", "orders_confirmed", "revenue_inr", 
                               "leads_new", "products_total", "reviews_total"]
                if all(key in stats for key in required_keys):
                    log_test("Regression: GET /api/admin/stats returns dashboard stats", True)
                else:
                    log_test("Regression: GET /api/admin/stats returns dashboard stats", False, 
                            f"Missing keys. Got: {list(stats.keys())}")
            else:
                log_test("Regression: GET /api/admin/stats returns dashboard stats", False, 
                        f"Status {resp.status_code}")
        except Exception as e:
            log_test("Regression: GET /api/admin/stats returns dashboard stats", False, 
                    f"Exception: {str(e)}")


def print_summary():
    """Print test summary"""
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for t in test_results if t["passed"])
    failed = sum(1 for t in test_results if not t["passed"])
    total = len(test_results)
    
    print(f"\nTotal Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    if failed > 0:
        print("\n" + "="*70)
        print("FAILED TESTS DETAILS")
        print("="*70)
        for t in test_results:
            if not t["passed"]:
                print(f"\n❌ {t['name']}")
                if t["details"]:
                    print(f"   {t['details']}")
    
    print("\n" + "="*70)
    return 0 if failed == 0 else 1


def main():
    """Main test runner"""
    global admin_token
    
    print("="*70)
    print("ArtyFex Phase B Backend Testing Suite")
    print("="*70)
    print(f"Backend URL: {BASE_URL}")
    print(f"Admin: {ADMIN_EMAIL}")
    print("="*70)
    
    # Login as admin first
    admin_token = admin_login()
    
    # Run all test suites
    test_coupon_validation()
    test_admin_coupon_crud()
    test_order_with_coupon()
    test_failed_payment_logging()
    test_regression()
    
    # Print summary and exit
    exit_code = print_summary()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
