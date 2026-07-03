import React from "react";
import { motion } from "framer-motion";
import { Hammer, Droplets, Gem, ShieldCheck } from "lucide-react";

const CRAFT_IMG =
  "https://images.pexels.com/photos/18325786/pexels-photo-18325786.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940";

const steps = [
  { icon: Hammer, title: "01 · Design", body: "A moodboard is composed with the collector. Dimensions, palette and crystal density are set." },
  { icon: Droplets, title: "02 · Pour", body: "Anti-yellowing epoxy is poured in layered veins. Every current is directed by hand." },
  { icon: Gem, title: "03 · Inlay", body: "Real crushed crystal (5–10mm) is placed grain by grain into the wet resin surface." },
  { icon: ShieldCheck, title: "04 · Frame", body: "A 1-inch hand-brushed golden aluminum border is fitted over 5mm scatter-proof glass." },
];

export const Craftsmanship = () => {
  return (
    <section id="craft" className="relative bg-ink-900 py-24 md:py-40 overflow-hidden">
      <div className="max-w-[1440px] mx-auto px-6 md:px-12 lg:px-16 grid lg:grid-cols-12 gap-12 lg:gap-20">
        <div className="lg:col-span-5">
          <motion.div
            initial={{ opacity: 0, x: -40 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
            className="relative aspect-[4/5] w-full overflow-hidden border border-white/10"
          >
            <img src={CRAFT_IMG} alt="ArtyFex craft" className="w-full h-full object-cover" />
            <div className="absolute inset-0 bg-gradient-to-t from-ink-950/70 to-transparent" />
            <div className="absolute bottom-6 left-6 right-6">
              <div className="text-[10px] uppercase tracking-luxury text-gold-soft">Atelier</div>
              <div className="font-serif text-3xl text-cream mt-1">The 120-hour ritual</div>
            </div>
          </motion.div>
        </div>

        <div className="lg:col-span-7">
          <div className="flex items-center gap-3 mb-6">
            <span className="gold-line w-10" />
            <span className="text-[10px] uppercase tracking-luxury text-gold-soft">Craft & Materials</span>
          </div>
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.9 }}
            className="font-serif text-4xl md:text-5xl lg:text-6xl leading-[0.95] text-cream text-balance"
          >
            No two are alike. <span className="italic font-display text-gold">That is the point.</span>
          </motion.h2>
          <p className="mt-8 text-base md:text-lg text-cream/70 max-w-2xl leading-relaxed font-light">
            Each ArtyFex mirror is poured, inlaid and framed entirely by hand in our Mumbai atelier.
            No moulds. No stamps. No two identical currents of resin. What arrives at your door will
            never exist again.
          </p>

          <div className="mt-14 grid sm:grid-cols-2 gap-x-8 gap-y-10">
            {steps.map((s, i) => (
              <motion.div
                key={s.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.7, delay: i * 0.1 }}
                className="group"
              >
                <div className="inline-flex p-3 border border-gold/20 group-hover:border-gold/60 transition-colors">
                  <s.icon className="w-5 h-5 text-gold" />
                </div>
                <div className="mt-5 font-serif text-2xl text-cream">{s.title}</div>
                <p className="mt-3 text-sm text-cream/60 leading-relaxed font-light max-w-sm">{s.body}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default Craftsmanship;
