import React, { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ArrowUpRight, Heart, Search, SlidersHorizontal, X } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import SEO from "@/components/SEO";
import { fetchProducts } from "@/lib/api";
import { useCart } from "@/context/CartContext";
import { displayableVariants } from "@/lib/utils";
import { useWishlist } from "@/context/WishlistContext";
import { useAuth } from "@/context/AuthContext";

const formatINR = (n) => `₹${(n || 0).toLocaleString("en-IN")}`;

// ---------- helpers ----------
const productMinMaxPrice = (p) => {
  const prices = (p.variants || [])
    .map((v) => v.price_inr)
    .filter((n) => typeof n === "number" && n > 0);
  if (!prices.length) return [p.price_inr, p.price_inr];
  return [Math.min(...prices, p.price_inr), Math.max(...prices, p.price_inr)];
};

const productSizes = (p) => {
  const set = new Set();
  (p.variants || []).forEach((v) => { if (v.size) set.add(v.size); });
  if (p.size) set.add(p.size);
  return [...set];
};

const productColours = (p) => (p.variants || []).map((v) => ({ hex: v.hex, label: v.label })).filter((v) => v.hex);

// ---------- component ----------
export default function ShopPage() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const { addItem } = useCart();
  const { has, toggle } = useWishlist();
  const { user, openAuth } = useAuth();

  // Filter/search state
  const [search, setSearch] = useState("");
  const [priceRange, setPriceRange] = useState([0, 100000]);
  const [selectedSizes, setSelectedSizes] = useState(new Set());
  const [selectedColours, setSelectedColours] = useState(new Set()); // stores hex strings
  const [inStockOnly, setInStockOnly] = useState(false);
  const [sortBy, setSortBy] = useState("featured"); // featured | price-asc | price-desc | newest
  const [category, setCategory] = useState("all"); // all | hero | companion
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    fetchProducts().then((data) => {
      setProducts(data);
      // Auto-fit price slider to catalog range
      if (data.length) {
        const all = data.flatMap(productMinMaxPrice);
        setPriceRange([Math.min(...all), Math.max(...all)]);
      }
    }).finally(() => setLoading(false));
  }, []);

  // Derive filter facets
  const facets = useMemo(() => {
    const sizes = new Set();
    const colourMap = new Map(); // hex -> label
    let min = Infinity, max = 0;
    products.forEach((p) => {
      productSizes(p).forEach((s) => sizes.add(s));
      productColours(p).forEach(({ hex, label }) => { if (!colourMap.has(hex)) colourMap.set(hex, label); });
      const [pmin, pmax] = productMinMaxPrice(p);
      if (pmin < min) min = pmin;
      if (pmax > max) max = pmax;
    });
    return {
      sizes: [...sizes].sort(),
      colours: [...colourMap.entries()].map(([hex, label]) => ({ hex, label })),
      priceMin: Number.isFinite(min) ? min : 0,
      priceMax: max || 100000,
    };
  }, [products]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    let out = products.filter((p) => {
      // Category
      if (category === "hero" && !p.is_hero) return false;
      if (category === "companion" && p.is_hero) return false;
      // Search — name, tagline, description, materials
      if (q) {
        const hay = [
          p.name, p.tagline, p.description,
          ...(p.materials || []),
          ...(p.variants || []).map((v) => v.label),
        ].join(" ").toLowerCase();
        if (!hay.includes(q)) return false;
      }
      // Price
      const [pmin, pmax] = productMinMaxPrice(p);
      if (pmax < priceRange[0] || pmin > priceRange[1]) return false;
      // Sizes
      if (selectedSizes.size > 0) {
        const sizes = productSizes(p);
        if (![...selectedSizes].some((s) => sizes.includes(s))) return false;
      }
      // Colours
      if (selectedColours.size > 0) {
        const hexes = productColours(p).map((c) => c.hex);
        if (![...selectedColours].some((h) => hexes.includes(h))) return false;
      }
      // Stock
      if (inStockOnly && (p.stock ?? 0) <= 0) return false;
      return true;
    });

    // Sort
    if (sortBy === "price-asc") {
      out = [...out].sort((a, b) => productMinMaxPrice(a)[0] - productMinMaxPrice(b)[0]);
    } else if (sortBy === "price-desc") {
      out = [...out].sort((a, b) => productMinMaxPrice(b)[1] - productMinMaxPrice(a)[1]);
    } else if (sortBy === "newest") {
      out = [...out].sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""));
    } else {
      // featured — hero first, then by created_at desc
      out = [...out].sort((a, b) => {
        if (a.is_hero && !b.is_hero) return -1;
        if (!a.is_hero && b.is_hero) return 1;
        return (b.created_at || "").localeCompare(a.created_at || "");
      });
    }
    return out;
  }, [products, search, category, priceRange, selectedSizes, selectedColours, inStockOnly, sortBy]);

  const toggleSize = (s) => setSelectedSizes((prev) => {
    const n = new Set(prev); n.has(s) ? n.delete(s) : n.add(s); return n;
  });
  const toggleColour = (hex) => setSelectedColours((prev) => {
    const n = new Set(prev); n.has(hex) ? n.delete(hex) : n.add(hex); return n;
  });

  const clearAll = () => {
    setSearch(""); setSelectedSizes(new Set()); setSelectedColours(new Set());
    setInStockOnly(false); setSortBy("featured"); setCategory("all");
    setPriceRange([facets.priceMin, facets.priceMax]);
  };

  const activeFilterCount =
    (search ? 1 : 0) +
    selectedSizes.size +
    selectedColours.size +
    (inStockOnly ? 1 : 0) +
    (category !== "all" ? 1 : 0) +
    (priceRange[0] !== facets.priceMin || priceRange[1] !== facets.priceMax ? 1 : 0);

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
      <SEO
        title="Luxury Handmade Mirrors & Modern Wall Art · Shop the ArtyFex Atelier | Mumbai"
        description={'Shop luxury handmade resin & crystal mirrors, modern statement wall art and bespoke furniture — hand-poured in Mumbai. One-of-a-kind pieces with insured white-glove delivery across India.'}
        path="/shop"
        jsonLd={{
          "@context": "https://schema.org",
          "@graph": [
            {
              "@type": "CollectionPage",
              "name": "ArtyFex Collection — Luxury Handmade Mirrors",
              "url": "https://www.artyfex.in/shop",
              "description": "Every handmade resin & crystal luxury mirror and modern wall-art piece from the ArtyFex atelier, Mumbai.",
              "isPartOf": { "@id": "https://www.artyfex.in/#website" },
              "about": ["luxury mirrors", "modern art", "handmade resin", "bespoke furniture"],
            },
            {
              "@type": "BreadcrumbList",
              "itemListElement": [
                { "@type": "ListItem", "position": 1, "name": "Home", "item": "https://www.artyfex.in" },
                { "@type": "ListItem", "position": 2, "name": "Shop", "item": "https://www.artyfex.in/shop" },
              ],
            },
          ],
        }}
      />
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
        </div>

        {/* Search + sort bar */}
        <div className="mt-10 flex flex-col md:flex-row gap-3 md:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-cream/40" />
            <input
              data-testid="shop-search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search pieces — name, material, colour…"
              className="w-full bg-ink-900 border border-white/10 focus:border-gold outline-none pl-11 pr-10 py-3.5 text-sm text-cream placeholder-cream/40"
            />
            {search && (
              <button onClick={() => setSearch("")} className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-cream/40 hover:text-gold" aria-label="Clear search">
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
          <button
            data-testid="shop-toggle-filters"
            onClick={() => setShowFilters((s) => !s)}
            className={`inline-flex items-center gap-2 px-5 py-3.5 border text-xs uppercase tracking-luxury transition-colors ${
              showFilters || activeFilterCount > 0 ? "border-gold text-gold bg-gold/5" : "border-white/10 text-cream/70 hover:border-gold/40"
            }`}
          >
            <SlidersHorizontal className="w-3.5 h-3.5" /> Filters
            {activeFilterCount > 0 && <span className="ml-1 text-[10px] bg-gold text-ink-950 rounded-full min-w-[18px] h-[18px] px-1.5 inline-flex items-center justify-center font-medium">{activeFilterCount}</span>}
          </button>
          <select
            data-testid="shop-sort"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="bg-ink-900 border border-white/10 focus:border-gold outline-none px-4 py-3.5 text-xs uppercase tracking-luxury text-cream/80"
          >
            <option value="featured">Sort · Featured</option>
            <option value="price-asc">Price · Low → High</option>
            <option value="price-desc">Price · High → Low</option>
            <option value="newest">Newest first</option>
          </select>
        </div>

        <div className="mt-8 grid lg:grid-cols-[280px_1fr] gap-8">
          {/* Filter sidebar */}
          <aside
            data-testid="shop-filter-panel"
            className={`${showFilters ? "block" : "hidden"} lg:block bg-ink-900 border border-white/5 p-6 h-fit lg:sticky lg:top-28`}
          >
            <div className="flex items-center justify-between mb-6">
              <div className="text-[10px] uppercase tracking-luxury text-gold-soft">Refine</div>
              {activeFilterCount > 0 && (
                <button data-testid="shop-clear-filters" onClick={clearAll} className="text-[10px] uppercase tracking-luxury text-cream/50 hover:text-red-400">Clear all</button>
              )}
            </div>

            {/* Category */}
            <FilterGroup title="Category">
              {[
                { k: "all", label: "All pieces" },
                { k: "hero", label: "Signature" },
                { k: "companion", label: "Companion" },
              ].map((c) => (
                <label key={c.k} className="flex items-center gap-2.5 text-sm cursor-pointer">
                  <input
                    type="radio"
                    name="cat"
                    checked={category === c.k}
                    onChange={() => setCategory(c.k)}
                    data-testid={`shop-filter-cat-${c.k}`}
                    className="accent-gold w-4 h-4"
                  />
                  <span className={category === c.k ? "text-gold" : "text-cream/70"}>{c.label}</span>
                </label>
              ))}
            </FilterGroup>

            {/* Price */}
            <FilterGroup title={`Price · ${formatINR(priceRange[0])} – ${formatINR(priceRange[1])}`}>
              <div className="space-y-3">
                <input
                  type="range"
                  min={facets.priceMin}
                  max={facets.priceMax}
                  step={500}
                  value={priceRange[0]}
                  onChange={(e) => setPriceRange([Math.min(+e.target.value, priceRange[1]), priceRange[1]])}
                  data-testid="shop-filter-price-min"
                  className="w-full accent-gold"
                />
                <input
                  type="range"
                  min={facets.priceMin}
                  max={facets.priceMax}
                  step={500}
                  value={priceRange[1]}
                  onChange={(e) => setPriceRange([priceRange[0], Math.max(+e.target.value, priceRange[0])])}
                  data-testid="shop-filter-price-max"
                  className="w-full accent-gold"
                />
                <div className="flex justify-between text-[10px] uppercase tracking-luxury text-cream/40">
                  <span>{formatINR(facets.priceMin)}</span>
                  <span>{formatINR(facets.priceMax)}</span>
                </div>
              </div>
            </FilterGroup>

            {/* Sizes */}
            {facets.sizes.length > 0 && (
              <FilterGroup title="Size">
                <div className="flex flex-wrap gap-2">
                  {facets.sizes.map((s) => (
                    <button
                      key={s}
                      data-testid={`shop-filter-size-${s}`}
                      onClick={() => toggleSize(s)}
                      className={`px-3 py-1.5 text-[11px] border transition-colors ${
                        selectedSizes.has(s)
                          ? "border-gold text-gold bg-gold/10"
                          : "border-white/10 text-cream/70 hover:border-gold/40 hover:text-gold"
                      }`}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </FilterGroup>
            )}

            {/* Colours */}
            {facets.colours.length > 0 && (
              <FilterGroup title="Colour">
                <div className="flex flex-wrap gap-3">
                  {facets.colours.map((c) => (
                    <button
                      key={c.hex}
                      data-testid={`shop-filter-colour-${c.hex}`}
                      onClick={() => toggleColour(c.hex)}
                      title={c.label}
                      aria-label={c.label}
                      className={`relative w-8 h-8 rounded-full transition-all ${
                        selectedColours.has(c.hex)
                          ? "ring-2 ring-gold ring-offset-2 ring-offset-ink-900"
                          : "ring-1 ring-white/20 hover:ring-white/40"
                      }`}
                      style={{ background: `radial-gradient(circle at 30% 30%, ${c.hex}, #0a0a0a 80%)` }}
                    />
                  ))}
                </div>
              </FilterGroup>
            )}

            {/* Stock */}
            <FilterGroup title="Availability" isLast>
              <label className="flex items-center gap-2.5 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={inStockOnly}
                  onChange={(e) => setInStockOnly(e.target.checked)}
                  data-testid="shop-filter-stock"
                  className="accent-gold w-4 h-4"
                />
                <span className={inStockOnly ? "text-gold" : "text-cream/70"}>In stock only</span>
              </label>
            </FilterGroup>
          </aside>

          {/* Product grid */}
          <div>
            <div className="mb-6 text-xs text-cream/50 uppercase tracking-luxury" data-testid="shop-count">
              {loading ? "Loading atelier…" : `${filtered.length} piece${filtered.length === 1 ? "" : "s"}`}
              {activeFilterCount > 0 && !loading ? " · filtered" : ""}
            </div>

            {!loading && filtered.length === 0 ? (
              <div data-testid="shop-empty" className="border border-white/5 py-24 text-center bg-ink-900">
                <div className="font-serif text-2xl text-cream">No pieces match your filters</div>
                <p className="mt-3 text-sm text-cream/50">Try widening the price range or clearing colours.</p>
                <button onClick={clearAll} className="mt-8 inline-flex text-xs uppercase tracking-luxury text-gold border-b border-gold/40 pb-1">
                  Clear all filters
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-3 sm:gap-6 lg:gap-8">
                {filtered.map((p, i) => {
                  const inWish = has(p.id);
                  const lowStock = p.stock > 0 && p.stock <= 3;
                  const out = p.stock <= 0;
                  const [pMin, pMax] = productMinMaxPrice(p);
                  const showRange = pMin !== pMax;
                  return (
                    <motion.div key={p.id} data-testid={`shop-card-${p.slug}`}
                      initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
                      viewport={{ once: true, amount: 0.1 }} transition={{ duration: 0.6, delay: (i%3)*0.06 }}
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
                      <div className="p-3 sm:p-6">
                        <div className="text-[9px] sm:text-[10px] uppercase tracking-luxury text-gold-soft truncate">{p.size}</div>
                        <Link to={`/product/${p.slug}`} className="block">
                          <h3 className="mt-2 sm:mt-3 font-serif text-base sm:text-2xl leading-tight hover:text-gold transition-colors line-clamp-2">{p.name.split(" — ")[0]}</h3>
                        </Link>
                        <p className="hidden sm:block mt-2 text-sm text-cream/50 italic font-serif">{p.tagline}</p>
                        <div className="mt-3 sm:mt-5 flex items-center justify-between gap-2 flex-wrap">
                          <div className="min-w-0">
                            <div className="font-serif text-base sm:text-2xl">
                              {showRange ? `${formatINR(pMin)} – ${formatINR(pMax)}` : formatINR(p.price_inr)}
                            </div>
                            {p.mrp_inr > p.price_inr && !showRange && (
                              <div className="text-[9px] sm:text-[10px] text-cream/40">
                                <span className="line-through">{formatINR(p.mrp_inr)}</span>
                                <span className="ml-2 text-gold">{Math.round(((p.mrp_inr - p.price_inr)/p.mrp_inr)*100)}% off</span>
                              </div>
                            )}
                          </div>
                          <button data-testid={`shop-add-${p.slug}`}
                            disabled={out}
                            onClick={() => addItem(p, p.variants[0].key, 1)}
                            className="inline-flex items-center gap-1 sm:gap-2 text-[9px] sm:text-[10px] uppercase tracking-luxury text-gold hover:text-cream disabled:opacity-40 disabled:cursor-not-allowed whitespace-nowrap">
                            {out ? "Sold out" : (<>Add <ArrowUpRight className="w-3 h-3 sm:w-3.5 sm:h-3.5" /></>)}
                          </button>
                        </div>
                        <div className="mt-4 flex gap-2">
                          {displayableVariants(p.variants).map((v) => (
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
        </div>
      </div>
      <Footer />
    </div>
  );
}

function FilterGroup({ title, children, isLast }) {
  return (
    <div className={isLast ? "" : "mb-6 pb-6 border-b border-white/5"}>
      <div className="text-[10px] uppercase tracking-luxury text-cream/50 mb-3">{title}</div>
      <div className="space-y-2">{children}</div>
    </div>
  );
}
