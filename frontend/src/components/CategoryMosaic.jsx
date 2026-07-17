import React from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";

// Small versions for mobile (w=600) and larger for desktop (w=1200). Loading is
// lazy + async to keep the homepage feeling instant.
const DEFAULTS = [
  {
    slug: "mirrors",
    label: "Luxury Mirrors",
    keyword: "handmade resin · crystal",
    image: "https://images.unsplash.com/photo-1599696848652-f0ff23bc911f?auto=format&fit=crop&w=900&q=60",
    spanDesktop: "md:col-span-3 md:row-span-2",
    aspectDesktop: "md:aspect-auto md:h-full",
  },
  {
    slug: "wall-art",
    label: "Modern Wall Art",
    keyword: "statement pieces",
    image: "https://images.unsplash.com/photo-1555432384-3b2fa7b650c9?auto=format&fit=crop&w=900&q=60",
    spanDesktop: "md:col-span-3 md:row-span-1",
    aspectDesktop: "md:aspect-[16/9]",
  },
  {
    slug: "sculpture",
    label: "Sculpture",
    keyword: "limited editions",
    image: "https://images.unsplash.com/photo-1601887389937-0b02c26b602c?auto=format&fit=crop&w=700&q=60",
    spanDesktop: "md:col-span-2",
    aspectDesktop: "md:aspect-square",
  },
  {
    slug: "lighting",
    label: "Lighting",
    keyword: "resin · brass",
    image: "https://images.unsplash.com/photo-1507494924047-60b8ee826ca9?auto=format&fit=crop&w=700&q=60",
    spanDesktop: "md:col-span-2",
    aspectDesktop: "md:aspect-square",
  },
  {
    slug: "custom",
    label: "Bespoke / Custom",
    keyword: "designed with you",
    image: "https://images.unsplash.com/photo-1716221234833-1888747eabec?auto=format&fit=crop&w=700&q=60",
    spanDesktop: "md:col-span-2",
    aspectDesktop: "md:aspect-square",
  },
];

export default function CategoryMosaic({ categories, content }) {
  const c = content || {};
  const items = (categories && categories.length ? categories : DEFAULTS).slice(0, 5);
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

        {/* Mobile: 2-col tight grid (native-app feel). Desktop: 6-col bento */}
        <div className="grid grid-cols-2 md:grid-cols-6 md:auto-rows-[240px] gap-2.5 md:gap-4">
          {items.map((cat, i) => (
            <motion.div
              key={cat.slug}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.1 }}
              transition={{ duration: 0.55, delay: Math.min(i, 4) * 0.05 }}
              className={`group relative overflow-hidden rounded-xl md:rounded-none border border-white/10 hover:border-gold/40 transition-colors aspect-square ${cat.spanDesktop || "md:col-span-2"} ${cat.aspectDesktop || "md:aspect-square"} ${cat.slug === "mirrors" ? "col-span-2 aspect-[16/10] md:col-span-3" : ""}`}
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
                    <div className="text-[8px] md:text-[10px] uppercase tracking-luxury text-gold-soft mb-0.5 md:mb-1 truncate">{cat.keyword}</div>
                    <h3 className="font-serif text-base md:text-2xl lg:text-3xl text-cream leading-tight line-clamp-2">{cat.label}</h3>
                  </div>
                  <span className="inline-flex items-center justify-center w-7 h-7 md:w-10 md:h-10 rounded-full bg-gold/10 border border-gold/30 text-gold shrink-0 md:group-hover:bg-gold md:group-hover:text-ink-950 transition-all">
                    <ArrowUpRight className="w-3 h-3 md:w-4 md:h-4" />
                  </span>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
