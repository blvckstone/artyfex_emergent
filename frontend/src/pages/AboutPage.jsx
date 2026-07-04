import React from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { ArrowUpRight, Sparkles, Palette, Award, Clock } from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import SEO from "@/components/SEO";

const HERO_IMG =
  "https://images.pexels.com/photos/8068653/pexels-photo-8068653.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=750&w=1260";

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "AboutPage",
  "name": "About ArtyFex",
  "description":
    "ArtyFex is a Mumbai atelier of 100% handmade resin art — statement mirrors, watches, tables and bespoke furniture. Founded by Maloni Mahada, each piece is hand-poured for luxury interiors.",
  "url": "https://www.artyfex.in/about",
  "publisher": {
    "@type": "Organization",
    "name": "ArtyFex",
    "url": "https://www.artyfex.in",
    "logo": "https://www.artyfex.in/brand/logo.svg",
    "founder": { "@type": "Person", "name": "Maloni Mahada" },
    "sameAs": ["https://www.instagram.com/artyfex", "https://www.facebook.com/artyfex"],
  },
};

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-ink-950 text-cream">
      <SEO
        title="About ArtyFex — Mumbai Atelier of Handmade Resin Art"
        description="ArtyFex is a Mumbai-based atelier crafting 100% handmade resin art — mirrors, watches, tables and bespoke furniture. Discover the craft, the founder, and the ethos behind every one-of-one piece."
        path="/about"
        jsonLd={jsonLd}
      />
      <Navbar />
      <main>
        {/* Hero */}
        <section className="relative pt-32 pb-16 md:pt-40 md:pb-24 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-b from-ink-950 via-ink-950/95 to-ink-950/80" />
          <div className="max-w-[1440px] mx-auto px-6 md:px-12 lg:px-16 grid lg:grid-cols-2 gap-12 items-center relative">
            <motion.div
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
            >
              <div className="flex items-center gap-3 mb-6">
                <span className="gold-line w-10" />
                <span className="text-[10px] uppercase tracking-luxury text-gold-soft">The Atelier</span>
              </div>
              <h1 className="font-serif text-5xl md:text-6xl lg:text-7xl leading-[0.95] text-balance">
                Handmade, in <span className="italic text-gold">Mumbai</span>.
              </h1>
              <p className="mt-6 text-lg md:text-xl text-cream/70 leading-relaxed font-light max-w-lg">
                ArtyFex is a small atelier of two — a founder and her senior artisan — pouring
                statement resin art by hand: mirrors, watches, tables, and bespoke furniture.
                Every piece is inspected by us before it leaves.
              </p>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, scale: 1.05 }} animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
              className="relative aspect-[4/5] overflow-hidden border border-white/10"
            >
              <img src={HERO_IMG} alt="ArtyFex atelier — a hand-poured resin mirror in the studio" className="w-full h-full object-cover" />
              <div className="absolute bottom-4 left-4 glass-gold px-3 py-1.5 text-[10px] uppercase tracking-luxury text-gold">Since 2023</div>
            </motion.div>
          </div>
        </section>

        {/* Story */}
        <section className="py-16 md:py-24 border-t border-white/5">
          <div className="max-w-3xl mx-auto px-6 md:px-12 space-y-8 text-cream/80 leading-relaxed font-light text-lg">
            <h2 className="font-serif text-4xl md:text-5xl text-cream text-center mb-10">Our story</h2>
            <p>
              ArtyFex began at a single kitchen table in Malad West, Mumbai — a founder obsessed with the way
              light moves through crushed crystal and translucent epoxy. What began as a hobby quickly
              became a craft: three years of prototyping, forty-eight failed pours, and thousands of hours
              learning how resin breathes as it cures.
            </p>
            <p>
              Today ArtyFex serves collectors, designers and boutique hotels who want a piece that is
              <em className="text-cream">&nbsp;theirs alone</em>. We work primarily in resin — statement
              mirrors, timepieces (watches), dining and coffee tables, and one-off furniture. No two
              pieces are ever identical. We refuse mass production. We are, and will remain, an atelier — not a factory.
            </p>
            <p>
              Every commission — from a 24" round mirror for a Bandra penthouse to a resin dining table
              for a Golf Links foyer — is poured by the founder herself, with our senior artisan of six years.
            </p>
          </div>
        </section>

        {/* Pillars */}
        <section className="py-16 md:py-24 border-t border-white/5 bg-ink-900">
          <div className="max-w-[1440px] mx-auto px-6 md:px-12 lg:px-16">
            <div className="text-center mb-12">
              <div className="text-[10px] uppercase tracking-luxury text-gold-soft">What sets us apart</div>
              <h2 className="mt-3 font-serif text-4xl md:text-5xl">The ArtyFex ethos</h2>
            </div>
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                { icon: Palette, title: "100% Handmade", body: "Every pour, every cure, every polish — done in-atelier. No outsourcing, ever." },
                { icon: Sparkles, title: "Crystal Sourcing", body: "5–10 mm crystals sourced ethically from Rajasthan and Gujarat mines." },
                { icon: Award, title: "24-Month Warranty", body: "Structural warranty on every piece. Because heirlooms should last generations." },
                { icon: Clock, title: "48–120 Hours Each", body: "A single statement piece — mirror, table or watch — takes 100+ artisan hours to complete. There is no shortcut." },
              ].map((p) => (
                <div key={p.title} className="p-8 border border-white/5 bg-ink-950">
                  <p.icon className="w-6 h-6 text-gold" />
                  <div className="mt-6 font-serif text-2xl">{p.title}</div>
                  <p className="mt-3 text-sm text-cream/60 leading-relaxed">{p.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-16 md:py-24 border-t border-white/5">
          <div className="max-w-3xl mx-auto px-6 text-center">
            <h2 className="font-serif text-4xl md:text-5xl">Come see the atelier</h2>
            <p className="mt-4 text-cream/60 font-light">
              Studio visits by appointment. B2B & bespoke commissions welcome.
            </p>
            <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/shop" className="inline-flex items-center gap-2 bg-gold text-ink-950 px-6 py-4 text-xs uppercase tracking-luxury hover:bg-cream">
                Explore the collection <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
              <Link to="/contact" className="inline-flex items-center gap-2 border border-gold/40 text-gold px-6 py-4 text-xs uppercase tracking-luxury hover:bg-gold hover:text-ink-950">
                Contact the atelier
              </Link>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
