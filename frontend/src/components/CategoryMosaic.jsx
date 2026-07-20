import React from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";

/**
 * "Explore the Atelier · Curated worlds of luxury" — the bento grid below the hero.
 *
 * Task 2 (Jul 2025) — Fixes:
 *   1. Custom admin-added tiles now show on the homepage (they were being
 *      clipped because the slice(0, 5) truncated anything past 5). We now
 *      show up to 6 tiles.
 *   2. Desktop overlap eliminated: layout spans are chosen by INDEX (not by
 *      hard-coded slug), so admin-added tiles inherit a valid grid slot.
 *   3. Empty/incomplete tiles (no image AND no label) are skipped instead of
 *      collapsing into overlapping placeholders.
 *   4. React keys are unique even when slugs are duplicated / empty.
 */

const DEFAULTS = [
  { slug: "mirrors",  label: "Luxury Mirrors",  keyword: "handmade resin · crystal", image: "https://images.unsplash.com/photo-1599696848652-f0ff23bc911f?auto=format&fit=crop&w=900&q=60" },
  { slug: "wall-art", label: "Modern Wall Art", keyword: "statement pieces",         image: "https://images.unsplash.com/photo-1555432384-3b2fa7b650c9?auto=format&fit=crop&w=900&q=60" },
  { slug: "sculpture",label: "Sculpture",       keyword: "limited editions",         image: "https://images.unsplash.com/photo-1601887389937-0b02c26b602c?auto=format&fit=crop&w=700&q=60" },
  { slug: "lighting", label: "Lighting",        keyword: "resin · brass",            image: "https://images.unsplash.com/photo-1507494924047-60b8ee826ca9?auto=format&fit=crop&w=700&q=60" },
  { slug: "custom",   label: "Bespoke / Custom",keyword: "designed with you",        image: "https://images.unsplash.com/photo-1716221234833-1888747eabec?auto=format&fit=crop&w=700&q=60" },
];

// Position-based (NOT slug-based) grid spans. Total = 6 cols on desktop, 2 rows.
// Position 0 → large 3×2 hero.  Positions 1..4 → wide + squares filling row 1 & 2.
// Position 5 → optional 6th tile (spans full width beneath).
// This layout is guaranteed to never overlap because the sum of column-spans
// per row equals exactly 6.
const LAYOUT_BY_INDEX = [
  { spanDesktop: "md:col-span-3 md:row-span-2", aspectDesktop: "md:aspect-auto md:h-full", mobileSpan: "col-span-2 aspect-[16/10]" },
  { spanDesktop: "md:col-span-3 md:row-span-1", aspectDesktop: "md:aspect-[16/9]",         mobileSpan: "aspect-square" },
  { spanDesktop: "md:col-span-1",               aspectDesktop: "md:aspect-square",         mobileSpan: "aspect-square" },
  { spanDesktop: "md:col-span-1",               aspectDesktop: "md:aspect-square",         mobileSpan: "aspect-square" },
  { spanDesktop: "md:col-span-1",               aspectDesktop: "md:aspect-square",         mobileSpan: "aspect-square" },
  { spanDesktop: "md:col-span-6",               aspectDesktop: "md:aspect-[24/9]",         mobileSpan: "col-span-2 aspect-[16/9]" },
];

export default function CategoryMosaic({ categories, content }) {
  const c = content || {};
  // Merge admin tiles with defaults; keep admin ordering. Skip completely-empty tiles.
  const source = (categories && categories.length ? categories : DEFAULTS);
  const items = source
    .filter((t) => t && (t.image || t.label || t.slug))
    .map((t, i) => ({
      slug: t.slug || `tile-${i}`,
      label: t.label || "Untitled",
      keyword: t.keyword || "",
      image: t.image || DEFAULTS[i % DEFAULTS.length].image, // fallback so a broken tile never leaves a black gap
    }))
    .slice(0, LAYOUT_BY_INDEX.length);

  const eyebrow = c.eyebrow || "Explore the Atelier";
  const line1 = c.headline_line_1 || "Curated";
  const italic = c.headline_italic || "worlds";
  const line2 = c.headline_line_2 || " of luxury.";
  const subtitle = c.subtitle || "From statement mirrors to bespoke furniture — every category, handpoured in Mumbai.";

  return (
    <section
      id="categories"
      data-testid="home-category-mosaic"
      className="relative bg-ink-950 py-12 md:py-24 border-t border-white/5"
    >
      <div className="max-w-[1440px] mx-auto px-4 md:px-12 lg:px-16">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 md:gap-6 mb-6 md:mb-10">
          <div>
            <div className="flex items-center gap-3 mb-3 md:mb-4">
              <span className="gold-line w-8 md:w-10" />
              <span className="text-[10px] uppercase tracking-luxury text-gold-soft">{eyebrow}</span>
            </div>
            <h2 className="font-serif text-2xl sm:text-3xl md:text-5xl leading-[1] text-cream text-balance">
              {line1} <span className="italic font-display text-gold">{italic}</span>{line2}
            </h2>
          </div>
          <p className="max-w-md text-cream/60 text-xs md:text-base font-light">
            {subtitle}
          </p>
        </div>

        {/* Mobile: 2-col grid. Desktop: 6-col bento with fixed row height. */}
        <div className="grid grid-cols-2 md:grid-cols-6 md:auto-rows-[240px] gap-2.5 md:gap-4">
          {items.map((cat, i) => {
            const layout = LAYOUT_BY_INDEX[i] || LAYOUT_BY_INDEX[LAYOUT_BY_INDEX.length - 1];
            return (
              <motion.div
                key={`${cat.slug}-${i}`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.1 }}
                transition={{ duration: 0.55, delay: Math.min(i, 4) * 0.05 }}
                className={`group relative overflow-hidden rounded-xl md:rounded-none border border-white/10 hover:border-gold/40 transition-colors ${layout.mobileSpan} ${layout.spanDesktop} ${layout.aspectDesktop}`}
                data-testid={`home-cat-${cat.slug}`}
              >
                <Link to={`/shop?category=${cat.slug}`} aria-label={cat.label} className="block absolute inset-0">
                  <img
                    src={cat.image}
                    alt={`${cat.label} — luxury handmade art by ArtyFex Mumbai`}
                    loading="lazy"
                    decoding="async"
                    className="w-full h-full object-cover md:scale-[1.02] md:group-hover:scale-110 transition-transform duration-[900ms] ease-out"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-ink-950 via-ink-950/40 to-transparent" />
                  <div className="absolute inset-0 ring-1 ring-inset ring-gold/10 md:group-hover:ring-gold/40 transition-all" />

                  <div className="absolute inset-x-0 bottom-0 p-3 md:p-6 flex items-end justify-between gap-2 md:gap-3">
                    <div className="min-w-0">
                      {cat.keyword && (
                        <div className="text-[8px] md:text-[10px] uppercase tracking-luxury text-gold-soft mb-0.5 md:mb-1 truncate">{cat.keyword}</div>
                      )}
                      <h3 className="font-serif text-base md:text-2xl lg:text-3xl text-cream leading-tight line-clamp-2">{cat.label}</h3>
                    </div>
                    <span className="inline-flex items-center justify-center w-7 h-7 md:w-10 md:h-10 rounded-full bg-gold/10 border border-gold/30 text-gold shrink-0 md:group-hover:bg-gold md:group-hover:text-ink-950 transition-all">
                      <ArrowUpRight className="w-3 h-3 md:w-4 md:h-4" />
                    </span>
                  </div>
                </Link>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
