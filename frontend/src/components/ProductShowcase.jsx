import React, { useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Minus, ShoppingBag, Check, Heart, ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { useCart } from "@/context/CartContext";
import { useWishlist } from "@/context/WishlistContext";
import { useAuth } from "@/context/AuthContext";
import { IDS } from "@/constants/testIds";

const formatINR = (n) => `₹${n.toLocaleString("en-IN")}`;

export const ProductShowcase = ({ product }) => {
  const { addItem } = useCart();
  const { has, toggle } = useWishlist();
  const { user, openAuth } = useAuth();
  const [variantKey, setVariantKey] = useState(product.variants[0].key);
  const [qty, setQty] = useState(1);
  const [added, setAdded] = useState(false);

  const activeVariant = useMemo(
    () => product.variants.find((v) => v.key === variantKey) || product.variants[0],
    [variantKey, product.variants],
  );

  // Combined image list: variant images (deduped) + gallery images, unique
  const allImages = useMemo(() => {
    const seen = new Set();
    const arr = [];
    (product.variants || []).forEach((v) => {
      if (v.image && !seen.has(v.image)) { seen.add(v.image); arr.push(v.image); }
    });
    (product.gallery || []).forEach((g) => {
      if (g && !seen.has(g)) { seen.add(g); arr.push(g); }
    });
    if (!arr.length && product.hero_image) arr.push(product.hero_image);
    return arr;
  }, [product]);

  const [activeIdx, setActiveIdx] = useState(0);

  // When variant changes, snap main image to that variant's image if it exists in allImages
  React.useEffect(() => {
    if (activeVariant?.image) {
      const idx = allImages.indexOf(activeVariant.image);
      if (idx >= 0) setActiveIdx(idx);
    }
  }, [activeVariant, allImages]);

  const mainImage = allImages[activeIdx] || product.hero_image;
  const inWishlist = has(product.id);
  const lowStock = product.stock > 0 && product.stock <= 3;

  const handleAdd = () => {
    addItem(product, variantKey, qty);
    setAdded(true);
    setTimeout(() => setAdded(false), 1600);
  };

  const handleWishlist = async () => {
    if (!user) { openAuth("login"); toast.info("Sign in to save pieces"); return; }
    try {
      const a = await toggle(product);
      toast.success(a === "added" ? "Saved to wishlist" : "Removed from wishlist");
    } catch { toast.error("Could not update wishlist"); }
  };

  return (
    <section
      id="product"
      data-testid={IDS.product.section}
      className="relative bg-ink-950 py-24 md:py-40 overflow-hidden"
    >
      <div className="absolute top-40 -left-40 w-[500px] h-[500px] rounded-full bg-gold/5 blur-3xl" />
      <div className="max-w-[1440px] mx-auto px-6 md:px-12 lg:px-16">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-24 items-start">
          {/* Gallery */}
          <div className="lg:sticky lg:top-28">
            <Link
              to={`/product/${product.slug}`}
              data-testid="hero-image-link"
              aria-label={`View ${product.name}`}
              className="block group/hero"
            >
              <motion.div
                key={mainImage}
                initial={{ opacity: 0, scale: 1.02 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
                className="relative aspect-[4/5] w-full overflow-hidden border border-white/10 cursor-pointer"
                data-testid={IDS.product.galleryMain}
              >
                <img
                  src={mainImage}
                  alt={product.name}
                  className="w-full h-full object-cover transition-transform duration-[1200ms] group-hover/hero:scale-[1.03]"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent opacity-0 group-hover/hero:opacity-100 transition-opacity duration-500" />
                <div className="absolute top-4 left-4 glass px-3 py-1.5 text-[10px] uppercase tracking-luxury text-gold-soft">
                  Edition · 1 of 1
                </div>
                <div className="absolute bottom-4 right-4 glass-gold px-4 py-2 text-[10px] uppercase tracking-luxury text-gold">
                  {product.craft_hours} artisan hours
                </div>
                <div className="absolute bottom-4 left-4 opacity-0 group-hover/hero:opacity-100 translate-y-2 group-hover/hero:translate-y-0 transition-all duration-500 glass px-3 py-1.5 text-[10px] uppercase tracking-luxury text-cream inline-flex items-center gap-2">
                  View full details <ArrowUpRight className="w-3 h-3" />
                </div>
              </motion.div>
            </Link>
            <div className="mt-4 grid grid-cols-4 gap-3">
              {allImages.slice(0, 4).map((g, i) => (
                <button
                  key={g + i}
                  data-testid={IDS.product.thumb(i)}
                  onClick={() => setActiveIdx(i)}
                  className={`aspect-square overflow-hidden border transition-all ${
                    activeIdx === i ? "border-gold" : "border-white/10 hover:border-white/30"
                  }`}
                >
                  <img src={g} alt="" className="w-full h-full object-cover" />
                </button>
              ))}
            </div>
          </div>

          {/* Details */}
          <div>
            <div className="flex items-center gap-3 mb-6">
              <span className="gold-line w-10" />
              <span className="text-[10px] uppercase tracking-luxury text-gold-soft">
                The Signature Piece
              </span>
            </div>
            <h2 className="font-serif text-4xl md:text-5xl lg:text-6xl leading-[0.95] text-cream text-balance">
              {product.name.split(" — ")[0]}
              <br />
              <span className="italic font-display text-gold text-3xl md:text-4xl">
                {product.tagline}
              </span>
            </h2>

            <div className="mt-8 flex items-baseline gap-4">
              <span className="font-serif text-4xl text-cream">{formatINR(product.price_inr)}</span>
              <span className="text-sm text-cream/40 line-through">{formatINR(product.mrp_inr)}</span>
              <span className="text-xs uppercase tracking-luxury text-gold">
                Save {formatINR(product.mrp_inr - product.price_inr)}
              </span>
            </div>
            <p className="text-xs text-cream/50 mt-2">Excl. GST (added at checkout) · Insured white-glove delivery</p>
            {lowStock && (
              <div className="mt-3 inline-flex items-center gap-2 text-xs uppercase tracking-luxury text-yellow-400">
                <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse" /> Only {product.stock} left
              </div>
            )}

            <p className="mt-8 text-base text-cream/70 leading-relaxed font-light max-w-xl">
              {product.description}
            </p>

            {/* Customizer — Task 3 fix: dedupe by hex+key so the same colour never appears twice
                (previously, colour variants like "Signature Gold · 24\"" and "Signature Gold · 36\""
                showed the same gold swatch twice — one per size row). Also hides the swatch row
                completely when the product only has a single default variant. */}
            {(() => {
              const seen = new Set();
              const uniqueVariants = (product.variants || []).filter((v) => {
                const dedupKey = `${(v.hex || "").toLowerCase()}|${((v.label || "").split("·")[0]).trim().toLowerCase()}`;
                if (seen.has(dedupKey)) return false;
                seen.add(dedupKey);
                return true;
              });
              const isDefaultOnly = uniqueVariants.length === 1
                && ((uniqueVariants[0].key === "default")
                    || (uniqueVariants[0].label || "").toLowerCase() === "default");
              if (uniqueVariants.length < 2 || isDefaultOnly) return null;
              return (
                <div className="mt-10">
                  <div className="flex items-center justify-between mb-4">
                    <div className="text-[10px] uppercase tracking-luxury text-cream/50">Colourway</div>
                    <div className="text-xs text-gold-soft italic font-serif">
                      {(activeVariant.label || "").split("·")[0].trim() || activeVariant.label}
                    </div>
                  </div>
                  <div className="flex gap-3 flex-wrap">
                    {uniqueVariants.map((v) => {
                      const isActive = (v.hex || "").toLowerCase() === (activeVariant.hex || "").toLowerCase();
                      return (
                        <button
                          key={v.key}
                          data-testid={IDS.product.variantSwatch(v.key)}
                          onClick={() => setVariantKey(v.key)}
                          className={`group relative w-14 h-14 rounded-full transition-all ${
                            isActive ? "ring-2 ring-offset-4 ring-offset-ink-950 ring-gold" : "ring-1 ring-white/20"
                          }`}
                          style={{ background: `radial-gradient(circle at 30% 30%, ${v.hex}, #0a0a0a 80%)` }}
                          aria-label={v.label}
                        >
                          <span className="absolute inset-0 rounded-full ring-1 ring-inset ring-white/10" />
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })()}

            {/* Materials */}
            <div className="mt-12 hairline p-6">
              <div className="text-[10px] uppercase tracking-luxury text-gold-soft mb-4">
                Materials
              </div>
              <ul className="grid sm:grid-cols-2 gap-x-6 gap-y-2">
                {product.materials.map((m) => (
                  <li key={m} className="flex items-start gap-2 text-sm text-cream/70">
                    <span className="mt-1.5 block w-1 h-1 bg-gold rounded-full shrink-0" />
                    {m}
                  </li>
                ))}
              </ul>
              <div className="mt-5 pt-5 border-t border-white/5 flex flex-wrap gap-6 text-xs text-cream/60">
                <div><span className="text-cream/40">Dimensions:</span> <span className="text-cream">{product.size}</span></div>
                <div><span className="text-cream/40">Craft:</span> <span className="text-cream">100% handmade</span></div>
              </div>
            </div>

            {/* Quantity + CTA */}
            <div className="mt-10 flex flex-col sm:flex-row gap-4">
              <div className="inline-flex items-center border border-white/10">
                <button
                  data-testid={IDS.product.qtyMinus}
                  onClick={() => setQty((q) => Math.max(1, q - 1))}
                  className="p-4 hover:bg-white/5 text-cream"
                  aria-label="Decrease"
                >
                  <Minus className="w-3.5 h-3.5" />
                </button>
                <span data-testid={IDS.product.qtyValue} className="px-6 font-serif text-lg text-cream min-w-[60px] text-center">
                  {qty}
                </span>
                <button
                  data-testid={IDS.product.qtyPlus}
                  onClick={() => setQty((q) => Math.min(5, q + 1))}
                  className="p-4 hover:bg-white/5 text-cream"
                  aria-label="Increase"
                >
                  <Plus className="w-3.5 h-3.5" />
                </button>
              </div>

              <button
                data-testid={IDS.product.addToCart}
                onClick={handleAdd}
                className="group flex-1 inline-flex items-center justify-center gap-3 bg-gold text-ink-950 px-7 py-5 text-xs uppercase tracking-luxury hover:bg-cream transition-colors relative overflow-hidden"
              >
                <AnimatePresence mode="wait">
                  {added ? (
                    <motion.span
                      key="added"
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      className="inline-flex items-center gap-2"
                    >
                      <Check className="w-4 h-4" /> Added to cart
                    </motion.span>
                  ) : (
                    <motion.span
                      key="add"
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      className="inline-flex items-center gap-3"
                    >
                      <ShoppingBag className="w-4 h-4" /> Add to Cart
                    </motion.span>
                  )}
                </AnimatePresence>
              </button>
            </div>
            <p className="mt-4 text-[11px] text-cream/40 leading-relaxed">
              Note: No inbuilt LED lighting. Ambient light shown in imagery is for styling visualisation only.
            </p>

            <div className="mt-6 flex flex-wrap gap-3">
              <button
                data-testid="hero-wishlist"
                onClick={handleWishlist}
                className={`inline-flex items-center gap-2 px-4 py-2.5 border text-[10px] uppercase tracking-luxury transition-colors ${
                  inWishlist ? "border-gold/60 text-gold bg-gold/5" : "border-white/15 text-cream/70 hover:border-gold/40 hover:text-gold"
                }`}
              >
                <Heart className={`w-3.5 h-3.5 ${inWishlist ? "fill-gold" : ""}`} /> {inWishlist ? "Saved" : "Wishlist"}
              </button>
              <Link
                to={`/product/${product.slug}`}
                data-testid="hero-view-details"
                className="inline-flex items-center gap-2 px-4 py-2.5 border border-white/15 text-cream/70 text-[10px] uppercase tracking-luxury hover:border-gold/40 hover:text-gold"
              >
                Full details <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default ProductShowcase;
