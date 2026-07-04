import React, { useEffect, useMemo, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { ShoppingBag, Check, Heart, Share2, Copy, Instagram, MessageCircle, ArrowLeft, Plus, Minus } from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import ProductGallery from "@/components/ProductGallery";
import { api } from "@/lib/api";
import { useCart } from "@/context/CartContext";
import { useWishlist } from "@/context/WishlistContext";
import { useAuth } from "@/context/AuthContext";

const formatINR = (n) => `₹${(n || 0).toLocaleString("en-IN")}`;
const WA_NUMBER = "919970107760";

export default function ProductPage() {
  const { slug } = useParams();
  const nav = useNavigate();
  const { addItem } = useCart();
  const { has, toggle } = useWishlist();
  const { user, openAuth } = useAuth();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [variantKey, setVariantKey] = useState("");
  const [qty, setQty] = useState(1);
  const [added, setAdded] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.get(`/products/${slug}`)
      .then((r) => { setProduct(r.data); setVariantKey(r.data.variants[0].key); })
      .catch(() => setProduct(null))
      .finally(() => setLoading(false));
  }, [slug]);

  const activeVariant = useMemo(
    () => (product ? product.variants.find((v) => v.key === variantKey) || product.variants[0] : null),
    [variantKey, product],
  );

  // Effective per-variant fields (fall back to product-level)
  const effectivePrice = activeVariant?.price_inr ?? product?.price_inr ?? 0;
  const effectiveMrp = activeVariant?.mrp_inr ?? product?.mrp_inr ?? 0;
  const effectiveStock = activeVariant?.stock ?? product?.stock ?? 0;
  const effectiveSize = activeVariant?.size || product?.size || "";

  // Group variants by "colour" (colour = variant.hex + base label prefix).
  // A variant with size means the product supports multi-size — we then split the picker into two axes.
  const hasSizeAxis = useMemo(
    () => Boolean(product?.variants?.some((v) => v?.size)),
    [product],
  );

  // Colours = unique { hex, label (before size), representative variant }
  const colourOptions = useMemo(() => {
    if (!product) return [];
    const map = new Map();
    product.variants.forEach((v) => {
      // If a size axis exists, group by hex (colour), else keep per-key
      const groupKey = hasSizeAxis ? v.hex : v.key;
      if (!map.has(groupKey)) {
        // Prefer the label part before " · " if present (e.g., "Signature Gold · 24\"" -> "Signature Gold")
        const cleanLabel = (v.label || "").split("·")[0].trim();
        map.set(groupKey, { hex: v.hex, key: v.key, label: cleanLabel, sample: v });
      }
    });
    return [...map.values()];
  }, [product, hasSizeAxis]);

  // Sizes available for the currently selected colour
  const sizeOptionsForColour = useMemo(() => {
    if (!product || !hasSizeAxis || !activeVariant) return [];
    return product.variants
      .filter((v) => v.hex === activeVariant.hex && v.size)
      .map((v) => ({ key: v.key, size: v.size, stock: v.stock ?? product.stock, price_inr: v.price_inr ?? product.price_inr }));
  }, [product, activeVariant, hasSizeAxis]);

  if (loading) {
    return (
      <div className="min-h-screen bg-ink-950 text-cream">
        <Navbar />
        <div className="pt-40 text-center text-cream/40 text-sm">Loading piece…</div>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="min-h-screen bg-ink-950 text-cream">
        <Navbar />
        <div className="pt-40 text-center px-6">
          <h1 className="font-serif text-4xl">Piece not found</h1>
          <Link to="/shop" className="mt-8 inline-block text-gold hover:text-cream">← Return to the atelier</Link>
        </div>
      </div>
    );
  }

  const inWishlist = has(product.id);
  const shareUrl = typeof window !== "undefined" ? `${window.location.origin}/product/${product.slug}` : "";
  const savings = effectiveMrp - effectivePrice;
  const savingsPct = effectiveMrp > 0 ? Math.round((savings / effectiveMrp) * 100) : 0;
  const lowStock = effectiveStock > 0 && effectiveStock <= 3;
  const outOfStock = effectiveStock <= 0;

  const waMessage = `Hi ArtyFex, I'm interested in the ${product.name} (${effectiveSize}) — ${formatINR(effectivePrice)}. Colour: ${activeVariant?.label}. Link: ${shareUrl}`;
  const waHref = `https://wa.me/${WA_NUMBER}?text=${encodeURIComponent(waMessage)}`;

  const handleAdd = () => {
    if (outOfStock) { toast.error("This piece is currently out of stock."); return; }
    addItem(product, variantKey, qty);
    setAdded(true);
    setTimeout(() => setAdded(false), 1600);
  };

  const handleWishlist = async () => {
    if (!user) { openAuth("login"); toast.info("Sign in to save pieces to your wishlist"); return; }
    try {
      const action = await toggle(product);
      toast.success(action === "added" ? "Saved to wishlist" : "Removed from wishlist");
    } catch { toast.error("Could not update wishlist"); }
  };

  const handleShare = async (channel) => {
    const shareText = `${product.name} · ${formatINR(product.price_inr)} — ArtyFex`;
    if (channel === "copy") {
      await navigator.clipboard.writeText(shareUrl);
      toast.success("Link copied to clipboard");
    } else if (channel === "whatsapp") {
      window.open(`https://wa.me/?text=${encodeURIComponent(shareText + " " + shareUrl)}`, "_blank");
    } else if (channel === "x") {
      window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(shareUrl)}`, "_blank");
    } else if (channel === "instagram") {
      await navigator.clipboard.writeText(shareUrl);
      toast.success("Link copied · paste into Instagram");
    } else if (channel === "native" && navigator.share) {
      try { await navigator.share({ title: product.name, text: shareText, url: shareUrl }); } catch { /* cancelled */ }
    }
    setShareOpen(false);
  };

  return (
    <div className="min-h-screen bg-ink-950 text-cream" data-testid="product-page">
      <Navbar />
      <div className="max-w-[1440px] mx-auto px-6 md:px-12 lg:px-16 pt-28 pb-24">
        <button onClick={() => nav(-1)} className="inline-flex items-center gap-2 text-xs uppercase tracking-luxury text-cream/50 hover:text-gold mb-8">
          <ArrowLeft className="w-3.5 h-3.5" /> Back
        </button>

        <div className="grid lg:grid-cols-2 gap-12 lg:gap-20 items-start">
          {/* Gallery */}
          <ProductGallery product={product} variantImage={activeVariant?.image} />

          {/* Details */}
          <div>
            <div className="text-[10px] uppercase tracking-luxury text-gold-soft">{effectiveSize}</div>
            <h1 className="mt-3 font-serif text-4xl md:text-5xl leading-[1.05] text-cream text-balance" data-testid="product-name">
              {product.name.split(" — ")[0]}
            </h1>
            <p className="mt-3 text-lg italic text-gold-soft font-serif">{product.tagline}</p>

            {/* Pricing */}
            <div className="mt-8 flex items-baseline gap-4 flex-wrap" data-testid="product-price-block">
              <span className="font-serif text-4xl text-cream" data-testid="product-price">{formatINR(effectivePrice)}</span>
              {effectiveMrp > effectivePrice && (
                <>
                  <span className="text-base text-cream/40 line-through" data-testid="product-mrp">{formatINR(effectiveMrp)}</span>
                  <span className="text-xs uppercase tracking-luxury text-gold">Save {formatINR(savings)} · {savingsPct}% off</span>
                </>
              )}
            </div>
            <p className="text-xs text-cream/50 mt-2">Inclusive of all taxes · Insured white-glove delivery</p>

            {/* Stock */}
            <div className="mt-5" data-testid="product-stock">
              {outOfStock ? (
                <span className="inline-flex items-center gap-2 text-xs uppercase tracking-luxury text-red-400">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-400" /> Out of stock — Made-to-order 4–6 weeks
                </span>
              ) : lowStock ? (
                <span className="inline-flex items-center gap-2 text-xs uppercase tracking-luxury text-yellow-400 animate-pulse">
                  <span className="w-1.5 h-1.5 rounded-full bg-yellow-400" /> Only {effectiveStock} left · Low stock
                </span>
              ) : (
                <span className="inline-flex items-center gap-2 text-xs uppercase tracking-luxury text-emerald-400/80">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> In stock · Ready to dispatch
                </span>
              )}
            </div>

            <p className="mt-8 text-base text-cream/70 leading-relaxed font-light">{product.description}</p>

            {/* Variants */}
            {colourOptions.length > 0 && (
              <div className="mt-10">
                <div className="flex items-center justify-between mb-4">
                  <div className="text-[10px] uppercase tracking-luxury text-cream/50">Colourway</div>
                  <div className="text-xs text-gold-soft italic font-serif">
                    {hasSizeAxis
                      ? (colourOptions.find((c) => c.hex === activeVariant?.hex)?.label || activeVariant?.label)
                      : activeVariant?.label}
                  </div>
                </div>
                <div className="flex gap-3 flex-wrap">
                  {colourOptions.map((c) => {
                    const isActive = hasSizeAxis ? c.hex === activeVariant?.hex : c.key === variantKey;
                    return (
                      <button
                        key={c.hex + c.key}
                        data-testid={`product-variant-${c.key}`}
                        onClick={() => {
                          if (!hasSizeAxis) { setVariantKey(c.key); return; }
                          // Switch colour — keep current size if the new colour offers it, else pick first
                          const currentSize = activeVariant?.size;
                          const match = product.variants.find((v) => v.hex === c.hex && v.size === currentSize);
                          const next = match || product.variants.find((v) => v.hex === c.hex);
                          if (next) setVariantKey(next.key);
                        }}
                        className={`group relative w-12 h-12 rounded-full transition-all ${
                          isActive ? "ring-2 ring-offset-4 ring-offset-ink-950 ring-gold" : "ring-1 ring-white/20"
                        }`}
                        style={{ background: `radial-gradient(circle at 30% 30%, ${c.hex}, #0a0a0a 80%)` }}
                        aria-label={c.label}
                      >
                        <span className="absolute inset-0 rounded-full ring-1 ring-inset ring-white/10" />
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Size selector — only when the product has variants with size defined */}
            {hasSizeAxis && sizeOptionsForColour.length > 0 && (
              <div className="mt-8" data-testid="product-size-selector">
                <div className="flex items-center justify-between mb-4">
                  <div className="text-[10px] uppercase tracking-luxury text-cream/50">Size</div>
                  <div className="text-xs text-gold-soft italic font-serif">{activeVariant?.size}</div>
                </div>
                <div className="flex flex-wrap gap-3">
                  {sizeOptionsForColour.map((s) => {
                    const isActive = s.key === variantKey;
                    const soldOut = (s.stock ?? 0) <= 0;
                    return (
                      <button
                        key={s.key}
                        data-testid={`product-size-${s.key}`}
                        onClick={() => setVariantKey(s.key)}
                        disabled={soldOut}
                        className={`px-4 py-2.5 text-xs uppercase tracking-luxury border transition-all ${
                          isActive
                            ? "border-gold text-gold bg-gold/5"
                            : "border-white/15 text-cream/80 hover:border-gold/40 hover:text-gold"
                        } ${soldOut ? "opacity-40 line-through cursor-not-allowed" : ""}`}
                      >
                        {s.size}
                        {s.price_inr !== effectivePrice && !soldOut && (
                          <span className="ml-2 text-[10px] text-cream/50 normal-case tracking-normal">{formatINR(s.price_inr)}</span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Quantity + Add to cart */}
            <div className="mt-10 flex flex-col sm:flex-row gap-4">
              <div className="inline-flex items-center border border-white/10">
                <button onClick={() => setQty((q) => Math.max(1, q - 1))} data-testid="product-qty-minus" className="p-4 hover:bg-white/5 text-cream"><Minus className="w-3.5 h-3.5" /></button>
                <span data-testid="product-qty-value" className="px-6 font-serif text-lg text-cream min-w-[60px] text-center">{qty}</span>
                <button onClick={() => setQty((q) => Math.min(5, q + 1))} data-testid="product-qty-plus" className="p-4 hover:bg-white/5 text-cream"><Plus className="w-3.5 h-3.5" /></button>
              </div>

              <button
                data-testid="product-add-to-cart"
                onClick={handleAdd}
                disabled={outOfStock}
                className="group flex-1 inline-flex items-center justify-center gap-3 bg-gold text-ink-950 px-7 py-5 text-xs uppercase tracking-luxury hover:bg-cream transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <AnimatePresence mode="wait">
                  {added ? (
                    <motion.span key="added" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} className="inline-flex items-center gap-2">
                      <Check className="w-4 h-4" /> Added to atelier
                    </motion.span>
                  ) : (
                    <motion.span key="add" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} className="inline-flex items-center gap-3">
                      <ShoppingBag className="w-4 h-4" /> {outOfStock ? "Out of stock" : "Add to Atelier"}
                    </motion.span>
                  )}
                </AnimatePresence>
              </button>
            </div>

            {/* Secondary actions */}
            <div className="mt-6 flex flex-wrap gap-3">
              <button
                data-testid="product-wishlist"
                onClick={handleWishlist}
                className={`inline-flex items-center gap-2 px-5 py-3 border text-xs uppercase tracking-luxury transition-colors ${
                  inWishlist ? "border-gold/60 text-gold bg-gold/5" : "border-white/15 text-cream/80 hover:border-gold/40 hover:text-gold"
                }`}
              >
                <Heart className={`w-3.5 h-3.5 ${inWishlist ? "fill-gold" : ""}`} />
                {inWishlist ? "Saved" : "Save to wishlist"}
              </button>

              <a
                data-testid="product-whatsapp"
                href={waHref}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 px-5 py-3 border border-emerald-500/40 text-emerald-400 text-xs uppercase tracking-luxury hover:bg-emerald-500/5"
              >
                <MessageCircle className="w-3.5 h-3.5" />
                Enquire on WhatsApp
              </a>

              <div className="relative">
                <button
                  data-testid="product-share"
                  onClick={() => setShareOpen((v) => !v)}
                  className="inline-flex items-center gap-2 px-5 py-3 border border-white/15 text-cream/80 text-xs uppercase tracking-luxury hover:border-gold/40 hover:text-gold"
                >
                  <Share2 className="w-3.5 h-3.5" /> Share
                </button>
                {shareOpen && (
                  <div className="absolute z-20 top-full mt-2 right-0 min-w-[220px] bg-ink-900 border border-white/10 py-2 shadow-xl" data-testid="product-share-menu">
                    <ShareItem icon={<MessageCircle className="w-3.5 h-3.5" />} label="WhatsApp" onClick={() => handleShare("whatsapp")} testid="share-whatsapp" />
                    <ShareItem icon={<Instagram className="w-3.5 h-3.5" />} label="Instagram" onClick={() => handleShare("instagram")} testid="share-instagram" />
                    <ShareItem icon={<XLogo />} label="X (Twitter)" onClick={() => handleShare("x")} testid="share-x" />
                    <ShareItem icon={<Copy className="w-3.5 h-3.5" />} label="Copy link" onClick={() => handleShare("copy")} testid="share-copy" />
                  </div>
                )}
              </div>
            </div>

            {/* Materials */}
            <div className="mt-12 hairline p-6">
              <div className="text-[10px] uppercase tracking-luxury text-gold-soft mb-4">Materials</div>
              <ul className="grid sm:grid-cols-2 gap-x-6 gap-y-2">
                {product.materials.map((m) => (
                  <li key={m} className="flex items-start gap-2 text-sm text-cream/70">
                    <span className="mt-1.5 block w-1 h-1 bg-gold rounded-full shrink-0" />
                    {m}
                  </li>
                ))}
              </ul>
              <div className="mt-5 pt-5 border-t border-white/5 flex flex-wrap gap-6 text-xs text-cream/60">
                <div><span className="text-cream/40">Dimensions:</span> <span className="text-cream">{effectiveSize}</span></div>
                <div><span className="text-cream/40">Craft time:</span> <span className="text-cream">{product.craft_hours} hours</span></div>
                <div><span className="text-cream/40">Origin:</span> <span className="text-cream">Handmade in Mumbai</span></div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}

function ShareItem({ icon, label, onClick, testid }) {
  return (
    <button data-testid={testid} onClick={onClick} className="w-full flex items-center gap-3 px-4 py-2.5 text-xs uppercase tracking-luxury text-cream/80 hover:bg-white/5 hover:text-gold">
      {icon}
      {label}
    </button>
  );
}

const XLogo = () => (
  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
  </svg>
);
