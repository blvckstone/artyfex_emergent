#!/usr/bin/env python3
"""
ArtyFex Phase A Backend Testing - Comprehensive Test Suite
Tests Homepage CMS, Shipping Settings + Calc, Order Tracking, and Backward Compat
"""

import requests
import json
import time
from datetime import datetime, timezone
import uuid

# Configuration
BACKEND_URL = "http://localhost:8001/api"

# Admin credentials
ADMIN_EMAIL = "admin@artyfex.in"
ADMIN_PASSWORD = "ArtyFex@2026"

# Test results tracking
test_results = []
admin_token = None


def log_test(section, test_name, passed, details=""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    result = {
        "section": section,
        "test": test_name,
        "passed": passed,
        "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    test_results.append(result)
    print(f"{status} | {section} | {test_name}")
    if details and not passed:
        print(f"   Details: {details}")


def print_section(title):
    """Print section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")


def admin_login():
    """Login as admin and get token"""
    global admin_token
    print_section("ADMIN LOGIN")
    try:
        resp = requests.post(f"{BACKEND_URL}/admin/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }, timeout=10)
        if resp.status_code == 200:
            admin_token = resp.json()["token"]
            log_test("Setup", "Admin login", True, f"Token: {admin_token[:20]}...")
            return True
        else:
            log_test("Setup", "Admin login", False, f"Status {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        log_test("Setup", "Admin login", False, str(e))
        return False


def test_task_1_homepage_cms():
    """Task 1 - Homepage CMS endpoints"""
    print_section("TASK 1: Homepage CMS")
    
    # Test 1.1: GET /api/homepage (public, no auth)
    try:
        resp = requests.get(f"{BACKEND_URL}/homepage", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            # Verify structure
            has_keys = all(k in data for k in ['announcement', 'hero', 'sale_banner', 'custom_css'])
            # Verify default values exist
            announcement_text = data.get('announcement', {}).get('text', '')
            hero_headline = data.get('hero', {}).get('headline_line_1', '')
            
            passed = has_keys and len(announcement_text) > 0 and len(hero_headline) > 0
            details = f"Keys present: {has_keys}, announcement.text: '{announcement_text[:50]}...', hero.headline_line_1: '{hero_headline[:50]}...'"
            log_test("Task 1", "GET /api/homepage (public) → 200 with defaults", passed, details)
        else:
            log_test("Task 1", "GET /api/homepage (public) → 200 with defaults", False,
                    f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    except Exception as e:
        log_test("Task 1", "GET /api/homepage (public) → 200 with defaults", False, str(e))
    
    # Test 1.2: GET /api/admin/homepage without auth → 401
    try:
        resp = requests.get(f"{BACKEND_URL}/admin/homepage", timeout=10)
        passed = resp.status_code == 401
        log_test("Task 1", "GET /api/admin/homepage without token → 401", passed,
                f"Status: {resp.status_code}")
    except Exception as e:
        log_test("Task 1", "GET /api/admin/homepage without token → 401", False, str(e))
    
    if not admin_token:
        log_test("Task 1", "Admin homepage tests", False, "No admin token available")
        return
    
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Test 1.3: GET /api/admin/homepage with auth → 200
    try:
        resp = requests.get(f"{BACKEND_URL}/admin/homepage", headers=admin_headers, timeout=10)
        passed = resp.status_code == 200
        log_test("Task 1", "GET /api/admin/homepage with token → 200", passed,
                f"Status: {resp.status_code}")
    except Exception as e:
        log_test("Task 1", "GET /api/admin/homepage with token → 200", False, str(e))
    
    # Test 1.4: PATCH /api/admin/homepage - update announcement and hero
    try:
        update_payload = {
            "announcement": {
                "enabled": True,
                "text": "TEST ANNOUNCEMENT - Phase A Testing",
                "link": "/shop",
                "bg_color": "#1a1208",
                "text_color": "#f5efdf"
            },
            "hero": {
                "headline_line_1": "TEST HEADLINE",
                "headline_italic": "Phase A",
                "headline_line_2": "Testing Suite",
                "subheadline": "Automated backend verification",
                "cta_primary_text": "Test Shop",
                "cta_primary_link": "/shop",
                "cta_secondary_text": "Test B2B",
                "cta_secondary_link": "/b2b",
                "bg_image": "https://example.com/test.jpg",
                "bg_overlay_opacity": 0.4,
                "text_color": "#f5efdf",
                "accent_color": "#D4AF37",
                "stats": [
                    {"k": "100%", "v": "test stat"}
                ]
            },
            "sale_banner": {
                "enabled": False,
                "title": "Test Sale",
                "subtitle": "Test subtitle",
                "cta_text": "Test",
                "cta_link": "/shop",
                "bg_color": "#1a1208",
                "text_color": "#f5efdf",
                "accent_color": "#D4AF37",
                "image": ""
            },
            "custom_css": "/* test css */"
        }
        
        resp = requests.patch(f"{BACKEND_URL}/admin/homepage", 
                            headers=admin_headers,
                            json=update_payload,
                            timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            # Verify response echoes the update
            announcement_match = data.get('announcement', {}).get('text') == update_payload['announcement']['text']
            hero_match = data.get('hero', {}).get('headline_italic') == update_payload['hero']['headline_italic']
            passed = announcement_match and hero_match
            details = f"announcement.text match: {announcement_match}, hero.headline_italic match: {hero_match}"
            log_test("Task 1", "PATCH /api/admin/homepage → 200 with updated values", passed, details)
        else:
            log_test("Task 1", "PATCH /api/admin/homepage → 200 with updated values", False,
                    f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    except Exception as e:
        log_test("Task 1", "PATCH /api/admin/homepage → 200 with updated values", False, str(e))
    
    # Test 1.5: GET /api/homepage again to verify persistence
    try:
        resp = requests.get(f"{BACKEND_URL}/homepage", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            announcement_persisted = data.get('announcement', {}).get('text') == "TEST ANNOUNCEMENT - Phase A Testing"
            hero_persisted = data.get('hero', {}).get('headline_italic') == "Phase A"
            passed = announcement_persisted and hero_persisted
            details = f"announcement persisted: {announcement_persisted}, hero persisted: {hero_persisted}"
            log_test("Task 1", "GET /api/homepage shows updated values", passed, details)
        else:
            log_test("Task 1", "GET /api/homepage shows updated values", False,
                    f"Status: {resp.status_code}")
    except Exception as e:
        log_test("Task 1", "GET /api/homepage shows updated values", False, str(e))


def test_task_2_shipping():
    """Task 2 - Shipping settings + calc endpoint"""
    print_section("TASK 2: Shipping Settings + Calc")
    
    if not admin_token:
        log_test("Task 2", "Shipping tests", False, "No admin token available")
        return
    
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Test 2.1: GET /api/admin/shipping-settings
    try:
        resp = requests.get(f"{BACKEND_URL}/admin/shipping-settings", headers=admin_headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            required_keys = ['method', 'flat_rate_inr', 'free_shipping_above_inr', 'zone_rates', 
                           'distance_base_fee_inr', 'distance_per_km_inr', 'distance_bands', 'origin_state']
            has_keys = all(k in data for k in required_keys)
            passed = has_keys
            details = f"Has all required keys: {has_keys}, method: {data.get('method')}"
            log_test("Task 2", "GET /api/admin/shipping-settings → 200 with structure", passed, details)
        else:
            log_test("Task 2", "GET /api/admin/shipping-settings → 200 with structure", False,
                    f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    except Exception as e:
        log_test("Task 2", "GET /api/admin/shipping-settings → 200 with structure", False, str(e))
    
    # Test 2.2: PATCH with invalid method → 400
    try:
        resp = requests.patch(f"{BACKEND_URL}/admin/shipping-settings",
                            headers=admin_headers,
                            json={"method": "invalid"},
                            timeout=10)
        passed = resp.status_code == 400
        log_test("Task 2", "PATCH shipping-settings with invalid method → 400", passed,
                f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    except Exception as e:
        log_test("Task 2", "PATCH shipping-settings with invalid method → 400", False, str(e))
    
    # Test 2.3: Flat method - subtotal below free threshold
    try:
        resp = requests.post(f"{BACKEND_URL}/shipping/calculate",
                           json={
                               "subtotal_inr": 10000,
                               "state": "Maharashtra",
                               "pincode": "400001",
                               "country": "India"
                           },
                           timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            # Should return flat_rate_inr (default 1499), not free
            passed = data.get('method') == 'flat' and data.get('shipping_inr') > 0 and data.get('free_shipping_applied') == False
            details = f"method: {data.get('method')}, shipping_inr: {data.get('shipping_inr')}, free_shipping_applied: {data.get('free_shipping_applied')}"
            log_test("Task 2", "Flat method, subtotal=10k → flat_rate_inr, not free", passed, details)
        else:
            log_test("Task 2", "Flat method, subtotal=10k → flat_rate_inr, not free", False,
                    f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    except Exception as e:
        log_test("Task 2", "Flat method, subtotal=10k → flat_rate_inr, not free", False, str(e))
    
    # Test 2.4: Flat method - subtotal above free threshold (30k > 25k default)
    try:
        resp = requests.post(f"{BACKEND_URL}/shipping/calculate",
                           json={
                               "subtotal_inr": 30000,
                               "state": "Maharashtra",
                               "pincode": "400001",
                               "country": "India"
                           },
                           timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            passed = data.get('shipping_inr') == 0 and data.get('free_shipping_applied') == True
            details = f"shipping_inr: {data.get('shipping_inr')}, free_shipping_applied: {data.get('free_shipping_applied')}"
            log_test("Task 2", "Flat method, subtotal=30k → free shipping", passed, details)
        else:
            log_test("Task 2", "Flat method, subtotal=30k → free shipping", False,
                    f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    except Exception as e:
        log_test("Task 2", "Flat method, subtotal=30k → free shipping", False, str(e))
    
    # Test 2.5: Set method to zone
    try:
        # Get current settings first
        resp = requests.get(f"{BACKEND_URL}/admin/shipping-settings", headers=admin_headers, timeout=10)
        current_settings = resp.json() if resp.status_code == 200 else {}
        
        # Update to zone method
        current_settings['method'] = 'zone'
        resp = requests.patch(f"{BACKEND_URL}/admin/shipping-settings",
                            headers=admin_headers,
                            json=current_settings,
                            timeout=10)
        passed = resp.status_code == 200 and resp.json().get('method') == 'zone'
        log_test("Task 2", "PATCH method=zone → 200", passed,
                f"Status: {resp.status_code}, method: {resp.json().get('method') if resp.status_code == 200 else 'N/A'}")
    except Exception as e:
        log_test("Task 2", "PATCH method=zone → 200", False, str(e))
    
    # Test 2.6: Zone method - Maharashtra (should match zone)
    try:
        resp = requests.post(f"{BACKEND_URL}/shipping/calculate",
                           json={
                               "subtotal_inr": 10000,
                               "state": "Maharashtra",
                               "pincode": "400001",
                               "country": "India"
                           },
                           timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            # Maharashtra should match a zone (default 499 for local)
            passed = data.get('method') == 'zone' and data.get('shipping_inr') > 0
            details = f"method: {data.get('method')}, shipping_inr: {data.get('shipping_inr')}, notes: {data.get('notes')}"
            log_test("Task 2", "Zone method, Maharashtra → zone rate", passed, details)
        else:
            log_test("Task 2", "Zone method, Maharashtra → zone rate", False,
                    f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    except Exception as e:
        log_test("Task 2", "Zone method, Maharashtra → zone rate", False, str(e))
    
    # Test 2.7: Zone method - Nagaland (not in any zone, should use fallback)
    try:
        resp = requests.post(f"{BACKEND_URL}/shipping/calculate",
                           json={
                               "subtotal_inr": 10000,
                               "state": "Nagaland",
                               "pincode": "797001",
                               "country": "India"
                           },
                           timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            # Should use fallback zone (empty states list or last zone)
            passed = data.get('method') == 'zone' and data.get('shipping_inr') > 0
            details = f"method: {data.get('method')}, shipping_inr: {data.get('shipping_inr')}, notes: {data.get('notes')}"
            log_test("Task 2", "Zone method, Nagaland → fallback zone", passed, details)
        else:
            log_test("Task 2", "Zone method, Nagaland → fallback zone", False,
                    f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    except Exception as e:
        log_test("Task 2", "Zone method, Nagaland → fallback zone", False, str(e))
    
    # Test 2.8: Set method to distance
    try:
        resp = requests.get(f"{BACKEND_URL}/admin/shipping-settings", headers=admin_headers, timeout=10)
        current_settings = resp.json() if resp.status_code == 200 else {}
        
        current_settings['method'] = 'distance'
        resp = requests.patch(f"{BACKEND_URL}/admin/shipping-settings",
                            headers=admin_headers,
                            json=current_settings,
                            timeout=10)
        passed = resp.status_code == 200 and resp.json().get('method') == 'distance'
        log_test("Task 2", "PATCH method=distance → 200", passed,
                f"Status: {resp.status_code}, method: {resp.json().get('method') if resp.status_code == 200 else 'N/A'}")
    except Exception as e:
        log_test("Task 2", "PATCH method=distance → 200", False, str(e))
    
    # Test 2.9: Distance method - Tamil Nadu (1330 km from Mumbai)
    try:
        resp = requests.post(f"{BACKEND_URL}/shipping/calculate",
                           json={
                               "subtotal_inr": 10000,
                               "state": "Tamil Nadu",
                               "pincode": "600001",
                               "country": "India"
                           },
                           timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            # Should be base_fee (299) + per_km (3) * 1330 = 299 + 3990 = 4289
            # Allow some tolerance
            expected_min = 4000
            expected_max = 5000
            shipping = data.get('shipping_inr', 0)
            passed = data.get('method') == 'distance' and expected_min <= shipping <= expected_max
            details = f"method: {data.get('method')}, shipping_inr: {shipping} (expected ~4289), notes: {data.get('notes')}"
            log_test("Task 2", "Distance method, Tamil Nadu → ~4289 INR", passed, details)
        else:
            log_test("Task 2", "Distance method, Tamil Nadu → ~4289 INR", False,
                    f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    except Exception as e:
        log_test("Task 2", "Distance method, Tamil Nadu → ~4289 INR", False, str(e))
    
    # Test 2.10: Restore method to flat
    try:
        resp = requests.get(f"{BACKEND_URL}/admin/shipping-settings", headers=admin_headers, timeout=10)
        current_settings = resp.json() if resp.status_code == 200 else {}
        
        current_settings['method'] = 'flat'
        resp = requests.patch(f"{BACKEND_URL}/admin/shipping-settings",
                            headers=admin_headers,
                            json=current_settings,
                            timeout=10)
        passed = resp.status_code == 200 and resp.json().get('method') == 'flat'
        log_test("Task 2", "PATCH restore method=flat → 200", passed,
                f"Status: {resp.status_code}, method: {resp.json().get('method') if resp.status_code == 200 else 'N/A'}")
    except Exception as e:
        log_test("Task 2", "PATCH restore method=flat → 200", False, str(e))


def test_task_3_order_tracking():
    """Task 3 - Order tracking"""
    print_section("TASK 3: Order Tracking")
    
    if not admin_token:
        log_test("Task 3", "Order tracking tests", False, "No admin token available")
        return
    
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # First, create a test order via razorpay method
    test_order_number = None
    
    try:
        # Get a product first
        resp = requests.get(f"{BACKEND_URL}/products", timeout=10)
        products = resp.json() if resp.status_code == 200 else []
        
        if not products:
            log_test("Task 3", "Create test order", False, "No products available")
            return
        
        product = products[0]
        variant_key = product['variants'][0]['key'] if product.get('variants') else 'default'
        
        # Create order
        order_payload = {
            "customer": {
                "name": "Test Customer",
                "email": "test@example.com",
                "phone": "9999999999",
                "address": "123 Test Street",
                "city": "Mumbai",
                "pincode": "400001"
            },
            "items": [{
                "product_id": product['id'],
                "variant_key": variant_key,
                "quantity": 1
            }],
            "payment_method": "razorpay",
            "subtotal_inr": 10000,
            "shipping_inr": 0,
            "total_inr": 10000
        }
        
        resp = requests.post(f"{BACKEND_URL}/orders", json=order_payload, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            # Order is nested in response
            order_data = data.get('order', {})
            test_order_number = order_data.get('order_number')
            log_test("Task 3", "Create test order", True, f"Order: {test_order_number}")
        else:
            log_test("Task 3", "Create test order", False,
                    f"Status: {resp.status_code}, Body: {resp.text[:200]}")
            return
    except Exception as e:
        log_test("Task 3", "Create test order", False, str(e))
        return
    
    if not test_order_number:
        log_test("Task 3", "Order tracking tests", False, "No test order created")
        return
    
    # Test 3.1: PATCH tracking with full payload
    try:
        tracking_payload = {
            "tracking_id": "DTDC12345",
            "tracking_url": "https://track.dtdc.in/DTDC12345",
            "tracking_carrier": "DTDC"
        }
        
        resp = requests.patch(f"{BACKEND_URL}/admin/orders/{test_order_number}/tracking",
                            headers=admin_headers,
                            json=tracking_payload,
                            timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            tracking_id_match = data.get('tracking_id') == "DTDC12345"
            tracking_url_match = data.get('tracking_url') == "https://track.dtdc.in/DTDC12345"
            tracking_carrier_match = data.get('tracking_carrier') == "DTDC"
            tracking_updated_at_present = data.get('tracking_updated_at') is not None
            
            passed = tracking_id_match and tracking_url_match and tracking_carrier_match and tracking_updated_at_present
            details = f"tracking_id: {tracking_id_match}, tracking_url: {tracking_url_match}, tracking_carrier: {tracking_carrier_match}, tracking_updated_at: {tracking_updated_at_present}"
            log_test("Task 3", "PATCH tracking with full payload → 200", passed, details)
        else:
            log_test("Task 3", "PATCH tracking with full payload → 200", False,
                    f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    except Exception as e:
        log_test("Task 3", "PATCH tracking with full payload → 200", False, str(e))
    
    # Test 3.2: PATCH tracking with partial payload (only carrier)
    try:
        partial_payload = {
            "tracking_carrier": "BlueDart"
        }
        
        resp = requests.patch(f"{BACKEND_URL}/admin/orders/{test_order_number}/tracking",
                            headers=admin_headers,
                            json=partial_payload,
                            timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            # tracking_id should remain DTDC12345, carrier should be BlueDart
            tracking_id_unchanged = data.get('tracking_id') == "DTDC12345"
            tracking_carrier_updated = data.get('tracking_carrier') == "BlueDart"
            
            passed = tracking_id_unchanged and tracking_carrier_updated
            details = f"tracking_id unchanged: {tracking_id_unchanged} ({data.get('tracking_id')}), tracking_carrier updated: {tracking_carrier_updated} ({data.get('tracking_carrier')})"
            log_test("Task 3", "PATCH tracking partial (only carrier) → carrier changes, id remains", passed, details)
        else:
            log_test("Task 3", "PATCH tracking partial (only carrier) → carrier changes, id remains", False,
                    f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    except Exception as e:
        log_test("Task 3", "PATCH tracking partial (only carrier) → carrier changes, id remains", False, str(e))
    
    # Test 3.3: GET order to verify tracking fields visible
    try:
        resp = requests.get(f"{BACKEND_URL}/orders/{test_order_number}", timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            has_tracking_id = 'tracking_id' in data
            has_tracking_url = 'tracking_url' in data
            has_tracking_carrier = 'tracking_carrier' in data
            has_tracking_updated_at = 'tracking_updated_at' in data
            
            passed = has_tracking_id and has_tracking_url and has_tracking_carrier and has_tracking_updated_at
            details = f"tracking_id: {data.get('tracking_id')}, tracking_carrier: {data.get('tracking_carrier')}"
            log_test("Task 3", "GET /api/orders/{n} → tracking fields visible", passed, details)
        else:
            log_test("Task 3", "GET /api/orders/{n} → tracking fields visible", False,
                    f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    except Exception as e:
        log_test("Task 3", "GET /api/orders/{n} → tracking fields visible", False, str(e))


def test_task_4_backward_compat():
    """Task 4 - Order create backward compatibility"""
    print_section("TASK 4: Order Create Backward Compat")
    
    # Get a product first
    try:
        resp = requests.get(f"{BACKEND_URL}/products", timeout=10)
        products = resp.json() if resp.status_code == 200 else []
        
        if not products:
            log_test("Task 4", "Get product for test", False, "No products available")
            return
        
        product = products[0]
        variant_key = product['variants'][0]['key'] if product.get('variants') else 'default'
        log_test("Task 4", "Get product for test", True, f"Using: {product['slug']}")
    except Exception as e:
        log_test("Task 4", "Get product for test", False, str(e))
        return
    
    # Test 4.1: Order with ONLY old fields
    try:
        old_payload = {
            "customer": {
                "name": "Old Format Customer",
                "email": "oldformat@example.com",
                "phone": "8888888888",
                "address": "456 Old Street",
                "city": "Delhi",
                "pincode": "110001"
            },
            "items": [{
                "product_id": product['id'],
                "variant_key": variant_key,
                "quantity": 1
            }],
            "payment_method": "cod",
            "subtotal_inr": 15000,
            "shipping_inr": 1499,
            "total_inr": 16499
        }
        
        resp = requests.post(f"{BACKEND_URL}/orders", json=old_payload, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            # Order is nested in response
            order_data = data.get('order', {})
            order_number = order_data.get('order_number')
            passed = order_number is not None
            log_test("Task 4", "Order with ONLY old fields → success", passed,
                    f"Order: {order_number}")
        else:
            log_test("Task 4", "Order with ONLY old fields → success", False,
                    f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    except Exception as e:
        log_test("Task 4", "Order with ONLY old fields → success", False, str(e))
    
    # Test 4.2: Order with new structured fields
    try:
        new_payload = {
            "customer": {
                "name": "New Format Customer",
                "email": "newformat@example.com",
                "phone": "7777777777",
                "address": "789 New Street, Sector 5, Near Mall",  # Composed address
                "city": "Bangalore",
                "pincode": "560001",
                "line1": "789 New Street",
                "line2": "Sector 5",
                "landmark": "Near Mall",
                "state": "Karnataka",
                "country": "India"
            },
            "items": [{
                "product_id": product['id'],
                "variant_key": variant_key,
                "quantity": 1
            }],
            "payment_method": "cod",
            "subtotal_inr": 20000,
            "shipping_inr": 999,
            "total_inr": 20999
        }
        
        resp = requests.post(f"{BACKEND_URL}/orders", json=new_payload, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            # Order is nested in response
            order_data = data.get('order', {})
            order_number = order_data.get('order_number')
            
            # Retrieve the order to verify all fields
            resp2 = requests.get(f"{BACKEND_URL}/orders/{order_number}", timeout=10)
            if resp2.status_code == 200:
                order_data = resp2.json()
                customer = order_data.get('customer', {})
                
                has_line1 = customer.get('line1') == "789 New Street"
                has_line2 = customer.get('line2') == "Sector 5"
                has_landmark = customer.get('landmark') == "Near Mall"
                has_state = customer.get('state') == "Karnataka"
                has_country = customer.get('country') == "India"
                
                passed = has_line1 and has_line2 and has_landmark and has_state and has_country
                details = f"line1: {has_line1}, line2: {has_line2}, landmark: {has_landmark}, state: {has_state}, country: {has_country}"
                log_test("Task 4", "Order with new fields → all fields persisted", passed, details)
            else:
                log_test("Task 4", "Order with new fields → all fields persisted", False,
                        f"Failed to retrieve order: {resp2.status_code}")
        else:
            log_test("Task 4", "Order with new fields → all fields persisted", False,
                    f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    except Exception as e:
        log_test("Task 4", "Order with new fields → all fields persisted", False, str(e))
    
    # Test 4.3: Verify total calculation (subtotal - discount + shipping = total)
    try:
        calc_payload = {
            "customer": {
                "name": "Calc Test",
                "email": "calc@example.com",
                "phone": "6666666666",
                "address": "Test",
                "city": "Mumbai",
                "pincode": "400001"
            },
            "items": [{
                "product_id": product['id'],
                "variant_key": variant_key,
                "quantity": 1
            }],
            "payment_method": "cod",
            "subtotal_inr": 25000,
            "discount_inr": 2500,
            "shipping_inr": 1499,
            "total_inr": 23999  # 25000 - 2500 + 1499 = 23999
        }
        
        resp = requests.post(f"{BACKEND_URL}/orders", json=calc_payload, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            # Order is nested in response
            order_data = data.get('order', {})
            order_number = order_data.get('order_number')
            
            # Retrieve to verify
            resp2 = requests.get(f"{BACKEND_URL}/orders/{order_number}", timeout=10)
            if resp2.status_code == 200:
                order_data = resp2.json()
                subtotal = order_data.get('subtotal_inr', 0)
                discount = order_data.get('discount_inr', 0)
                shipping = order_data.get('shipping_inr', 0)
                total = order_data.get('total_inr', 0)
                
                expected_total = subtotal - discount + shipping
                passed = total == expected_total
                details = f"subtotal: {subtotal}, discount: {discount}, shipping: {shipping}, total: {total}, expected: {expected_total}"
                log_test("Task 4", "Total calculation: subtotal - discount + shipping = total", passed, details)
            else:
                log_test("Task 4", "Total calculation: subtotal - discount + shipping = total", False,
                        f"Failed to retrieve order: {resp2.status_code}")
        else:
            log_test("Task 4", "Total calculation: subtotal - discount + shipping = total", False,
                    f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    except Exception as e:
        log_test("Task 4", "Total calculation: subtotal - discount + shipping = total", False, str(e))


def print_summary():
    """Print test summary"""
    print_section("TEST SUMMARY")
    
    total = len(test_results)
    passed = sum(1 for r in test_results if r["passed"])
    failed = total - passed
    
    print(f"\nTotal Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(passed/total*100):.1f}%\n")
    
    if failed > 0:
        print("FAILED TESTS:")
        print("-" * 80)
        for r in test_results:
            if not r["passed"]:
                print(f"❌ [{r['section']}] {r['test']}")
                if r["details"]:
                    print(f"   {r['details']}")
        print()
    
    # Group by section
    sections = {}
    for r in test_results:
        section = r["section"]
        if section not in sections:
            sections[section] = {"passed": 0, "failed": 0}
        if r["passed"]:
            sections[section]["passed"] += 1
        else:
            sections[section]["failed"] += 1
    
    print("BY TASK:")
    print("-" * 80)
    for section, counts in sections.items():
        total_section = counts["passed"] + counts["failed"]
        status = "✅" if counts["failed"] == 0 else "❌"
        print(f"{status} {section}: {counts['passed']}/{total_section} passed")
    print()


def main():
    """Main test execution"""
    print("\n" + "="*80)
    print("  ArtyFex Phase A Backend Testing")
    print("  Backend URL:", BACKEND_URL)
    print("="*80)
    
    # Setup
    if not admin_login():
        print("\n❌ CRITICAL: Admin login failed. Cannot proceed with tests.")
        return
    
    # Run test tasks
    test_task_1_homepage_cms()
    test_task_2_shipping()
    test_task_3_order_tracking()
    test_task_4_backward_compat()
    
    # Summary
    print_summary()
    
    # Save results to file
    with open("/app/backend_test_phase_a_results.json", "w") as f:
        json.dump(test_results, f, indent=2)
    print(f"Detailed results saved to: /app/backend_test_phase_a_results.json\n")


if __name__ == "__main__":
    main()
