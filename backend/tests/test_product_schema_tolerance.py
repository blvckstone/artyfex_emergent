"""Offline tests for product_schema.normalize_product_doc.

Why this exists (24 Nov 2026): the pink-silver mirror's photos were destroyed at
Cloudinary and a repair pass wrote ``variants[].image = None``. ``Variant.image``
is a required ``str``, so Pydantic rejected that one document — and because
``GET /api/products`` validates the *whole list* at once, a single bad record
made the entire catalogue return 500. The storefront sat on "Loading the
atelier…" and every admin save failed.

These tests pin the contract: a stored document is coerced into something
``Product`` accepts instead of raising. Pure stdlib, no DB, no network — they run
with ``python backend/tests/test_product_schema_tolerance.py`` or under pytest.
"""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from product_schema import (  # noqa: E402
    REQUIRED_INT_FIELDS,
    REQUIRED_LIST_FIELDS,
    REQUIRED_STR_FIELDS,
    VARIANT_REQUIRED_STR_FIELDS,
    normalize_product_doc,
    save_errors,
    slugify,
)


def _base_doc(**overrides):
    doc = {
        "id": "abc-123",
        "slug": "luxury-handmade-geode-resin-wall-mirror-pink-silver",
        "name": "Pink & Silver",
        "tagline": "Hand-poured",
        "description": "A mirror.",
        "price_inr": 18999,
        "mrp_inr": 24999,
        "size": "24 inch",
        "craft_hours": 40,
        "materials": ["resin"],
        "hero_image": "https://res.cloudinary.com/x/a.jpg",
        "gallery": ["https://res.cloudinary.com/x/a.jpg"],
        "variants": [{"key": "rose", "label": "Rose", "hex": "#c98", "image": "https://res.cloudinary.com/x/a.jpg"}],
        "is_hero": False,
        "stock": 3,
        "tags": ["mirror"],
        "variation_options": [],
        "a_plus_content": [],
        "amazon_url": None,
        "created_at": "2026-11-01T00:00:00+00:00",
    }
    doc.update(overrides)
    return doc


# ---- the exact production failure ------------------------------------------
def test_destroyed_photo_variant_image_none_becomes_empty_string():
    doc = _base_doc(
        hero_image="",
        gallery=[],
        variants=[{"key": "rose", "label": "Rose", "hex": "#c98", "image": None}],
    )
    out = normalize_product_doc(doc)
    assert out["variants"][0]["image"] == ""
    assert isinstance(out["variants"][0]["image"], str)


def test_every_required_field_is_present_and_right_type():
    out = normalize_product_doc(_base_doc(tagline=None, size=None, hero_image=None))
    for field in REQUIRED_STR_FIELDS:
        assert field in out, f"{field} missing"
        assert isinstance(out[field], str), f"{field} is {type(out[field])}"
    for field in REQUIRED_INT_FIELDS:
        assert field in out, f"{field} missing"
        assert isinstance(out[field], int) and not isinstance(out[field], bool), f"{field} is {type(out[field])}"
    for field in REQUIRED_LIST_FIELDS:
        assert isinstance(out[field], list), f"{field} is {type(out[field])}"


def test_variant_required_strings_are_coerced():
    out = normalize_product_doc(
        _base_doc(variants=[{"key": None, "label": None, "hex": None, "image": "https://x/a.jpg"}])
    )
    variant = out["variants"][0]
    for field in VARIANT_REQUIRED_STR_FIELDS:
        assert isinstance(variant[field], str), f"variant.{field} is {type(variant[field])}"
    assert variant["hex"].startswith("#")


def test_numeric_strings_and_junk_prices_are_coerced():
    assert normalize_product_doc(_base_doc(price_inr="8899"))["price_inr"] == 8899
    assert normalize_product_doc(_base_doc(price_inr=" ₹8,899 "))["price_inr"] == 8899
    assert normalize_product_doc(_base_doc(price_inr=None))["price_inr"] == 0
    assert normalize_product_doc(_base_doc(price_inr="abc"))["price_inr"] == 0
    assert normalize_product_doc(_base_doc(price_inr=True))["price_inr"] == 0


def test_newline_strings_become_lists():
    out = normalize_product_doc(_base_doc(materials="resin\npigment\n\n", gallery="a.jpg\nb.jpg"))
    assert out["materials"] == ["resin", "pigment"]
    assert out["gallery"] == ["a.jpg", "b.jpg"]


def test_none_lists_become_empty_lists():
    out = normalize_product_doc(_base_doc(materials=None, gallery=None, variants=None, tags=None))
    assert out["materials"] == []
    assert out["gallery"] == []
    assert out["variants"] == []
    assert out["tags"] == []


def test_junk_variant_entries_are_dropped_and_bad_gallery_items_removed():
    out = normalize_product_doc(
        _base_doc(
            variants=[
                {"key": "rose", "label": "Rose", "hex": "#c98", "image": "https://x/a.jpg"},
                None,
                "garbage",
                {},
            ],
            gallery=["https://x/a.jpg", None, ""],
        )
    )
    assert len(out["variants"]) == 1
    assert out["variants"][0]["key"] == "rose"
    assert out["gallery"] == ["https://x/a.jpg"]


def test_variation_options_and_a_plus_are_sanitised():
    out = normalize_product_doc(
        _base_doc(
            variation_options=[
                {"key": "shape", "label": "Shape", "values": [{"key": "round", "label": "Round", "image": None}]},
                "junk",
                {"key": None, "label": None, "values": None},
            ],
            a_plus_content="not-a-list",
        )
    )
    assert isinstance(out["variation_options"], list)
    assert all(isinstance(opt, dict) for opt in out["variation_options"])
    assert all(isinstance(opt.get("key"), str) for opt in out["variation_options"])
    assert all(isinstance(v.get("key"), str) and isinstance(v.get("label"), str)
               for opt in out["variation_options"] for v in opt["values"])
    assert out["a_plus_content"] == []


def test_bool_and_stock_are_coerced():
    out = normalize_product_doc(_base_doc(is_hero="yes", stock=None))
    assert out["is_hero"] is True
    assert out["stock"] == 5
    assert normalize_product_doc(_base_doc(stock="7"))["stock"] == 7


def test_missing_fields_are_filled():
    out = normalize_product_doc({"slug": "only-a-slug"})
    for field in REQUIRED_STR_FIELDS + REQUIRED_INT_FIELDS + REQUIRED_LIST_FIELDS:
        assert field in out


def test_input_document_is_not_mutated():
    doc = _base_doc(variants=[{"key": "rose", "label": "Rose", "hex": None, "image": None}])
    snapshot = copy.deepcopy(doc)
    normalize_product_doc(doc)
    assert doc == snapshot


def test_idempotent():
    once = normalize_product_doc(_base_doc(tagline=None, variants=[{"key": None, "image": None}]))
    twice = normalize_product_doc(once)
    assert once == twice


# ---- half-saved drafts must not be publishable ------------------------------
# The admin form opens pre-filled with name "", slug "" and price 0. The old save
# path accepted all three, which is how two nameless, unopenable, ₹0 records got
# into the catalogue on 24 Nov 2026.
def test_blank_name_or_zero_price_is_refused_in_plain_english():
    errors = save_errors(_base_doc(name="  ", price_inr=0))
    assert any("name" in e.lower() for e in errors)
    assert any("price" in e.lower() for e in errors)


def test_priced_named_product_has_no_errors():
    assert save_errors(_base_doc()) == []


def test_slugify_builds_a_web_address_from_the_name():
    assert slugify("Pink Geode Luxury Resin Round Mirror") == "pink-geode-luxury-resin-round-mirror"
    assert slugify("  Gold   & Teal  ") == "gold-teal"
    assert slugify("₹") == "art-piece"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
            except Exception as exc:  # noqa: BLE001
                failures += 1
                print(f"ERROR {name}: {type(exc).__name__}: {exc}")
    print(f"\n{'ALL PASSED' if not failures else str(failures) + ' FAILED'}")
    raise SystemExit(1 if failures else 0)
