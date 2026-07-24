import React, { createContext, useContext, useEffect, useMemo, useState, useRef } from "react";
import { api } from "@/lib/api";

const CartContext = createContext(null);

const STORAGE_KEY = "artyfex_cart_v1";
const COUPON_KEY = "artyfex_coupon_v1";

/**
 * Cart items now carry:
 *  - product_id, product_slug, product_name
 *  - variant_key, variant_label
 *  - image (variant.image || product.hero_image)
 *  - price_inr (variant.price_inr || product.price_inr — resolved when item added)
 *  - variant_size (optional — for display)
 *  - quantity
 *
 * `coupon` shape (persisted):
 *  { code, type: 'percentage' | 'flat', value, discount_inr, description }
 */
export const CartProvider = ({ children }) => {
  const [items, setItems] = useState(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  });
  const [coupon, setCoupon] = useState(() => {
    try {
      const raw = localStorage.getItem(COUPON_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  });
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  }, [items]);

  useEffect(() => {
    if (coupon) localStorage.setItem(COUPON_KEY, JSON.stringify(coupon));
    else localStorage.removeItem(COUPON_KEY);
  }, [coupon]);

  const addItem = (product, variantKey, quantity = 1, selectedOptions = null, notes = null) => {
    const variant = product.variants.find((v) => v.key === variantKey) || product.variants[0];
    // Resolve per-variant overrides with fallback to product-level
    const basePrice = variant?.price_inr ?? product.price_inr;
    const image = variant?.image || product.hero_image;
    const variantSize = variant?.size || null;
    // Task 3 — compute price delta from selected extra options (Shape/Frame/Gift…)
    const options = selectedOptions || {};
    const optionLabels = {};
    let optionsDelta = 0;
    (product.variation_options || []).forEach((opt) => {
      const chosenKey = options[opt.key];
      if (!chosenKey) return;
      const match = (opt.values || []).find((v) => v.key === chosenKey);
      if (match) {
        optionLabels[opt.label || opt.key] = match.label || match.key;
        optionsDelta += Number(match.price_delta_inr || 0);
      }
    });
    const finalPrice = basePrice + optionsDelta;
    // Same product + variant + option-set + notes → treat as same cart line (merge qty)
    const cleanNotes = notes && typeof notes === "object" ? Object.fromEntries(Object.entries(notes).filter(([, v]) => (v || "").toString().trim())) : {};
    const optionsKey = JSON.stringify(options || {});
    const notesKey = JSON.stringify(cleanNotes);
    setItems((prev) => {
      const idx = prev.findIndex(
        (i) => i.product_id === product.id
          && i.variant_key === variant.key
          && JSON.stringify(i.selected_options || {}) === optionsKey
          && JSON.stringify(i.notes || {}) === notesKey,
      );
      if (idx >= 0) {
        const clone = [...prev];
        clone[idx] = { ...clone[idx], quantity: clone[idx].quantity + quantity };
        return clone;
      }
      return [
        ...prev,
        {
          product_id: product.id,
          product_slug: product.slug,
          product_name: product.name,
          variant_key: variant.key,
          variant_label: variant.label,
          variant_size: variantSize,
          image,
          price_inr: finalPrice,
          quantity,
          selected_options: options,
          selected_options_labels: optionLabels,
          options_price_delta_inr: optionsDelta,
          notes: cleanNotes,
        },
      ];
    });
    setIsOpen(true);
  };

  const updateQty = (product_id, variant_key, quantity) => {
    setItems((prev) =>
      prev
        .map((i) => (i.product_id === product_id && i.variant_key === variant_key ? { ...i, quantity } : i))
        .filter((i) => i.quantity > 0),
    );
  };

  const removeItem = (product_id, variant_key) => {
    setItems((prev) => prev.filter((i) => !(i.product_id === product_id && i.variant_key === variant_key)));
  };

  const clear = () => { setItems([]); setCoupon(null); };
  const clearCoupon = () => setCoupon(null);
  const applyCoupon = (couponPayload) => setCoupon(couponPayload);

  const { subtotal, count } = useMemo(() => {
    const subtotal = items.reduce((s, i) => s + i.price_inr * i.quantity, 0);
    const count = items.reduce((s, i) => s + i.quantity, 0);
    return { subtotal, count };
  }, [items]);

  // Recompute discount client-side each render (server validates on order create too)
  const discount = useMemo(() => {
    if (!coupon || !items.length || subtotal <= 0) return 0;
    // Enforce min cart on the client for immediate UX; backend enforces authoritatively
    if (coupon.min_cart_inr && subtotal < coupon.min_cart_inr) return 0;
    if (coupon.type === "percentage") {
      return Math.floor(Math.max(0, Math.min(subtotal, subtotal * (coupon.value / 100))));
    }
    return Math.floor(Math.max(0, Math.min(subtotal, coupon.value)));
  }, [coupon, items.length, subtotal]);

  const discountedSubtotal = Math.max(0, subtotal - discount);
  const shipping = items.length === 0 ? 0 : discountedSubtotal >= 25000 ? 0 : 1499;

  // ---------- Phase A (Jul 2025) · GST computation ----------
  // GST is EXCLUSIVE — added on top of the shown INR price (standard e-commerce practice).
  // Total = subtotal - discount + shipping + gst
  const [taxBreakdown, setTaxBreakdown] = useState({
    gst_total_inr: 0, cgst_inr: 0, sgst_inr: 0, igst_inr: 0,
    gst_lines: [], intra_state: false, ship_state: null,
  });
  const [shipState, setShipState] = useState(null);
  const taxReqRef = useRef(0);
  useEffect(() => {
    if (!items.length) {
      setTaxBreakdown({ gst_total_inr: 0, cgst_inr: 0, sgst_inr: 0, igst_inr: 0, gst_lines: [], intra_state: false, ship_state: shipState });
      return;
    }
    const rid = ++taxReqRef.current;
    api.post("/cart/compute-tax", {
      items: items.map((i) => ({ product_id: i.product_id, variant_key: i.variant_key, quantity: i.quantity })),
      ship_state: shipState || null,
    })
      .then(({ data }) => {
        if (rid !== taxReqRef.current) return;
        setTaxBreakdown({
          gst_total_inr: data.gst_total_inr || 0,
          cgst_inr: data.cgst_inr || 0,
          sgst_inr: data.sgst_inr || 0,
          igst_inr: data.igst_inr || 0,
          gst_lines: data.gst_lines || [],
          intra_state: !!data.intra_state,
          ship_state: data.ship_state || shipState || null,
        });
      })
      .catch(() => {
        if (rid !== taxReqRef.current) return;
        setTaxBreakdown({ gst_total_inr: 0, cgst_inr: 0, sgst_inr: 0, igst_inr: 0, gst_lines: [], intra_state: false, ship_state: shipState });
      });
  }, [items, shipState]);

  // Scale tax proportionally when a discount is applied so the GST reflects the payable subtotal
  const gstScale = subtotal > 0 ? discountedSubtotal / subtotal : 0;
  const gstIncluded = Math.round((taxBreakdown.gst_total_inr || 0) * gstScale);
  const cgstIncluded = Math.round((taxBreakdown.cgst_inr || 0) * gstScale);
  const sgstIncluded = Math.round((taxBreakdown.sgst_inr || 0) * gstScale);
  const igstIncluded = Math.round((taxBreakdown.igst_inr || 0) * gstScale);

  // Total INCLUDES GST (exclusive treatment)
  const total = discountedSubtotal + shipping + gstIncluded;

  const value = {
    items, isOpen, setIsOpen,
    addItem, updateQty, removeItem, clear,
    subtotal, shipping, total, count,
    coupon, discount, applyCoupon, clearCoupon,
    // GST (exclusive treatment — added on top)
    gstIncluded, cgstIncluded, sgstIncluded, igstIncluded,
    gstIntraState: taxBreakdown.intra_state,
    gstLines: taxBreakdown.gst_lines,
    setShipState, shipState,
  };

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
};

export const useCart = () => {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within CartProvider");
  return ctx;
};
