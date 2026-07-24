"""
NimbusPost courier integration (Task 7 / Batch 4)

Provides a lightweight async client for:
  - JWT login (auto-refresh + fallback to legacy API key)
  - Create shipment/order
  - Track by AWB
  - Cancel shipment
  - Serviceability check

Every function returns a dict shaped as:
  {"ok": bool, "data": <raw>, "error": <str or None>, "status": <http code or None>}

Env vars consumed (backend/.env):
  NIMBUSPOST_BASE_URL          (default https://api.nimbuspost.com/v1)
  NIMBUSPOST_EMAIL             (JWT flow — recommended)
  NIMBUSPOST_PASSWORD
  NIMBUSPOST_LEGACY_KEY        (fallback — old flat API key)
  NIMBUSPOST_WAREHOUSE_NAME    (dashboard-registered pickup address name)

DB collection `site_settings` key='nimbuspost' can override
warehouse_name at runtime so the owner can set it from Admin UI.
"""

from __future__ import annotations
import os
import re
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx

log = logging.getLogger("nimbuspost")

BASE_URL = os.getenv("NIMBUSPOST_BASE_URL", "https://api.nimbuspost.com/v1").rstrip("/")
EMAIL = os.getenv("NIMBUSPOST_EMAIL", "").strip()
PASSWORD = os.getenv("NIMBUSPOST_PASSWORD", "").strip()
LEGACY_KEY = os.getenv("NIMBUSPOST_LEGACY_KEY", "").strip()
WAREHOUSE_ENV = os.getenv("NIMBUSPOST_WAREHOUSE_NAME", "").strip()

_token_cache: Dict[str, Any] = {"token": None, "expires_at": datetime.min}


def is_configured() -> bool:
    """Returns True if we at least have login creds OR a legacy key."""
    return bool((EMAIL and PASSWORD) or LEGACY_KEY)


def _ok(data: Any, status: int = 200) -> Dict[str, Any]:
    return {"ok": True, "data": data, "error": None, "status": status}


def _err(msg: str, status: Optional[int] = None, data: Any = None) -> Dict[str, Any]:
    return {"ok": False, "data": data, "error": msg, "status": status}


async def _fetch_jwt() -> Optional[str]:
    """Login and cache JWT for ~23h. Returns None on failure."""
    global _token_cache
    if not (EMAIL and PASSWORD):
        return None
    if _token_cache["token"] and datetime.utcnow() < _token_cache["expires_at"]:
        return _token_cache["token"]
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                f"{BASE_URL}/users/login",
                json={"email": EMAIL, "password": PASSWORD},
            )
        if r.status_code != 200:
            log.warning("NimbusPost login failed: %s %s", r.status_code, r.text[:200])
            return None
        body = r.json()
        # NimbusPost usually returns { "status": true, "data": "<jwt>" }
        token = body.get("data") if isinstance(body.get("data"), str) else body.get("token")
        if not token:
            log.warning("NimbusPost login returned no token: %s", body)
            return None
        _token_cache["token"] = token
        _token_cache["expires_at"] = datetime.utcnow() + timedelta(hours=23)
        return token
    except Exception as exc:  # pragma: no cover
        log.exception("NimbusPost login exception: %s", exc)
        return None


async def _headers() -> Dict[str, str]:
    """Prefers JWT, falls back to legacy API key."""
    token = await _fetch_jwt()
    if not token and LEGACY_KEY:
        token = LEGACY_KEY
    if not token:
        return {"Content-Type": "application/json"}
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _pick(*vals: Any) -> str:
    for v in vals:
        if v not in (None, ""):
            return str(v)
    return ""


def _to_10digit_phone(raw: Any) -> str:
    """NimbusPost expects a 10-digit Indian phone. Strip +91 / 0091 / 91 prefix
    and any non-digit characters (spaces, dashes, brackets, dots)."""
    s = re.sub(r"\D", "", str(raw or ""))
    # Common Indian prefixes → drop
    if s.startswith("0091") and len(s) == 14:
        s = s[4:]
    elif s.startswith("91") and len(s) == 12:
        s = s[2:]
    elif s.startswith("0") and len(s) == 11:
        s = s[1:]
    return s[-10:] if len(s) >= 10 else s


def _build_ship_payload(order: dict, pickup: dict) -> dict:
    """Map an ArtyFex order document to NimbusPost's create-shipment schema.
    `pickup` is a dict with keys: warehouse_name, contact_name, address,
    city, state, pincode, phone (all optional but NimbusPost may reject if
    contact_name/address/city/state/pincode/phone are blank)."""
    cust = order.get("customer", {}) or {}
    items = order.get("items", []) or []

    # Aggregate physical dims + weight from item snapshots (fallback safe defaults)
    total_weight_g = 0
    max_len = max_wid = max_hgt = 0
    ns_items = []
    for it in items:
        qty = int(it.get("quantity") or 1)
        w = int(it.get("weight_grams") or 500)  # 500 g fallback per unit
        total_weight_g += w * qty
        max_len = max(max_len, int(it.get("length_cm") or 20))
        max_wid = max(max_wid, int(it.get("width_cm") or 20))
        max_hgt = max(max_hgt, int(it.get("height_cm") or 5))
        ns_items.append({
            "name": (it.get("product_name") or "Artwork")[:100],
            "qty": qty,
            "price": int(it.get("price_inr") or 0),
            "sku": (it.get("product_sku") or it.get("product_slug") or "ARF-DEFAULT")[:50],
        })
    total_weight_g = max(total_weight_g, 500)
    max_len = max(max_len, 10); max_wid = max(max_wid, 10); max_hgt = max(max_hgt, 3)

    is_cod = (order.get("payment_method") or "").lower() == "cod"

    address_line = _pick(cust.get("line1"), cust.get("address"))
    if cust.get("line2"):
        address_line = f"{address_line}, {cust.get('line2')}"
    if cust.get("landmark"):
        address_line = f"{address_line}, Near {cust.get('landmark')}"

    consignee_phone = _to_10digit_phone(cust.get("phone"))

    return {
        "order_number": order.get("order_number") or order.get("id"),
        "payment_type": "cod" if is_cod else "prepaid",
        "order_amount": int(order.get("total_inr") or 0),
        "package_weight": total_weight_g,      # grams
        "package_length": max_len,             # cm
        "package_breadth": max_wid,
        "package_height": max_hgt,
        "consignee": {
            "name": (cust.get("name") or "Customer")[:100],
            "address": (address_line or "-")[:200],
            "city": cust.get("city") or "-",
            "state": cust.get("state") or "-",
            "pincode": str(cust.get("pincode") or "").strip(),
            "phone": consignee_phone,
        },
        # Batch 9 — NimbusPost validation demands the FULL pickup block, not just
        # the warehouse_name. Warehouse name still sent so their dashboard can
        # link the shipment to your pre-registered warehouse for wallet accounting.
        "pickup": {
            "warehouse_name": (pickup.get("warehouse_name") or "").strip(),
            "name": (pickup.get("contact_name") or "").strip(),
            "address": (pickup.get("address") or "").strip(),
            "city": (pickup.get("city") or "").strip(),
            "state": (pickup.get("state") or "").strip(),
            "pincode": str(pickup.get("pincode") or "").strip(),
            "phone": _to_10digit_phone(pickup.get("phone")),
        },
        "order_items": ns_items or [{"name": "Artwork", "qty": 1, "price": int(order.get("total_inr") or 0), "sku": "ARF-DEFAULT"}],
    }


async def create_shipment(order: dict, pickup: dict) -> Dict[str, Any]:
    if not is_configured():
        return _err("NimbusPost not configured — set NIMBUSPOST_EMAIL/PASSWORD in Northflank env")
    warehouse_name = (pickup or {}).get("warehouse_name") or ""
    if not warehouse_name.strip():
        return _err("NimbusPost warehouse not set — configure it in Admin → Shipping → NimbusPost")
    # Validate pickup contact block up-front so the operator gets a friendly
    # error INSTEAD of a wall of NimbusPost validation messages.
    missing = [k for k, v in {
        "contact_name": pickup.get("contact_name"),
        "address": pickup.get("address"),
        "city": pickup.get("city"),
        "state": pickup.get("state"),
        "pincode": pickup.get("pincode"),
        "phone": pickup.get("phone"),
    }.items() if not (str(v or "").strip())]
    if missing:
        return _err(f"NimbusPost pickup contact incomplete — fill in {', '.join(missing)} in Admin → Shipping → NimbusPost", status=400)
    payload = _build_ship_payload(order, pickup)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{BASE_URL}/shipments", json=payload, headers=await _headers())
    except Exception as exc:
        return _err(f"NimbusPost request failed: {exc}")
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text[:500]}
    if r.status_code not in (200, 201) or (isinstance(body, dict) and body.get("status") is False):
        return _err(
            (body.get("message") if isinstance(body, dict) else None) or f"HTTP {r.status_code}",
            status=r.status_code, data=body,
        )
    return _ok(body, status=r.status_code)


async def track_shipment(awb: str) -> Dict[str, Any]:
    if not is_configured():
        return _err("NimbusPost not configured")
    if not (awb or "").strip():
        return _err("AWB is required")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(f"{BASE_URL}/shipments/track/{awb.strip()}", headers=await _headers())
    except Exception as exc:
        return _err(f"NimbusPost request failed: {exc}")
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text[:500]}
    if r.status_code >= 400:
        return _err(f"HTTP {r.status_code}", status=r.status_code, data=body)
    return _ok(body, status=r.status_code)


async def cancel_shipment(awb: str) -> Dict[str, Any]:
    if not is_configured():
        return _err("NimbusPost not configured")
    if not (awb or "").strip():
        return _err("AWB is required")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(f"{BASE_URL}/shipments/cancel", json={"awb": awb.strip()}, headers=await _headers())
    except Exception as exc:
        return _err(f"NimbusPost request failed: {exc}")
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text[:500]}
    if r.status_code >= 400:
        return _err(f"HTTP {r.status_code}", status=r.status_code, data=body)
    return _ok(body, status=r.status_code)


async def check_serviceability(pincode: str, cod: bool = False, weight_g: int = 500, origin: str = "") -> Dict[str, Any]:
    if not is_configured():
        return _err("NimbusPost not configured")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                f"{BASE_URL}/courier/serviceability",
                json={
                    "origin": str(origin or "").strip(),
                    "destination": str(pincode).strip(),
                    "payment_type": "cod" if cod else "prepaid",
                    "order_weight": int(weight_g),
                },
                headers=await _headers(),
            )
    except Exception as exc:
        return _err(f"NimbusPost request failed: {exc}")
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text[:500]}
    if r.status_code >= 400 or (isinstance(body, dict) and body.get("status") is False):
        return _err(
            (body.get("message") if isinstance(body, dict) else None) or f"HTTP {r.status_code}",
            status=r.status_code, data=body,
        )
    return _ok(body, status=r.status_code)
