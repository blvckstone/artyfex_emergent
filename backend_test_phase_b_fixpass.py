#!/usr/bin/env python3
"""
Phase B fix-pass backend testing (Jul 17 2026)
Tests ONLY the Phase B fix-pass changes:
- HomepageContent model extension (category_section, why_section, featured_section, nav_default_links)
- Cloudinary signature endpoint
- Regression tests (products, reviews, pages)
"""

import requests
import json
import sys
import re
from typing import Dict, Any

# Backend URL from frontend/.env
BASE_URL = "https://atelier-worlds.preview.emergentagent.com/api"

# Admin credentials from /app/memory/test_credentials.md
ADMIN_EMAIL = "admin@artyfex.in"
ADMIN_PASSWORD = "ArtyFex@2026"

# Test results
results = []
admin_token = None
original_homepage = None


def log_test(name: str, passed: bool, details: str = ""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {name}")
    if details:
        print(f"    {details}")
    results.append({
        "test": name,
        "passed": passed,
        "details": details
    })


def test_admin_login():
    """1.2) POST /api/admin/login to get admin token"""
    global admin_token
    try:
        resp = requests.post(
            f"{BASE_URL}/admin/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            admin_token = data.get("token")
            if admin_token:
                log_test("1.2 Admin login", True, f"Token received (length: {len(admin_token)})")
                return True
            else:
                log_test("1.2 Admin login", False, "No token in response")
                return False
        else:
            log_test("1.2 Admin login", False, f"Status {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        log_test("1.2 Admin login", False, f"Exception: {str(e)}")
        return False


def test_homepage_get_public():
    """1.1) GET /api/homepage (public, no auth) - verify all new keys"""
    global original_homepage
    try:
        resp = requests.get(f"{BASE_URL}/homepage", timeout=10)
        if resp.status_code != 200:
            log_test("1.1 GET /api/homepage (public)", False, f"Status {resp.status_code}: {resp.text[:200]}")
            return False
        
        data = resp.json()
        original_homepage = data  # Save for restoration later
        
        # Verify all required keys exist
        required_keys = [
            "announcement", "hero", "sale_banner", "craft", "collection_section",
            "reviews_section", "important_note", "custom_css",
            # NEW Phase B keys:
            "category_section", "why_section", "featured_section", "nav_default_links"
        ]
        
        missing_keys = [k for k in required_keys if k not in data]
        if missing_keys:
            log_test("1.1 GET /api/homepage (public)", False, f"Missing keys: {missing_keys}")
            return False
        
        # Verify category_section structure
        cat_sec = data.get("category_section", {})
        if not isinstance(cat_sec, dict):
            log_test("1.1 GET /api/homepage (public)", False, "category_section is not a dict")
            return False
        
        cat_required = ["enabled", "eyebrow", "headline_line_1", "headline_italic", "headline_line_2", "subtitle", "tiles"]
        cat_missing = [k for k in cat_required if k not in cat_sec]
        if cat_missing:
            log_test("1.1 GET /api/homepage (public)", False, f"category_section missing keys: {cat_missing}")
            return False
        
        if cat_sec.get("enabled") != True:
            log_test("1.1 GET /api/homepage (public)", False, f"category_section.enabled is {cat_sec.get('enabled')}, expected True")
            return False
        
        if cat_sec.get("eyebrow") != "Explore the Atelier":
            log_test("1.1 GET /api/homepage (public)", False, f"category_section.eyebrow is '{cat_sec.get('eyebrow')}', expected 'Explore the Atelier'")
            return False
        
        if cat_sec.get("headline_line_1") != "Curated":
            log_test("1.1 GET /api/homepage (public)", False, f"category_section.headline_line_1 is '{cat_sec.get('headline_line_1')}', expected 'Curated'")
            return False
        
        if cat_sec.get("headline_italic") != "worlds":
            log_test("1.1 GET /api/homepage (public)", False, f"category_section.headline_italic is '{cat_sec.get('headline_italic')}', expected 'worlds'")
            return False
        
        if cat_sec.get("headline_line_2") != " of luxury.":
            log_test("1.1 GET /api/homepage (public)", False, f"category_section.headline_line_2 is '{cat_sec.get('headline_line_2')}', expected ' of luxury.'")
            return False
        
        if not cat_sec.get("subtitle"):
            log_test("1.1 GET /api/homepage (public)", False, "category_section.subtitle is empty")
            return False
        
        if not isinstance(cat_sec.get("tiles"), list):
            log_test("1.1 GET /api/homepage (public)", False, "category_section.tiles is not a list")
            return False
        
        # Verify why_section structure
        why_sec = data.get("why_section", {})
        if not isinstance(why_sec, dict):
            log_test("1.1 GET /api/homepage (public)", False, "why_section is not a dict")
            return False
        
        why_required = ["enabled", "eyebrow", "stats"]
        why_missing = [k for k in why_required if k not in why_sec]
        if why_missing:
            log_test("1.1 GET /api/homepage (public)", False, f"why_section missing keys: {why_missing}")
            return False
        
        if why_sec.get("enabled") != True:
            log_test("1.1 GET /api/homepage (public)", False, f"why_section.enabled is {why_sec.get('enabled')}, expected True")
            return False
        
        if why_sec.get("eyebrow") != "Why ArtyFex":
            log_test("1.1 GET /api/homepage (public)", False, f"why_section.eyebrow is '{why_sec.get('eyebrow')}', expected 'Why ArtyFex'")
            return False
        
        stats = why_sec.get("stats", [])
        if not isinstance(stats, list):
            log_test("1.1 GET /api/homepage (public)", False, "why_section.stats is not a list")
            return False
        
        if len(stats) != 4:
            log_test("1.1 GET /api/homepage (public)", False, f"why_section.stats has {len(stats)} items, expected 4")
            return False
        
        # Verify each stat has required keys
        for i, stat in enumerate(stats):
            stat_required = ["icon", "value", "suffix", "label", "note"]
            stat_missing = [k for k in stat_required if k not in stat]
            if stat_missing:
                log_test("1.1 GET /api/homepage (public)", False, f"why_section.stats[{i}] missing keys: {stat_missing}")
                return False
        
        # Verify featured_section structure
        feat_sec = data.get("featured_section", {})
        if not isinstance(feat_sec, dict):
            log_test("1.1 GET /api/homepage (public)", False, "featured_section is not a dict")
            return False
        
        feat_required = ["enabled", "eyebrow", "headline_line_1", "headline_italic"]
        feat_missing = [k for k in feat_required if k not in feat_sec]
        if feat_missing:
            log_test("1.1 GET /api/homepage (public)", False, f"featured_section missing keys: {feat_missing}")
            return False
        
        if feat_sec.get("enabled") != True:
            log_test("1.1 GET /api/homepage (public)", False, f"featured_section.enabled is {feat_sec.get('enabled')}, expected True")
            return False
        
        if feat_sec.get("eyebrow") != "Featured":
            log_test("1.1 GET /api/homepage (public)", False, f"featured_section.eyebrow is '{feat_sec.get('eyebrow')}', expected 'Featured'")
            return False
        
        if feat_sec.get("headline_line_1") != "Editor's":
            log_test("1.1 GET /api/homepage (public)", False, f"featured_section.headline_line_1 is '{feat_sec.get('headline_line_1')}', expected 'Editor's'")
            return False
        
        if feat_sec.get("headline_italic") != "pick":
            log_test("1.1 GET /api/homepage (public)", False, f"featured_section.headline_italic is '{feat_sec.get('headline_italic')}', expected 'pick'")
            return False
        
        # Verify nav_default_links structure
        nav_links = data.get("nav_default_links", {})
        if not isinstance(nav_links, dict):
            log_test("1.1 GET /api/homepage (public)", False, "nav_default_links is not a dict")
            return False
        
        nav_required = ["show_shop", "show_craft", "show_reviews", "show_b2b"]
        nav_missing = [k for k in nav_required if k not in nav_links]
        if nav_missing:
            log_test("1.1 GET /api/homepage (public)", False, f"nav_default_links missing keys: {nav_missing}")
            return False
        
        if nav_links.get("show_shop") != True:
            log_test("1.1 GET /api/homepage (public)", False, f"nav_default_links.show_shop is {nav_links.get('show_shop')}, expected True")
            return False
        
        if nav_links.get("show_craft") != True:
            log_test("1.1 GET /api/homepage (public)", False, f"nav_default_links.show_craft is {nav_links.get('show_craft')}, expected True")
            return False
        
        if nav_links.get("show_reviews") != True:
            log_test("1.1 GET /api/homepage (public)", False, f"nav_default_links.show_reviews is {nav_links.get('show_reviews')}, expected True")
            return False
        
        if nav_links.get("show_b2b") != True:
            log_test("1.1 GET /api/homepage (public)", False, f"nav_default_links.show_b2b is {nav_links.get('show_b2b')}, expected True")
            return False
        
        log_test("1.1 GET /api/homepage (public)", True, "All new Phase B keys present with correct defaults")
        return True
        
    except Exception as e:
        log_test("1.1 GET /api/homepage (public)", False, f"Exception: {str(e)}")
        return False


def test_homepage_patch_with_overrides():
    """1.3) PATCH /api/admin/homepage with overrides"""
    if not admin_token or not original_homepage:
        log_test("1.3 PATCH /api/admin/homepage (overrides)", False, "Missing admin_token or original_homepage")
        return False
    
    try:
        # Create modified payload
        modified = dict(original_homepage)
        modified["category_section"]["enabled"] = False
        modified["category_section"]["tiles"] = [{
            "slug": "mirrors",
            "label": "Test Tile",
            "keyword": "kw",
            "image": "https://res.cloudinary.com/wir5svfq/image/upload/v1/artyfex/x.jpg"
        }]
        modified["nav_default_links"]["show_craft"] = False
        modified["why_section"]["enabled"] = False
        modified["why_section"]["stats"] = [{
            "icon": "award",
            "value": 50,
            "suffix": "+",
            "label": "Awards",
            "note": ""
        }]
        
        # PATCH request
        resp = requests.patch(
            f"{BASE_URL}/admin/homepage",
            json=modified,
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        
        if resp.status_code != 200:
            log_test("1.3 PATCH /api/admin/homepage (overrides)", False, f"Status {resp.status_code}: {resp.text[:200]}")
            return False
        
        # Verify response echoes changes
        data = resp.json()
        
        # Now GET to verify persistence
        resp2 = requests.get(f"{BASE_URL}/homepage", timeout=10)
        if resp2.status_code != 200:
            log_test("1.3 PATCH /api/admin/homepage (overrides)", False, f"GET after PATCH failed: {resp2.status_code}")
            return False
        
        data2 = resp2.json()
        
        # Verify all 4 overrides persisted
        if data2.get("category_section", {}).get("enabled") != False:
            log_test("1.3 PATCH /api/admin/homepage (overrides)", False, f"category_section.enabled not persisted: {data2.get('category_section', {}).get('enabled')}")
            return False
        
        tiles = data2.get("category_section", {}).get("tiles", [])
        if len(tiles) != 1:
            log_test("1.3 PATCH /api/admin/homepage (overrides)", False, f"category_section.tiles length is {len(tiles)}, expected 1")
            return False
        
        if tiles[0].get("slug") != "mirrors" or tiles[0].get("label") != "Test Tile":
            log_test("1.3 PATCH /api/admin/homepage (overrides)", False, f"category_section.tiles[0] not correct: {tiles[0]}")
            return False
        
        if data2.get("nav_default_links", {}).get("show_craft") != False:
            log_test("1.3 PATCH /api/admin/homepage (overrides)", False, f"nav_default_links.show_craft not persisted: {data2.get('nav_default_links', {}).get('show_craft')}")
            return False
        
        if data2.get("why_section", {}).get("enabled") != False:
            log_test("1.3 PATCH /api/admin/homepage (overrides)", False, f"why_section.enabled not persisted: {data2.get('why_section', {}).get('enabled')}")
            return False
        
        stats = data2.get("why_section", {}).get("stats", [])
        if len(stats) != 1:
            log_test("1.3 PATCH /api/admin/homepage (overrides)", False, f"why_section.stats length is {len(stats)}, expected 1")
            return False
        
        if stats[0].get("value") != 50 or stats[0].get("label") != "Awards":
            log_test("1.3 PATCH /api/admin/homepage (overrides)", False, f"why_section.stats[0] not correct: {stats[0]}")
            return False
        
        log_test("1.3 PATCH /api/admin/homepage (overrides)", True, "All 4 overrides persisted correctly")
        return True
        
    except Exception as e:
        log_test("1.3 PATCH /api/admin/homepage (overrides)", False, f"Exception: {str(e)}")
        return False


def test_homepage_restore_defaults():
    """1.4) Restore to defaults"""
    if not admin_token or not original_homepage:
        log_test("1.4 PATCH /api/admin/homepage (restore)", False, "Missing admin_token or original_homepage")
        return False
    
    try:
        resp = requests.patch(
            f"{BASE_URL}/admin/homepage",
            json=original_homepage,
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        
        if resp.status_code != 200:
            log_test("1.4 PATCH /api/admin/homepage (restore)", False, f"Status {resp.status_code}: {resp.text[:200]}")
            return False
        
        log_test("1.4 PATCH /api/admin/homepage (restore)", True, "Restored to original defaults")
        return True
        
    except Exception as e:
        log_test("1.4 PATCH /api/admin/homepage (restore)", False, f"Exception: {str(e)}")
        return False


def test_homepage_patch_no_auth():
    """1.5) PATCH /api/admin/homepage WITHOUT token → 401"""
    try:
        resp = requests.patch(
            f"{BASE_URL}/admin/homepage",
            json={"announcement": {"text": "test"}},
            timeout=10
        )
        
        if resp.status_code == 401:
            log_test("1.5 PATCH /api/admin/homepage (no auth)", True, "Correctly returned 401")
            return True
        else:
            log_test("1.5 PATCH /api/admin/homepage (no auth)", False, f"Expected 401, got {resp.status_code}")
            return False
        
    except Exception as e:
        log_test("1.5 PATCH /api/admin/homepage (no auth)", False, f"Exception: {str(e)}")
        return False


def test_cloudinary_signature_no_auth():
    """2.1) GET /api/cloudinary/signature (no auth) → 401"""
    try:
        resp = requests.get(f"{BASE_URL}/cloudinary/signature", timeout=10)
        
        if resp.status_code == 401:
            log_test("2.1 GET /api/cloudinary/signature (no auth)", True, "Correctly returned 401")
            return True
        else:
            log_test("2.1 GET /api/cloudinary/signature (no auth)", False, f"Expected 401, got {resp.status_code}")
            return False
        
    except Exception as e:
        log_test("2.1 GET /api/cloudinary/signature (no auth)", False, f"Exception: {str(e)}")
        return False


def test_cloudinary_signature_with_auth():
    """2.2) GET /api/cloudinary/signature (admin token) → 200 with all keys"""
    if not admin_token:
        log_test("2.2 GET /api/cloudinary/signature (with auth)", False, "Missing admin_token")
        return False
    
    try:
        resp = requests.get(
            f"{BASE_URL}/cloudinary/signature",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        
        if resp.status_code != 200:
            log_test("2.2 GET /api/cloudinary/signature (with auth)", False, f"Status {resp.status_code}: {resp.text[:200]}")
            return False
        
        data = resp.json()
        
        # Verify all 6 required keys
        required_keys = ["signature", "timestamp", "cloud_name", "api_key", "folder", "resource_type"]
        missing_keys = [k for k in required_keys if k not in data]
        if missing_keys:
            log_test("2.2 GET /api/cloudinary/signature (with auth)", False, f"Missing keys: {missing_keys}")
            return False
        
        # Verify signature is hex string
        signature = data.get("signature", "")
        if not re.match(r'^[a-f0-9]+$', signature):
            log_test("2.2 GET /api/cloudinary/signature (with auth)", False, f"signature is not hex: {signature}")
            return False
        
        # Verify api_key
        if data.get("api_key") != "667774888644289":
            log_test("2.2 GET /api/cloudinary/signature (with auth)", False, f"api_key is {data.get('api_key')}, expected 667774888644289")
            return False
        
        # Verify cloud_name
        if data.get("cloud_name") != "wir5svfq":
            log_test("2.2 GET /api/cloudinary/signature (with auth)", False, f"cloud_name is {data.get('cloud_name')}, expected wir5svfq")
            return False
        
        # Verify folder default
        if data.get("folder") != "artyfex":
            log_test("2.2 GET /api/cloudinary/signature (with auth)", False, f"folder is {data.get('folder')}, expected artyfex")
            return False
        
        # Verify resource_type default
        if data.get("resource_type") != "image":
            log_test("2.2 GET /api/cloudinary/signature (with auth)", False, f"resource_type is {data.get('resource_type')}, expected image")
            return False
        
        log_test("2.2 GET /api/cloudinary/signature (with auth)", True, f"All keys present, signature={signature[:16]}...")
        return True
        
    except Exception as e:
        log_test("2.2 GET /api/cloudinary/signature (with auth)", False, f"Exception: {str(e)}")
        return False


def test_cloudinary_signature_wrong_folder():
    """2.3) GET /api/cloudinary/signature?folder=wrong-prefix → 400"""
    if not admin_token:
        log_test("2.3 GET /api/cloudinary/signature (wrong folder)", False, "Missing admin_token")
        return False
    
    try:
        resp = requests.get(
            f"{BASE_URL}/cloudinary/signature?folder=wrong-prefix",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        
        if resp.status_code == 400:
            log_test("2.3 GET /api/cloudinary/signature (wrong folder)", True, "Correctly returned 400")
            return True
        else:
            log_test("2.3 GET /api/cloudinary/signature (wrong folder)", False, f"Expected 400, got {resp.status_code}")
            return False
        
    except Exception as e:
        log_test("2.3 GET /api/cloudinary/signature (wrong folder)", False, f"Exception: {str(e)}")
        return False


def test_cloudinary_signature_wrong_resource_type():
    """2.4) GET /api/cloudinary/signature?resource_type=pdf → 400"""
    if not admin_token:
        log_test("2.4 GET /api/cloudinary/signature (wrong resource_type)", False, "Missing admin_token")
        return False
    
    try:
        resp = requests.get(
            f"{BASE_URL}/cloudinary/signature?resource_type=pdf",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        
        if resp.status_code == 400:
            log_test("2.4 GET /api/cloudinary/signature (wrong resource_type)", True, "Correctly returned 400")
            return True
        else:
            log_test("2.4 GET /api/cloudinary/signature (wrong resource_type)", False, f"Expected 400, got {resp.status_code}")
            return False
        
    except Exception as e:
        log_test("2.4 GET /api/cloudinary/signature (wrong resource_type)", False, f"Exception: {str(e)}")
        return False


def test_cloudinary_signature_custom_folder():
    """2.5) GET /api/cloudinary/signature?folder=artyfex/homepage → 200"""
    if not admin_token:
        log_test("2.5 GET /api/cloudinary/signature (custom folder)", False, "Missing admin_token")
        return False
    
    try:
        resp = requests.get(
            f"{BASE_URL}/cloudinary/signature?folder=artyfex/homepage",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        
        if resp.status_code != 200:
            log_test("2.5 GET /api/cloudinary/signature (custom folder)", False, f"Status {resp.status_code}: {resp.text[:200]}")
            return False
        
        data = resp.json()
        if data.get("folder") != "artyfex/homepage":
            log_test("2.5 GET /api/cloudinary/signature (custom folder)", False, f"folder is {data.get('folder')}, expected artyfex/homepage")
            return False
        
        log_test("2.5 GET /api/cloudinary/signature (custom folder)", True, "Custom folder accepted")
        return True
        
    except Exception as e:
        log_test("2.5 GET /api/cloudinary/signature (custom folder)", False, f"Exception: {str(e)}")
        return False


def test_regression_products():
    """3.1) GET /api/products → 200 with ≥ 4 products"""
    try:
        resp = requests.get(f"{BASE_URL}/products", timeout=10)
        
        if resp.status_code != 200:
            log_test("3.1 GET /api/products (regression)", False, f"Status {resp.status_code}: {resp.text[:200]}")
            return False
        
        data = resp.json()
        if not isinstance(data, list):
            log_test("3.1 GET /api/products (regression)", False, f"Response is not a list: {type(data)}")
            return False
        
        if len(data) < 4:
            log_test("3.1 GET /api/products (regression)", False, f"Only {len(data)} products, expected ≥ 4")
            return False
        
        log_test("3.1 GET /api/products (regression)", True, f"{len(data)} products returned")
        return True
        
    except Exception as e:
        log_test("3.1 GET /api/products (regression)", False, f"Exception: {str(e)}")
        return False


def test_regression_reviews():
    """3.2) GET /api/reviews → 200 with array"""
    try:
        resp = requests.get(f"{BASE_URL}/reviews", timeout=10)
        
        if resp.status_code != 200:
            log_test("3.2 GET /api/reviews (regression)", False, f"Status {resp.status_code}: {resp.text[:200]}")
            return False
        
        data = resp.json()
        if not isinstance(data, list):
            log_test("3.2 GET /api/reviews (regression)", False, f"Response is not a list: {type(data)}")
            return False
        
        log_test("3.2 GET /api/reviews (regression)", True, f"{len(data)} reviews returned")
        return True
        
    except Exception as e:
        log_test("3.2 GET /api/reviews (regression)", False, f"Exception: {str(e)}")
        return False


def test_regression_pages():
    """3.3) GET /api/pages (public) → 200 with ≥ 5 seeded pages"""
    try:
        resp = requests.get(f"{BASE_URL}/pages", timeout=10)
        
        if resp.status_code != 200:
            log_test("3.3 GET /api/pages (regression)", False, f"Status {resp.status_code}: {resp.text[:200]}")
            return False
        
        data = resp.json()
        if not isinstance(data, list):
            log_test("3.3 GET /api/pages (regression)", False, f"Response is not a list: {type(data)}")
            return False
        
        if len(data) < 5:
            log_test("3.3 GET /api/pages (regression)", False, f"Only {len(data)} pages, expected ≥ 5")
            return False
        
        log_test("3.3 GET /api/pages (regression)", True, f"{len(data)} pages returned")
        return True
        
    except Exception as e:
        log_test("3.3 GET /api/pages (regression)", False, f"Exception: {str(e)}")
        return False


def main():
    print("=" * 80)
    print("Phase B fix-pass backend testing (Jul 17 2026)")
    print("=" * 80)
    print()
    
    # FOCUS 1 - HomepageContent model extension
    print("FOCUS 1 - HomepageContent model extension")
    print("-" * 80)
    test_homepage_get_public()  # 1.1
    test_admin_login()  # 1.2
    test_homepage_patch_with_overrides()  # 1.3
    test_homepage_restore_defaults()  # 1.4
    test_homepage_patch_no_auth()  # 1.5
    print()
    
    # FOCUS 2 - Cloudinary signature endpoint
    print("FOCUS 2 - Cloudinary signature endpoint")
    print("-" * 80)
    test_cloudinary_signature_no_auth()  # 2.1
    test_cloudinary_signature_with_auth()  # 2.2
    test_cloudinary_signature_wrong_folder()  # 2.3
    test_cloudinary_signature_wrong_resource_type()  # 2.4
    test_cloudinary_signature_custom_folder()  # 2.5
    print()
    
    # FOCUS 3 - Regression
    print("FOCUS 3 - Regression")
    print("-" * 80)
    test_regression_products()  # 3.1
    test_regression_reviews()  # 3.2
    test_regression_pages()  # 3.3
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print()
    
    if passed < total:
        print("FAILED TESTS:")
        for r in results:
            if not r["passed"]:
                print(f"  ❌ {r['test']}")
                if r["details"]:
                    print(f"     {r['details']}")
        print()
    
    # Save results to JSON
    with open("/app/backend_test_phase_b_fixpass_results.json", "w") as f:
        json.dump({
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "results": results
        }, f, indent=2)
    
    print(f"Results saved to /app/backend_test_phase_b_fixpass_results.json")
    
    # Exit with appropriate code
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
