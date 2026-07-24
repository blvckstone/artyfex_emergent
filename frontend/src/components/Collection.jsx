import React from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import { useCart } from "@/context/CartContext";
import { IDS } from "@/constants/testIds";
import { displayableVariants } from "@/lib/utils";

const formatINR = (n) => `₹${n.toLocaleString("en-IN")}`;

export const Collection = ({ products = [], content }) => {
  const { addItem } = useCart();
  const c = content || {};
  const eyebrow = c.eyebrow || "The Collection";
  const line1 = c.headline_line_1 || "Companion";
  const italic = c.headline_italic || "pieces";
  const subtitle = c.subtitle || "Smaller edits from the atelier — each still 100% handpoured, still one of one.";
  const featuredIds = Array.isArray(c.featured_product_ids) ? c.featured_product_ids : [];

  // Filter items: exclude hero product. If admin has picked specific products, honour that order + limit to those.
  let items;
  if (featuredIds.length > 0) {
    const map = new Map(products.map((p) => [p.id, p]));
    items = featuredIds.map((id) => map.get(id)).filter(Boolean);
  } else {
    items = products.filter((p) => !p.is_hero);
  }

  return (
    <section id="collection" data-testid={IDS.collection.section} className="relative bg-ink-950 py-14 md:py-32">
      <div className="max-w-[1440px] mx-auto px-4 md:px-12 lg:px-16">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 md:gap-8 mb-8 md:mb-16">
          <div>
            <div className="flex items-center gap-3 mb-3 md:mb-6">
              <span className="gold-line w-8 md:w-10" />
              <span className="text-[10px] uppercase tracking-luxury text-gold-soft">{eyebrow}</span>
            </div>
            <h2 className="font-serif text-2xl sm:text-3xl md:text-5xl lg:text-6xl leading-[1] text-cream text-balance">
              {line1} <span className="italic font-display text-gold">{italic}</span>.
            </h2>
          </div>
          <p className="max-w-md text-cream/60 text-xs md:text-base font-light">
            {subtitle}
          </p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-2 lg:grid-cols-3 gap-2.5 md:gap-6 lg:gap-8">
          {items.map((p, i) => (
            <motion.div
              key={p.id}
              data-testid={IDS.collection.card(p.slug)}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.8, delay: i * 0.08 }}
              className="group relative bg-ink-900 border border-white/10 rounded-xl md:rounded-none overflow-hidden hover:border-gold/30 transition-colors"
            >
              <Link
                to={`/product/${p.slug}`}
                data-testid={`collection-image-link-${p.slug}`}
                aria-label={`View ${p.name}`}
                className="block aspect-[4/5] overflow-hidden relative group/img"
              >
                <img
                  src={p.hero_image}
                  alt={p.name}
                  loading="lazy"
                  decoding="async"
                  className="w-full h-full object-cover transition-transform duration-[900ms] md:group-hover:scale-105"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent opacity-0 group-hover/img:opacity-100 transition-opacity duration-500" />
                <div className="absolute bottom-4 right-4 opacity-0 group-hover/img:opacity-100 translate-y-2 group-hover/img:translate-y-0 transition-all duration-500">
                  <span className="inline-flex items-center gap-2 glass-gold px-3 py-1.5 text-[10px] uppercase tracking-luxury text-gold">
                    View piece <ArrowUpRight className="w-3 h-3" />
                  </span>
                </div>
              </Link>
              <div className="p-3 md:p-6">
                <div className="text-[9px] md:text-[10px] uppercase tracking-luxury text-gold-soft truncate">{p.size}</div>
                <Link
                  to={`/product/${p.slug}`}
                  data-testid={`collection-title-link-${p.slug}`}
                  className="block mt-1.5 md:mt-3 group/title"
                >
                  <h3 className="font-serif text-base md:text-2xl text-cream leading-tight line-clamp-2 group-hover/title:text-gold transition-colors">
                    {p.name.split(" — ")[0]}
                  </h3>
                </Link>
                <p className="mt-1.5 md:mt-2 text-xs md:text-sm text-cream/50 italic font-serif hidden md:block">{p.tagline}</p>
                <div className="mt-3 md:mt-5 flex items-center justify-between gap-2">
                  <span className="font-serif text-lg md:text-2xl text-cream">{formatINR(p.price_inr)}</span>
                  <button
                    data-testid={IDS.collection.add(p.slug)}
                    onClick={() => addItem(p, p.variants[0].key, 1)}
                    className="inline-flex items-center gap-1 md:gap-2 text-[9px] md:text-[10px] uppercase tracking-luxury text-gold hover:text-cream transition-colors shrink-0"
                  >
                    Add <ArrowUpRight className="w-3 h-3 md:w-3.5 md:h-3.5" />
                  </button>
                </div>
                <div className="mt-3 md:mt-4 flex gap-1.5 md:gap-2">
                  {displayableVariants(p.variants).map((v) => (
                    <span
                      key={v.key}
                      title={v.label}
                      className="w-3.5 h-3.5 md:w-4 md:h-4 rounded-full ring-1 ring-white/20"
                      style={{ background: `radial-gradient(circle at 30% 30%, ${v.hex}, #0a0a0a 80%)` }}
                    />
                  ))}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Collection;
