#!/usr/bin/env python3
"""
Batch 6 Backend Testing
Tests ONLY the 3 Batch 6 backend tasks:
1. Bug #5 verification: variant shipping fields round-trip through PUT/GET
2. Product.a_plus_content field CRUD
3. OrderItem.notes round-trip (gift-wrap recipient + message)

DO NOT re-test earlier batches (1-5) or Task 7 (NimbusPost).
"""

import requests
import json
import random
import string
from typing import Dict, Any

# Backend URL from frontend/.env
BASE_URL = "https://html-inject-scan.preview.emergentagent.com/api"

# Admin credentials from /app/memory/test_credentials.md
ADMIN_EMAIL = "admin@artyfex.in"
ADMIN_PASSWORD = "ArtyFex@2026"

def random_slug():
    """Generate random slug for test products"""
    return f"test-batch6-{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}"

def admin_login() -> str:
    """Login as admin and return JWT token"""
    resp = requests.post(f"{BASE_URL}/admin/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert resp.status_code == 200, f"Admin login failed: {resp.status_code} {resp.text}"
    return resp.json()["token"]

def test_task1_variant_shipping_fields_roundtrip():
    """
    TASK 1 — Bug #5 verification: variant shipping fields ROUND-TRIP through PUT/GET
    
    The Batch 5 backend passed but the fields were being DROPPED at the frontend map layer.
    The fix is in the frontend, but let's verify the backend still round-trips them cleanly.
    """
    print("\n" + "="*80)
    print("TASK 1 — Bug #5 verification: variant shipping fields ROUND-TRIP")
    print("="*80)
    
    token = admin_login()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 1.1: POST /admin/products with a variant containing ALL 5 new fields
    print("\n[Test 1.1] POST /admin/products with variant containing all 5 new fields...")
    slug = random_slug()
    product_payload = {
        "slug": slug,
        "name": "Test Batch 6 Product",
        "tagline": "test",
        "description": "test",
        "price_inr": 1000,
        "mrp_inr": 1200,
        "size": "2 ft",
        "craft_hours": 24,
        "materials": ["resin"],
        "hero_image": "https://example.com/h.jpg",
        "gallery": [],
        "stock": 5,
        "is_hero": False,
        "has_variations": True,
        "variants": [{
            "key": "large",
            "label": "Large",
            "hex": "#D4AF37",
            "image": "https://ex.com/v.jpg",
            "size": "3 ft",
            "stock": 3,
            "price_inr": 1500,
            "mrp_inr": 1800,
            "sku": "VAR-LARGE-B6",
            "weight_grams": 8500,
            "length_cm": 90,
            "width_cm": 60,
            "height_cm": 5
        }]
    }
    
    resp = requests.post(f"{BASE_URL}/admin/products", json=product_payload, headers=headers)
    assert resp.status_code == 200, f"POST /admin/products failed: {resp.status_code} {resp.text}"
    product = resp.json()
    product_id = product["id"]
    
    # Verify response has all 5 fields with EXACT values
    variant = product["variants"][0]
    assert variant["sku"] == "VAR-LARGE-B6", f"SKU mismatch: {variant.get('sku')}"
    assert variant["weight_grams"] == 8500, f"weight_grams mismatch: {variant.get('weight_grams')}"
    assert variant["length_cm"] == 90, f"length_cm mismatch: {variant.get('length_cm')}"
    assert variant["width_cm"] == 60, f"width_cm mismatch: {variant.get('width_cm')}"
    assert variant["height_cm"] == 5, f"height_cm mismatch: {variant.get('height_cm')}"
    print(f"✅ POST response has all 5 fields: sku={variant['sku']}, weight={variant['weight_grams']}g, dims={variant['length_cm']}×{variant['width_cm']}×{variant['height_cm']}cm")
    
    # Test 1.2: GET /api/products/{slug} → variants[0] MUST have all 5 fields intact
    print(f"\n[Test 1.2] GET /api/products/{slug} → verify all 5 fields intact...")
    resp = requests.get(f"{BASE_URL}/products/{slug}")
    assert resp.status_code == 200, f"GET /api/products/{slug} failed: {resp.status_code} {resp.text}"
    product = resp.json()
    variant = product["variants"][0]
    
    assert variant["sku"] == "VAR-LARGE-B6", f"SKU lost after GET: {variant.get('sku')}"
    assert variant["weight_grams"] == 8500, f"weight_grams lost after GET: {variant.get('weight_grams')}"
    assert variant["length_cm"] == 90, f"length_cm lost after GET: {variant.get('length_cm')}"
    assert variant["width_cm"] == 60, f"width_cm lost after GET: {variant.get('width_cm')}"
    assert variant["height_cm"] == 5, f"height_cm lost after GET: {variant.get('height_cm')}"
    print(f"✅ GET response has all 5 fields intact")
    
    # Test 1.3: PUT /admin/products/{id} with weight_grams changed to 9500
    print(f"\n[Test 1.3] PUT /admin/products/{product_id} with weight_grams changed to 9500...")
    product["variants"][0]["weight_grams"] = 9500
    resp = requests.put(f"{BASE_URL}/admin/products/{product_id}", json=product, headers=headers)
    assert resp.status_code == 200, f"PUT /admin/products/{product_id} failed: {resp.status_code} {resp.text}"
    updated_product = resp.json()
    
    assert updated_product["variants"][0]["weight_grams"] == 9500, f"weight_grams not updated: {updated_product['variants'][0].get('weight_grams')}"
    print(f"✅ PUT response has updated weight_grams=9500")
    
    # Cleanup
    print(f"\n[Cleanup] DELETE /admin/products/{product_id}...")
    resp = requests.delete(f"{BASE_URL}/admin/products/{product_id}", headers=headers)
    assert resp.status_code == 200, f"DELETE failed: {resp.status_code} {resp.text}"
    print(f"✅ Test product deleted")
    
    print("\n✅ TASK 1 PASSED: Variant shipping fields round-trip correctly through POST → GET → PUT")

def test_task2_a_plus_content_crud():
    """
    TASK 2 — Product.a_plus_content field CRUD
    
    New field added to both Product and ProductIn models.
    """
    print("\n" + "="*80)
    print("TASK 2 — Product.a_plus_content field CRUD")
    print("="*80)
    
    token = admin_login()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 2.1: POST /admin/products with a_plus_content
    print("\n[Test 2.1] POST /admin/products with a_plus_content (2 blocks)...")
    slug = random_slug()
    product_payload = {
        "slug": slug,
        "name": "Test A+ Content Product",
        "tagline": "test",
        "description": "test",
        "price_inr": 2000,
        "mrp_inr": 2500,
        "size": "2 ft",
        "craft_hours": 24,
        "materials": ["resin"],
        "hero_image": "https://example.com/h.jpg",
        "gallery": [],
        "stock": 5,
        "is_hero": False,
        "has_variations": False,
        "variants": [],  # Required field even when has_variations=False
        "a_plus_content": [
            {
                "heading": "Hand-poured resin",
                "body": "Each mirror is cured for 72 hours",
                "image": "https://ex.com/a.jpg"
            },
            {
                "heading": "Ships in double-walled crate",
                "body": "",
                "image": ""
            }
        ]
    }
    
    resp = requests.post(f"{BASE_URL}/admin/products", json=product_payload, headers=headers)
    assert resp.status_code == 200, f"POST /admin/products failed: {resp.status_code} {resp.text}"
    product = resp.json()
    product_id = product["id"]
    
    # Verify response has a_plus_content with 2 blocks
    assert "a_plus_content" in product, "a_plus_content field missing in response"
    assert len(product["a_plus_content"]) == 2, f"Expected 2 blocks, got {len(product['a_plus_content'])}"
    assert product["a_plus_content"][0]["heading"] == "Hand-poured resin", "First block heading mismatch"
    assert product["a_plus_content"][1]["heading"] == "Ships in double-walled crate", "Second block heading mismatch"
    print(f"✅ POST response has a_plus_content with 2 blocks")
    
    # Test 2.2: GET /api/products/{slug} → a_plus_content still present
    print(f"\n[Test 2.2] GET /api/products/{slug} → verify a_plus_content persisted...")
    resp = requests.get(f"{BASE_URL}/products/{slug}")
    assert resp.status_code == 200, f"GET /api/products/{slug} failed: {resp.status_code} {resp.text}"
    product = resp.json()
    
    assert "a_plus_content" in product, "a_plus_content field missing after GET"
    assert len(product["a_plus_content"]) == 2, f"Expected 2 blocks after GET, got {len(product['a_plus_content'])}"
    print(f"✅ GET response has a_plus_content with 2 blocks intact")
    
    # Test 2.3: POST /admin/products WITHOUT a_plus_content → 200 (backward-compat)
    print("\n[Test 2.3] POST /admin/products WITHOUT a_plus_content (backward-compat)...")
    slug2 = random_slug()
    product_payload2 = {
        "slug": slug2,
        "name": "Test No A+ Content",
        "tagline": "test",
        "description": "test",
        "price_inr": 1000,
        "mrp_inr": 1200,
        "size": "2 ft",
        "craft_hours": 24,
        "materials": ["resin"],
        "hero_image": "https://example.com/h.jpg",
        "gallery": [],
        "stock": 5,
        "is_hero": False,
        "has_variations": False,
        "variants": []  # Required field
        # NO a_plus_content field
    }
    
    resp = requests.post(f"{BASE_URL}/admin/products", json=product_payload2, headers=headers)
    assert resp.status_code == 200, f"POST without a_plus_content failed: {resp.status_code} {resp.text}"
    product2 = resp.json()
    product2_id = product2["id"]
    
    # Response should have a_plus_content = [] (default)
    assert "a_plus_content" in product2, "a_plus_content field missing (should default to [])"
    assert product2["a_plus_content"] == [], f"Expected empty list, got {product2['a_plus_content']}"
    print(f"✅ POST without a_plus_content succeeded, defaults to []")
    
    # Test 2.4: PUT /admin/products/{id} with empty a_plus_content: []
    print(f"\n[Test 2.4] PUT /admin/products/{product_id} with empty a_plus_content=[]...")
    product["a_plus_content"] = []
    resp = requests.put(f"{BASE_URL}/admin/products/{product_id}", json=product, headers=headers)
    assert resp.status_code == 200, f"PUT with empty a_plus_content failed: {resp.status_code} {resp.text}"
    updated_product = resp.json()
    
    assert updated_product["a_plus_content"] == [], f"Expected empty list after PUT, got {updated_product['a_plus_content']}"
    print(f"✅ PUT with empty a_plus_content succeeded")
    
    # Cleanup
    print(f"\n[Cleanup] DELETE test products...")
    requests.delete(f"{BASE_URL}/admin/products/{product_id}", headers=headers)
    requests.delete(f"{BASE_URL}/admin/products/{product2_id}", headers=headers)
    print(f"✅ Test products deleted")
    
    print("\n✅ TASK 2 PASSED: Product.a_plus_content field CRUD working correctly")

def test_task3_orderitem_notes_roundtrip():
    """
    TASK 3 — OrderItem.notes round-trip (gift-wrap recipient + message)
    
    New optional field on OrderItem.
    """
    print("\n" + "="*80)
    print("TASK 3 — OrderItem.notes round-trip (gift-wrap recipient + message)")
    print("="*80)
    
    token = admin_login()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Step 1: Get an existing product with a variant
    print("\n[Step 1] GET /api/products → pick a product with variant...")
    resp = requests.get(f"{BASE_URL}/products")
    assert resp.status_code == 200, f"GET /api/products failed: {resp.status_code} {resp.text}"
    products = resp.json()
    assert len(products) > 0, "No products found in database"
    
    # Find a product with variants
    product = None
    for p in products:
        if p.get("has_variations") and len(p.get("variants", [])) > 0:
            product = p
            break
    
    if not product:
        # Use first product even without variants
        product = products[0]
    
    product_id = product["id"]
    variant_key = product["variants"][0]["key"] if product.get("variants") else None
    print(f"✅ Using product: {product['name']} (id={product_id}, variant_key={variant_key})")
    
    # Test 3.1: POST /api/orders/create with notes
    print("\n[Test 3.1] POST /api/orders/create with item containing notes...")
    order_payload = {
        "customer": {
            "name": "Test Customer Batch6",
            "email": f"test-batch6-{random.randint(1000,9999)}@example.com",
            "phone": "9876543210",
            "address": "123 Test Street",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400001",
            "country": "India"
        },
        "items": [{
            "product_id": product_id,
            "variant_key": variant_key,
            "quantity": 1,
            "notes": {
                "gift_recipient": "Aarav",
                "gift_message": "Happy birthday!"
            }
        }],
        "payment_method": "cod",
        "subtotal_inr": product["price_inr"],
        "discount_inr": 0,
        "shipping_inr": 0,
        "total_inr": product["price_inr"]
    }
    
    resp = requests.post(f"{BASE_URL}/orders", json=order_payload)
    assert resp.status_code == 200, f"POST /api/orders/create failed: {resp.status_code} {resp.text}"
    order_response = resp.json()
    
    # Handle both response formats: {"order": {...}} or direct order object
    if "order" in order_response:
        order = order_response["order"]
    else:
        order = order_response
    
    order_number = order["order_number"]
    print(f"✅ Order created: {order_number}")
    
    # Test 3.2: GET /api/admin/orders → verify notes has BOTH keys
    print(f"\n[Test 3.2] GET /api/admin/orders → verify order has notes with both keys...")
    resp = requests.get(f"{BASE_URL}/admin/orders", headers=headers)
    assert resp.status_code == 200, f"GET /api/admin/orders failed: {resp.status_code} {resp.text}"
    orders = resp.json()
    
    # Find our order
    our_order = None
    for o in orders:
        if o["order_number"] == order_number:
            our_order = o
            break
    
    assert our_order is not None, f"Order {order_number} not found in admin orders list"
    
    # Verify notes field
    item = our_order["items"][0]
    assert "notes" in item, "notes field missing from OrderItem"
    assert "gift_recipient" in item["notes"], "gift_recipient missing from notes"
    assert "gift_message" in item["notes"], "gift_message missing from notes"
    assert item["notes"]["gift_recipient"] == "Aarav", f"gift_recipient mismatch: {item['notes']['gift_recipient']}"
    assert item["notes"]["gift_message"] == "Happy birthday!", f"gift_message mismatch: {item['notes']['gift_message']}"
    print(f"✅ Order item has notes with both keys: gift_recipient='{item['notes']['gift_recipient']}', gift_message='{item['notes']['gift_message']}'")
    
    # Test 3.3: POST another order WITHOUT notes → 200, order.items[0].notes == {}
    print("\n[Test 3.3] POST /api/orders/create WITHOUT notes (backward-compat)...")
    order_payload2 = {
        "customer": {
            "name": "Test Customer Batch6 No Notes",
            "email": f"test-batch6-{random.randint(1000,9999)}@example.com",
            "phone": "9876543210",
            "address": "123 Test Street",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400001",
            "country": "India"
        },
        "items": [{
            "product_id": product_id,
            "variant_key": variant_key,
            "quantity": 1
            # NO notes field
        }],
        "payment_method": "cod",
        "subtotal_inr": product["price_inr"],
        "discount_inr": 0,
        "shipping_inr": 0,
        "total_inr": product["price_inr"]
    }
    
    resp = requests.post(f"{BASE_URL}/orders", json=order_payload2)
    assert resp.status_code == 200, f"POST without notes failed: {resp.status_code} {resp.text}"
    order_response2 = resp.json()
    
    # Handle both response formats
    if "order" in order_response2:
        order2 = order_response2["order"]
    else:
        order2 = order_response2
    
    # Verify notes defaults to {}
    item2 = order2["items"][0]
    assert "notes" in item2, "notes field missing (should default to {})"
    assert item2["notes"] == {}, f"Expected empty dict, got {item2['notes']}"
    print(f"✅ Order without notes succeeded, notes defaults to {{}}")
    
    print("\n✅ TASK 3 PASSED: OrderItem.notes round-trip working correctly")

def test_regression_smoke():
    """
    REGRESSION SMOKE (quick):
    - GET /api/health → 200 mongo=ok
    - GET /api/products (public) → 200 non-empty
    - GET /api/admin/nimbuspost/config (admin) → 200 configured=true (Batch 4 sanity)
    """
    print("\n" + "="*80)
    print("REGRESSION SMOKE CHECK")
    print("="*80)
    
    # Test: GET /api/health
    print("\n[Smoke 1] GET /api/health...")
    resp = requests.get(f"{BASE_URL}/health")
    assert resp.status_code == 200, f"Health check failed: {resp.status_code} {resp.text}"
    health = resp.json()
    assert health.get("mongo") == "ok", f"MongoDB not ok: {health}"
    print(f"✅ Health check passed: mongo=ok")
    
    # Test: GET /api/products
    print("\n[Smoke 2] GET /api/products (public)...")
    resp = requests.get(f"{BASE_URL}/products")
    assert resp.status_code == 200, f"GET /api/products failed: {resp.status_code} {resp.text}"
    products = resp.json()
    assert len(products) > 0, "No products found"
    print(f"✅ GET /api/products returned {len(products)} products")
    
    # Test: GET /api/admin/nimbuspost/config (Batch 4 sanity)
    print("\n[Smoke 3] GET /api/admin/nimbuspost/config (Batch 4 sanity)...")
    token = admin_login()
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/admin/nimbuspost/config", headers=headers)
    assert resp.status_code == 200, f"GET /api/admin/nimbuspost/config failed: {resp.status_code} {resp.text}"
    config = resp.json()
    assert config.get("configured") == True, f"NimbusPost not configured: {config}"
    print(f"✅ NimbusPost config: configured={config['configured']}")
    
    print("\n✅ REGRESSION SMOKE PASSED")

def main():
    """Run all Batch 6 backend tests"""
    print("\n" + "="*80)
    print("BATCH 6 BACKEND TESTING")
    print("Testing ONLY the 3 Batch 6 backend tasks")
    print("DO NOT re-test earlier batches (1-5) or Task 7 (NimbusPost)")
    print("="*80)
    
    results = {
        "batch": "Batch 6",
        "total_tests": 0,
        "passed": 0,
        "failed": 0,
        "tasks": []
    }
    
    # Task 1: Variant shipping fields round-trip
    try:
        test_task1_variant_shipping_fields_roundtrip()
        results["tasks"].append({"task": "Task 1 - Variant shipping fields round-trip", "status": "PASSED"})
        results["passed"] += 1
    except Exception as e:
        print(f"\n❌ TASK 1 FAILED: {e}")
        results["tasks"].append({"task": "Task 1 - Variant shipping fields round-trip", "status": "FAILED", "error": str(e)})
        results["failed"] += 1
    results["total_tests"] += 1
    
    # Task 2: Product.a_plus_content field CRUD
    try:
        test_task2_a_plus_content_crud()
        results["tasks"].append({"task": "Task 2 - Product.a_plus_content CRUD", "status": "PASSED"})
        results["passed"] += 1
    except Exception as e:
        print(f"\n❌ TASK 2 FAILED: {e}")
        results["tasks"].append({"task": "Task 2 - Product.a_plus_content CRUD", "status": "FAILED", "error": str(e)})
        results["failed"] += 1
    results["total_tests"] += 1
    
    # Task 3: OrderItem.notes round-trip
    try:
        test_task3_orderitem_notes_roundtrip()
        results["tasks"].append({"task": "Task 3 - OrderItem.notes round-trip", "status": "PASSED"})
        results["passed"] += 1
    except Exception as e:
        print(f"\n❌ TASK 3 FAILED: {e}")
        results["tasks"].append({"task": "Task 3 - OrderItem.notes round-trip", "status": "FAILED", "error": str(e)})
        results["failed"] += 1
    results["total_tests"] += 1
    
    # Regression smoke
    try:
        test_regression_smoke()
        results["tasks"].append({"task": "Regression Smoke", "status": "PASSED"})
        results["passed"] += 1
    except Exception as e:
        print(f"\n❌ REGRESSION SMOKE FAILED: {e}")
        results["tasks"].append({"task": "Regression Smoke", "status": "FAILED", "error": str(e)})
        results["failed"] += 1
    results["total_tests"] += 1
    
    # Summary
    print("\n" + "="*80)
    print("BATCH 6 BACKEND TESTING SUMMARY")
    print("="*80)
    print(f"Total tests: {results['total_tests']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print("\nTask Results:")
    for task in results["tasks"]:
        status_icon = "✅" if task["status"] == "PASSED" else "❌"
        print(f"{status_icon} {task['task']}: {task['status']}")
        if "error" in task:
            print(f"   Error: {task['error']}")
    
    # Save results to JSON
    with open("/app/backend_test_batch6_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to /app/backend_test_batch6_results.json")
    
    if results["failed"] > 0:
        print("\n❌ SOME TESTS FAILED")
        exit(1)
    else:
        print("\n✅ ALL TESTS PASSED")
        exit(0)

if __name__ == "__main__":
    main()
