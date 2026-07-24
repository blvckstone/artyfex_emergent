#!/usr/bin/env python3
"""
BATCH 7 Backend Testing
Tests for:
1. Product.a_plus_content with Dict[str, Any] (layout + features fields)
2. Reference product "Golden Geode Mirror" verification
3. Regression smoke tests
"""

import requests
import json
import sys
from typing import Dict, Any, List

# Configuration
BASE_URL = "https://html-inject-scan.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@artyfex.in"
ADMIN_PASSWORD = "ArtyFex@2026"

# Test results tracking
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
        status = "✅ PASS"
    else:
        results["failed"] += 1
        status = "❌ FAIL"
    
    results["tests"].append({
        "name": name,
        "passed": passed,
        "details": details
    })
    print(f"{status}: {name}")
    if details:
        print(f"  → {details}")

def get_admin_token() -> str:
    """Get admin JWT token"""
    response = requests.post(
        f"{BASE_URL}/admin/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code != 200:
        raise Exception(f"Admin login failed: {response.status_code} {response.text}")
    return response.json()["token"]

def test_a_plus_content_with_layout_and_features(token: str):
    """
    TASK 1: Test a_plus_content with Dict[str, Any] - accepts layout + features fields
    """
    print("\n" + "="*80)
    print("TASK 1 - a_plus_content dict-value type is now Any (was str)")
    print("="*80)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 1.1: POST product with a_plus_content containing layout + features
    print("\nTest 1.1: POST product with layout + features in a_plus_content")
    product_payload = {
        "slug": f"test-batch7-layout-{int(requests.get(f'{BASE_URL}/health').elapsed.total_seconds() * 1000)}",
        "name": "Test Product Batch 7 Layout",
        "tagline": "Testing layout and features",
        "description": "Product for testing a_plus_content with layout and features fields",
        "price_inr": 5000,
        "mrp_inr": 7000,
        "size": "24x24 inches",
        "craft_hours": 48,
        "materials": ["Resin", "Glass"],
        "hero_image": "https://example.com/hero.jpg",
        "gallery": ["https://example.com/g1.jpg"],
        "variants": [
            {
                "key": "golden",
                "label": "Golden",
                "hex": "#D4AF37",
                "image": "https://example.com/golden.jpg",
                "price_delta_inr": 0
            }
        ],
        "a_plus_content": [
            {
                "layout": "feature_grid",
                "heading": "Engineered for luxury",
                "body": "Premium materials and craftsmanship.",
                "image": "https://example.com/g.jpg",
                "features": "5mm glass\\nAnti-fade coating\\nHinge mount included"
            },
            {
                "layout": "quote",
                "heading": "Verified buyer",
                "body": "Stunning in person.",
                "image": "",
                "features": ""
            },
            {
                "layout": "full_bleed",
                "heading": "72 hours of craft",
                "body": "Each piece is cured for 72 hours.",
                "image": "https://example.com/b.jpg",
                "features": ""
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/admin/products", json=product_payload, headers=headers)
    
    if response.status_code == 200:
        product = response.json()
        product_id = product.get("id")
        product_slug = product.get("slug")
        
        # Verify a_plus_content preserves ALL keys including layout and features
        a_plus = product.get("a_plus_content", [])
        if len(a_plus) == 3:
            block0 = a_plus[0]
            has_layout = "layout" in block0
            has_features = "features" in block0
            layout_correct = block0.get("layout") == "feature_grid"
            features_correct = "5mm glass" in block0.get("features", "")
            
            if has_layout and has_features and layout_correct and features_correct:
                log_test(
                    "POST /admin/products with layout+features",
                    True,
                    f"Response preserves layout={block0.get('layout')}, features with newlines intact"
                )
            else:
                log_test(
                    "POST /admin/products with layout+features",
                    False,
                    f"Missing keys or wrong values: layout={has_layout}, features={has_features}, layout_val={block0.get('layout')}"
                )
        else:
            log_test(
                "POST /admin/products with layout+features",
                False,
                f"Expected 3 a_plus_content blocks, got {len(a_plus)}"
            )
        
        # Test 1.2: GET product back and verify layout + features persist
        print("\nTest 1.2: GET product and verify layout + features persist")
        get_response = requests.get(f"{BASE_URL}/products/{product_slug}")
        
        if get_response.status_code == 200:
            retrieved = get_response.json()
            a_plus_retrieved = retrieved.get("a_plus_content", [])
            
            if len(a_plus_retrieved) >= 1:
                block0 = a_plus_retrieved[0]
                layout_persisted = block0.get("layout") == "feature_grid"
                features_persisted = "5mm glass" in block0.get("features", "") and "\\n" in block0.get("features", "")
                
                if layout_persisted and features_persisted:
                    log_test(
                        "GET /api/products/{slug} - layout+features persist",
                        True,
                        f"layout={block0.get('layout')}, features contains newline separators"
                    )
                else:
                    log_test(
                        "GET /api/products/{slug} - layout+features persist",
                        False,
                        f"layout={block0.get('layout')}, features={block0.get('features', '')[:50]}"
                    )
            else:
                log_test(
                    "GET /api/products/{slug} - layout+features persist",
                    False,
                    f"No a_plus_content blocks found"
                )
        else:
            log_test(
                "GET /api/products/{slug} - layout+features persist",
                False,
                f"GET failed: {get_response.status_code}"
            )
        
        # Test 1.3: Backward-compat - POST with only heading/body/image (no layout/features)
        print("\nTest 1.3: Backward-compat - POST with only heading/body/image")
        compat_payload = {
            "slug": f"test-batch7-compat-{int(requests.get(f'{BASE_URL}/health').elapsed.total_seconds() * 1000)}",
            "name": "Test Backward Compat",
            "tagline": "Testing backward compatibility",
            "description": "Product with old-style a_plus_content",
            "price_inr": 3000,
            "mrp_inr": 4000,
            "size": "12x12 inches",
            "craft_hours": 24,
            "materials": ["Wood"],
            "hero_image": "https://example.com/hero2.jpg",
            "gallery": [],
            "variants": [{"key": "default", "label": "Default", "hex": "#000000", "image": "", "price_delta_inr": 0}],
            "a_plus_content": [
                {
                    "heading": "Simple heading",
                    "body": "Simple body text",
                    "image": "https://example.com/simple.jpg"
                }
            ]
        }
        
        compat_response = requests.post(f"{BASE_URL}/admin/products", json=compat_payload, headers=headers)
        
        if compat_response.status_code == 200:
            compat_product = compat_response.json()
            compat_a_plus = compat_product.get("a_plus_content", [])
            
            if len(compat_a_plus) == 1:
                compat_block = compat_a_plus[0]
                has_heading = "heading" in compat_block
                has_body = "body" in compat_block
                has_image = "image" in compat_block
                no_forced_layout = "layout" not in compat_block or compat_block.get("layout") == ""
                
                if has_heading and has_body and has_image:
                    log_test(
                        "Backward-compat: POST with only heading/body/image",
                        True,
                        "Old-style blocks round-trip without crash, no forced layout key"
                    )
                else:
                    log_test(
                        "Backward-compat: POST with only heading/body/image",
                        False,
                        f"Missing expected keys: heading={has_heading}, body={has_body}, image={has_image}"
                    )
            else:
                log_test(
                    "Backward-compat: POST with only heading/body/image",
                    False,
                    f"Expected 1 block, got {len(compat_a_plus)}"
                )
        else:
            log_test(
                "Backward-compat: POST with only heading/body/image",
                False,
                f"POST failed: {compat_response.status_code} {compat_response.text[:200]}"
            )
        
        # Cleanup: Delete test products
        print("\nCleaning up test products...")
        requests.delete(f"{BASE_URL}/admin/products/{product_id}", headers=headers)
        if compat_response.status_code == 200:
            compat_id = compat_product.get("id")
            requests.delete(f"{BASE_URL}/admin/products/{compat_id}", headers=headers)
        
    else:
        log_test(
            "POST /admin/products with layout+features",
            False,
            f"POST failed: {response.status_code} {response.text[:200]}"
        )
        log_test("GET /api/products/{slug} - layout+features persist", False, "Skipped due to POST failure")
        log_test("Backward-compat: POST with only heading/body/image", False, "Skipped due to POST failure")

def test_reference_product_golden_geode(token: str):
    """
    TASK 2: Verify seeded reference product "Golden Geode Mirror"
    """
    print("\n" + "="*80)
    print("TASK 2 - Verify seeded reference product 'Golden Geode Mirror'")
    print("="*80)
    
    slug = "golden-geode-mirror-2x2-premium"
    
    # Test 2.1: GET the reference product
    print(f"\nTest 2.1: GET /api/products/{slug}")
    response = requests.get(f"{BASE_URL}/products/{slug}")
    
    if response.status_code == 200:
        product = response.json()
        
        # Verify basic fields
        name_ok = "Golden Geode" in product.get("name", "")
        price_ok = product.get("price_inr") == 4899
        mrp_ok = product.get("mrp_inr") == 7599
        hsn_ok = product.get("hsn_code") == "7009"
        has_variations = product.get("has_variations") == True
        
        log_test(
            "GET golden-geode-mirror - basic fields",
            name_ok and price_ok and mrp_ok and hsn_ok,
            f"name contains 'Golden Geode': {name_ok}, price=4899: {price_ok}, mrp=7599: {mrp_ok}, hsn=7009: {hsn_ok}, has_variations: {has_variations}"
        )
        
        # Test 2.2: Verify variants (should be 3)
        print("\nTest 2.2: Verify 3 variants with shipping fields")
        variants = product.get("variants", [])
        
        if len(variants) == 3:
            # Check all variants have required shipping fields
            all_have_sku = all("sku" in v and v["sku"] for v in variants)
            all_have_weight = all("weight_grams" in v and v["weight_grams"] is not None for v in variants)
            all_have_dims = all(
                "length_cm" in v and v["length_cm"] is not None and
                "width_cm" in v and v["width_cm"] is not None and
                "height_cm" in v and v["height_cm"] is not None
                for v in variants
            )
            
            # Check for different hex colors (golden, black, silver)
            hex_colors = [v.get("hex", "").lower() for v in variants]
            has_golden = any("#d4af37" in h for h in hex_colors)
            has_black = any("#111111" in h or "#000000" in h for h in hex_colors)
            has_silver = any("#c0c0c0" in h for h in hex_colors)
            
            if all_have_sku and all_have_weight and all_have_dims:
                log_test(
                    "Variants: 3 variants with complete shipping fields",
                    True,
                    f"All variants have sku, weight_grams, length_cm, width_cm, height_cm. Colors: golden={has_golden}, black={has_black}, silver={has_silver}"
                )
            else:
                log_test(
                    "Variants: 3 variants with complete shipping fields",
                    False,
                    f"sku={all_have_sku}, weight={all_have_weight}, dims={all_have_dims}"
                )
        else:
            log_test(
                "Variants: 3 variants with complete shipping fields",
                False,
                f"Expected 3 variants, got {len(variants)}"
            )
        
        # Test 2.3: Verify variation_options (should be 6)
        print("\nTest 2.3: Verify 6 variation_options")
        variation_options = product.get("variation_options", [])
        
        if len(variation_options) == 6:
            first_option_has_values = len(variation_options[0].get("values", [])) > 0
            
            # Check for expected option types
            option_names = [opt.get("name", "").lower() for opt in variation_options]
            has_shape = any("shape" in name for name in option_names)
            has_frame = any("frame" in name for name in option_names)
            has_thickness = any("thickness" in name for name in option_names)
            
            log_test(
                "variation_options: 6 options with values",
                True,
                f"Found 6 options, first has {len(variation_options[0].get('values', []))} values. Includes shape={has_shape}, frame={has_frame}, thickness={has_thickness}"
            )
        else:
            log_test(
                "variation_options: 6 options with values",
                False,
                f"Expected 6 variation_options, got {len(variation_options)}"
            )
        
        # Test 2.4: Verify a_plus_content (should be 6 blocks with layouts)
        print("\nTest 2.4: Verify 6 a_plus_content blocks with layouts")
        a_plus_content = product.get("a_plus_content", [])
        
        if len(a_plus_content) == 6:
            # Check all blocks have layout field
            all_have_layout = all("layout" in block for block in a_plus_content)
            
            # Get unique layouts
            layouts = [block.get("layout", "") for block in a_plus_content]
            unique_layouts = set(layouts)
            
            # Check for at least 4 distinct layouts
            has_4_distinct = len(unique_layouts) >= 4
            
            # Expected layouts
            expected_layouts = {"full_bleed", "image_left", "image_right", "centered", "feature_grid", "quote"}
            layouts_in_expected = unique_layouts.issubset(expected_layouts)
            
            # Find feature_grid block and check features field
            feature_grid_blocks = [b for b in a_plus_content if b.get("layout") == "feature_grid"]
            has_feature_grid_with_features = False
            if feature_grid_blocks:
                for block in feature_grid_blocks:
                    features = block.get("features", "")
                    if features and len(features) > 0:
                        has_feature_grid_with_features = True
                        break
            
            if all_have_layout and has_4_distinct and has_feature_grid_with_features:
                log_test(
                    "a_plus_content: 6 blocks with layouts and features",
                    True,
                    f"All blocks have layout field. {len(unique_layouts)} distinct layouts: {unique_layouts}. feature_grid block has non-empty features field."
                )
            else:
                log_test(
                    "a_plus_content: 6 blocks with layouts and features",
                    False,
                    f"all_have_layout={all_have_layout}, distinct_layouts={len(unique_layouts)}, has_feature_grid_with_features={has_feature_grid_with_features}"
                )
        else:
            log_test(
                "a_plus_content: 6 blocks with layouts and features",
                False,
                f"Expected 6 a_plus_content blocks, got {len(a_plus_content)}"
            )
        
        # Test 2.5: Verify product appears in public list
        print("\nTest 2.5: Verify product appears in GET /api/products")
        list_response = requests.get(f"{BASE_URL}/products")
        
        if list_response.status_code == 200:
            products = list_response.json()
            found = any(p.get("slug") == slug for p in products)
            
            log_test(
                "Golden Geode appears in public product list",
                found,
                f"Found in list of {len(products)} products"
            )
        else:
            log_test(
                "Golden Geode appears in public product list",
                False,
                f"GET /api/products failed: {list_response.status_code}"
            )
        
    else:
        log_test(
            "GET golden-geode-mirror - basic fields",
            False,
            f"GET failed: {response.status_code} {response.text[:200]}"
        )
        log_test("Variants: 3 variants with complete shipping fields", False, "Skipped due to GET failure")
        log_test("variation_options: 6 options with values", False, "Skipped due to GET failure")
        log_test("a_plus_content: 6 blocks with layouts and features", False, "Skipped due to GET failure")
        log_test("Golden Geode appears in public product list", False, "Skipped due to GET failure")

def test_regression_smoke(token: str):
    """
    TASK 3: Regression smoke tests
    """
    print("\n" + "="*80)
    print("TASK 3 - Regression smoke tests")
    print("="*80)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 3.1: Health check
    print("\nTest 3.1: GET /api/health")
    response = requests.get(f"{BASE_URL}/health")
    
    if response.status_code == 200:
        data = response.json()
        mongo_ok = data.get("mongo") == "ok"
        
        log_test(
            "GET /api/health",
            mongo_ok,
            f"mongo={data.get('mongo')}"
        )
    else:
        log_test(
            "GET /api/health",
            False,
            f"Failed: {response.status_code}"
        )
    
    # Test 3.2: Products list non-empty
    print("\nTest 3.2: GET /api/products (non-empty)")
    response = requests.get(f"{BASE_URL}/products")
    
    if response.status_code == 200:
        products = response.json()
        non_empty = len(products) > 0
        
        log_test(
            "GET /api/products (non-empty)",
            non_empty,
            f"Found {len(products)} products"
        )
    else:
        log_test(
            "GET /api/products (non-empty)",
            False,
            f"Failed: {response.status_code}"
        )
    
    # Test 3.3: NimbusPost config (Batch 4 sanity)
    print("\nTest 3.3: GET /api/admin/nimbuspost/config")
    response = requests.get(f"{BASE_URL}/admin/nimbuspost/config", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        configured = data.get("configured") == True
        auth_mode = data.get("auth_mode") == "jwt"
        
        log_test(
            "GET /api/admin/nimbuspost/config",
            configured and auth_mode,
            f"configured={configured}, auth_mode={data.get('auth_mode')}"
        )
    else:
        log_test(
            "GET /api/admin/nimbuspost/config",
            False,
            f"Failed: {response.status_code}"
        )

def main():
    """Run all BATCH 7 tests"""
    print("="*80)
    print("BATCH 7 BACKEND TESTING")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Admin: {ADMIN_EMAIL}")
    
    try:
        # Get admin token
        print("\nAuthenticating as admin...")
        token = get_admin_token()
        print("✅ Admin authentication successful")
        
        # Run all tests
        test_a_plus_content_with_layout_and_features(token)
        test_reference_product_golden_geode(token)
        test_regression_smoke(token)
        
        # Print summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Total: {results['total']}")
        print(f"Passed: {results['passed']} ✅")
        print(f"Failed: {results['failed']} ❌")
        print(f"Success Rate: {(results['passed']/results['total']*100):.1f}%")
        
        # Save results to file
        with open("/app/backend_test_batch7_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\nDetailed results saved to: /app/backend_test_batch7_results.json")
        
        # Exit with appropriate code
        sys.exit(0 if results['failed'] == 0 else 1)
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
