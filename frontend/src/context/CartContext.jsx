import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

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

  const addItem = (product, variantKey, quantity = 1) => {
    const variant = product.variants.find((v) => v.key === variantKey) || product.variants[0];
    // Resolve per-variant overrides with fallback to product-level
    const price = variant?.price_inr ?? product.price_inr;
    const image = variant?.image || product.hero_image;
    const variantSize = variant?.size || null;
    setItems((prev) => {
      const idx = prev.findIndex((i) => i.product_id === product.id && i.variant_key === variant.key);
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
          price_inr: price,
          quantity,
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
  const total = discountedSubtotal + shipping;

  const value = {
    items, isOpen, setIsOpen,
    addItem, updateQty, removeItem, clear,
    subtotal, shipping, total, count,
    coupon, discount, applyCoupon, clearCoupon,
  };

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
};

export const useCart = () => {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within CartProvider");
  return ctx;
};
