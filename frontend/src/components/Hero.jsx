import React from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import { ArrowDownRight, Sparkles } from "lucide-react";
import { IDS } from "@/constants/testIds";

const DEFAULT_HERO_BG =
  "https://images.unsplash.com/photo-1688646953306-5ec93eab8c06?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxOTJ8MHwxfHNlYXJjaHwzfHxsdXh1cnklMjBwZW50aG91c2UlMjBsaXZpbmclMjByb29tfGVufDB8fHx8MTc4MzA2MjM3M3ww&ixlib=rb-4.1.0&q=85";

const DEFAULT_MIRROR_IMG =
  "https://images.pexels.com/photos/8068653/pexels-photo-8068653.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940";

const fade = {
  hidden: { opacity: 0, y: 30 },
  show: (i = 0) => ({
    opacity: 1, y: 0,
    transition: { duration: 0.9, delay: i * 0.15, ease: [0.22, 1, 0.36, 1] },
  }),
};

const DEFAULT_STATS = [
  { k: "120", v: "artisan hours" },
  { k: "1 of 1", v: "unique piece" },
  { k: "24 mo", v: "warranty" },
];

export const Hero = ({ content }) => {
  const c = content || {};
  const bg = c.background_image || DEFAULT_HERO_BG;
  const mirror = c.mirror_image || DEFAULT_MIRROR_IMG;
  const accent = c.accent_color || "#D4AF37";
  const textColor = c.text_color || "#f5efdf";
  const stats = (c.stats && c.stats.length ? c.stats : DEFAULT_STATS).slice(0, 3);
  const { scrollY } = useScroll();
  const bgY = useTransform(scrollY, [0, 800], [0, 180]);
  const mirrorY = useTransform(scrollY, [0, 800], [0, -80]);
  const bgScale = useTransform(scrollY, [0, 800], [1.05, 1.15]);
  const copyY = useTransform(scrollY, [0, 800], [0, -40]);

  return (
    <section
      id="top"
      data-testid={IDS.hero.section}
      className="relative min-h-[100svh] w-full overflow-hidden bg-ink-950"
    >
      {/* Background image (parallax) */}
      <motion.div className="absolute inset-0" style={{ y: bgY, scale: bgScale }}>
        <img src={bg} alt="" className="w-full h-full object-cover opacity-40" />
        <div className="absolute inset-0 bg-gradient-to-b from-ink-950/70 via-ink-950/50 to-ink-950" />
        <div className="absolute inset-0 grain" />
      </motion.div>

      <div className="relative max-w-[1440px] mx-auto px-6 md:px-12 lg:px-16 pt-40 md:pt-44 pb-24">
        <div className="grid lg:grid-cols-12 gap-10 lg:gap-16 items-center">
          {/* Copy */}
          <motion.div className="lg:col-span-7 relative z-10 min-w-0" style={{ y: copyY }}>
            <motion.div
              variants={fade}
              initial="hidden"
              animate="show"
              custom={0}
              className="flex items-center gap-3 mb-8"
            >
              <span className="gold-line w-16" />
              <span className="text-[10px] md:text-xs uppercase tracking-luxury" style={{ color: accent }}>
                {c.eyebrow || "ArtyFex Atelier · Est. 2020 · Mumbai"}
              </span>
            </motion.div>

            <motion.h1
              variants={fade}
              initial="hidden"
              animate="show"
              custom={1}
              data-testid={IDS.hero.title}
              className="font-serif text-[11vw] sm:text-[8vw] md:text-6xl lg:text-7xl xl:text-[5.5rem] 2xl:text-[6.5rem] leading-[0.94] tracking-tight text-balance break-words"
              style={{ color: textColor }}
            >
              {c.headline_line_1 || "A mirror,"}{" "}
              <span className="italic font-display" style={{ color: accent }}>
                {c.headline_italic || "poured"}
              </span>
              <br />
              {c.headline_line_2 || "over one hundred"}
              <br />
              {c.headline_line_3 || "and twenty hours."}
            </motion.h1>

            <motion.p
              variants={fade}
              initial="hidden"
              animate="show"
              custom={2}
              className="mt-10 max-w-xl text-base md:text-lg text-cream/70 leading-relaxed font-light"
            >
              {c.subheadline || "The Obsidian Aurora — a 2×3 ft statement mirror of black marbled resin, real crushed blue crystal, and a hand-brushed golden aluminum border. Signed by the artisan. One of one."}
            </motion.p>

            <motion.div
              variants={fade}
              initial="hidden"
              animate="show"
              custom={3}
              className="mt-12 flex flex-col sm:flex-row gap-4"
            >
              <a
                href={c.primary_cta_link || "#product"}
                data-testid={IDS.hero.shopNow}
                className="group inline-flex items-center justify-between gap-6 bg-gold text-ink-950 px-7 py-5 text-xs uppercase tracking-luxury hover:bg-cream transition-colors duration-500"
              >
                <span>{c.primary_cta_text || "Acquire the piece"}</span>
                <ArrowDownRight className="w-4 h-4 group-hover:translate-x-1 group-hover:translate-y-1 transition-transform" />
              </a>
              {c.secondary_cta_text && (
                <a
                  href={c.secondary_cta_link || "#craft"}
                  data-testid={IDS.hero.exploreCraft}
                  className="group inline-flex items-center gap-3 px-7 py-5 text-xs uppercase tracking-luxury text-cream border border-white/15 hover:border-gold hover:text-gold transition-all"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  {c.secondary_cta_text}
                </a>
              )}
            </motion.div>

            <motion.div
              variants={fade}
              initial="hidden"
              animate="show"
              custom={4}
              className="mt-16 grid grid-cols-3 gap-6 max-w-lg"
            >
              {stats.map((s, i) => (
                <div key={`${s.v}-${i}`}>
                  <div className="font-serif text-3xl md:text-4xl text-cream">{s.k}</div>
                  <div className="mt-1 text-[10px] uppercase tracking-luxury text-cream/50">{s.v}</div>
                </div>
              ))}
            </motion.div>
          </motion.div>

          {/* Mirror image */}
          <motion.div className="lg:col-span-5 relative" style={{ y: mirrorY }}>
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 40 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1], delay: 0.2 }}
              className="relative aspect-[3/4] w-full max-w-md mx-auto"
            >
              <div className="absolute -inset-6 bg-gold/10 blur-3xl rounded-full" />
              <div className="relative w-full h-full overflow-hidden border border-gold/30">
                <img src={mirror} alt="Hero mirror" className="w-full h-full object-cover animate-float" />
                <div className="absolute inset-0 ring-1 ring-inset ring-gold/20" />
              </div>
              {c.edition_text && (
                <div className="absolute -bottom-6 -left-6 glass px-5 py-4 hidden md:block">
                  <div className="text-[10px] uppercase tracking-luxury" style={{ color: accent }}>{c.edition_label || "Edition"}</div>
                  <div className="font-serif text-xl text-cream">{c.edition_text}</div>
                </div>
              )}
            </motion.div>
          </motion.div>
        </div>
      </div>

      {/* Marquee */}
      <div className="relative border-y border-white/5 py-6 overflow-hidden">
        <div className="marquee font-serif text-2xl md:text-3xl text-cream/40 italic">
          {Array.from({ length: 2 }).map((_, j) => (
            <div key={j} className="flex gap-16 shrink-0">
              {["Handpoured in Mumbai", "· Anti-yellowing epoxy ·", "5mm scatter-proof glass", "· 1-inch golden aluminum border ·", "Real crushed crystal", "· 100% original ·"].map(
                (t, i) => (
                  <span key={`${j}-${i}`}>{t}</span>
                ),
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Hero;
