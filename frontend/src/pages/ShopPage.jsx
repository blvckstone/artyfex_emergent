import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ArrowUpRight, Heart } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { fetchProducts } from "@/lib/api";
import { useCart } from "@/context/CartContext";
import { useWishlist } from "@/context/WishlistContext";
import { useAuth } from "@/context/AuthContext";

const formatINR = (n) => `₹${n.toLocaleString("en-IN")}`;

export default function ShopPage() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const { addItem } = useCart();
  const { has, toggle } = useWishlist();
  const { user, openAuth } = useAuth();

  useEffect(() => {
    fetchProducts().then(setProducts).finally(() => setLoading(false));
  }, []);

  const items = filter === "all" ? products : filter === "hero" ? products.filter(p => p.is_hero) : products.filter(p => !p.is_hero);

  const onWishlist = async (e, p) => {
    e.preventDefault();
    e.stopPropagation();
    if (!user) { openAuth("login"); toast.info("Sign in to save pieces"); return; }
    try {
      const action = await toggle(p);
      toast.success(action === "added" ? "Saved to wishlist" : "Removed from wishlist");
    } catch { toast.error("Could not update wishlist"); }
  };

  return (
    <div className="min-h-screen bg-ink-950 text-cream">
      <Navbar />
      <div className="max-w-[1440px] mx-auto px-6 md:px-12 lg:px-16 pt-32 pb-16">
        <div className="flex items-center gap-3 mb-6">
          <span className="gold-line w-10" />
          <span className="text-[10px] uppercase tracking-luxury text-gold-soft">The Full Atelier</span>
        </div>
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6">
          <h1 className="font-serif text-5xl md:text-6xl lg:text-7xl leading-[0.95] text-balance">
            Every <span className="italic font-display text-gold">piece</span> we pour.
          </h1>
          <div className="flex gap-2">
            {[
              { k: "all", label: "All" },
              { k: "hero", label: "Statement" },
              { k: "companion", label: "Companion" },
            ].map((f) => (
              <button key={f.k} data-testid={`shop-filter-${f.k}`} onClick={() => setFilter(f.k)}
                className={`px-4 py-2.5 text-xs uppercase tracking-luxury border ${filter===f.k?"border-gold text-gold bg-gold/5":"border-white/10 text-cream/60 hover:border-white/30"}`}>
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="mt-16 text-cream/40">Loading atelier…</div>
        ) : (
          <div className="mt-16 grid md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8">
            {items.map((p, i) => {
              const inWish = has(p.id);
              const lowStock = p.stock > 0 && p.stock <= 3;
              const out = p.stock <= 0;
              return (
                <motion.div key={p.id} data-testid={`shop-card-${p.slug}`}
                  initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, amount: 0.1 }} transition={{ duration: 0.7, delay: (i%3)*0.08 }}
                  className="group relative bg-ink-900 border border-white/5 hover:border-gold/30 transition-colors">
                  <Link to={`/product/${p.slug}`} className="block" data-testid={`shop-card-link-${p.slug}`}>
                    <div className="aspect-[4/5] overflow-hidden relative">
                      <img src={p.hero_image} alt={p.name} className="w-full h-full object-cover transition-transform duration-[1200ms] group-hover:scale-105" />
                      {p.is_hero && <div className="absolute top-3 left-3 glass-gold px-3 py-1 text-[10px] uppercase tracking-luxury text-gold">Signature</div>}
                      {out && <div className="absolute top-3 right-14 glass px-3 py-1 text-[10px] uppercase tracking-luxury text-red-400">Sold out</div>}
                      {!out && lowStock && <div className="absolute top-3 right-14 glass px-3 py-1 text-[10px] uppercase tracking-luxury text-yellow-400">Only {p.stock} left</div>}
                      <button
                        data-testid={`shop-wishlist-${p.slug}`}
                        onClick={(e) => onWishlist(e, p)}
                        className={`absolute top-3 right-3 w-9 h-9 flex items-center justify-center backdrop-blur-md border transition-colors ${
                          inWish ? "bg-gold/20 border-gold text-gold" : "bg-black/40 border-white/10 text-cream/70 hover:text-gold hover:border-gold/40"
                        }`}
                        aria-label={inWish ? "Remove from wishlist" : "Add to wishlist"}
                      >
                        <Heart className={`w-4 h-4 ${inWish ? "fill-gold" : ""}`} />
                      </button>
                    </div>
                  </Link>
                  <div className="p-6">
                    <div className="text-[10px] uppercase tracking-luxury text-gold-soft">{p.size}</div>
                    <Link to={`/product/${p.slug}`} className="block">
                      <h3 className="mt-3 font-serif text-2xl leading-tight hover:text-gold transition-colors">{p.name.split(" — ")[0]}</h3>
                    </Link>
                    <p className="mt-2 text-sm text-cream/50 italic font-serif">{p.tagline}</p>
                    <div className="mt-5 flex items-center justify-between">
                      <div>
                        <div className="font-serif text-2xl">{formatINR(p.price_inr)}</div>
                        {p.mrp_inr > p.price_inr && (
                          <div className="text-[10px] text-cream/40">
                            <span className="line-through">{formatINR(p.mrp_inr)}</span>
                            <span className="ml-2 text-gold">{Math.round(((p.mrp_inr - p.price_inr)/p.mrp_inr)*100)}% off</span>
                          </div>
                        )}
                      </div>
                      <button data-testid={`shop-add-${p.slug}`} onClick={() => addItem(p, p.variants[0].key, 1)}
                        className="inline-flex items-center gap-2 text-[10px] uppercase tracking-luxury text-gold hover:text-cream">
                        Add <ArrowUpRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    <div className="mt-4 flex gap-2">
                      {p.variants.map((v) => (
                        <span key={v.key} title={v.label} className="w-4 h-4 rounded-full ring-1 ring-white/20"
                          style={{ background: `radial-gradient(circle at 30% 30%, ${v.hex}, #0a0a0a 80%)` }} />
                      ))}
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
      <Footer />
    </div>
  );
}
