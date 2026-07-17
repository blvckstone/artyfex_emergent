import React, { useEffect, useRef, useState } from "react";
import { motion, useInView } from "framer-motion";
import { Sparkles, ShieldCheck, Award, Truck } from "lucide-react";

const ICON_MAP = { sparkles: Sparkles, award: Award, shield: ShieldCheck, truck: Truck };

const DEFAULT_STATS = [
  { icon: "sparkles", value: 120, suffix: "+", label: "Artisan hours per piece", note: "Every mirror, hand-poured" },
  { icon: "award", value: 1, suffix: " / 1", label: "One-of-one editions", note: "No two pieces alike" },
  { icon: "shield", value: 24, suffix: " mo", label: "Signature warranty", note: "Anti-yellowing epoxy" },
  { icon: "truck", value: 500, suffix: "+", label: "Delivered pan-India", note: "Insured white-glove" },
];

function Counter({ target, suffix }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, amount: 0.5 });
  const [n, setN] = useState(0);
  useEffect(() => {
    if (!inView) return;
    let raf; const start = performance.now(); const dur = 1400;
    const tick = (t) => {
      const p = Math.min(1, (t - start) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      setN(Math.round(target * eased));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [inView, target]);
  return <span ref={ref}>{n}{suffix}</span>;
}

export default function WhyArtyFex({ content }) {
  const c = content || {};
  const stats = (Array.isArray(c.stats) && c.stats.length ? c.stats : DEFAULT_STATS).slice(0, 4);
  const eyebrow = c.eyebrow || "Why ArtyFex";
  const line1 = c.headline_line_1 || "The Mumbai atelier";
  const italic = c.headline_italic || "obsessed";
  const line2 = c.headline_line_2 || " with detail.";
  const subtitle = c.subtitle || "Modern art collectors, luxury interior designers and celebrities trust ArtyFex for one reason — each piece is a story of 120+ artisan hours, poured by hand, signed by the maker.";
  return (
    <section id="why-artyfex" data-testid="home-why-artyfex" className="relative bg-ink-950 py-12 md:py-24 border-t border-white/5 overflow-hidden">
      <div className="absolute inset-0 pointer-events-none opacity-30">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-gold/10 blur-3xl rounded-full" />
        <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-gold/5 blur-3xl rounded-full" />
      </div>
      <div className="relative max-w-[1440px] mx-auto px-4 md:px-12 lg:px-16">
        <div className="text-center mb-8 md:mb-14 max-w-2xl mx-auto">
          <div className="flex items-center gap-3 justify-center mb-3 md:mb-4">
            <span className="gold-line w-8 md:w-10" />
            <span className="text-[10px] uppercase tracking-luxury text-gold-soft">{eyebrow}</span>
            <span className="gold-line w-8 md:w-10" />
          </div>
          <h2 className="font-serif text-2xl sm:text-3xl md:text-5xl leading-[1] text-cream text-balance">
            {line1} <span className="italic font-display text-gold">{italic}</span>{line2}
          </h2>
          <p className="mt-4 md:mt-5 text-cream/60 text-xs md:text-base font-light">
            {subtitle}
          </p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 md:gap-6">
          {stats.map((s, i) => {
            const Icon = ICON_MAP[s.icon] || Sparkles;
            return (
              <motion.div
                key={`${s.label}-${i}`}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={{ duration: 0.6, delay: Math.min(i, 3) * 0.06 }}
                className="group relative bg-ink-900/60 backdrop-blur border border-white/10 hover:border-gold/40 p-4 md:p-8 rounded-xl md:rounded-none transition-colors"
                data-testid={`home-why-stat-${i}`}
              >
                <div className="inline-flex items-center justify-center w-9 h-9 md:w-11 md:h-11 rounded-full bg-gold/10 border border-gold/30 text-gold mb-3 md:mb-5 group-hover:bg-gold group-hover:text-ink-950 transition-all">
                  <Icon className="w-4 h-4 md:w-5 md:h-5" />
                </div>
                <div className="font-serif text-2xl md:text-5xl text-cream leading-none">
                  <Counter target={s.value} suffix={s.suffix} />
                </div>
                <div className="mt-2 md:mt-3 text-[9px] md:text-xs uppercase tracking-luxury text-gold-soft">{s.label}</div>
                <div className="mt-1 md:mt-1.5 text-[11px] md:text-sm text-cream/50 font-light hidden md:block">{s.note}</div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
