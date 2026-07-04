import React, { useState } from "react";
import { motion } from "framer-motion";
import { Mail, Phone, MapPin, Instagram, Facebook, Send, CheckCircle2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import SEO from "@/components/SEO";
import { api } from "@/lib/api";

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "ContactPage",
  "name": "Contact ArtyFex",
  "url": "https://www.artyfex.in/contact",
  "publisher": {
    "@type": "Organization",
    "name": "ArtyFex",
    "url": "https://www.artyfex.in",
    "email": "artyfex@artyfex.in",
    "address": {
      "@type": "PostalAddress",
      "addressLocality": "Mumbai",
      "addressRegion": "Maharashtra",
      "addressCountry": "IN",
    },
    "sameAs": [
      "https://www.instagram.com/artyfex",
      "https://www.facebook.com/artyfex",
    ],
  },
};

export default function ContactPage() {
  const [form, setForm] = useState({ name: "", email: "", subject: "", message: "" });
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.email.trim() || !form.message.trim()) {
      toast.error("Please complete the required fields.");
      return;
    }
    setBusy(true);
    try {
      // Reuse the existing B2B lead endpoint as a general contact channel.
      // Prefix subject with [CONTACT] so admin can distinguish.
      await api.post("/b2b/leads", {
        name: form.name,
        email: form.email,
        company: "",
        phone: "",
        message: `[CONTACT — ${form.subject || "General"}] ${form.message}`,
      });
      setSent(true);
      toast.success("Message received — we'll reply within 24 hours.");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not send. Please email us directly.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-ink-950 text-cream">
      <SEO
        title="Contact ArtyFex — Mumbai Atelier"
        description="Get in touch with ArtyFex for bespoke commissions, B2B trade enquiries, press or general questions. We reply within 24 hours."
        path="/contact"
        jsonLd={jsonLd}
      />
      <Navbar />
      <main className="max-w-[1440px] mx-auto px-6 md:px-12 lg:px-16 pt-32 pb-24">
        <div className="flex items-center gap-3 mb-6">
          <span className="gold-line w-10" />
          <span className="text-[10px] uppercase tracking-luxury text-gold-soft">The Atelier · Mumbai</span>
        </div>
        <h1 className="font-serif text-5xl md:text-6xl lg:text-7xl leading-[0.95] text-balance">
          Let's <span className="italic text-gold">talk</span>.
        </h1>
        <p className="mt-6 text-lg text-cream/70 font-light max-w-xl">
          Bespoke commission, B2B project, press enquiry or a simple hello — we read every message
          and reply personally within 24 hours (Mon–Sat).
        </p>

        <div className="mt-14 grid lg:grid-cols-[420px_1fr] gap-10">
          {/* Contact cards */}
          <aside className="space-y-4">
            <a
              href="mailto:artyfex@artyfex.in"
              className="block hairline p-6 hover:border-gold/40 transition-colors group"
              data-testid="contact-email-card"
            >
              <div className="flex items-center gap-3">
                <div className="p-2.5 border border-gold/30"><Mail className="w-4 h-4 text-gold" /></div>
                <div className="text-[10px] uppercase tracking-luxury text-gold-soft">Email</div>
              </div>
              <div className="mt-4 font-serif text-xl text-cream group-hover:text-gold transition-colors">artyfex@artyfex.in</div>
              <div className="mt-1 text-xs text-cream/50">For all enquiries · Replies within 24h</div>
            </a>
            <a
              href="tel:+919876543210"
              className="block hairline p-6 hover:border-gold/40 transition-colors group"
              data-testid="contact-phone-card"
            >
              <div className="flex items-center gap-3">
                <div className="p-2.5 border border-gold/30"><Phone className="w-4 h-4 text-gold" /></div>
                <div className="text-[10px] uppercase tracking-luxury text-gold-soft">Phone / WhatsApp</div>
              </div>
              <div className="mt-4 font-serif text-xl text-cream group-hover:text-gold transition-colors">+91 98765 43210</div>
              <div className="mt-1 text-xs text-cream/50">Mon–Sat · 10 am – 7 pm IST</div>
            </a>
            <div className="hairline p-6">
              <div className="flex items-center gap-3">
                <div className="p-2.5 border border-gold/30"><MapPin className="w-4 h-4 text-gold" /></div>
                <div className="text-[10px] uppercase tracking-luxury text-gold-soft">Atelier · Studio visits by appointment</div>
              </div>
              <div className="mt-4 font-serif text-lg text-cream leading-tight">
                Andheri West, Mumbai — 400058<br />
                Maharashtra, India
              </div>
            </div>
            <div className="hairline p-6">
              <div className="text-[10px] uppercase tracking-luxury text-gold-soft mb-4">Social</div>
              <div className="flex gap-3">
                <a href="https://instagram.com/artyfex" target="_blank" rel="noreferrer" className="p-3 border border-white/10 hover:border-gold/40 hover:text-gold text-cream" aria-label="Instagram">
                  <Instagram className="w-4 h-4" />
                </a>
                <a href="https://facebook.com/artyfex" target="_blank" rel="noreferrer" className="p-3 border border-white/10 hover:border-gold/40 hover:text-gold text-cream" aria-label="Facebook">
                  <Facebook className="w-4 h-4" />
                </a>
              </div>
            </div>
          </aside>

          {/* Form */}
          <motion.div
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="bg-ink-900 border border-white/10 p-6 md:p-10"
          >
            {sent ? (
              <div className="text-center py-16" data-testid="contact-success">
                <div className="inline-flex p-4 border border-gold/40 mb-6"><CheckCircle2 className="w-8 h-8 text-gold" /></div>
                <div className="font-serif text-3xl">Message received</div>
                <p className="mt-3 text-cream/60">Thank you for reaching out. We'll respond within 24 hours.</p>
                <button
                  onClick={() => { setSent(false); setForm({ name: "", email: "", subject: "", message: "" }); }}
                  className="mt-8 inline-flex text-xs uppercase tracking-luxury text-gold border-b border-gold/40 pb-1"
                >
                  Send another
                </button>
              </div>
            ) : (
              <form onSubmit={submit} data-testid="contact-form" className="grid sm:grid-cols-2 gap-5">
                <label className="block">
                  <span className="text-[10px] uppercase tracking-luxury text-cream/50">Full name *</span>
                  <input required data-testid="contact-name" value={form.name} onChange={upd("name")} className={inp} />
                </label>
                <label className="block">
                  <span className="text-[10px] uppercase tracking-luxury text-cream/50">Email *</span>
                  <input required type="email" data-testid="contact-email" value={form.email} onChange={upd("email")} className={inp} />
                </label>
                <label className="block sm:col-span-2">
                  <span className="text-[10px] uppercase tracking-luxury text-cream/50">Subject</span>
                  <select data-testid="contact-subject" value={form.subject} onChange={upd("subject")} className={inp}>
                    <option value="">Choose a topic (optional)</option>
                    <option>Bespoke commission</option>
                    <option>B2B / trade enquiry</option>
                    <option>Order question</option>
                    <option>Press / feature</option>
                    <option>Studio visit</option>
                    <option>General enquiry</option>
                  </select>
                </label>
                <label className="block sm:col-span-2">
                  <span className="text-[10px] uppercase tracking-luxury text-cream/50">Message *</span>
                  <textarea required rows={6} data-testid="contact-message" value={form.message} onChange={upd("message")} className={`${inp} resize-none`} placeholder="Tell us about the space, the vibe, or your question." />
                </label>
                <div className="sm:col-span-2 flex items-center justify-between gap-4 mt-2">
                  <p className="text-xs text-cream/40">We reply within 24 hours (Mon–Sat).</p>
                  <button
                    type="submit"
                    disabled={busy}
                    data-testid="contact-submit"
                    className="inline-flex items-center gap-2 bg-gold text-ink-950 px-6 py-4 text-xs uppercase tracking-luxury hover:bg-cream disabled:opacity-60"
                  >
                    {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : (<><Send className="w-3.5 h-3.5" /> Send message</>)}
                  </button>
                </div>
              </form>
            )}
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

const inp =
  "mt-1.5 w-full bg-ink-950 border border-white/15 focus:border-gold outline-none px-3 py-3 text-sm text-cream placeholder-cream/30";
