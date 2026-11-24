"""Coerce a stored product document into data the API models accept.

Pure stdlib on purpose: ``server.py`` imports this at module load and the unit
tests import it alone (no Mongo, no FastAPI), so it must stay dependency-free.

Why (24 Nov 2026): ``Product`` and ``Variant`` declare required strings
(``hero_image``, ``tagline``, ``variants[].image`` …). MongoDB documents are
untyped, and past repair passes could write ``None`` into those fields — e.g. a
piece whose photos were destroyed at the host had ``variants[].image = None``.
``GET /api/products`` validates the entire list in one response model, so ONE
such document made the whole catalogue return 500. The storefront then had no
products and every admin save failed.

``normalize_product_doc`` never raises and never mutates its input: a missing or
junk value becomes the field's safe default (``""``, ``0``, ``[]``) so a bad
record degrades to "this one piece looks bare" instead of "the shop is down".
"""
from typing import Any, Dict, List

# Must mirror the required fields on server.Product.
REQUIRED_STR_FIELDS = ("slug", "name", "tagline", "description", "size", "hero_image")
REQUIRED_INT_FIELDS = ("price_inr", "mrp_inr", "craft_hours")
REQUIRED_LIST_FIELDS = ("materials", "gallery", "variants")

# Must mirror the required fields on server.Variant.
VARIANT_REQUIRED_STR_FIELDS = ("key", "label", "hex", "image")

DEFAULT_HEX = "#333333"
DEFAULT_STOCK = 5


def as_str(value: Any, default: str = "") -> str:
    """Return a clean string. None/missing -> default; numbers are stringified."""
    if value is None:
        return default
    if isinstance(value, str):
        return value
    if isinstance(value, (bool, int, float)):
        return str(value)
    return default


def as_int(value: Any, default: int = 0) -> int:
    """Return a clean int. Tolerates "₹8,899", "8899", 8899.0, True, junk."""
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):  # NaN / inf
            return default
        return int(round(value))
    if isinstance(value, str):
        digits = "".join(ch for ch in value if ch.isdigit() or ch in ".-")
        try:
            return int(float(digits))
        except (TypeError, ValueError):
            return default
    return default


def as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return default


def as_str_list(value: Any) -> List[str]:
    """Accept a list or a newline/comma-free string; drop blanks and non-strings."""
    if value is None:
        return []
    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]
    if isinstance(value, (list, tuple)):
        out = []
        for item in value:
            text = as_str(item).strip()
            if text:
                out.append(text)
        return out
    return []


def normalize_variant(value: Any) -> Dict[str, Any]:
    """Coerce one colour/size swatch into something ``Variant`` accepts."""
    variant = dict(value) if isinstance(value, dict) else {}
    variant.update(
        {
            "key": as_str(variant.get("key")),
            "label": as_str(variant.get("label")),
            "hex": as_str(variant.get("hex")) or DEFAULT_HEX,
            # A destroyed photo must read as "no photo" (empty string), never
            # None — None is what took the whole catalogue down.
            "image": as_str(variant.get("image")),
        }
    )
    for field in ("size",):
        if variant.get(field) is not None:
            variant[field] = as_str(variant.get(field)) or None
    for field in ("stock", "price_inr", "mrp_inr", "weight_grams"):
        if variant.get(field) is not None:
            variant[field] = as_int(variant.get(field))
    for field in ("length_cm", "width_cm", "height_cm"):
        if variant.get(field) is not None:
            try:
                variant[field] = float(variant[field])
            except (TypeError, ValueError):
                variant[field] = None
    return variant


def _normalize_variation_options(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    options = []
    for raw in value:
        if not isinstance(raw, dict):
            continue
        values = []
        for item in raw.get("values") or []:
            if not isinstance(item, dict):
                continue
            entry = dict(item)
            entry["key"] = as_str(entry.get("key"))
            entry["label"] = as_str(entry.get("label")) or entry["key"]
            entry["image"] = as_str(entry.get("image")) or None
            entry["price_delta_inr"] = as_int(entry.get("price_delta_inr"))
            if entry.get("hex") is not None:
                entry["hex"] = as_str(entry.get("hex")) or None
            if entry.get("stock") is not None:
                entry["stock"] = as_int(entry.get("stock"))
            values.append(entry)
        option = dict(raw)
        option["key"] = as_str(option.get("key")) or as_str(option.get("label")).lower().replace(" ", "_")
        option["label"] = as_str(option.get("label")) or option["key"]
        option["type"] = as_str(option.get("type"), "select") or "select"
        option["values"] = values
        options.append(option)
    return options


def _normalize_a_plus(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    return [dict(block) for block in value if isinstance(block, dict)]


def normalize_product_doc(doc: Any) -> Dict[str, Any]:
    """Return a copy of ``doc`` with every required field at a safe value."""
    out: Dict[str, Any] = dict(doc) if isinstance(doc, dict) else {}

    for field in REQUIRED_STR_FIELDS:
        out[field] = as_str(out.get(field))
    for field in REQUIRED_INT_FIELDS:
        out[field] = as_int(out.get(field))
    for field in REQUIRED_LIST_FIELDS:
        if field == "variants":
            raw_variants = out.get(field)
            if not isinstance(raw_variants, (list, tuple)):
                raw_variants = []
            # A swatch that carries no key, no label and no photo is unusable
            # noise (often a placeholder row from a half-finished form) — drop it.
            out[field] = [
                variant
                for variant in (normalize_variant(v) for v in raw_variants if isinstance(v, dict))
                if variant["key"] or variant["label"] or variant["image"]
            ]
        else:
            out[field] = as_str_list(out.get(field))

    out["is_hero"] = as_bool(out.get("is_hero"))
    out["stock"] = as_int(out.get("stock"), DEFAULT_STOCK)
    out["tags"] = as_str_list(out.get("tags"))
    out["variation_options"] = _normalize_variation_options(out.get("variation_options"))
    out["a_plus_content"] = _normalize_a_plus(out.get("a_plus_content"))

    for field in ("category", "hsn_code", "sku", "amazon_url"):
        if out.get(field) is not None:
            out[field] = as_str(out.get(field)).strip() or None
    for field in ("weight_grams",):
        if out.get(field) is not None:
            out[field] = as_int(out.get(field))
    for field in ("length_cm", "width_cm", "height_cm"):
        if out.get(field) is not None:
            try:
                out[field] = float(out[field])
            except (TypeError, ValueError):
                out[field] = None

    return out


def slugify(value: str) -> str:
    """Turn a product name into a web address, e.g. "Gold & Teal" -> "gold-teal"."""
    text = as_str(value).lower().strip()
    text = "".join(ch if ch.isalnum() else "-" for ch in text)
    while "--" in text:
        text = text.replace("--", "-")
    return text.strip("-") or "art-piece"


def save_errors(doc: Any) -> List[str]:
    """Plain-English reasons a product cannot be saved yet (empty list = fine).

    The admin form opens with an empty name, empty slug and a ₹0 price, and the
    old save path stored exactly that — a nameless, unopenable, unpriced record
    that showed up nowhere. These messages are displayed to the owner verbatim.
    """
    data = normalize_product_doc(doc)
    errors = []
    if not data["name"].strip():
        errors.append("Please give this piece a name before saving.")
    if data["price_inr"] <= 0:
        errors.append("Please set the selling price in ₹ — a ₹0 piece cannot be published.")
    return errors


def fields_needing_repair(original: Any, normalized: Dict[str, Any]) -> Dict[str, Any]:
    """Return only the keys whose stored value differs from the normalized one.

    Used by the startup heal pass so a fix writes back the broken fields (or
    nothing at all when the document is already healthy).
    """
    if not isinstance(original, dict):
        return dict(normalized)
    changed = {}
    for key, value in normalized.items():
        if original.get(key) != value:
            changed[key] = value
    return changed
