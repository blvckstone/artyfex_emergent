#!/usr/bin/env python3
"""
Phase A (Jul 2025) Backend Testing for ArtyFex
Tests: Product schema expansion, Categories CRUD, GST Rules CRUD, Tax Engine, Order GST computation
"""

import requests
import json
import sys
from typing import Dict, Any, List

# Backend URL from environment
BACKEND_URL = "https://backend-migration-24.preview.emergentagent.com/api"

# Admin credentials
ADMIN_EMAIL = "admin@artyfex.in"
ADMIN_PASSWORD = "ArtyFex@2026"

# Test results
results = []
admin_token = None


def log_test(name: str, passed: bool, details: str = ""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    results.append({"test": name, "passed": passed, "details": details})
    print(f"{status}: {name}")
    if details:
        print(f"  → {details}")


def admin_login() -> str:
    """Login as admin and return token"""
    global admin_token
    try:
        resp = requests.post(
            f"{BACKEND_URL}/admin/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10
        )
        if resp.status_code == 200:
            admin_token = resp.json()["token"]
            log_test("Admin login", True, f"Token received")
            return admin_token
        else:
            log_test("Admin login", False, f"Status {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        log_test("Admin login", False, f"Exception: {e}")
        return None


def test_product_schema_expansion():
    """Test 1: Product schema expansion - all products should have new fields"""
    print("\n=== SECTION 1: PRODUCT SCHEMA EXPANSION ===")
    
    try:
        resp = requests.get(f"{BACKEND_URL}/products", timeout=10)
        if resp.status_code != 200:
            log_test("GET /api/products", False, f"Status {resp.status_code}")
            return
        
        products = resp.json()
        if not products:
            log_test("GET /api/products", False, "No products returned")
            return
        
        log_test("GET /api/products", True, f"Returned {len(products)} products")
        
        # Check first product has all new fields
        p = products[0]
        required_fields = ["category", "hsn_code", "sku", "weight_grams", "length_cm", "width_cm", "height_cm", "tags"]
        missing = [f for f in required_fields if f not in p]
        
        if missing:
            log_test("Product has new schema fields", False, f"Missing fields: {missing}")
        else:
            log_test("Product has new schema fields", True, f"All fields present: {required_fields}")
        
        # Check seed products (mirrors) have category="mirrors" and hsn_code="7009"
        mirrors = [p for p in products if p.get("category") == "mirrors"]
        if not mirrors:
            log_test("Seed products have category='mirrors'", False, "No products with category='mirrors'")
        else:
            log_test("Seed products have category='mirrors'", True, f"{len(mirrors)} mirror products found")
        
        mirrors_with_hsn = [p for p in mirrors if p.get("hsn_code") == "7009"]
        if len(mirrors_with_hsn) == len(mirrors):
            log_test("Mirror products have hsn_code='7009'", True, f"All {len(mirrors)} mirrors have HSN 7009")
        else:
            log_test("Mirror products have hsn_code='7009'", False, 
                    f"Only {len(mirrors_with_hsn)}/{len(mirrors)} mirrors have HSN 7009")
        
    except Exception as e:
        log_test("Product schema expansion", False, f"Exception: {e}")


def test_product_categories():
    """Test 2: Product Categories CRUD"""
    print("\n=== SECTION 2: PRODUCT CATEGORIES CRUD ===")
    
    # Public endpoint
    try:
        resp = requests.get(f"{BACKEND_URL}/product-categories", timeout=10)
        if resp.status_code == 200:
            cats = resp.json()
            log_test("GET /api/product-categories (public)", True, f"Returned {len(cats)} categories")
            if len(cats) >= 8:
                log_test("8 seeded categories present", True, f"Found {len(cats)} categories")
            else:
                log_test("8 seeded categories present", False, f"Only {len(cats)} categories found")
        else:
            log_test("GET /api/product-categories (public)", False, f"Status {resp.status_code}")
    except Exception as e:
        log_test("GET /api/product-categories (public)", False, f"Exception: {e}")
    
    # Admin endpoint
    try:
        resp = requests.get(
            f"{BACKEND_URL}/admin/product-categories",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        if resp.status_code == 200:
            cats = resp.json()
            log_test("GET /api/admin/product-categories (admin)", True, f"Returned {len(cats)} categories")
        else:
            log_test("GET /api/admin/product-categories (admin)", False, f"Status {resp.status_code}")
    except Exception as e:
        log_test("GET /api/admin/product-categories (admin)", False, f"Exception: {e}")
    
    # Create new category
    test_cat_id = None
    try:
        resp = requests.post(
            f"{BACKEND_URL}/admin/product-categories",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Test Cat", "active": True},
            timeout=10
        )
        if resp.status_code == 200:
            cat = resp.json()
            test_cat_id = cat.get("id")
            if cat.get("slug") == "test-cat":
                log_test("POST /api/admin/product-categories (create)", True, 
                        f"Created category with auto-slug: {cat.get('slug')}")
            else:
                log_test("POST /api/admin/product-categories (create)", False, 
                        f"Slug mismatch: expected 'test-cat', got '{cat.get('slug')}'")
        else:
            log_test("POST /api/admin/product-categories (create)", False, 
                    f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_test("POST /api/admin/product-categories (create)", False, f"Exception: {e}")
    
    # Try to create duplicate
    try:
        resp = requests.post(
            f"{BACKEND_URL}/admin/product-categories",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Test Cat", "active": True},
            timeout=10
        )
        if resp.status_code == 400:
            log_test("POST duplicate category slug", True, "400 error as expected")
        else:
            log_test("POST duplicate category slug", False, 
                    f"Expected 400, got {resp.status_code}")
    except Exception as e:
        log_test("POST duplicate category slug", False, f"Exception: {e}")
    
    # Update category (note: backend requires 'name' field even for partial updates)
    if test_cat_id:
        try:
            resp = requests.patch(
                f"{BACKEND_URL}/admin/product-categories/{test_cat_id}",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"name": "Test Cat", "description": "Updated description"},
                timeout=10
            )
            if resp.status_code == 200:
                cat = resp.json()
                if cat.get("description") == "Updated description":
                    log_test("PATCH /api/admin/product-categories/{id}", True, "Description updated")
                else:
                    log_test("PATCH /api/admin/product-categories/{id}", False, "Description not updated")
            else:
                log_test("PATCH /api/admin/product-categories/{id}", False, 
                        f"Status {resp.status_code}")
        except Exception as e:
            log_test("PATCH /api/admin/product-categories/{id}", False, f"Exception: {e}")
    
    # Delete category
    if test_cat_id:
        try:
            resp = requests.delete(
                f"{BACKEND_URL}/admin/product-categories/{test_cat_id}",
                headers={"Authorization": f"Bearer {admin_token}"},
                timeout=10
            )
            if resp.status_code == 200 and resp.json().get("deleted") == True:
                log_test("DELETE /api/admin/product-categories/{id}", True, "Category deleted")
            else:
                log_test("DELETE /api/admin/product-categories/{id}", False, 
                        f"Status {resp.status_code}")
        except Exception as e:
            log_test("DELETE /api/admin/product-categories/{id}", False, f"Exception: {e}")


def test_gst_rules():
    """Test 3: GST Rules CRUD"""
    print("\n=== SECTION 3: GST RULES CRUD ===")
    
    # List GST rules
    try:
        resp = requests.get(
            f"{BACKEND_URL}/admin/gst-rules",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        if resp.status_code == 200:
            rules = resp.json()
            log_test("GET /api/admin/gst-rules", True, f"Returned {len(rules)} rules")
            if len(rules) >= 11:
                log_test("11 seeded GST rules present", True, f"Found {len(rules)} rules")
            else:
                log_test("11 seeded GST rules present", False, f"Only {len(rules)} rules found")
        else:
            log_test("GET /api/admin/gst-rules", False, f"Status {resp.status_code}")
    except Exception as e:
        log_test("GET /api/admin/gst-rules", False, f"Exception: {e}")
    
    # Create new GST rule
    test_rule_id = None
    try:
        resp = requests.post(
            f"{BACKEND_URL}/admin/gst-rules",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "hsn_code": "9999",
                "rate_percent": 5,
                "description": "Test HSN Rule",
                "active": True
            },
            timeout=10
        )
        if resp.status_code == 200:
            rule = resp.json()
            test_rule_id = rule.get("id")
            log_test("POST /api/admin/gst-rules (create)", True, 
                    f"Created rule with HSN 9999, rate 5%")
        else:
            log_test("POST /api/admin/gst-rules (create)", False, 
                    f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_test("POST /api/admin/gst-rules (create)", False, f"Exception: {e}")
    
    # Try to create duplicate
    try:
        resp = requests.post(
            f"{BACKEND_URL}/admin/gst-rules",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "hsn_code": "9999",
                "rate_percent": 10,
                "description": "Duplicate",
                "active": True
            },
            timeout=10
        )
        if resp.status_code == 400:
            log_test("POST duplicate GST rule", True, "400 error as expected")
        else:
            log_test("POST duplicate GST rule", False, 
                    f"Expected 400, got {resp.status_code}")
    except Exception as e:
        log_test("POST duplicate GST rule", False, f"Exception: {e}")
    
    # Try invalid rate (negative)
    try:
        resp = requests.post(
            f"{BACKEND_URL}/admin/gst-rules",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "hsn_code": "8888",
                "rate_percent": -5,
                "description": "Invalid rate",
                "active": True
            },
            timeout=10
        )
        if resp.status_code == 400:
            log_test("POST GST rule with invalid rate (negative)", True, "400 error as expected")
        else:
            log_test("POST GST rule with invalid rate (negative)", False, 
                    f"Expected 400, got {resp.status_code}")
    except Exception as e:
        log_test("POST GST rule with invalid rate (negative)", False, f"Exception: {e}")
    
    # Try invalid rate (>100)
    try:
        resp = requests.post(
            f"{BACKEND_URL}/admin/gst-rules",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "hsn_code": "7777",
                "rate_percent": 150,
                "description": "Invalid rate",
                "active": True
            },
            timeout=10
        )
        if resp.status_code == 400:
            log_test("POST GST rule with invalid rate (>100)", True, "400 error as expected")
        else:
            log_test("POST GST rule with invalid rate (>100)", False, 
                    f"Expected 400, got {resp.status_code}")
    except Exception as e:
        log_test("POST GST rule with invalid rate (>100)", False, f"Exception: {e}")
    
    # Try with neither hsn_code nor category
    try:
        resp = requests.post(
            f"{BACKEND_URL}/admin/gst-rules",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "rate_percent": 5,
                "description": "No target",
                "active": True
            },
            timeout=10
        )
        if resp.status_code == 400:
            log_test("POST GST rule without hsn_code or category", True, "400 error as expected")
        else:
            log_test("POST GST rule without hsn_code or category", False, 
                    f"Expected 400, got {resp.status_code}")
    except Exception as e:
        log_test("POST GST rule without hsn_code or category", False, f"Exception: {e}")
    
    # Update GST rule
    if test_rule_id:
        try:
            resp = requests.patch(
                f"{BACKEND_URL}/admin/gst-rules/{test_rule_id}",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"rate_percent": 8},
                timeout=10
            )
            if resp.status_code == 200:
                rule = resp.json()
                if rule.get("rate_percent") == 8:
                    log_test("PATCH /api/admin/gst-rules/{id}", True, "Rate updated to 8%")
                else:
                    log_test("PATCH /api/admin/gst-rules/{id}", False, 
                            f"Rate not updated: {rule.get('rate_percent')}")
            else:
                log_test("PATCH /api/admin/gst-rules/{id}", False, 
                        f"Status {resp.status_code}")
        except Exception as e:
            log_test("PATCH /api/admin/gst-rules/{id}", False, f"Exception: {e}")
    
    # Delete GST rule
    if test_rule_id:
        try:
            resp = requests.delete(
                f"{BACKEND_URL}/admin/gst-rules/{test_rule_id}",
                headers={"Authorization": f"Bearer {admin_token}"},
                timeout=10
            )
            if resp.status_code == 200 and resp.json().get("deleted") == True:
                log_test("DELETE /api/admin/gst-rules/{id}", True, "Rule deleted")
            else:
                log_test("DELETE /api/admin/gst-rules/{id}", False, 
                        f"Status {resp.status_code}")
        except Exception as e:
            log_test("DELETE /api/admin/gst-rules/{id}", False, f"Exception: {e}")


def test_tax_engine():
    """Test 4: Tax Engine - POST /api/cart/compute-tax"""
    print("\n=== SECTION 4: TAX ENGINE ===")
    
    # Get a product with HSN 7009
    try:
        resp = requests.get(f"{BACKEND_URL}/products", timeout=10)
        products = resp.json()
        mirror_product = next((p for p in products if p.get("hsn_code") == "7009"), None)
        
        if not mirror_product:
            log_test("Find product with HSN 7009", False, "No product with HSN 7009 found")
            return
        
        product_id = mirror_product["id"]
        log_test("Find product with HSN 7009", True, f"Found product: {mirror_product['name']}")
        
        # Test A: Intra-state (Maharashtra) - CGST + SGST
        resp = requests.post(
            f"{BACKEND_URL}/cart/compute-tax",
            json={
                "items": [{"product_id": product_id, "quantity": 1}],
                "ship_state": "Maharashtra"
            },
            timeout=10
        )
        if resp.status_code == 200:
            tax = resp.json()
            intra = tax.get("intra_state")
            gst_total = tax.get("gst_total_inr", 0)
            cgst = tax.get("cgst_inr", 0)
            sgst = tax.get("sgst_inr", 0)
            igst = tax.get("igst_inr", 0)
            
            checks = []
            checks.append(("intra_state == True", intra == True))
            checks.append(("gst_total_inr > 0", gst_total > 0))
            checks.append(("cgst_inr + sgst_inr == gst_total_inr", cgst + sgst == gst_total))
            checks.append(("igst_inr == 0", igst == 0))
            
            all_pass = all(c[1] for c in checks)
            details = f"intra_state={intra}, gst_total={gst_total}, cgst={cgst}, sgst={sgst}, igst={igst}"
            log_test("Tax Engine: Intra-state (Maharashtra) → CGST+SGST", all_pass, details)
        else:
            log_test("Tax Engine: Intra-state (Maharashtra)", False, 
                    f"Status {resp.status_code}")
        
        # Test B: Inter-state (Karnataka) - IGST
        resp = requests.post(
            f"{BACKEND_URL}/cart/compute-tax",
            json={
                "items": [{"product_id": product_id, "quantity": 1}],
                "ship_state": "Karnataka"
            },
            timeout=10
        )
        if resp.status_code == 200:
            tax = resp.json()
            intra = tax.get("intra_state")
            gst_total = tax.get("gst_total_inr", 0)
            cgst = tax.get("cgst_inr", 0)
            sgst = tax.get("sgst_inr", 0)
            igst = tax.get("igst_inr", 0)
            
            checks = []
            checks.append(("intra_state == False", intra == False))
            checks.append(("cgst_inr == 0", cgst == 0))
            checks.append(("sgst_inr == 0", sgst == 0))
            checks.append(("igst_inr == gst_total_inr", igst == gst_total))
            
            all_pass = all(c[1] for c in checks)
            details = f"intra_state={intra}, gst_total={gst_total}, cgst={cgst}, sgst={sgst}, igst={igst}"
            log_test("Tax Engine: Inter-state (Karnataka) → IGST", all_pass, details)
        else:
            log_test("Tax Engine: Inter-state (Karnataka)", False, 
                    f"Status {resp.status_code}")
        
        # Test C: Multi-item cart
        if len(products) >= 2:
            product_ids = [products[0]["id"], products[1]["id"]]
            resp = requests.post(
                f"{BACKEND_URL}/cart/compute-tax",
                json={
                    "items": [
                        {"product_id": product_ids[0], "quantity": 2},
                        {"product_id": product_ids[1], "quantity": 2}
                    ],
                    "ship_state": "Maharashtra"
                },
                timeout=10
            )
            if resp.status_code == 200:
                tax = resp.json()
                gst_total = tax.get("gst_total_inr", 0)
                gst_lines = tax.get("gst_lines", [])
                line_sum = sum(line.get("tax_inr", 0) for line in gst_lines)
                
                if gst_total == line_sum and len(gst_lines) == 2:
                    log_test("Tax Engine: Multi-item cart", True, 
                            f"gst_total={gst_total} == sum of line taxes={line_sum}, {len(gst_lines)} lines")
                else:
                    log_test("Tax Engine: Multi-item cart", False, 
                            f"gst_total={gst_total}, line_sum={line_sum}, lines={len(gst_lines)}")
            else:
                log_test("Tax Engine: Multi-item cart", False, f"Status {resp.status_code}")
        
        # Test D: Unknown product / quantity=0
        resp = requests.post(
            f"{BACKEND_URL}/cart/compute-tax",
            json={
                "items": [
                    {"product_id": "unknown-id-12345", "quantity": 1},
                    {"product_id": product_id, "quantity": 0}
                ],
                "ship_state": "Maharashtra"
            },
            timeout=10
        )
        if resp.status_code == 200:
            tax = resp.json()
            gst_lines = tax.get("gst_lines", [])
            log_test("Tax Engine: Unknown product / qty=0", True, 
                    f"No crash, returned {len(gst_lines)} lines (skipped invalid items)")
        else:
            log_test("Tax Engine: Unknown product / qty=0", False, 
                    f"Status {resp.status_code}")
        
        # Test E: No ship_state → treated as inter-state (IGST)
        resp = requests.post(
            f"{BACKEND_URL}/cart/compute-tax",
            json={
                "items": [{"product_id": product_id, "quantity": 1}]
            },
            timeout=10
        )
        if resp.status_code == 200:
            tax = resp.json()
            intra = tax.get("intra_state")
            igst = tax.get("igst_inr", 0)
            cgst = tax.get("cgst_inr", 0)
            sgst = tax.get("sgst_inr", 0)
            
            if intra == False and igst > 0 and cgst == 0 and sgst == 0:
                log_test("Tax Engine: No ship_state → inter-state (IGST)", True, 
                        f"intra_state={intra}, igst={igst}")
            else:
                log_test("Tax Engine: No ship_state → inter-state (IGST)", False, 
                        f"intra_state={intra}, igst={igst}, cgst={cgst}, sgst={sgst}")
        else:
            log_test("Tax Engine: No ship_state", False, f"Status {resp.status_code}")
        
    except Exception as e:
        log_test("Tax Engine", False, f"Exception: {e}")


def test_hsn_vs_category_priority():
    """Test 5: HSN vs Category Priority"""
    print("\n=== SECTION 5: HSN vs CATEGORY PRIORITY ===")
    
    temp_rule_id = None
    existing_mirrors_rule = None
    try:
        # First, find and delete the existing category="mirrors" rule (will recreate after test)
        resp = requests.get(
            f"{BACKEND_URL}/admin/gst-rules",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        if resp.status_code == 200:
            rules = resp.json()
            existing_rule = next((r for r in rules if r.get("category") == "mirrors" and not r.get("hsn_code")), None)
            if existing_rule:
                existing_mirrors_rule = existing_rule.copy()
                # Delete it temporarily
                resp = requests.delete(
                    f"{BACKEND_URL}/admin/gst-rules/{existing_rule['id']}",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    timeout=10
                )
                if resp.status_code == 200:
                    log_test("Temporarily delete existing mirrors category rule", True, 
                            f"Deleted rule with rate {existing_rule['rate_percent']}%")
        
        # Create a temporary GST rule for category "mirrors" with rate 5%
        resp = requests.post(
            f"{BACKEND_URL}/admin/gst-rules",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "category": "mirrors",
                "rate_percent": 5,
                "description": "Temp category rule for priority test",
                "active": True
            },
            timeout=10
        )
        
        if resp.status_code != 200:
            log_test("Create temp category rule", False, f"Status {resp.status_code}: {resp.text}")
            return
        
        temp_rule_id = resp.json().get("id")
        log_test("Create temp category rule", True, "Created category='mirrors' rule with 5%")
        
        # Get a mirror product (HSN 7009 has 18% seeded)
        resp = requests.get(f"{BACKEND_URL}/products", timeout=10)
        products = resp.json()
        mirror = next((p for p in products if p.get("hsn_code") == "7009"), None)
        
        if not mirror:
            log_test("Find mirror product", False, "No mirror with HSN 7009")
            return
        
        # Compute tax - HSN rule (18%) should win over category rule (5%)
        resp = requests.post(
            f"{BACKEND_URL}/cart/compute-tax",
            json={
                "items": [{"product_id": mirror["id"], "quantity": 1}],
                "ship_state": "Maharashtra"
            },
            timeout=10
        )
        
        if resp.status_code == 200:
            tax = resp.json()
            gst_lines = tax.get("gst_lines", [])
            if gst_lines:
                line = gst_lines[0]
                source = line.get("source", "")
                rate = line.get("rate_percent", 0)
                
                if "hsn:7009" in source and rate == 18:
                    log_test("HSN priority over category", True, 
                            f"HSN 7009 (18%) wins over category (5%), source={source}")
                else:
                    log_test("HSN priority over category", False, 
                            f"Expected HSN 7009 (18%), got source={source}, rate={rate}")
            else:
                log_test("HSN priority over category", False, "No gst_lines returned")
        else:
            log_test("HSN priority over category", False, f"Status {resp.status_code}")
        
    except Exception as e:
        log_test("HSN vs Category Priority", False, f"Exception: {e}")
    finally:
        # Cleanup: delete temp rule and restore existing rule
        if temp_rule_id:
            try:
                resp = requests.delete(
                    f"{BACKEND_URL}/admin/gst-rules/{temp_rule_id}",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    timeout=10
                )
                if resp.status_code == 200:
                    log_test("Cleanup temp GST rule", True, "Deleted temp rule")
                else:
                    log_test("Cleanup temp GST rule", False, f"Status {resp.status_code}")
            except Exception as e:
                log_test("Cleanup temp GST rule", False, f"Exception: {e}")
        
        # Restore the existing mirrors rule if we deleted it
        if existing_mirrors_rule:
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/admin/gst-rules",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    json={
                        "category": existing_mirrors_rule.get("category"),
                        "hsn_code": existing_mirrors_rule.get("hsn_code"),
                        "rate_percent": existing_mirrors_rule.get("rate_percent"),
                        "description": existing_mirrors_rule.get("description"),
                        "active": existing_mirrors_rule.get("active", True)
                    },
                    timeout=10
                )
                if resp.status_code == 200:
                    log_test("Restore original mirrors rule", True, 
                            f"Restored rule with rate {existing_mirrors_rule.get('rate_percent')}%")
            except Exception as e:
                log_test("Restore original mirrors rule", False, f"Exception: {e}")


def test_order_gst_computation():
    """Test 6: Order create computes GST server-side"""
    print("\n=== SECTION 6: ORDER CREATE COMPUTES GST ===")
    
    try:
        # Get a product
        resp = requests.get(f"{BACKEND_URL}/products", timeout=10)
        products = resp.json()
        if not products:
            log_test("Get product for order", False, "No products available")
            return
        
        product = products[0]
        product_id = product["id"]
        variant_key = product["variants"][0]["key"] if product.get("variants") else None
        
        # Create order with wrong gst_total_inr=0 (server should recompute)
        order_payload = {
            "customer": {
                "name": "Test Customer",
                "email": "test@example.com",
                "phone": "9876543210",
                "address": "123 Test Street",
                "city": "Mumbai",
                "pincode": "400001",
                "state": "Maharashtra",
                "country": "India"
            },
            "items": [
                {"product_id": product_id, "variant_key": variant_key, "quantity": 1}
            ],
            "payment_method": "cod",
            "subtotal_inr": product["price_inr"],
            "shipping_inr": 0,
            "total_inr": product["price_inr"],
            "discount_inr": 0,
            "gst_total_inr": 0,  # Wrong value - server should recompute
            "cgst_inr": 0,
            "sgst_inr": 0,
            "igst_inr": 0
        }
        
        resp = requests.post(
            f"{BACKEND_URL}/orders",
            json=order_payload,
            timeout=10
        )
        
        if resp.status_code != 200:
            log_test("POST /api/orders", False, f"Status {resp.status_code}: {resp.text}")
            return
        
        order_data = resp.json()
        order = order_data.get("order", {})
        order_number = order.get("order_number")
        
        if not order_number:
            log_test("POST /api/orders", False, "No order_number in response")
            return
        
        log_test("POST /api/orders", True, f"Order created: {order_number}")
        
        # Check server recomputed GST
        gst_total = order.get("gst_total_inr", 0)
        cgst = order.get("cgst_inr", 0)
        sgst = order.get("sgst_inr", 0)
        igst = order.get("igst_inr", 0)
        gst_lines = order.get("gst_lines", [])
        
        if gst_total > 0:
            log_test("Server recomputed GST (gst_total_inr > 0)", True, 
                    f"gst_total={gst_total}, cgst={cgst}, sgst={sgst}, igst={igst}")
        else:
            log_test("Server recomputed GST (gst_total_inr > 0)", False, 
                    f"gst_total={gst_total}")
        
        if gst_lines:
            log_test("Order has gst_lines[]", True, f"{len(gst_lines)} lines")
        else:
            log_test("Order has gst_lines[]", False, "No gst_lines")
        
        # Check CGST+SGST for Maharashtra (intra-state)
        if cgst > 0 and sgst > 0 and igst == 0:
            log_test("Intra-state order has CGST+SGST", True, 
                    f"cgst={cgst}, sgst={sgst}, igst={igst}")
        else:
            log_test("Intra-state order has CGST+SGST", False, 
                    f"cgst={cgst}, sgst={sgst}, igst={igst}")
        
        # Verify GET /api/orders/{order_number} returns persisted GST fields
        resp = requests.get(f"{BACKEND_URL}/orders/{order_number}", timeout=10)
        if resp.status_code == 200:
            fetched_order = resp.json()
            fetched_gst = fetched_order.get("gst_total_inr", 0)
            fetched_lines = fetched_order.get("gst_lines", [])
            
            if fetched_gst == gst_total and len(fetched_lines) == len(gst_lines):
                log_test("GET /api/orders/{n} returns persisted GST", True, 
                        f"gst_total={fetched_gst}, {len(fetched_lines)} lines")
            else:
                log_test("GET /api/orders/{n} returns persisted GST", False, 
                        f"Mismatch: fetched_gst={fetched_gst}, original={gst_total}")
        else:
            log_test("GET /api/orders/{n}", False, f"Status {resp.status_code}")
        
    except Exception as e:
        log_test("Order GST computation", False, f"Exception: {e}")


def test_permission_check():
    """Test 7: Permission check"""
    print("\n=== SECTION 7: PERMISSION CHECK ===")
    
    # Anonymous request to /api/admin/gst-rules should return 401
    try:
        resp = requests.get(f"{BACKEND_URL}/admin/gst-rules", timeout=10)
        if resp.status_code == 401:
            log_test("Anonymous request to /api/admin/gst-rules → 401", True, "Unauthorized as expected")
        else:
            log_test("Anonymous request to /api/admin/gst-rules → 401", False, 
                    f"Expected 401, got {resp.status_code}")
    except Exception as e:
        log_test("Anonymous request to /api/admin/gst-rules", False, f"Exception: {e}")
    
    # Admin token should succeed
    try:
        resp = requests.get(
            f"{BACKEND_URL}/admin/gst-rules",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        if resp.status_code == 200:
            log_test("Admin request to /api/admin/gst-rules → 200", True, "Authorized")
        else:
            log_test("Admin request to /api/admin/gst-rules → 200", False, 
                    f"Expected 200, got {resp.status_code}")
    except Exception as e:
        log_test("Admin request to /api/admin/gst-rules", False, f"Exception: {e}")


def main():
    print("=" * 80)
    print("PHASE A (JUL 2025) BACKEND TESTING - ArtyFex")
    print("=" * 80)
    
    # Login first
    if not admin_login():
        print("\n❌ FATAL: Admin login failed. Cannot proceed with tests.")
        sys.exit(1)
    
    # Run all tests
    test_product_schema_expansion()
    test_product_categories()
    test_gst_rules()
    test_tax_engine()
    test_hsn_vs_category_priority()
    test_order_gst_computation()
    test_permission_check()
    
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
        print(f"\n❌ {total - passed} TESTS FAILED")
        print("\nFailed tests:")
        for r in results:
            if not r["passed"]:
                print(f"  - {r['test']}")
                if r["details"]:
                    print(f"    {r['details']}")
    
    # Save results to JSON
    with open("/app/backend_test_phase_a_jul2025_results.json", "w") as f:
        json.dump({
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "results": results
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: /app/backend_test_phase_a_jul2025_results.json")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
