import React from "react";
import { Link } from "react-router-dom";
import { Sparkles, ArrowRight } from "lucide-react";

/**
 * Large in-page sale banner controlled by homepage CMS.
 * Rendered between Collection and Reviews (or wherever the Home layout injects it).
 */
export default function SaleBanner({ content }) {
  if (!content || !content.enabled) return null;
  const bg = content.bg_color || "#1a1208";
  const text = content.text_color || "#f5efdf";
  const accent = content.accent_color || "#D4AF37";
  const img = (content.image || "").trim();
  const cta = (content.cta_text || "Discover").trim();
  const link = (content.cta_link || "/shop").trim();

  return (
    <section
      data-testid="sale-banner"
      className="relative overflow-hidden border-y border-white/5"
      style={{ backgroundColor: bg, color: text }}
    >
      {img && (
        <div className="absolute inset-0 opacity-30">
          <img src={img} alt="" className="w-full h-full object-cover" />
          <div className="absolute inset-0" style={{ backgroundColor: bg, opacity: 0.55 }} />
        </div>
      )}
      <div className="relative max-w-[1200px] mx-auto px-6 md:px-12 py-14 md:py-20 flex flex-col md:flex-row items-start md:items-center gap-8">
        <div className="flex-1">
          <div className="flex items-center gap-2 text-[10px] uppercase tracking-luxury" style={{ color: accent }}>
            <Sparkles className="w-3.5 h-3.5" /> Limited edit
          </div>
          <h2 className="mt-3 font-serif text-4xl md:text-6xl leading-tight">{content.title}</h2>
          {content.subtitle && (
            <p className="mt-4 max-w-xl text-sm md:text-base opacity-80 font-light leading-relaxed">
              {content.subtitle}
            </p>
          )}
        </div>
        {link.startsWith("http") ? (
          <a
            href={link}
            data-testid="sale-banner-cta"
            className="inline-flex items-center gap-3 px-6 py-4 text-xs uppercase tracking-luxury border transition-colors"
            style={{ borderColor: accent, color: accent }}
          >
            {cta} <ArrowRight className="w-3.5 h-3.5" />
          </a>
        ) : (
          <Link
            to={link}
            data-testid="sale-banner-cta"
            className="inline-flex items-center gap-3 px-6 py-4 text-xs uppercase tracking-luxury border transition-colors"
            style={{ borderColor: accent, color: accent }}
          >
            {cta} <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        )}
      </div>
    </section>
  );
}
