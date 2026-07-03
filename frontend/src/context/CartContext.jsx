import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

const CartContext = createContext(null);

const STORAGE_KEY = "artyfex_cart_v1";

export const CartProvider = ({ children }) => {
  const [items, setItems] = useState(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  });
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  }, [items]);

  const addItem = (product, variantKey, quantity = 1) => {
    const variant = product.variants.find((v) => v.key === variantKey) || product.variants[0];
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
          image: variant.image || product.hero_image,
          price_inr: product.price_inr,
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

  const clear = () => setItems([]);

  const { subtotal, count } = useMemo(() => {
    const subtotal = items.reduce((s, i) => s + i.price_inr * i.quantity, 0);
    const count = items.reduce((s, i) => s + i.quantity, 0);
    return { subtotal, count };
  }, [items]);

  const shipping = items.length === 0 ? 0 : subtotal >= 25000 ? 0 : 1499;
  const total = subtotal + shipping;

  const value = {
    items, isOpen, setIsOpen, addItem, updateQty, removeItem, clear, subtotal, shipping, total, count,
  };

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
};

export const useCart = () => {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within CartProvider");
  return ctx;
};
