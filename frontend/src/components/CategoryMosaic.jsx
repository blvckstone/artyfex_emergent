import React from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";

const DEFAULTS = [
  {
    slug: "mirrors",
    label: "Luxury Mirrors",
    keyword: "handmade resin · crystal",
    image: "https://images.unsplash.com/photo-1599696848652-f0ff23bc911f?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzNDR8MHwxfHNlYXJjaHwxfHxsdXh1cnklMjBpbnRlcmlvcnxlbnwwfHx8YmxhY2t8MTc4NDIwMzQ1OHww&ixlib=rb-4.1.0&q=85",
    span: "md:col-span-3 md:row-span-2",
    aspect: "aspect-[4/5] md:aspect-auto md:h-full",
  },
  {
    slug: "wall-art",
    label: "Modern Wall Art",
    keyword: "statement pieces",
    image: "https://images.unsplash.com/photo-1555432384-3b2fa7b650c9?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjY2NzN8MHwxfHNlYXJjaHwyfHxtb2Rlcm4lMjBhcnR8ZW58MHx8fGJsYWNrfDE3ODQyMDM0NTd8MA&ixlib=rb-4.1.0&q=85",
    span: "md:col-span-3 md:row-span-1",
    aspect: "aspect-[16/9]",
  },
  {
    slug: "sculpture",
    label: "Sculpture",
    keyword: "limited editions",
    image: "https://images.unsplash.com/photo-1601887389937-0b02c26b602c?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NjZ8MHwxfHNlYXJjaHwxfHxzY3VscHR1cmV8ZW58MHx8fGJsYWNrfDE3ODQyMDM0NTd8MA&ixlib=rb-4.1.0&q=85",
    span: "md:col-span-2",
    aspect: "aspect-square",
  },
  {
    slug: "lighting",
    label: "Lighting",
    keyword: "resin · brass",
    image: "https://images.unsplash.com/photo-1507494924047-60b8ee826ca9?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2Nzh8MHwxfHNlYXJjaHw0fHxsaWdodGluZ3xlbnwwfHx8YmxhY2t8MTc4NDIwMzQ1OHww&ixlib=rb-4.1.0&q=85",
    span: "md:col-span-2",
    aspect: "aspect-square",
  },
  {
    slug: "custom",
    label: "Bespoke / Custom",
    keyword: "designed with you",
    image: "https://images.unsplash.com/photo-1716221234833-1888747eabec?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2ODh8MHwxfHNlYXJjaHwxfHxiZXNwb2tlJTIwZnVybml0dXJlfGVufDB8fHxibGFja3wxNzg0MjAzNDU4fDA&ixlib=rb-4.1.0&q=85",
    span: "md:col-span-2",
    aspect: "aspect-square",
  },
];

export default function CategoryMosaic({ categories }) {
  const items = (categories && categories.length ? categories : DEFAULTS).slice(0, 5);
  return (
    <section id="categories" data-testid="home-category-mosaic" className="relative bg-ink-950 py-20 md:py-28 border-t border-white/5">
      <div className="max-w-[1440px] mx-auto px-6 md:px-12 lg:px-16">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6 mb-10">
          <div>
            <div className="flex items-center gap-3 mb-4">
              <span className="gold-line w-10" />
              <span className="text-[10px] uppercase tracking-luxury text-gold-soft">Explore the Atelier</span>
            </div>
            <h2 className="font-serif text-3xl md:text-5xl leading-[0.95] text-cream text-balance">
              Curated <span className="italic font-display text-gold">worlds</span> of luxury.
            </h2>
          </div>
          <p className="max-w-md text-cream/60 text-sm md:text-base font-light">
            From statement mirrors to bespoke furniture — every category, handpoured in Mumbai. Discover the piece that will complete your interior.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-6 md:auto-rows-[260px] gap-4 md:gap-5">
          {items.map((cat, i) => (
            <motion.div
              key={cat.slug}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.15 }}
              transition={{ duration: 0.7, delay: i * 0.06 }}
              className={`group relative overflow-hidden border border-white/5 hover:border-gold/40 transition-colors ${cat.span || "md:col-span-2"} ${cat.aspect || "aspect-square"}`}
              data-testid={`home-cat-${cat.slug}`}
            >
              <Link to={`/shop?category=${cat.slug}`} aria-label={cat.label} className="block absolute inset-0">
                <img
                  src={cat.image}
                  alt={`${cat.label} — luxury handmade art by ArtyFex Mumbai`}
                  loading="lazy"
                  className="w-full h-full object-cover scale-[1.02] group-hover:scale-110 transition-transform duration-[1400ms] ease-out"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-ink-950 via-ink-950/40 to-transparent" />
                <div className="absolute inset-0 ring-1 ring-inset ring-gold/10 group-hover:ring-gold/40 transition-all" />

                <div className="absolute inset-x-0 bottom-0 p-5 md:p-6 flex items-end justify-between gap-3">
                  <div>
                    <div className="text-[10px] uppercase tracking-luxury text-gold-soft mb-1">{cat.keyword}</div>
                    <h3 className="font-serif text-xl md:text-2xl lg:text-3xl text-cream leading-tight">{cat.label}</h3>
                  </div>
                  <span className="inline-flex items-center justify-center w-9 h-9 md:w-10 md:h-10 rounded-full bg-gold/10 border border-gold/30 text-gold shrink-0 group-hover:bg-gold group-hover:text-ink-950 transition-all">
                    <ArrowUpRight className="w-4 h-4" />
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
