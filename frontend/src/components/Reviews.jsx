import React from "react";
import { motion } from "framer-motion";
import { Star, BadgeCheck, Quote } from "lucide-react";
import { IDS } from "@/constants/testIds";

const Stars = ({ rating = 5 }) => (
  <div className="flex gap-0.5">
    {Array.from({ length: 5 }).map((_, i) => (
      <Star key={i} className={`w-3.5 h-3.5 ${i < rating ? "fill-gold text-gold" : "text-cream/20"}`} />
    ))}
  </div>
);

export const Reviews = ({ reviews = [] }) => {
  return (
    <section id="reviews" data-testid={IDS.reviews.section} className="relative bg-ink-900 py-24 md:py-40">
      <div className="max-w-[1440px] mx-auto px-6 md:px-12 lg:px-16">
        <div className="grid lg:grid-cols-12 gap-10 mb-16">
          <div className="lg:col-span-6">
            <div className="flex items-center gap-3 mb-6">
              <span className="gold-line w-10" />
              <span className="text-[10px] uppercase tracking-luxury text-gold-soft">
                Verified Collectors
              </span>
            </div>
            <h2 className="font-serif text-4xl md:text-5xl lg:text-6xl leading-[0.95] text-cream text-balance">
              Voices from <span className="italic font-display text-gold">the collectors</span>.
            </h2>
          </div>
          <div className="lg:col-span-5 lg:col-start-8 self-end">
            <div className="flex items-center gap-6">
              <div className="font-serif text-6xl text-cream">4.98</div>
              <div>
                <Stars rating={5} />
                <div className="mt-2 text-xs text-cream/50">
                  Based on {reviews.length}+ verified purchases
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {reviews.map((r, i) => (
            <motion.article
              key={r.id || i}
              data-testid={IDS.reviews.card(i)}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.15 }}
              transition={{ duration: 0.8, delay: (i % 3) * 0.1 }}
              className={`relative bg-ink-800 border border-white/5 p-8 flex flex-col ${
                i === 0 || i === 3 ? "lg:row-span-2" : ""
              }`}
            >
              <Quote className="w-6 h-6 text-gold/40 mb-4" />
              {r.image && (i === 0 || i === 3) && (
                <div className="aspect-[4/3] overflow-hidden mb-6 -mx-8 -mt-8 border-b border-white/5">
                  <img src={r.image} alt="" className="w-full h-full object-cover" />
                </div>
              )}
              <Stars rating={r.rating} />
              <h3 className="mt-4 font-serif text-xl text-cream leading-snug">{r.title}</h3>
              <p className="mt-3 text-sm text-cream/60 leading-relaxed font-light flex-1">
                {r.body}
              </p>
              <div className="mt-6 pt-6 border-t border-white/5 flex items-center justify-between">
                <div>
                  <div className="text-sm text-cream">{r.author}</div>
                  <div className="text-[10px] uppercase tracking-luxury text-cream/40 mt-1">{r.location}</div>
                </div>
                <BadgeCheck className="w-4 h-4 text-gold" />
              </div>
            </motion.article>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Reviews;
