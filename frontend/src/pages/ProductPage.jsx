import React, { useEffect, useMemo, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { ShoppingBag, Check, Heart, Share2, Copy, Instagram, MessageCircle, ArrowLeft, Plus, Minus, Star } from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import ProductGallery from "@/components/ProductGallery";
import SEO from "@/components/SEO";
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
  const [reviews, setReviews] = useState([]);
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

  // Fetch all reviews once and filter for this product (backend has no per-product endpoint)
  useEffect(() => {
    if (!product?.id) return;
    api.get("/reviews")
      .then((r) => setReviews((r.data || []).filter((rv) => rv.product_id === product.id)))
      .catch(() => setReviews([]));
  }, [product?.id]);

  // Compute average rating (rounded to 1 decimal) and count
  const ratingStats = useMemo(() => {
    if (!reviews.length) return { count: 0, avg: 0 };
    const sum = reviews.reduce((a, r) => a + (Number(r.rating) || 0), 0);
    return { count: reviews.length, avg: Math.round((sum / reviews.length) * 10) / 10 };
  }, [reviews]);

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

  // Task 3 — hide the colour swatches when the product has no real colour choice
  // (only "Default" variant OR only one option OR variants collapsed to a single dummy).
  const hasRealColourChoice = useMemo(() => {
    if (!product) return false;
    if (colourOptions.length < 2) return false;
    // If the only "colours" are the single default seeded variant, hide.
    const isDefaultOnly = (product.variants || []).length === 1
      && ((product.variants[0].key === "default") || (product.variants[0].label || "").toLowerCase() === "default");
    return !isDefaultOnly;
  }, [product, colourOptions]);

  // Task 3 — user's chosen values for extra variation options (Shape / Frame / …).
  // Initialise from is_default flags when the product loads.
  const [selectedOptions, setSelectedOptions] = useState({});
  useEffect(() => {
    if (!product) return;
    const init = {};
    (product.variation_options || []).forEach((opt) => {
      const def = (opt.values || []).find((v) => v.is_default) || (opt.values || [])[0];
      if (def) init[opt.key] = def.key;
    });
    setSelectedOptions(init);
  }, [product?.id]); // eslint-disable-line

  const optionsPriceDelta = useMemo(() => {
    let d = 0;
    (product?.variation_options || []).forEach((opt) => {
      const chosen = selectedOptions[opt.key];
      const m = (opt.values || []).find((v) => v.key === chosen);
      if (m) d += Number(m.price_delta_inr || 0);
    });
    return d;
  }, [product, selectedOptions]);

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
    // Task 3 — enforce required options
    for (const opt of (product.variation_options || [])) {
      if (opt.required && !selectedOptions[opt.key]) {
        toast.error(`Please choose ${opt.label}`);
        return;
      }
    }
    addItem(product, variantKey, qty, selectedOptions);
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
      <SEO
        title={`${product.name} — Luxury Handmade Resin Mirror | ArtyFex Mumbai`}
        description={`${product.tagline || ''} ${product.description || ''}`.slice(0, 175).trim() || `${product.name} · handmade luxury mirror by ArtyFex, Mumbai. ${effectiveSize}. Insured white-glove delivery.`}
        path={`/product/${product.slug}`}
        image={product.hero_image}
        type="product"
        jsonLd={{
          "@context": "https://schema.org",
          "@graph": [
            {
              "@type": "Product",
              "@id": `https://www.artyfex.in/product/${product.slug}#product`,
              "name": product.name,
              "description": product.description,
              "image": [product.hero_image, ...(product.gallery || [])].filter(Boolean),
              "sku": product.sku || product.slug,
              "gtin": product.sku || undefined,
              "category": product.category || "Mirrors",
              "brand": { "@type": "Brand", "name": "ArtyFex" },
              "manufacturer": { "@type": "Organization", "name": "ArtyFex Atelier, Mumbai" },
              "offers": {
                "@type": "Offer",
                "url": `https://www.artyfex.in/product/${product.slug}`,
                "priceCurrency": "INR",
                "price": effectivePrice,
                "availability": outOfStock
                  ? "https://schema.org/OutOfStock"
                  : "https://schema.org/InStock",
                "itemCondition": "https://schema.org/NewCondition",
                "seller": { "@type": "Organization", "name": "ArtyFex" },
                "hasMerchantReturnPolicy": {
                  "@type": "MerchantReturnPolicy",
                  "applicableCountry": "IN",
                  "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow",
                  "merchantReturnDays": 3,
                  "returnMethod": "https://schema.org/ReturnByMail",
                  "returnFees": "https://schema.org/FreeReturn",
                },
                "shippingDetails": {
                  "@type": "OfferShippingDetails",
                  "shippingRate": { "@type": "MonetaryAmount", "value": 0, "currency": "INR" },
                  "shippingDestination": { "@type": "DefinedRegion", "addressCountry": "IN" },
                  "deliveryTime": {
                    "@type": "ShippingDeliveryTime",
                    "handlingTime": { "@type": "QuantitativeValue", "minValue": 2, "maxValue": 5, "unitCode": "DAY" },
                    "transitTime":  { "@type": "QuantitativeValue", "minValue": 2, "maxValue": 7, "unitCode": "DAY" },
                  },
                },
              },
            },
            {
              "@type": "BreadcrumbList",
              "itemListElement": [
                { "@type": "ListItem", "position": 1, "name": "Home", "item": "https://www.artyfex.in" },
                { "@type": "ListItem", "position": 2, "name": "Shop", "item": "https://www.artyfex.in/shop" },
                { "@type": "ListItem", "position": 3, "name": product.name, "item": `https://www.artyfex.in/product/${product.slug}` },
              ],
            },
          ],
        }}
      />
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

            {/* Ratings — hidden entirely when no reviews for this product */}
            {ratingStats.count > 0 && (
              <div className="mt-4 inline-flex items-center gap-2" data-testid="product-rating">
                <div className="flex items-center gap-0.5" aria-label={`${ratingStats.avg} out of 5 stars`}>
                  {[1, 2, 3, 4, 5].map((n) => {
                    const filled = ratingStats.avg >= n;
                    const half = !filled && ratingStats.avg >= n - 0.5;
                    return (
                      <span key={n} className="relative inline-flex">
                        <Star className={`w-4 h-4 ${filled ? "fill-gold text-gold" : "text-cream/25"}`} />
                        {half && (
                          <span className="absolute inset-0 overflow-hidden" style={{ width: "50%" }}>
                            <Star className="w-4 h-4 fill-gold text-gold" />
                          </span>
                        )}
                      </span>
                    );
                  })}
                </div>
                <span className="text-sm text-cream/80 font-medium" data-testid="product-rating-avg">{ratingStats.avg.toFixed(1)}</span>
                <a href="#reviews" className="text-xs text-cream/50 hover:text-gold underline underline-offset-2" data-testid="product-rating-count">
                  ({ratingStats.count} {ratingStats.count === 1 ? "review" : "reviews"})
                </a>
              </div>
            )}

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
            <p className="text-xs text-cream/50 mt-2">Excl. GST (added at checkout) · Insured white-glove delivery</p>

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
            {hasRealColourChoice && (
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

            {/* Task 3 — Extra option groups (Shape / Frame / Thickness / Gift Wrap / Care Kit / Mount) */}
            {(product.variation_options || []).length > 0 && (
              <div className="mt-8 space-y-6" data-testid="product-options">
                {(product.variation_options || []).map((opt) => {
                  const chosen = selectedOptions[opt.key];
                  return (
                    <div key={opt.key} data-testid={`product-option-${opt.key}`}>
                      <div className="flex items-center justify-between mb-3">
                        <div className="text-[10px] uppercase tracking-luxury text-cream/50">
                          {opt.label}{opt.required && <span className="text-gold ml-1">*</span>}
                        </div>
                        {chosen && (
                          <div className="text-xs text-gold-soft italic font-serif">
                            {((opt.values || []).find((v) => v.key === chosen) || {}).label || chosen}
                          </div>
                        )}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {(opt.values || []).map((v) => {
                          const isActive = chosen === v.key;
                          const delta = Number(v.price_delta_inr || 0);
                          return (
                            <button
                              key={v.key}
                              type="button"
                              onClick={() => setSelectedOptions((prev) => ({ ...prev, [opt.key]: v.key }))}
                              data-testid={`product-option-${opt.key}-${v.key}`}
                              className={`px-4 py-2.5 text-xs uppercase tracking-luxury border transition-all ${
                                isActive
                                  ? "border-gold text-gold bg-gold/5"
                                  : "border-white/15 text-cream/80 hover:border-gold/40 hover:text-gold"
                              }`}
                            >
                              {v.label}
                              {delta > 0 && (
                                <span className="ml-2 text-[10px] text-cream/60 normal-case tracking-normal">+{formatINR(delta)}</span>
                              )}
                            </button>
                          );
                        })}
                      </div>
                      {opt.help_text && (
                        <div className="mt-2 text-[11px] italic text-cream/40">{opt.help_text}</div>
                      )}
                    </div>
                  );
                })}
                {optionsPriceDelta > 0 && (
                  <div className="text-xs text-gold-soft border-t border-white/5 pt-3">
                    Add-ons total: <span className="font-serif text-cream">+{formatINR(optionsPriceDelta)}</span>
                    <span className="text-cream/50 ml-2">·  new unit price {formatINR(effectivePrice + optionsPriceDelta)}</span>
                  </div>
                )}
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
                      <Check className="w-4 h-4" /> Added to cart
                    </motion.span>
                  ) : (
                    <motion.span key="add" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} className="inline-flex items-center gap-3">
                      <ShoppingBag className="w-4 h-4" /> {outOfStock ? "Out of stock" : "Add to Cart"}
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

        {/* CUSTOMER REVIEWS (Amazon/Flipkart-style) */}
        <ProductReviewsSection
          reviews={reviews}
          avg={ratingStats.avg}
          count={ratingStats.count}
          product={product}
          user={user}
          openAuth={openAuth}
          onSubmitted={(newReview) => {
            // Optimistically insert (as pending) even though we filter for
            // approved only elsewhere — this gives the customer instant feedback.
            setReviews((prev) => [{ ...newReview }, ...prev]);
          }}
        />
      </div>
      {/* Sticky mobile Add-to-Cart bar (native app feel) */}
      <div
        data-testid="product-sticky-cta"
        className="lg:hidden fixed left-0 right-0 z-40 bg-ink-950/95 backdrop-blur border-t border-white/10 px-4 py-3 flex items-center gap-3"
        style={{ bottom: "64px", paddingBottom: "calc(0.75rem + env(safe-area-inset-bottom))" }}
      >
        <div className="flex flex-col min-w-0">
          <span className="text-[10px] uppercase tracking-luxury text-gold-soft">{effectiveSize}</span>
          <span className="font-serif text-lg text-cream leading-none">{formatINR(effectivePrice)}</span>
        </div>
        <button
          data-testid="product-sticky-add"
          onClick={handleAdd}
          disabled={outOfStock}
          className="ml-auto flex-1 max-w-[220px] inline-flex items-center justify-center gap-2 bg-gold text-ink-950 px-5 py-3 text-xs uppercase tracking-luxury hover:bg-cream transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {added ? (<><Check className="w-4 h-4" /> Added</>) : (<><ShoppingBag className="w-4 h-4" /> {outOfStock ? "Sold out" : "Add to Cart"}</>)}
        </button>
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

/* -------------------- Reviews list (Amazon/Flipkart-style) -------------------- */
function StarRow({ rating, size = "sm" }) {
  const cls = size === "lg" ? "w-4 h-4" : "w-3 h-3";
  return (
    <div className="inline-flex items-center gap-0.5" aria-label={`${rating} out of 5`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <Star key={n} className={`${cls} ${rating >= n ? "fill-gold text-gold" : "text-cream/25"}`} />
      ))}
    </div>
  );
}

function ProductReviewsSection({ reviews, avg, count, product, user, openAuth, onSubmitted }) {
  const [sort, setSort] = useState("recent");
  const [filterStar, setFilterStar] = useState(0);
  const [limit, setLimit] = useState(6);
  const [writeOpen, setWriteOpen] = useState(false);

  const buckets = useMemo(() => {
    const b = { 5: 0, 4: 0, 3: 0, 2: 0, 1: 0 };
    reviews.forEach((r) => { const n = Math.round(Number(r.rating) || 0); if (b[n] != null) b[n] += 1; });
    return b;
  }, [reviews]);

  const filtered = useMemo(() => {
    let out = filterStar > 0 ? reviews.filter((r) => Math.round(Number(r.rating) || 0) === filterStar) : reviews.slice();
    if (sort === "helpful") out.sort((a, b) => (Number(b.rating) || 0) - (Number(a.rating) || 0));
    else if (sort === "high") out.sort((a, b) => (Number(b.rating) || 0) - (Number(a.rating) || 0));
    else if (sort === "low") out.sort((a, b) => (Number(a.rating) || 0) - (Number(b.rating) || 0));
    else out.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
    return out;
  }, [reviews, sort, filterStar]);

  const photos = useMemo(() => reviews.flatMap((r) => (Array.isArray(r.photos) ? r.photos : []).map((u) => ({ url: u, review: r }))), [reviews]);

  if (!count) {
    return (
      <section id="reviews" className="mt-16 md:mt-24 pt-10 md:pt-16 border-t border-white/5">
        <div className="flex items-center gap-3 mb-4">
          <span className="gold-line w-8 md:w-10" />
          <span className="text-[10px] uppercase tracking-luxury text-gold-soft">Customer Reviews</span>
        </div>
        <h2 className="font-serif text-2xl md:text-3xl text-cream">No reviews yet</h2>
        <p className="mt-3 text-cream/50 text-sm md:text-base font-light">Be the first to share your experience with this piece.</p>
        <button
          type="button"
          onClick={() => (user ? setWriteOpen(true) : openAuth?.("login"))}
          data-testid="review-write-cta-empty"
          className="mt-6 inline-flex items-center gap-2 border border-gold/40 text-gold text-xs uppercase tracking-luxury px-5 py-3 hover:bg-gold hover:text-ink-950 transition-colors"
        >
          <Star className="w-3.5 h-3.5" /> Write a review
        </button>
        <WriteReviewDialog
          open={writeOpen}
          onClose={() => setWriteOpen(false)}
          product={product}
          onSubmitted={(rv) => { onSubmitted?.(rv); setWriteOpen(false); }}
        />
      </section>
    );
  }

  return (
    <section id="reviews" data-testid="product-reviews" className="mt-16 md:mt-24 pt-10 md:pt-16 border-t border-white/5">
      <div className="flex items-center justify-between gap-3 mb-6 md:mb-8">
        <div className="flex items-center gap-3">
          <span className="gold-line w-8 md:w-10" />
          <span className="text-[10px] uppercase tracking-luxury text-gold-soft">Customer Reviews</span>
        </div>
        <button
          type="button"
          onClick={() => (user ? setWriteOpen(true) : openAuth?.("login"))}
          data-testid="review-write-cta"
          className="inline-flex items-center gap-2 border border-gold/40 text-gold text-[10px] uppercase tracking-luxury px-3 py-2 hover:bg-gold hover:text-ink-950 transition-colors"
        >
          <Star className="w-3 h-3" /> Write a review
        </button>
      </div>

      <div className="grid md:grid-cols-3 gap-6 md:gap-10 mb-8 md:mb-12">
        {/* Summary card */}
        <div className="bg-ink-900 border border-white/10 rounded-xl md:rounded-none p-5 md:p-6">
          <div className="flex items-baseline gap-3">
            <span className="font-serif text-4xl md:text-5xl text-cream leading-none">{avg.toFixed(1)}</span>
            <span className="text-cream/50 text-sm">/ 5</span>
          </div>
          <StarRow rating={avg} size="lg" />
          <div className="mt-2 text-xs text-cream/60">Based on {count} {count === 1 ? "review" : "reviews"}</div>
        </div>
        {/* Rating breakdown */}
        <div className="md:col-span-2 bg-ink-900 border border-white/10 rounded-xl md:rounded-none p-5 md:p-6">
          <div className="space-y-2">
            {[5, 4, 3, 2, 1].map((n) => {
              const c = buckets[n] || 0;
              const pct = count ? (c / count) * 100 : 0;
              return (
                <button
                  key={n}
                  onClick={() => setFilterStar(filterStar === n ? 0 : n)}
                  data-testid={`review-bucket-${n}`}
                  className={`w-full flex items-center gap-3 text-xs text-cream/70 hover:text-gold transition-colors ${filterStar === n ? "text-gold" : ""}`}
                >
                  <span className="w-8 text-right">{n}★</span>
                  <span className="flex-1 h-1.5 bg-white/5 rounded overflow-hidden">
                    <span className="block h-full bg-gold" style={{ width: `${pct}%` }} />
                  </span>
                  <span className="w-8 text-left text-cream/50">{c}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Photo strip */}
      {photos.length > 0 && (
        <div className="mb-8 md:mb-12">
          <div className="text-[10px] uppercase tracking-luxury text-gold-soft mb-3">Photos from customers · {photos.length}</div>
          <div className="flex gap-2 overflow-x-auto no-scrollbar -mx-4 px-4 md:-mx-0 md:px-0 pb-2" style={{ scrollbarWidth: "none" }}>
            {photos.slice(0, 20).map((p, i) => (
              <a key={i} href={p.url} target="_blank" rel="noreferrer" className="shrink-0 w-20 h-20 md:w-24 md:h-24 rounded-lg overflow-hidden border border-white/10 hover:border-gold/40 transition">
                <img src={p.url} alt="Customer photo" loading="lazy" decoding="async" className="w-full h-full object-cover" />
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div className="text-sm text-cream/60">
          {filtered.length} {filtered.length === 1 ? "review" : "reviews"}
          {filterStar > 0 && (
            <button onClick={() => setFilterStar(0)} className="ml-3 text-xs uppercase tracking-luxury text-red-400 hover:text-red-300">Clear filter</button>
          )}
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor="rv-sort" className="text-[10px] uppercase tracking-luxury text-cream/50">Sort</label>
          <select
            id="rv-sort"
            data-testid="review-sort"
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            className="bg-ink-900 border border-white/10 text-xs text-cream/80 px-3 py-2 rounded"
          >
            <option value="recent">Most recent</option>
            <option value="high">Highest rated</option>
            <option value="low">Lowest rated</option>
          </select>
        </div>
      </div>

      {/* Review list */}
      <div className="grid gap-4 md:gap-5">
        {filtered.slice(0, limit).map((r) => (
          <div key={r.id || `${r.author_name}-${r.created_at}`} data-testid={`review-item-${r.id || ""}`} className="bg-ink-900 border border-white/10 rounded-xl md:rounded-none p-4 md:p-6">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div>
                <div className="flex items-center gap-2 text-cream">
                  <span className="font-serif text-base md:text-lg">{r.author_name || "Anonymous collector"}</span>
                  {r.verified && (
                    <span className="text-[9px] uppercase tracking-luxury text-emerald-400 border border-emerald-500/40 px-1.5 py-0.5 rounded">Verified purchase</span>
                  )}
                </div>
                <div className="mt-1 flex items-center gap-2 text-xs text-cream/50">
                  <StarRow rating={Number(r.rating) || 0} />
                  {r.location && <span>· {r.location}</span>}
                  {r.created_at && <span>· {new Date(r.created_at).toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" })}</span>}
                </div>
              </div>
              {r.rating != null && (
                <div className="text-xs text-cream/60 hidden sm:block">{Number(r.rating).toFixed(1)} / 5</div>
              )}
            </div>
            {r.title && <h4 className="mt-3 font-serif text-cream text-lg leading-tight">{r.title}</h4>}
            {r.body && <p className="mt-2 text-sm text-cream/70 leading-relaxed font-light whitespace-pre-line">{r.body}</p>}
            {Array.isArray(r.photos) && r.photos.length > 0 && (
              <div className="mt-3 flex gap-2 flex-wrap">
                {r.photos.slice(0, 6).map((u, i) => (
                  <a key={i} href={u} target="_blank" rel="noreferrer" className="w-16 h-16 md:w-20 md:h-20 overflow-hidden rounded-md border border-white/10 hover:border-gold/40 transition">
                    <img src={u} alt="Customer" loading="lazy" decoding="async" className="w-full h-full object-cover" />
                  </a>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {filtered.length > limit && (
        <div className="mt-6 flex justify-center">
          <button
            data-testid="review-load-more"
            onClick={() => setLimit((l) => l + 6)}
            className="inline-flex items-center gap-2 px-5 py-3 border border-white/15 text-cream/80 text-xs uppercase tracking-luxury hover:border-gold/50 hover:text-gold"
          >Load more reviews</button>
        </div>
      )}
      <WriteReviewDialog
        open={writeOpen}
        onClose={() => setWriteOpen(false)}
        product={product}
        onSubmitted={(rv) => { onSubmitted?.(rv); setWriteOpen(false); }}
      />
    </section>
  );
}


/* Task 5 · Customer "Write a review" modal.
   Requires the user to be signed in. Backend applies the actual verified-buyer
   check server-side + queues the review as "pending" for admin approval. */
function WriteReviewDialog({ open, onClose, product, onSubmitted }) {
  const [rating, setRating] = useState(5);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!open) return;
    setRating(5); setTitle(""); setBody(""); setBusy(false);
  }, [open]);
  if (!open || !product) return null;
  const submit = async () => {
    if (!title.trim() || !body.trim()) {
      toast.error("Title and body are required");
      return;
    }
    if (rating < 1 || rating > 5) {
      toast.error("Please pick 1–5 stars");
      return;
    }
    setBusy(true);
    try {
      const token = (typeof window !== "undefined") ? localStorage.getItem("artyfex_user_token") : "";
      const r = await api.post(`/products/${product.slug}/reviews`, {
        rating, title: title.trim(), body: body.trim(),
        product_id: product.id,
      }, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
      toast.success("Thank you — your review is pending admin approval.", { duration: 4500 });
      onSubmitted?.(r.data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not submit review");
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="fixed inset-0 z-[100] bg-black/70 flex items-center justify-center p-4" onClick={onClose} data-testid="review-modal">
      <div className="bg-ink-950 border border-gold/30 w-full max-w-lg p-6 md:p-8" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between gap-3 mb-4">
          <h3 className="font-serif text-xl md:text-2xl text-cream">Write a review</h3>
          <button onClick={onClose} className="text-cream/50 hover:text-red-400 text-xl leading-none" aria-label="Close">×</button>
        </div>
        <p className="text-xs text-cream/50 mb-5">Reviewing <span className="text-cream">{product.name}</span>. Your review will be visible after admin approval. If you have a delivered order for this piece, you will automatically show as a Verified purchase.</p>
        <label className="block text-[10px] uppercase tracking-luxury text-gold-soft mb-2">Your rating</label>
        <div className="flex items-center gap-1 mb-4">
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => setRating(n)}
              data-testid={`review-rating-${n}`}
              className="p-1"
              aria-label={`${n} stars`}
            >
              <Star className={`w-6 h-6 transition ${rating >= n ? "fill-gold text-gold" : "text-cream/25"}`} />
            </button>
          ))}
        </div>
        <label className="block text-[10px] uppercase tracking-luxury text-gold-soft mb-2">Title</label>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={140}
          placeholder="Sums up your experience in a few words"
          data-testid="review-title"
          className="w-full bg-ink-900 border border-white/10 text-cream text-sm px-3 py-2.5 mb-4 focus:border-gold outline-none"
        />
        <label className="block text-[10px] uppercase tracking-luxury text-gold-soft mb-2">Your review</label>
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={5}
          maxLength={4000}
          placeholder="What did you love? Anything the atelier can improve?"
          data-testid="review-body"
          className="w-full bg-ink-900 border border-white/10 text-cream text-sm px-3 py-2.5 mb-4 focus:border-gold outline-none resize-y"
        />
        <div className="flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="text-xs uppercase tracking-luxury text-cream/60 hover:text-cream px-4 py-2"
          >Cancel</button>
          <button
            type="button"
            disabled={busy}
            onClick={submit}
            data-testid="review-submit"
            className="text-xs uppercase tracking-luxury bg-gold text-ink-950 px-5 py-2.5 hover:bg-gold-soft disabled:opacity-50"
          >{busy ? "Submitting…" : "Submit review"}</button>
        </div>
      </div>
    </div>
  );
}
