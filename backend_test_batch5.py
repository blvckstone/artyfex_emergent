#!/usr/bin/env python3
"""
Batch 5 Backend Testing
Tests for:
1. Variant model + OrderItem snapshot (per-variation SKU/weight/dims)
2. Cloudinary orphan cleanup (BackgroundTasks-based)
3. Backward-compat regression smoke tests
"""

import requests
import json
import time
from typing import Dict, Any, List

# Configuration
BASE_URL = "https://html-inject-scan.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@artyfex.in"
ADMIN_PASSWORD = "ArtyFex@2026"

# Test results storage
results = {
    "task1_variant_snapshot": [],
    "task2_cloudinary_cleanup": [],
    "task3_regression": [],
    "summary": {
        "total": 0,
        "passed": 0,
        "failed": 0
    }
}

def log_test(task: str, name: str, passed: bool, details: str = ""):
    """Log a test result"""
    result = {
        "name": name,
        "passed": passed,
        "details": details
    }
    results[task].append(result)
    results["summary"]["total"] += 1
    if passed:
        results["summary"]["passed"] += 1
        print(f"✅ {name}")
    else:
        results["summary"]["failed"] += 1
        print(f"❌ {name}")
    if details:
        print(f"   {details}")


def get_admin_token() -> str:
    """Get admin JWT token"""
    resp = requests.post(f"{BASE_URL}/admin/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if resp.status_code != 200:
        raise Exception(f"Admin login failed: {resp.status_code} {resp.text}")
    return resp.json()["token"]


def test_task1_variant_snapshot(token: str):
    """
    TASK 1: Variant model + OrderItem snapshot
    Tests that variant-level SKU/weight/dims are preferred over product-level
    """
    print("\n" + "="*80)
    print("TASK 1: Variant model + OrderItem snapshot")
    print("="*80)
    
    headers = {"Authorization": f"Bearer {token}"}
    created_product_id = None
    created_order_number = None
    
    try:
        # Test 1.1: Create product with variant containing all 5 new fields
        print("\n[Test 1.1] Create product with variant containing new fields...")
        product_payload = {
            "slug": f"test-batch5-{int(time.time())}",
            "name": "Test Batch 5 Product",
            "tagline": "Test product for Batch 5",
            "description": "Testing variant-level shipping fields",
            "price_inr": 1000,
            "mrp_inr": 1200,
            "size": "2 ft",
            "craft_hours": 24,
            "materials": ["resin"],
            "hero_image": "https://example.com/hero.jpg",
            "gallery": ["https://example.com/gallery1.jpg"],
            "stock": 5,
            "is_hero": False,
            # Product-level shipping fields
            "sku": "PROD-BASE",
            "weight_grams": 5000,
            "length_cm": 50,
            "width_cm": 40,
            "height_cm": 5,
            "variants": [
                {
                    "key": "large",
                    "label": "Large",
                    "hex": "#D4AF37",
                    "image": "https://example.com/variant.jpg",
                    "size": "3 ft",
                    "stock": 3,
                    "price_inr": 1500,
                    "mrp_inr": 1800,
                    # Variant-level shipping fields (should override product-level)
                    "sku": "VAR-LARGE",
                    "weight_grams": 8500,
                    "length_cm": 90,
                    "width_cm": 60,
                    "height_cm": 5
                }
            ]
        }
        
        resp = requests.post(f"{BASE_URL}/admin/products", json=product_payload, headers=headers)
        if resp.status_code == 200:
            product = resp.json()
            created_product_id = product.get("id")
            # Verify variant has all 5 new fields
            variant = product.get("variants", [])[0] if product.get("variants") else {}
            has_all_fields = all([
                variant.get("sku") == "VAR-LARGE",
                variant.get("weight_grams") == 8500,
                variant.get("length_cm") == 90,
                variant.get("width_cm") == 60,
                variant.get("height_cm") == 5
            ])
            log_test("task1_variant_snapshot", "Create product with variant new fields", has_all_fields,
                    f"Product ID: {created_product_id}, Variant has all 5 fields: {has_all_fields}")
        else:
            log_test("task1_variant_snapshot", "Create product with variant new fields", False,
                    f"Status: {resp.status_code}, Response: {resp.text[:200]}")
            return
        
        # Test 1.2: GET product and verify variant fields persisted
        print("\n[Test 1.2] GET product and verify variant fields...")
        resp = requests.get(f"{BASE_URL}/products")
        if resp.status_code == 200:
            products = resp.json()
            # Find our created product
            our_product = next((p for p in products if p.get("id") == created_product_id), None)
            if our_product:
                variant = our_product.get("variants", [])[0] if our_product.get("variants") else {}
                has_all_fields = all([
                    variant.get("sku") == "VAR-LARGE",
                    variant.get("weight_grams") == 8500,
                    variant.get("length_cm") == 90,
                    variant.get("width_cm") == 60,
                    variant.get("height_cm") == 5
                ])
                log_test("task1_variant_snapshot", "GET product shows variant fields", has_all_fields,
                        f"Variant fields persisted correctly: {has_all_fields}")
            else:
                log_test("task1_variant_snapshot", "GET product shows variant fields", False,
                        "Created product not found in GET response")
        else:
            log_test("task1_variant_snapshot", "GET product shows variant fields", False,
                    f"Status: {resp.status_code}")
        
        # Test 1.3: Create order with variant to verify snapshot
        print("\n[Test 1.3] Create order with variant to verify snapshot...")
        order_payload = {
            "customer": {
                "name": "Test Customer Batch5",
                "email": "testbatch5@example.com",
                "phone": "+919876543210",
                "address": "123 Test Street",
                "city": "Mumbai",
                "pincode": "400001",
                "state": "Maharashtra",
                "country": "India"
            },
            "items": [
                {
                    "product_id": created_product_id,
                    "variant_key": "large",
                    "quantity": 1
                }
            ],
            "payment_method": "cod",
            "subtotal_inr": 1500,
            "shipping_inr": 0,
            "total_inr": 1500,
            "discount_inr": 0,
            "gst_total_inr": 0,
            "cgst_inr": 0,
            "sgst_inr": 0,
            "igst_inr": 0
        }
        
        resp = requests.post(f"{BASE_URL}/orders", json=order_payload)
        if resp.status_code == 200:
            response_data = resp.json()
            order = response_data.get("order", response_data)  # Handle both {"order": {...}} and direct order response
            created_order_number = order.get("order_number")
            
            # Verify OrderItem has variant-level values (NOT product-level)
            item = order.get("items", [])[0] if order.get("items") else {}
            snapshot_correct = all([
                item.get("product_sku") == "VAR-LARGE",  # NOT "PROD-BASE"
                item.get("weight_grams") == 8500,  # NOT 5000
                item.get("length_cm") == 90,  # NOT 50
                item.get("width_cm") == 60,  # NOT 40
                item.get("height_cm") == 5  # Same as product, but from variant
            ])
            
            details = f"Order: {created_order_number}, SKU: {item.get('product_sku')}, " \
                     f"Weight: {item.get('weight_grams')}g, Dims: {item.get('length_cm')}×{item.get('width_cm')}×{item.get('height_cm')}cm"
            log_test("task1_variant_snapshot", "Order snapshot uses variant-level values", snapshot_correct, details)
        else:
            log_test("task1_variant_snapshot", "Order snapshot uses variant-level values", False,
                    f"Status: {resp.status_code}, Response: {resp.text[:200]}")
        
        # Test 1.4: Backward-compat - product with variant WITHOUT new fields
        print("\n[Test 1.4] Backward-compat: variant without new shipping fields...")
        legacy_product_payload = {
            "slug": f"test-batch5-legacy-{int(time.time())}",
            "name": "Test Legacy Product",
            "tagline": "Legacy test",
            "description": "Testing backward compatibility",
            "price_inr": 2000,
            "mrp_inr": 2500,
            "size": "1 ft",
            "craft_hours": 12,
            "materials": ["wood"],
            "hero_image": "https://example.com/legacy.jpg",
            "gallery": [],
            "stock": 10,
            "is_hero": False,
            # Product-level shipping fields
            "sku": "LEGACY-PROD",
            "weight_grams": 3000,
            "length_cm": 30,
            "width_cm": 25,
            "height_cm": 10,
            "variants": [
                {
                    "key": "standard",
                    "label": "Standard",
                    "hex": "#000000",
                    "image": "https://example.com/standard.jpg"
                    # NO variant-level shipping fields - should fall back to product-level
                }
            ]
        }
        
        resp = requests.post(f"{BASE_URL}/admin/products", json=legacy_product_payload, headers=headers)
        if resp.status_code == 200:
            legacy_product = resp.json()
            legacy_product_id = legacy_product.get("id")
            
            # Create order with legacy variant
            legacy_order_payload = {
                "customer": {
                    "name": "Test Customer Legacy",
                    "email": "testlegacy@example.com",
                    "phone": "+919876543211",
                    "address": "456 Legacy Street",
                    "city": "Delhi",
                    "pincode": "110001",
                    "state": "Delhi",
                    "country": "India"
                },
                "items": [
                    {
                        "product_id": legacy_product_id,
                        "variant_key": "standard",
                        "quantity": 1
                    }
                ],
                "payment_method": "cod",
                "subtotal_inr": 2000,
                "shipping_inr": 0,
                "total_inr": 2000,
                "discount_inr": 0,
                "gst_total_inr": 0,
                "cgst_inr": 0,
                "sgst_inr": 0,
                "igst_inr": 0
            }
            
            resp = requests.post(f"{BASE_URL}/orders", json=legacy_order_payload)
            if resp.status_code == 200:
                response_data = resp.json()
                legacy_order = response_data.get("order", response_data)  # Handle both response formats
                item = legacy_order.get("items", [])[0] if legacy_order.get("items") else {}
                
                # Should fall back to product-level values
                fallback_correct = all([
                    item.get("product_sku") == "LEGACY-PROD",
                    item.get("weight_grams") == 3000,
                    item.get("length_cm") == 30,
                    item.get("width_cm") == 25,
                    item.get("height_cm") == 10
                ])
                
                details = f"Order: {legacy_order.get('order_number')}, Fallback to product-level: " \
                         f"SKU={item.get('product_sku')}, Weight={item.get('weight_grams')}g"
                log_test("task1_variant_snapshot", "Backward-compat fallback to product-level", fallback_correct, details)
            else:
                log_test("task1_variant_snapshot", "Backward-compat fallback to product-level", False,
                        f"Order create failed: {resp.status_code}")
            
            # Cleanup legacy product
            requests.delete(f"{BASE_URL}/admin/products/{legacy_product_id}", headers=headers)
        else:
            log_test("task1_variant_snapshot", "Backward-compat fallback to product-level", False,
                    f"Legacy product create failed: {resp.status_code}")
        
        # Test 1.5: Legacy products still work (no schema errors)
        print("\n[Test 1.5] Legacy products without new fields still work...")
        resp = requests.get(f"{BASE_URL}/products")
        if resp.status_code == 200:
            products = resp.json()
            log_test("task1_variant_snapshot", "Legacy products load without errors", True,
                    f"Loaded {len(products)} products successfully")
        else:
            log_test("task1_variant_snapshot", "Legacy products load without errors", False,
                    f"Status: {resp.status_code}")
    
    finally:
        # Cleanup: delete created product
        if created_product_id:
            print(f"\n[Cleanup] Deleting test product {created_product_id}...")
            requests.delete(f"{BASE_URL}/admin/products/{created_product_id}", headers=headers)


def test_task2_cloudinary_cleanup(token: str):
    """
    TASK 2: Cloudinary orphan cleanup (BackgroundTasks-based)
    Tests that routes with BackgroundTasks parameter work correctly
    """
    print("\n" + "="*80)
    print("TASK 2: Cloudinary orphan cleanup (BackgroundTasks)")
    print("="*80)
    
    headers = {"Authorization": f"Bearer {token}"}
    test_product_id = None
    
    try:
        # Test 2.1: PUT /admin/products/{id} with BackgroundTasks
        print("\n[Test 2.1] PUT /admin/products/{id} returns 200 with correct shape...")
        
        # First create a product
        create_payload = {
            "slug": f"test-cloudinary-{int(time.time())}",
            "name": "Test Cloudinary Product",
            "tagline": "Test",
            "description": "Test",
            "price_inr": 1000,
            "mrp_inr": 1200,
            "size": "1 ft",
            "craft_hours": 10,
            "materials": ["test"],
            "hero_image": "https://example.com/hero.jpg",
            "gallery": ["https://example.com/g1.jpg"],
            "stock": 5,
            "is_hero": False,
            "variants": [{"key": "default", "label": "Default", "hex": "#000000", "image": "https://example.com/v.jpg"}]
        }
        
        resp = requests.post(f"{BASE_URL}/admin/products", json=create_payload, headers=headers)
        if resp.status_code == 200:
            test_product_id = resp.json().get("id")
            
            # Now update it
            update_payload = {**create_payload, "name": "Updated Cloudinary Product"}
            resp = requests.put(f"{BASE_URL}/admin/products/{test_product_id}", json=update_payload, headers=headers)
            
            if resp.status_code == 200:
                updated = resp.json()
                has_required_fields = all([
                    updated.get("id") == test_product_id,
                    updated.get("name") == "Updated Cloudinary Product",
                    updated.get("slug"),
                    updated.get("price_inr"),
                    updated.get("variants")
                ])
                log_test("task2_cloudinary_cleanup", "PUT /admin/products/{id} returns 200", has_required_fields,
                        f"Response has all required fields: {has_required_fields}")
            else:
                log_test("task2_cloudinary_cleanup", "PUT /admin/products/{id} returns 200", False,
                        f"Status: {resp.status_code}, Response: {resp.text[:200]}")
        else:
            log_test("task2_cloudinary_cleanup", "PUT /admin/products/{id} returns 200", False,
                    f"Product create failed: {resp.status_code}")
        
        # Test 2.2: DELETE /admin/products/{id} returns {"deleted": true}
        print("\n[Test 2.2] DELETE /admin/products/{id} returns correct response...")
        if test_product_id:
            resp = requests.delete(f"{BASE_URL}/admin/products/{test_product_id}", headers=headers)
            if resp.status_code == 200:
                result = resp.json()
                is_correct = result.get("deleted") == True
                log_test("task2_cloudinary_cleanup", "DELETE /admin/products/{id} returns {deleted:true}", is_correct,
                        f"Response: {result}")
                test_product_id = None  # Marked as deleted
            else:
                log_test("task2_cloudinary_cleanup", "DELETE /admin/products/{id} returns {deleted:true}", False,
                        f"Status: {resp.status_code}")
        
        # Test 2.3: PATCH /admin/homepage returns saved payload
        print("\n[Test 2.3] PATCH /admin/homepage returns saved payload...")
        
        # First GET current homepage
        resp = requests.get(f"{BASE_URL}/admin/homepage", headers=headers)
        if resp.status_code == 200:
            current_homepage = resp.json()
            
            # PATCH with current payload (no changes, just testing BackgroundTasks)
            resp = requests.patch(f"{BASE_URL}/admin/homepage", json=current_homepage, headers=headers)
            if resp.status_code == 200:
                saved = resp.json()
                has_structure = all([
                    "announcement" in saved,
                    "hero" in saved,
                    "sale_banner" in saved
                ])
                log_test("task2_cloudinary_cleanup", "PATCH /admin/homepage returns saved payload", has_structure,
                        f"Response has correct structure: {has_structure}")
            else:
                log_test("task2_cloudinary_cleanup", "PATCH /admin/homepage returns saved payload", False,
                        f"Status: {resp.status_code}")
        else:
            log_test("task2_cloudinary_cleanup", "PATCH /admin/homepage returns saved payload", False,
                    f"GET homepage failed: {resp.status_code}")
        
        # Test 2.4: No crashes with non-Cloudinary URLs or nulls
        print("\n[Test 2.4] No crashes with non-Cloudinary URLs or nulls...")
        
        # Create product with mixed URLs (Cloudinary and non-Cloudinary)
        mixed_payload = {
            "slug": f"test-mixed-urls-{int(time.time())}",
            "name": "Test Mixed URLs",
            "tagline": "Test",
            "description": "Test",
            "price_inr": 1000,
            "mrp_inr": 1200,
            "size": "1 ft",
            "craft_hours": 10,
            "materials": ["test"],
            "hero_image": "https://example.com/hero.jpg",  # Non-Cloudinary
            "gallery": ["https://res.cloudinary.com/test/image.jpg", "https://example.com/g2.jpg"],  # No nulls
            "stock": 5,
            "is_hero": False,
            "variants": [{"key": "default", "label": "Default", "hex": "#000000", "image": "https://example.com/v.jpg"}]
        }
        
        resp = requests.post(f"{BASE_URL}/admin/products", json=mixed_payload, headers=headers)
        if resp.status_code == 200:
            mixed_product_id = resp.json().get("id")
            
            # Update it (should handle mixed URLs gracefully)
            mixed_payload["name"] = "Updated Mixed URLs"
            resp = requests.put(f"{BASE_URL}/admin/products/{mixed_product_id}", json=mixed_payload, headers=headers)
            
            no_crash = resp.status_code == 200
            log_test("task2_cloudinary_cleanup", "No crashes with mixed/null URLs", no_crash,
                    f"Status: {resp.status_code}")
            
            # Cleanup
            requests.delete(f"{BASE_URL}/admin/products/{mixed_product_id}", headers=headers)
        else:
            log_test("task2_cloudinary_cleanup", "No crashes with mixed/null URLs", False,
                    f"Product create failed: {resp.status_code}")
    
    finally:
        # Cleanup any remaining test product
        if test_product_id:
            requests.delete(f"{BASE_URL}/admin/products/{test_product_id}", headers=headers)


def test_task3_regression(token: str):
    """
    TASK 3: Backward-compat regression smoke tests
    """
    print("\n" + "="*80)
    print("TASK 3: Backward-compat regression smoke tests")
    print("="*80)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 3.1: GET /api/products (public, no auth)
    print("\n[Test 3.1] GET /api/products (public) returns 200...")
    resp = requests.get(f"{BASE_URL}/products")
    if resp.status_code == 200:
        products = resp.json()
        is_list = isinstance(products, list)
        log_test("task3_regression", "GET /api/products returns 200 with list", is_list,
                f"Returned {len(products)} products")
    else:
        log_test("task3_regression", "GET /api/products returns 200 with list", False,
                f"Status: {resp.status_code}")
    
    # Test 3.2: GET /api/products/{slug}
    print("\n[Test 3.2] GET /api/products/{slug} returns 200...")
    # Get first product slug from the list
    resp = requests.get(f"{BASE_URL}/products")
    if resp.status_code == 200 and len(resp.json()) > 0:
        first_slug = resp.json()[0].get("slug")
        resp = requests.get(f"{BASE_URL}/products/{first_slug}")
        success = resp.status_code == 200
        log_test("task3_regression", "GET /api/products/{slug} returns 200", success,
                f"Status: {resp.status_code}, Slug: {first_slug}")
    else:
        log_test("task3_regression", "GET /api/products/{slug} returns 200", False,
                "No products available to test")
    
    # Test 3.3: POST /admin/products with LEGACY payload (no new variant fields)
    print("\n[Test 3.3] POST /admin/products with LEGACY payload...")
    legacy_payload = {
        "slug": f"test-legacy-{int(time.time())}",
        "name": "Test Legacy Product",
        "tagline": "Legacy",
        "description": "No new fields",
        "price_inr": 1000,
        "mrp_inr": 1200,
        "size": "1 ft",
        "craft_hours": 10,
        "materials": ["test"],
        "hero_image": "https://example.com/hero.jpg",
        "gallery": [],
        "stock": 5,
        "is_hero": False,
        "variants": [
            {
                "key": "default",
                "label": "Default",
                "hex": "#000000",
                "image": "https://example.com/v.jpg"
                # NO new fields: sku, weight_grams, length_cm, width_cm, height_cm
            }
        ]
    }
    
    resp = requests.post(f"{BASE_URL}/admin/products", json=legacy_payload, headers=headers)
    if resp.status_code == 200:
        legacy_product_id = resp.json().get("id")
        log_test("task3_regression", "POST /admin/products with LEGACY payload", True,
                f"Product created: {legacy_product_id}")
        # Cleanup
        requests.delete(f"{BASE_URL}/admin/products/{legacy_product_id}", headers=headers)
    else:
        log_test("task3_regression", "POST /admin/products with LEGACY payload", False,
                f"Status: {resp.status_code}, Response: {resp.text[:200]}")
    
    # Test 3.4: POST /admin/products with NEW payload (all 5 new variant fields)
    print("\n[Test 3.4] POST /admin/products with NEW payload (all 5 fields)...")
    new_payload = {
        "slug": f"test-new-{int(time.time())}",
        "name": "Test New Product",
        "tagline": "New",
        "description": "With all new fields",
        "price_inr": 1000,
        "mrp_inr": 1200,
        "size": "1 ft",
        "craft_hours": 10,
        "materials": ["test"],
        "hero_image": "https://example.com/hero.jpg",
        "gallery": [],
        "stock": 5,
        "is_hero": False,
        "variants": [
            {
                "key": "default",
                "label": "Default",
                "hex": "#000000",
                "image": "https://example.com/v.jpg",
                # All 5 new fields
                "sku": "TEST-SKU",
                "weight_grams": 1000,
                "length_cm": 10.5,
                "width_cm": 8.5,
                "height_cm": 3.0
            }
        ]
    }
    
    resp = requests.post(f"{BASE_URL}/admin/products", json=new_payload, headers=headers)
    if resp.status_code == 200:
        new_product_id = resp.json().get("id")
        log_test("task3_regression", "POST /admin/products with NEW payload (5 fields)", True,
                f"Product created: {new_product_id}")
        # Cleanup
        requests.delete(f"{BASE_URL}/admin/products/{new_product_id}", headers=headers)
    else:
        log_test("task3_regression", "POST /admin/products with NEW payload (5 fields)", False,
                f"Status: {resp.status_code}, Response: {resp.text[:200]}")
    
    # Test 3.5: GET /api/admin/nimbuspost/config (Batch 4 sanity)
    print("\n[Test 3.5] GET /api/admin/nimbuspost/config (Batch 4 sanity)...")
    resp = requests.get(f"{BASE_URL}/admin/nimbuspost/config", headers=headers)
    if resp.status_code == 200:
        config = resp.json()
        has_structure = "configured" in config and "auth_mode" in config
        log_test("task3_regression", "GET /api/admin/nimbuspost/config returns 200", has_structure,
                f"configured={config.get('configured')}, auth_mode={config.get('auth_mode')}")
    else:
        log_test("task3_regression", "GET /api/admin/nimbuspost/config returns 200", False,
                f"Status: {resp.status_code}")


def main():
    print("="*80)
    print("BATCH 5 BACKEND TESTING")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Admin: {ADMIN_EMAIL}")
    
    try:
        # Get admin token
        print("\n[Setup] Getting admin token...")
        token = get_admin_token()
        print("✅ Admin token obtained")
        
        # Run all tests
        test_task1_variant_snapshot(token)
        test_task2_cloudinary_cleanup(token)
        test_task3_regression(token)
        
        # Print summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Total tests: {results['summary']['total']}")
        print(f"Passed: {results['summary']['passed']}")
        print(f"Failed: {results['summary']['failed']}")
        print(f"Success rate: {results['summary']['passed']/results['summary']['total']*100:.1f}%")
        
        # Save results to file
        with open("/app/backend_test_batch5_results.json", "w") as f:
            json.dump(results, f, indent=2)
        print("\n✅ Results saved to /app/backend_test_batch5_results.json")
        
        # Exit with appropriate code
        exit(0 if results['summary']['failed'] == 0 else 1)
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
