import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2, Ticket, Heart, Search, ChevronDown, ChevronUp } from "lucide-react";

const inp = "w-full bg-ink-950 border border-white/15 focus:border-gold focus:outline-none px-3 py-2.5 text-sm text-cream outline-none";

/**
 * Customers tab: existing list + expandable per-customer breakdown of
 * (1) coupons used and (2) wishlisted items.
 */
export default function CustomersTab({ authed, users, formatDate }) {
  const [couponData, setCouponData] = useState({ codes: [], customers: [] });
  const [wishlistData, setWishlistData] = useState({ total_wishlists: 0, by_customer: [], by_product: [] });
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [expanded, setExpanded] = useState({}); // { email: bool }

  useEffect(() => {
    if (!authed) return;
    (async () => {
      setLoading(true);
      try {
        const [c, w] = await Promise.all([
          authed.get("/admin/analytics/coupon-usage"),
          authed.get("/admin/analytics/wishlist-usage"),
        ]);
        setCouponData(c.data);
        setWishlistData(w.data);
      } catch (err) {
        toast.error("Could not load customer insights");
      } finally { setLoading(false); }
    })();
  }, [authed]);

  const couponsByEmail = {};
  couponData.customers.forEach((row) => {
    couponsByEmail[row.customer_email] = couponsByEmail[row.customer_email] || [];
    couponsByEmail[row.customer_email].push(row);
  });
  const wishlistByEmail = {};
  wishlistData.by_customer.forEach((row) => { wishlistByEmail[row.user_email] = row.items; });

  const filtered = users.filter((u) => {
    if (!q) return true;
    const s = q.toLowerCase();
    return (u.name || "").toLowerCase().includes(s) || (u.email || "").toLowerCase().includes(s);
  });

  return (
    <div>
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-serif text-4xl">Customers</h1>
          <p className="mt-2 text-sm text-cream/50">{users.length} account{users.length === 1 ? "" : "s"} · tap any row to see their coupons + wishlist.</p>
        </div>
        <div className="relative">
          <Search className="w-4 h-4 text-cream/40 absolute left-3 top-1/2 -translate-y-1/2" />
          <input placeholder="Search by name or email" value={q} onChange={(e) => setQ(e.target.value)} className={`${inp} pl-9 min-w-[280px]`} />
        </div>
      </div>

      {loading && <div className="mt-6 text-cream/40 text-sm"><Loader2 className="w-4 h-4 animate-spin inline" /> Loading insights…</div>}

      {/* Global summaries */}
      {!loading && (
        <div className="mt-6 grid sm:grid-cols-2 gap-4">
          <div className="hairline p-5 bg-ink-900/50">
            <div className="flex items-center gap-2 mb-3"><Ticket className="w-4 h-4 text-gold" /><div className="text-[10px] uppercase tracking-luxury text-gold-soft">Coupons used · all-time</div></div>
            {couponData.codes.length === 0 ? <div className="text-sm text-cream/40">No coupons used yet.</div> : (
              <div className="space-y-1">
                {couponData.codes.map((c) => (
                  <div key={c.code} className="flex justify-between text-sm"><span className="font-mono text-gold">{c.code}</span><span className="text-cream/60">{c.uses} uses</span></div>
                ))}
              </div>
            )}
          </div>
          <div className="hairline p-5 bg-ink-900/50">
            <div className="flex items-center gap-2 mb-3"><Heart className="w-4 h-4 text-gold" /><div className="text-[10px] uppercase tracking-luxury text-gold-soft">Wishlist · {wishlistData.total_wishlists} saves</div></div>
            {wishlistData.by_product.length === 0 ? <div className="text-sm text-cream/40">No wishlists yet.</div> : (
              <div className="space-y-1 max-h-40 overflow-y-auto pr-2">
                {wishlistData.by_product.slice(0, 8).map((p) => (
                  <div key={p.product_id} className="flex justify-between text-sm"><span className="text-cream/80 truncate">{p.product_name}</span><span className="text-cream/60">× {p.count}</span></div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Customers list */}
      <div className="mt-6 grid gap-2">
        {filtered.length === 0 && <div className="text-sm text-cream/40 hairline p-6">No customers match.</div>}
        {filtered.map((u) => {
          const isOpen = !!expanded[u.email];
          const cUses = couponsByEmail[u.email] || [];
          const wList = wishlistByEmail[u.email] || [];
          return (
            <div key={u.email || u.id} className="hairline" data-testid={`customer-row-${u.email || u.id}`}>
              <button
                onClick={() => setExpanded((prev) => ({ ...prev, [u.email]: !prev[u.email] }))}
                className="w-full flex items-center gap-4 p-4 text-left hover:bg-ink-900/50 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-cream">{u.name || "(no name)"}</div>
                  <div className="text-xs text-cream/50">{u.email}</div>
                </div>
                <div className="hidden sm:flex items-center gap-4 text-xs text-cream/50">
                  <span title="Coupons used">🎟 {cUses.reduce((a, b) => a + b.uses, 0)}</span>
                  <span title="Wishlist items">♥ {wList.length}</span>
                </div>
                <div className="text-[10px] uppercase tracking-luxury text-cream/40">{formatDate(u.created_at)}</div>
                {isOpen ? <ChevronUp className="w-4 h-4 text-cream/60" /> : <ChevronDown className="w-4 h-4 text-cream/60" />}
              </button>
              {isOpen && (
                <div className="px-4 pb-4 grid sm:grid-cols-2 gap-4 border-t border-white/5">
                  <div className="pt-4">
                    <div className="text-[10px] uppercase tracking-luxury text-cream/50 mb-2 flex items-center gap-1"><Ticket className="w-3 h-3" /> Coupons used</div>
                    {cUses.length === 0 ? <div className="text-sm text-cream/40">— none —</div> : (
                      <div className="space-y-2">
                        {cUses.map((row) => (
                          <div key={`${row.code}-${row.customer_email}`} className="border border-white/10 p-2" data-testid={`customer-coupon-${row.code}`}>
                            <div className="flex justify-between text-sm"><span className="font-mono text-gold">{row.code}</span><span className="text-cream/70">{row.uses}×</span></div>
                            <div className="text-[11px] text-cream/50 mt-1">Total discount: ₹{row.total_discount_inr.toLocaleString("en-IN")}</div>
                            <div className="text-[10px] text-cream/40 mt-1">Orders: {row.orders.join(", ")}</div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="pt-4">
                    <div className="text-[10px] uppercase tracking-luxury text-cream/50 mb-2 flex items-center gap-1"><Heart className="w-3 h-3" /> Wishlist</div>
                    {wList.length === 0 ? <div className="text-sm text-cream/40">— nothing wishlisted —</div> : (
                      <div className="space-y-1">
                        {wList.map((item, i) => (
                          <div key={i} className="flex items-center gap-2 text-sm" data-testid={`customer-wishlist-${item.product_id}`}>
                            {item.product_image && <img src={item.product_image} alt="" className="w-8 h-8 object-cover" />}
                            <span className="text-cream/80 flex-1 truncate">{item.product_name}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
