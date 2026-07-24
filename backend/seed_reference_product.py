"""
Seed script — uploads the "Golden Geode Mirror" reference product
(mirrors https://amzn.in/d/02CK5FmM) using EVERY feature the ArtyFex admin
product editor supports, so the owner can visually verify each field renders
correctly on the storefront.

Usage:
    python /app/backend/seed_reference_product.py
"""

import os
import sys
import json
import requests

BASE = os.environ.get("SEED_BASE_URL", "http://localhost:8001")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@artyfex.in")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "ArtyFex@2026")

# Amazon-hosted product images (safe to embed as URLs — Cloudinary optional)
HERO = "https://m.media-amazon.com/images/I/91mbumbwrIL._SL1500_.jpg"
GAL = [
    "https://m.media-amazon.com/images/I/51CAJA46UZL._SL1000_.jpg",
    "https://m.media-amazon.com/images/I/51v1Monv20L._SL1000_.jpg",
    "https://m.media-amazon.com/images/I/41cEeDwqYOL._SL1000_.jpg",
    "https://m.media-amazon.com/images/I/41xc5fLFKWL._SL1000_.jpg",
    "https://m.media-amazon.com/images/I/41WlyhaG7jL._SL1000_.jpg",
    "https://m.media-amazon.com/images/I/512OZFZxuxL._SL1000_.jpg",
    "https://m.media-amazon.com/images/I/310t7dEYPBL._SL1000_.jpg",
]
BANNER_1 = GAL[0]
BANNER_2 = GAL[1]
BANNER_3 = GAL[2]


def login() -> str:
    r = requests.post(f"{BASE}/api/admin/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                      timeout=15)
    r.raise_for_status()
    return r.json()["token"]


PRODUCT = {
    "slug": "golden-geode-mirror-2x2-premium",
    "name": "Premium 2×2 ft Designer Resin Mirror · Golden Geode",
    "tagline": "Anti-yellowing · Anti-fade · Handcrafted luxury for your wall",
    "description": (
        "Bring home timeless elegance and luxury with the ArtyFex Golden Geode Mirror — a "
        "handcrafted masterpiece measuring 2×2 ft (61 × 61 cm). Made using anti-yellowing, "
        "anti-fade premium-grade resin and finished with 100% shining crystal-quality stones, "
        "this designer mirror blends modern artistry with royal sophistication. The 5 mm thick "
        "reflective surface guarantees distortion-free reflections. A rear metal-mount hinge "
        "makes installation effortless, and the piece is backed by a lifetime warranty against "
        "yellowing and fading."
    ),
    "price_inr": 4899,
    "mrp_inr": 7599,
    "size": "2 × 2 ft (61 × 61 cm)",
    "craft_hours": 72,
    "materials": [
        "Premium anti-yellow resin",
        "5 mm float mirror glass",
        "Crystal-quality stones",
        "Metal wall-mount hinge",
    ],
    "hero_image": HERO,
    "gallery": GAL,
    "is_hero": True,
    "stock": 12,
    "has_variations": True,
    "category": "mirrors",
    "hsn_code": "7009",
    "sku": "ARF-GG-2X2-BASE",
    "weight_grams": 6000,
    "length_cm": 61,
    "width_cm": 61,
    "height_cm": 8,
    "tags": [
        "wall mirror", "resin mirror", "designer", "luxury", "golden",
        "housewarming", "geode", "art deco", "modern", "royal",
    ],
    # 3 real colour swatches, each with its own weight/dims/SKU
    "variants": [
        {
            "key": "golden", "label": "Golden Geode · 2 ft", "hex": "#D4AF37",
            "image": GAL[0], "size": "2 × 2 ft", "stock": 6,
            "price_inr": 4899, "mrp_inr": 7599,
            "sku": "ARF-GG-2X2-GOLD",
            "weight_grams": 6000, "length_cm": 61, "width_cm": 61, "height_cm": 8,
        },
        {
            "key": "black", "label": "Onyx Black · 2 ft", "hex": "#111111",
            "image": GAL[2], "size": "2 × 2 ft", "stock": 4,
            "price_inr": 4899, "mrp_inr": 7599,
            "sku": "ARF-GG-2X2-BLACK",
            "weight_grams": 6100, "length_cm": 61, "width_cm": 61, "height_cm": 8,
        },
        {
            "key": "silver", "label": "Platinum Silver · 2 ft", "hex": "#C0C0C0",
            "image": GAL[3], "size": "2 × 2 ft", "stock": 2,
            "price_inr": 5199, "mrp_inr": 7999,
            "sku": "ARF-GG-2X2-SILVER",
            "weight_grams": 6050, "length_cm": 61, "width_cm": 61, "height_cm": 8,
        },
    ],
    # Every option group filled: shape · frame · thickness · gift wrap · care kit · mount
    "variation_options": [
        {
            "key": "shape", "label": "Shape", "type": "select", "required": True,
            "help_text": "Choose the outline that best fits your wall.",
            "values": [
                {"key": "round", "label": "Round", "price_delta_inr": 0, "is_default": True},
                {"key": "square", "label": "Square", "price_delta_inr": 200},
                {"key": "arch", "label": "Arch", "price_delta_inr": 400},
            ],
        },
        {
            "key": "frame", "label": "Frame", "type": "select", "required": False,
            "help_text": "Optional framed edge — leave frameless for the classic geode look.",
            "values": [
                {"key": "frameless", "label": "Frameless (default)", "price_delta_inr": 0, "is_default": True},
                {"key": "gold-thin", "label": "Thin gold rim", "price_delta_inr": 600},
                {"key": "black-thick", "label": "Thick black border", "price_delta_inr": 900},
            ],
        },
        {
            "key": "thickness", "label": "Glass thickness", "type": "select", "required": False,
            "help_text": "5 mm is our standard for luxury clarity.",
            "values": [
                {"key": "5mm", "label": "5 mm (standard)", "price_delta_inr": 0, "is_default": True},
                {"key": "6mm", "label": "6 mm (extra sturdy)", "price_delta_inr": 500},
            ],
        },
        {
            "key": "gift_wrap", "label": "Gift Wrap", "type": "toggle", "required": False,
            "help_text": "Adds premium gift packaging. If Yes, buyers can add recipient name + handwritten message.",
            "values": [
                {"key": "no", "label": "No", "price_delta_inr": 0, "is_default": True},
                {"key": "yes", "label": "Yes · Premium wrap", "price_delta_inr": 500},
            ],
        },
        {
            "key": "care_kit", "label": "Care Kit", "type": "select", "required": False,
            "help_text": "Optional cleaning + shining items shipped with the piece.",
            "values": [
                {"key": "none", "label": "No care kit", "price_delta_inr": 0, "is_default": True},
                {"key": "basic", "label": "Basic · Cloth + Tissue", "price_delta_inr": 150},
                {"key": "premium", "label": "Premium · Cloth + Gel + Shine cream", "price_delta_inr": 500},
            ],
        },
        {
            "key": "mount", "label": "Wall mount", "type": "select", "required": False,
            "help_text": "Rear hinge is pre-fitted — no drilling from your end.",
            "values": [
                {"key": "hinge", "label": "Pre-fitted rear hinge", "price_delta_inr": 0, "is_default": True},
                {"key": "hook-kit", "label": "Hinge + heavy-duty hook kit", "price_delta_inr": 250},
            ],
        },
    ],
    # A+ content — one block per layout so buyer sees each renders differently
    "a_plus_content": [
        {
            "layout": "full_bleed",
            "heading": "One mirror. Seventy-two hours of craft.",
            "body": "Every ArtyFex Golden Geode Mirror is hand-poured, cured for 72 hours, and finished with 100% shining crystal-quality stones — no two are identical.",
            "image": BANNER_1,
            "features": "",
        },
        {
            "layout": "image_left",
            "heading": "Anti-yellowing. Anti-fade. Lifetime warranty.",
            "body": "Premium-grade resin resists heat and UV so your mirror keeps its clarity for decades. Backed by a lifetime warranty against yellowing or fading.",
            "image": BANNER_2,
            "features": "",
        },
        {
            "layout": "feature_grid",
            "heading": "Every detail engineered for luxury",
            "body": "From the glass thickness to the mounting hinge, every element is upgraded from the market standard.",
            "image": "",
            "features": (
                "5 mm crystal-clear glass\n"
                "Anti-yellow resin frame\n"
                "100% shining crystal stones\n"
                "Rear metal-mount hinge\n"
                "Handcrafted in Mumbai\n"
                "Lifetime warranty"
            ),
        },
        {
            "layout": "image_right",
            "heading": "Statement piece for every room",
            "body": "Bedroom, drawing room, hallway, dressing room, boutique — the Golden Geode Mirror lifts every space it touches. Golden + black finish complements art-deco, modern and royal interiors alike.",
            "image": BANNER_3,
            "features": "",
        },
        {
            "layout": "quote",
            "heading": "Verified buyer, Amazon",
            "body": "It’s far more stunning in person than the photos. The stones catch the light beautifully — the room feels twice as luxurious.",
            "image": "",
            "features": "",
        },
        {
            "layout": "centered",
            "heading": "Ships in a double-walled crate",
            "body": "Each piece leaves our atelier in a custom-cut EPE-foam sleeve inside a double-walled crate, then travels via NimbusPost priority. If anything breaks in transit — we replace it, free.",
            "image": "",
            "features": "",
        },
    ],
}


def main() -> int:
    try:
        token = login()
    except Exception as e:
        print(f"[seed] login failed: {e}", file=sys.stderr)
        return 1
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # If slug already exists → delete first so this script is idempotent
    r = requests.get(f"{BASE}/api/products/{PRODUCT['slug']}", timeout=10)
    if r.status_code == 200:
        pid = r.json().get("id")
        if pid:
            d = requests.delete(f"{BASE}/api/admin/products/{pid}", headers=h, timeout=10)
            print(f"[seed] deleted existing product {pid}: HTTP {d.status_code}")

    r = requests.post(f"{BASE}/api/admin/products", headers=h, json=PRODUCT, timeout=30)
    if r.status_code >= 300:
        print(f"[seed] create failed: HTTP {r.status_code}", file=sys.stderr)
        print(r.text[:2000], file=sys.stderr)
        return 1
    created = r.json()
    print(f"[seed] created product id={created.get('id')} slug={created.get('slug')}")
    print(f"[seed] variants: {len(created.get('variants') or [])}, "
          f"variation_options: {len(created.get('variation_options') or [])}, "
          f"a_plus_content: {len(created.get('a_plus_content') or [])}")
    print(f"[seed] view: {BASE.replace('8001','3000').replace('http://localhost','http://localhost')}/product/{created.get('slug')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
