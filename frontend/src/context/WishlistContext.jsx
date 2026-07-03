import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";

const WishlistContext = createContext(null);

export const WishlistProvider = ({ children }) => {
  const { user, authedApi, ready } = useAuth();
  const [ids, setIds] = useState(new Set());
  const [items, setItems] = useState([]); // full items with product data
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!user) { setIds(new Set()); setItems([]); return; }
    setLoading(true);
    try {
      const { data } = await authedApi().get("/me/wishlist");
      setItems(data);
      setIds(new Set(data.map((x) => x.product_id)));
    } catch {
      // silent
    } finally { setLoading(false); }
  }, [user, authedApi]);

  useEffect(() => { if (ready) refresh(); }, [ready, refresh]);

  const has = (productId) => ids.has(productId);

  const toggle = async (product) => {
    if (!user) throw new Error("auth_required");
    const a = authedApi();
    if (ids.has(product.id)) {
      await a.delete(`/me/wishlist/${product.id}`);
      setIds((s) => { const n = new Set(s); n.delete(product.id); return n; });
      setItems((arr) => arr.filter((x) => x.product_id !== product.id));
      return "removed";
    }
    await a.post(`/me/wishlist/${product.id}`);
    setIds((s) => { const n = new Set(s); n.add(product.id); return n; });
    setItems((arr) => [{ product_id: product.id, added_at: new Date().toISOString(), product }, ...arr]);
    return "added";
  };

  return (
    <WishlistContext.Provider value={{ ids, items, loading, has, toggle, refresh }}>
      {children}
    </WishlistContext.Provider>
  );
};

export const useWishlist = () => {
  const ctx = useContext(WishlistContext);
  if (!ctx) throw new Error("useWishlist must be used within WishlistProvider");
  return ctx;
};
