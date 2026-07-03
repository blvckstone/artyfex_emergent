import React from "react";
import { motion } from "framer-motion";
import { ArrowUpRight } from "lucide-react";
import { useCart } from "@/context/CartContext";
import { IDS } from "@/constants/testIds";

const formatINR = (n) => `₹${n.toLocaleString("en-IN")}`;

export const Collection = ({ products = [] }) => {
  const { addItem } = useCart();
  const items = products.filter((p) => !p.is_hero);

  return (
    <section id="collection" data-testid={IDS.collection.section} className="relative bg-ink-950 py-24 md:py-40">
      <div className="max-w-[1440px] mx-auto px-6 md:px-12 lg:px-16">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-8 mb-16">
          <div>
            <div className="flex items-center gap-3 mb-6">
              <span className="gold-line w-10" />
              <span className="text-[10px] uppercase tracking-luxury text-gold-soft">The Collection</span>
            </div>
            <h2 className="font-serif text-4xl md:text-5xl lg:text-6xl leading-[0.95] text-cream text-balance">
              Companion <span className="italic font-display text-gold">pieces</span>.
            </h2>
          </div>
          <p className="max-w-md text-cream/60 font-light">
            Smaller edits from the atelier — each still 100% handpoured, still one of one.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8">
          {items.map((p, i) => (
            <motion.div
              key={p.id}
              data-testid={IDS.collection.card(p.slug)}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.8, delay: i * 0.08 }}
              className="group relative bg-ink-900 border border-white/5 hover:border-gold/30 transition-colors"
            >
              <div className="aspect-[4/5] overflow-hidden">
                <img
                  src={p.hero_image}
                  alt={p.name}
                  className="w-full h-full object-cover transition-transform duration-[1200ms] group-hover:scale-105"
                />
              </div>
              <div className="p-6">
                <div className="text-[10px] uppercase tracking-luxury text-gold-soft">{p.size}</div>
                <h3 className="mt-3 font-serif text-2xl text-cream leading-tight">{p.name.split(" — ")[0]}</h3>
                <p className="mt-2 text-sm text-cream/50 italic font-serif">{p.tagline}</p>
                <div className="mt-5 flex items-center justify-between">
                  <span className="font-serif text-2xl text-cream">{formatINR(p.price_inr)}</span>
                  <button
                    data-testid={IDS.collection.add(p.slug)}
                    onClick={() => addItem(p, p.variants[0].key, 1)}
                    className="inline-flex items-center gap-2 text-[10px] uppercase tracking-luxury text-gold hover:text-cream transition-colors"
                  >
                    Add <ArrowUpRight className="w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="mt-4 flex gap-2">
                  {p.variants.map((v) => (
                    <span
                      key={v.key}
                      title={v.label}
                      className="w-4 h-4 rounded-full ring-1 ring-white/20"
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
