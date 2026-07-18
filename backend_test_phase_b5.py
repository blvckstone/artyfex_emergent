#!/usr/bin/env python3
"""
Phase B5 Backend Testing - ArtyFex E-commerce
Tests: Order line-item snapshot (Phase A closure), Dynamic-Page CMS (Phase B5), SEO endpoints (Phase B4)
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "https://backend-migration-24.preview.emergentagent.com/api"
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
print("PHASE B5 BACKEND TESTING - ArtyFex E-commerce")
print("=" * 80)
print()

# ============================================================================
# SECTION 1: ORDER LINE-ITEM SNAPSHOT (Phase A closure)
# ============================================================================
print("SECTION 1: Order Line-Item Snapshot (Phase A closure)")
print("-" * 80)

try:
    # Test 1.1: GET /api/products → pick first product
    resp = requests.get(f"{BASE_URL}/products")
    if resp.status_code == 200:
        products = resp.json()
        log_test("GET /api/products", len(products) > 0, f"Found {len(products)} products")
        
        if len(products) > 0:
            first_product = products[0]
            product_id = first_product.get("id")
            variant_key = first_product.get("variants", [{}])[0].get("key") if first_product.get("variants") else None
            
            print(f"   Using product_id: {product_id}, variant_key: {variant_key}")
            
            # Test 1.2: POST /api/orders with COD payment method
            order_payload = {
                "customer": {
                    "name": "Test Customer Phase B5",
                    "email": "testb5@example.com",
                    "phone": "+919876543210",
                    "address": "123 Test Street",
                    "city": "Mumbai",
                    "pincode": "400001",
                    "state": "Maharashtra",
                    "country": "India"
                },
                "items": [
                    {
                        "product_id": product_id,
                        "variant_key": variant_key,
                        "quantity": 2
                    }
                ],
                "payment_method": "cod",
                "subtotal_inr": 10000,
                "shipping_inr": 0,
                "total_inr": 10000,
                "discount_inr": 0
            }
            
            resp = requests.post(f"{BASE_URL}/orders", json=order_payload)
            if resp.status_code == 200:
                order_data = resp.json().get("order", {})
                order_number = order_data.get("order_number")
                log_test("POST /api/orders (COD)", True, f"Order created: {order_number}")
                
                # Test 1.3: GET /api/admin/orders (with admin auth) → check snapshot fields
                owner_token = admin_login()
                headers = {"Authorization": f"Bearer {owner_token}"}
                
                resp = requests.get(f"{BASE_URL}/admin/orders", headers=headers)
                if resp.status_code == 200:
                    orders = resp.json()
                    log_test("GET /api/admin/orders", True, f"Found {len(orders)} orders")
                    
                    # Find the most recent order (should be ours)
                    if len(orders) > 0:
                        recent_order = orders[0]  # Assuming sorted by created_at desc
                        items = recent_order.get("items", [])
                        
                        if len(items) > 0:
                            item = items[0]
                            
                            # Check all required snapshot fields
                            required_fields = [
                                "product_name", "product_image", "product_category",
                                "product_sku", "product_hsn_code", "variant_label",
                                "size", "price_inr", "line_total_inr"
                            ]
                            
                            missing_fields = []
                            null_fields = []
                            
                            for field in required_fields:
                                if field not in item:
                                    missing_fields.append(field)
                                elif item[field] is None:
                                    null_fields.append(field)
                            
                            snapshot_valid = len(missing_fields) == 0 and len(null_fields) == 0
                            
                            details = ""
                            if not snapshot_valid:
                                if missing_fields:
                                    details += f"Missing fields: {missing_fields}. "
                                if null_fields:
                                    details += f"Null fields: {null_fields}. "
                            else:
                                # Verify line_total_inr = price_inr * quantity
                                price = item.get("price_inr", 0)
                                quantity = item.get("quantity", 0)
                                line_total = item.get("line_total_inr", 0)
                                expected_total = price * quantity
                                
                                if line_total == expected_total:
                                    details = f"Snapshot fields present. line_total_inr={line_total} = price_inr({price}) * quantity({quantity})"
                                else:
                                    snapshot_valid = False
                                    details = f"line_total_inr mismatch: {line_total} != {price} * {quantity} = {expected_total}"
                            
                            log_test("Order item snapshot fields (admin)", snapshot_valid, details)
                        else:
                            log_test("Order item snapshot fields (admin)", False, "No items in order")
                    else:
                        log_test("Order item snapshot fields (admin)", False, "No orders found")
                else:
                    log_test("GET /api/admin/orders", False, f"Status: {resp.status_code}, Body: {resp.text[:200]}")
                
                # Test 1.4: GET /api/orders/{order_number} (public) → check snapshot fields
                resp = requests.get(f"{BASE_URL}/orders/{order_number}")
                if resp.status_code == 200:
                    order = resp.json()
                    items = order.get("items", [])
                    
                    if len(items) > 0:
                        item = items[0]
                        
                        # Check all required snapshot fields
                        required_fields = [
                            "product_name", "product_image", "product_category",
                            "product_sku", "product_hsn_code", "variant_label",
                            "size", "price_inr", "line_total_inr"
                        ]
                        
                        missing_fields = []
                        null_fields = []
                        
                        for field in required_fields:
                            if field not in item:
                                missing_fields.append(field)
                            elif item[field] is None:
                                null_fields.append(field)
                        
                        snapshot_valid = len(missing_fields) == 0 and len(null_fields) == 0
                        
                        details = ""
                        if not snapshot_valid:
                            if missing_fields:
                                details += f"Missing fields: {missing_fields}. "
                            if null_fields:
                                details += f"Null fields: {null_fields}. "
                        else:
                            details = f"All snapshot fields present in public endpoint"
                        
                        log_test("Order item snapshot fields (public)", snapshot_valid, details)
                    else:
                        log_test("Order item snapshot fields (public)", False, "No items in order")
                else:
                    log_test("GET /api/orders/{order_number}", False, f"Status: {resp.status_code}, Body: {resp.text[:200]}")
            else:
                log_test("POST /api/orders (COD)", False, f"Status: {resp.status_code}, Body: {resp.text[:200]}")
        else:
            log_test("POST /api/orders (COD)", False, "No products available to create order")
    else:
        log_test("GET /api/products", False, f"Status: {resp.status_code}, Body: {resp.text[:200]}")
except Exception as e:
    log_test("Section 1 - Order snapshot", False, f"Exception: {str(e)}")

print()

# ============================================================================
# SECTION 2: DYNAMIC-PAGE CMS (Phase B5)
# ============================================================================
print("SECTION 2: Dynamic-Page CMS (Phase B5)")
print("-" * 80)

try:
    # Test 2.1: GET /api/pages (public, no auth) → 200, array with 5 seeded defaults
    resp = requests.get(f"{BASE_URL}/pages")
    if resp.status_code == 200:
        pages = resp.json()
        
        # Check if it's an array
        is_array = isinstance(pages, list)
        
        # Check for the 5 seeded defaults
        expected_slugs = [
            "privacy-policy", "terms-and-conditions", "shipping-policy",
            "refund-and-return-policy", "cookie-policy"
        ]
        
        found_slugs = [p.get("slug") for p in pages if isinstance(p, dict)]
        has_all_defaults = all(slug in found_slugs for slug in expected_slugs)
        
        details = f"Found {len(pages)} pages. Slugs: {found_slugs[:10]}"
        if not has_all_defaults:
            missing = [s for s in expected_slugs if s not in found_slugs]
            details += f". Missing: {missing}"
        
        log_test("GET /api/pages (public)", is_array and has_all_defaults, details)
    else:
        log_test("GET /api/pages (public)", False, f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    
    # Test 2.2: GET /api/pages/privacy-policy → 200 with title, meta_title, blocks[]
    resp = requests.get(f"{BASE_URL}/pages/privacy-policy")
    if resp.status_code == 200:
        page = resp.json()
        
        has_title = page.get("title") == "Privacy Policy"
        has_meta_title = "meta_title" in page and page.get("meta_title") is not None
        has_blocks = isinstance(page.get("blocks"), list) and len(page.get("blocks", [])) > 0
        
        all_valid = has_title and has_meta_title and has_blocks
        
        details = f"title={page.get('title')}, meta_title present={has_meta_title}, blocks count={len(page.get('blocks', []))}"
        
        log_test("GET /api/pages/privacy-policy", all_valid, details)
    else:
        log_test("GET /api/pages/privacy-policy", False, f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    
    # Test 2.3: GET /api/pages/does-not-exist → 404
    resp = requests.get(f"{BASE_URL}/pages/does-not-exist")
    log_test("GET /api/pages/does-not-exist → 404", resp.status_code == 404, f"Status: {resp.status_code}")
    
    # Test 2.4: GET /api/admin/pages (admin auth) → 200 array (>=5 items)
    owner_token = admin_login()
    headers = {"Authorization": f"Bearer {owner_token}"}
    
    resp = requests.get(f"{BASE_URL}/admin/pages", headers=headers)
    if resp.status_code == 200:
        admin_pages = resp.json()
        is_array = isinstance(admin_pages, list)
        has_min_5 = len(admin_pages) >= 5
        
        log_test("GET /api/admin/pages", is_array and has_min_5, f"Found {len(admin_pages)} pages")
    else:
        log_test("GET /api/admin/pages", False, f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    
    # Test 2.5: POST /api/admin/pages (admin auth) → create new page
    new_page_payload = {
        "slug": "test-page",
        "title": "Test Page",
        "blocks": [
            {
                "type": "heading",
                "level": 2,
                "text": "Hello"
            }
        ],
        "published": True,
        "show_in_header": False,
        "show_in_footer": True,
        "header_order": 200,
        "meta_title": "Test Page Meta",
        "meta_description": "Test page description"
    }
    
    resp = requests.post(f"{BASE_URL}/admin/pages", json=new_page_payload, headers=headers)
    if resp.status_code == 200:
        created_page = resp.json()
        page_id = created_page.get("id")
        
        log_test("POST /api/admin/pages (create)", True, f"Created page with id: {page_id}")
        
        # Test 2.6: POST duplicate slug → 400
        resp = requests.post(f"{BASE_URL}/admin/pages", json=new_page_payload, headers=headers)
        log_test("POST /api/admin/pages (duplicate slug) → 400", resp.status_code == 400, f"Status: {resp.status_code}")
        
        # Test 2.7: PATCH /api/admin/pages/{id} → update page
        update_payload = {
            "slug": "test-page",
            "title": "Test Updated",
            "blocks": [
                {
                    "type": "paragraph",
                    "html": "Updated body"
                }
            ],
            "published": True,
            "show_in_header": True,
            "show_in_footer": True,
            "header_order": 200,
            "meta_title": "Test Updated Meta",
            "meta_description": "Test updated description"
        }
        
        resp = requests.patch(f"{BASE_URL}/admin/pages/{page_id}", json=update_payload, headers=headers)
        if resp.status_code == 200:
            updated_page = resp.json()
            show_in_header = updated_page.get("show_in_header")
            
            log_test("PATCH /api/admin/pages/{id}", show_in_header == True, f"show_in_header={show_in_header}")
        else:
            log_test("PATCH /api/admin/pages/{id}", False, f"Status: {resp.status_code}, Body: {resp.text[:200]}")
        
        # Test 2.8: GET /api/pages → verify updated page with show_in_header:true
        resp = requests.get(f"{BASE_URL}/pages")
        if resp.status_code == 200:
            pages = resp.json()
            test_page = next((p for p in pages if p.get("slug") == "test-page"), None)
            
            if test_page:
                has_show_in_header = test_page.get("show_in_header") == True
                log_test("GET /api/pages (updated page visible)", has_show_in_header, f"show_in_header={test_page.get('show_in_header')}")
            else:
                log_test("GET /api/pages (updated page visible)", False, "test-page not found in list")
        else:
            log_test("GET /api/pages (updated page visible)", False, f"Status: {resp.status_code}")
        
        # Test 2.9: POST /api/admin/pages/reorder → reorder pages
        # Get all page IDs first
        resp = requests.get(f"{BASE_URL}/admin/pages", headers=headers)
        if resp.status_code == 200:
            all_pages = resp.json()
            all_ids = [p.get("id") for p in all_pages if p.get("id")]
            
            reorder_payload = {"ids": all_ids}
            
            resp = requests.post(f"{BASE_URL}/admin/pages/reorder", json=reorder_payload, headers=headers)
            if resp.status_code == 200:
                result = resp.json()
                reordered_count = result.get("reordered", 0)
                
                log_test("POST /api/admin/pages/reorder", reordered_count == len(all_ids), f"Reordered {reordered_count} pages")
                
                # Verify header_order values updated
                resp = requests.get(f"{BASE_URL}/admin/pages", headers=headers)
                if resp.status_code == 200:
                    updated_pages = resp.json()
                    header_orders = [p.get("header_order") for p in updated_pages]
                    
                    # Check if header_orders are in sequence (0, 10, 20, ...)
                    expected_orders = [i * 10 for i in range(len(updated_pages))]
                    orders_match = header_orders == expected_orders
                    
                    log_test("GET /api/admin/pages (header_order updated)", orders_match, f"header_orders: {header_orders[:5]}...")
                else:
                    log_test("GET /api/admin/pages (header_order updated)", False, f"Status: {resp.status_code}")
            else:
                log_test("POST /api/admin/pages/reorder", False, f"Status: {resp.status_code}, Body: {resp.text[:200]}")
        else:
            log_test("POST /api/admin/pages/reorder", False, "Could not get page IDs")
        
        # Test 2.10: DELETE /api/admin/pages/{id} → 200
        resp = requests.delete(f"{BASE_URL}/admin/pages/{page_id}", headers=headers)
        log_test("DELETE /api/admin/pages/{id}", resp.status_code == 200, f"Status: {resp.status_code}")
        
        # Test 2.11: GET /api/admin/pages/{id} after delete → 404
        resp = requests.get(f"{BASE_URL}/admin/pages/{page_id}", headers=headers)
        log_test("GET /api/admin/pages/{id} after delete → 404", resp.status_code == 404, f"Status: {resp.status_code}")
    else:
        log_test("POST /api/admin/pages (create)", False, f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    
    # Test 2.12: Auth check - GET /api/admin/pages without auth → 401
    resp = requests.get(f"{BASE_URL}/admin/pages")
    log_test("GET /api/admin/pages (no auth) → 401", resp.status_code == 401, f"Status: {resp.status_code}")

except Exception as e:
    log_test("Section 2 - Dynamic-Page CMS", False, f"Exception: {str(e)}")

print()

# ============================================================================
# SECTION 3: SEO ENDPOINTS (Phase B4)
# ============================================================================
print("SECTION 3: SEO Endpoints (Phase B4)")
print("-" * 80)

try:
    # Test 3.1: GET /api/seo/robots.txt → 200 text/plain
    resp = requests.get(f"{BASE_URL}/seo/robots.txt")
    if resp.status_code == 200:
        content_type = resp.headers.get("content-type", "")
        is_text_plain = "text/plain" in content_type
        
        body = resp.text
        has_user_agent = "User-agent: *" in body
        has_disallow_admin = "Disallow: /admin" in body
        has_sitemap = "Sitemap:" in body
        
        all_valid = is_text_plain and has_user_agent and has_disallow_admin and has_sitemap
        
        details = f"content-type={content_type}, has User-agent={has_user_agent}, has Disallow admin={has_disallow_admin}, has Sitemap={has_sitemap}"
        
        log_test("GET /api/seo/robots.txt", all_valid, details)
    else:
        log_test("GET /api/seo/robots.txt", False, f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    
    # Test 3.2: GET /api/seo/sitemap.xml → 200 application/xml
    resp = requests.get(f"{BASE_URL}/seo/sitemap.xml")
    if resp.status_code == 200:
        content_type = resp.headers.get("content-type", "")
        is_xml = "xml" in content_type.lower()
        
        body = resp.text
        starts_with_xml = body.strip().startswith("<?xml")
        has_url_tag = "<url>" in body
        
        # Check for at least one product slug (from seeded products)
        # Based on test_result.md, seeded products include "obsidian-geode-2x3"
        has_product = "obsidian-geode" in body or "/product/" in body
        
        # Check for at least one CMS page (privacy-policy)
        has_cms_page = "/p/privacy-policy" in body
        
        all_valid = is_xml and starts_with_xml and has_url_tag and (has_product or has_cms_page)
        
        details = f"content-type={content_type}, starts with <?xml={starts_with_xml}, has <url>={has_url_tag}, has product={has_product}, has CMS page={has_cms_page}"
        
        log_test("GET /api/seo/sitemap.xml", all_valid, details)
    else:
        log_test("GET /api/seo/sitemap.xml", False, f"Status: {resp.status_code}, Body: {resp.text[:200]}")

except Exception as e:
    log_test("Section 3 - SEO Endpoints", False, f"Exception: {str(e)}")

print()

# ============================================================================
# SUMMARY
# ============================================================================
print("=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print(f"Total tests: {results['total']}")
print(f"Passed: {results['passed']}")
print(f"Failed: {results['failed']}")
print(f"Success rate: {(results['passed'] / results['total'] * 100) if results['total'] > 0 else 0:.1f}%")
print()

# Save results to JSON
with open("/app/backend_test_phase_b5_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("Results saved to /app/backend_test_phase_b5_results.json")
print()

# Exit with appropriate code
exit(0 if results['failed'] == 0 else 1)
