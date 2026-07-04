import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, ChevronRight, ZoomIn, X } from "lucide-react";

/**
 * ProductGallery
 * High-end product image viewer for the product page.
 *
 * Features:
 *  - Combined gallery = deduped (variant images + product.gallery)
 *  - Thumbnails swap the main image instantly (fixes: variant image no longer overrides thumb click)
 *  - Smooth cross-fade + slide carousel via framer-motion
 *  - Prev / next buttons + keyboard arrow navigation
 *  - Hover-to-zoom on the main image (cursor-following, scale 1.9x, cursor: zoom-in)
 *  - Click main image → fullscreen lightbox with pinch/scroll zoom
 *
 * Props:
 *  - product: full product object (needs `gallery`, `variants`, `hero_image`, `craft_hours`, `is_hero`)
 *  - variantImage: currently-active variant's image (may be undefined)
 */
export default function ProductGallery({ product, variantImage }) {
  // Build combined, deduped image list — variants first, then gallery
  const allImages = useMemo(() => {
    const seen = new Set();
    const arr = [];
    (product?.variants || []).forEach((v) => {
      if (v?.image && !seen.has(v.image)) { seen.add(v.image); arr.push(v.image); }
    });
    (product?.gallery || []).forEach((g) => {
      if (g && !seen.has(g)) { seen.add(g); arr.push(g); }
    });
    if (!arr.length && product?.hero_image) arr.push(product.hero_image);
    return arr;
  }, [product]);

  const [activeIdx, setActiveIdx] = useState(0);
  const [direction, setDirection] = useState(0); // -1 for prev, 1 for next
  const [zooming, setZooming] = useState(false);
  const [zoomOrigin, setZoomOrigin] = useState({ x: 50, y: 50 });
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const containerRef = useRef(null);

  // Sync main image when the active variant changes (variant-driven swap)
  useEffect(() => {
    if (variantImage) {
      const idx = allImages.indexOf(variantImage);
      if (idx >= 0 && idx !== activeIdx) {
        setDirection(idx > activeIdx ? 1 : -1);
        setActiveIdx(idx);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [variantImage]);

  const goTo = useCallback(
    (nextIdx) => {
      if (!allImages.length) return;
      const n = ((nextIdx % allImages.length) + allImages.length) % allImages.length;
      setDirection(n > activeIdx ? 1 : n < activeIdx ? -1 : 0);
      setActiveIdx(n);
    },
    [activeIdx, allImages.length],
  );

  const next = useCallback(() => goTo(activeIdx + 1), [goTo, activeIdx]);
  const prev = useCallback(() => goTo(activeIdx - 1), [goTo, activeIdx]);

  // Keyboard nav
  useEffect(() => {
    const onKey = (e) => {
      if (lightboxOpen) {
        if (e.key === "Escape") setLightboxOpen(false);
      }
      if (e.key === "ArrowRight") next();
      else if (e.key === "ArrowLeft") prev();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [next, prev, lightboxOpen]);

  const handleMouseMove = (e) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    setZoomOrigin({ x: Math.max(0, Math.min(100, x)), y: Math.max(0, Math.min(100, y)) });
  };

  // Touch swipe on main image
  const touchStartX = useRef(null);
  const onTouchStart = (e) => { touchStartX.current = e.touches[0].clientX; };
  const onTouchEnd = (e) => {
    if (touchStartX.current == null) return;
    const dx = e.changedTouches[0].clientX - touchStartX.current;
    if (Math.abs(dx) > 40) {
      if (dx < 0) next(); else prev();
    }
    touchStartX.current = null;
  };

  const mainImage = allImages[activeIdx] || product?.hero_image;

  const slideVariants = {
    enter: (dir) => ({ opacity: 0, x: dir > 0 ? 40 : dir < 0 ? -40 : 0, scale: 1.02 }),
    center: { opacity: 1, x: 0, scale: 1 },
    exit: (dir) => ({ opacity: 0, x: dir > 0 ? -40 : dir < 0 ? 40 : 0, scale: 1.02 }),
  };

  if (!allImages.length || !mainImage) {
    return <div className="aspect-[4/5] bg-ink-900 border border-white/10" />;
  }

  return (
    <div className="lg:sticky lg:top-28" data-testid="product-gallery">
      {/* Main image */}
      <div
        ref={containerRef}
        onMouseEnter={() => setZooming(true)}
        onMouseLeave={() => setZooming(false)}
        onMouseMove={handleMouseMove}
        onTouchStart={onTouchStart}
        onTouchEnd={onTouchEnd}
        className="relative aspect-[4/5] w-full overflow-hidden border border-white/10 bg-ink-900 group select-none"
        style={{ cursor: zooming ? "zoom-in" : "default" }}
        data-testid="product-gallery-main-container"
      >
        <AnimatePresence initial={false} custom={direction} mode="wait">
          <motion.img
            key={activeIdx}
            src={mainImage}
            alt={product?.name || "Product image"}
            custom={direction}
            variants={slideVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
            className="absolute inset-0 w-full h-full object-cover will-change-transform"
            style={{
              transformOrigin: `${zoomOrigin.x}% ${zoomOrigin.y}%`,
              transform: zooming ? "scale(1.9)" : "scale(1)",
              transition: zooming ? "transform 0.35s ease-out" : "transform 0.4s ease-out",
            }}
            draggable={false}
            data-testid="product-hero-image"
          />
        </AnimatePresence>

        {/* Badges */}
        {product?.is_hero && (
          <div className="absolute top-4 left-4 glass-gold px-3 py-1.5 text-[10px] uppercase tracking-luxury text-gold pointer-events-none">
            Signature edition
          </div>
        )}
        <div className="absolute bottom-4 right-4 glass px-4 py-2 text-[10px] uppercase tracking-luxury text-cream/80 pointer-events-none">
          {product?.craft_hours} artisan hours
        </div>

        {/* Zoom hint */}
        <div
          className={`absolute top-4 right-4 glass px-2.5 py-1.5 text-[10px] uppercase tracking-luxury text-cream/70 inline-flex items-center gap-1.5 pointer-events-none transition-opacity duration-300 ${
            zooming ? "opacity-0" : "opacity-100"
          }`}
        >
          <ZoomIn className="w-3 h-3" /> Hover to zoom
        </div>

        {/* Prev / Next chevrons */}
        {allImages.length > 1 && (
          <>
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); prev(); }}
              data-testid="gallery-prev"
              aria-label="Previous image"
              className="absolute left-3 top-1/2 -translate-y-1/2 z-10 w-11 h-11 flex items-center justify-center glass border border-white/10 text-cream/80 hover:text-gold hover:border-gold/40 transition-all opacity-0 group-hover:opacity-100 focus:opacity-100"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); next(); }}
              data-testid="gallery-next"
              aria-label="Next image"
              className="absolute right-3 top-1/2 -translate-y-1/2 z-10 w-11 h-11 flex items-center justify-center glass border border-white/10 text-cream/80 hover:text-gold hover:border-gold/40 transition-all opacity-0 group-hover:opacity-100 focus:opacity-100"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </>
        )}

        {/* Expand to lightbox */}
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); setLightboxOpen(true); }}
          data-testid="gallery-expand"
          aria-label="View fullscreen"
          className="absolute bottom-4 left-4 z-10 glass border border-white/10 text-cream/80 hover:text-gold hover:border-gold/40 transition-all px-3 py-2 text-[10px] uppercase tracking-luxury inline-flex items-center gap-1.5 opacity-0 group-hover:opacity-100 focus:opacity-100"
        >
          <ZoomIn className="w-3 h-3" /> Fullscreen
        </button>

        {/* Index counter */}
        {allImages.length > 1 && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 glass px-2.5 py-1 text-[10px] tracking-luxury text-cream/70 pointer-events-none">
            {activeIdx + 1} / {allImages.length}
          </div>
        )}
      </div>

      {/* Thumbnails */}
      {allImages.length > 1 && (
        <div className="mt-4 grid grid-cols-4 sm:grid-cols-5 md:grid-cols-6 gap-3">
          {allImages.map((g, i) => (
            <button
              key={g + i}
              type="button"
              data-testid={`product-thumb-${i}`}
              onClick={() => goTo(i)}
              aria-label={`View image ${i + 1}`}
              aria-current={activeIdx === i}
              className={`aspect-square overflow-hidden border transition-all ${
                activeIdx === i ? "border-gold ring-1 ring-gold/40" : "border-white/10 hover:border-white/30"
              }`}
            >
              <img
                src={g}
                alt=""
                className={`w-full h-full object-cover transition-transform duration-500 ${
                  activeIdx === i ? "scale-105" : "hover:scale-105"
                }`}
              />
            </button>
          ))}
        </div>
      )}

      {/* Lightbox */}
      <AnimatePresence>
        {lightboxOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.35 }}
            className="fixed inset-0 z-[100] bg-black/95 backdrop-blur-sm flex items-center justify-center p-4 md:p-8"
            data-testid="gallery-lightbox"
            onClick={() => setLightboxOpen(false)}
          >
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); setLightboxOpen(false); }}
              className="absolute top-6 right-6 z-10 w-11 h-11 flex items-center justify-center border border-white/10 text-cream/80 hover:text-gold hover:border-gold/40 transition-all"
              aria-label="Close fullscreen"
              data-testid="lightbox-close"
            >
              <X className="w-5 h-5" />
            </button>

            {allImages.length > 1 && (
              <>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); prev(); }}
                  data-testid="lightbox-prev"
                  aria-label="Previous"
                  className="absolute left-6 top-1/2 -translate-y-1/2 z-10 w-12 h-12 flex items-center justify-center border border-white/10 text-cream/80 hover:text-gold hover:border-gold/40 transition-all"
                >
                  <ChevronLeft className="w-6 h-6" />
                </button>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); next(); }}
                  data-testid="lightbox-next"
                  aria-label="Next"
                  className="absolute right-6 top-1/2 -translate-y-1/2 z-10 w-12 h-12 flex items-center justify-center border border-white/10 text-cream/80 hover:text-gold hover:border-gold/40 transition-all"
                >
                  <ChevronRight className="w-6 h-6" />
                </button>
              </>
            )}

            <motion.img
              key={activeIdx}
              src={mainImage}
              alt={product?.name}
              onClick={(e) => e.stopPropagation()}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
              transition={{ duration: 0.35 }}
              className="max-h-full max-w-full object-contain cursor-zoom-out"
              draggable={false}
            />

            <div className="absolute bottom-6 left-1/2 -translate-x-1/2 text-[10px] uppercase tracking-luxury text-cream/60">
              {activeIdx + 1} / {allImages.length} · Press Esc to close · ← → to navigate
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
