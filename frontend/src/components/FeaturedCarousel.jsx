import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, ArrowRight } from "lucide-react";

const formatINR = (n) => `₹${(n || 0).toLocaleString("en-IN")}`;

export default function FeaturedCarousel({ products = [], content }) {
  const c = content || {};
  const eyebrow = c.eyebrow || "Featured";
  const line1 = c.headline_line_1 || "Editor's";
  const italic = c.headline_italic || "pick";
  const scroller = useRef(null);
  const [canL, setCanL] = useState(false);
  const [canR, setCanR] = useState(true);

  const items = products.slice(0, 8);

  const update = () => {
    const el = scroller.current; if (!el) return;
    setCanL(el.scrollLeft > 8);
    setCanR(el.scrollLeft + el.clientWidth < el.scrollWidth - 8);
  };

  useEffect(() => {
    update();
    const el = scroller.current; if (!el) return;
    el.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => { el.removeEventListener("scroll", update); window.removeEventListener("resize", update); };
  }, []);

  if (items.length === 0) return null;

  const scrollBy = (dir) => {
    const el = scroller.current; if (!el) return;
    const card = el.querySelector("[data-card]");
    const step = card ? card.getBoundingClientRect().width + 16 : el.clientWidth * 0.8;
    el.scrollBy({ left: dir * step, behavior: "smooth" });
  };

  return (
    <section id="featured" data-testid="home-featured-carousel" className="relative bg-ink-950 py-12 md:py-24 border-t border-white/5">
      <div className="max-w-[1440px] mx-auto px-4 md:px-12 lg:px-16">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 md:gap-6 mb-6 md:mb-10">
          <div>
            <div className="flex items-center gap-3 mb-3 md:mb-4">
              <span className="gold-line w-8 md:w-10" />
              <span className="text-[10px] uppercase tracking-luxury text-gold-soft">{eyebrow}</span>
            </div>
            <h2 className="font-serif text-2xl sm:text-3xl md:text-5xl leading-[1] text-cream text-balance">
              {line1} <span className="italic font-display text-gold">{italic}</span>.
            </h2>
          </div>
          <div className="hidden md:flex items-center gap-3">
            <button
              data-testid="featured-prev"
              onClick={() => scrollBy(-1)}
              disabled={!canL}
              className="inline-flex items-center justify-center w-11 h-11 border border-white/15 text-cream/80 hover:border-gold/50 hover:text-gold disabled:opacity-30 disabled:cursor-not-allowed transition-all"
              aria-label="Scroll left"
            ><ArrowLeft className="w-4 h-4" /></button>
            <button
              data-testid="featured-next"
              onClick={() => scrollBy(1)}
              disabled={!canR}
              className="inline-flex items-center justify-center w-11 h-11 border border-white/15 text-cream/80 hover:border-gold/50 hover:text-gold disabled:opacity-30 disabled:cursor-not-allowed transition-all"
              aria-label="Scroll right"
            ><ArrowRight className="w-4 h-4" /></button>
          </div>
        </div>

        <div
          ref={scroller}
          className="flex gap-3 md:gap-5 overflow-x-auto snap-x snap-mandatory scroll-smooth -mx-4 px-4 md:-mx-12 md:px-12 lg:-mx-16 lg:px-16 no-scrollbar pb-2"
          style={{ scrollbarWidth: "none" }}
        >
          {items.map((p, i) => (
            <motion.div
              key={p.id}
              data-card
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.1 }}
              transition={{ duration: 0.5, delay: Math.min(i, 4) * 0.04 }}
              className="snap-start shrink-0 w-[68%] sm:w-[45%] md:w-[32%] lg:w-[26%] xl:w-[22%] bg-ink-900 border border-white/10 rounded-xl md:rounded-none overflow-hidden hover:border-gold/40 transition-colors group"
            >
              <Link to={`/product/${p.slug}`} className="block aspect-[4/5] overflow-hidden relative">
                <img src={p.hero_image} alt={p.name} loading="lazy" decoding="async" className="w-full h-full object-cover md:group-hover:scale-105 transition-transform duration-[900ms]" />
                <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent" />
                {p.stock_count !== undefined && p.stock_count <= 1 && (
                  <span className="absolute top-3 left-3 bg-red-500/20 border border-red-400/40 text-red-300 text-[10px] uppercase tracking-luxury px-2 py-1 rounded">Last one</span>
                )}
              </Link>
              <div className="p-3 md:p-5">
                <div className="text-[9px] md:text-[10px] uppercase tracking-luxury text-gold-soft truncate">{p.size}</div>
                <Link to={`/product/${p.slug}`} className="block mt-1.5 md:mt-2">
                  <h3 className="font-serif text-base md:text-xl text-cream leading-tight line-clamp-2 group-hover:text-gold transition-colors">{p.name.split(" — ")[0]}</h3>
                </Link>
                <div className="mt-2 md:mt-3 font-serif text-lg md:text-xl text-cream">{formatINR(p.price_inr)}</div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
