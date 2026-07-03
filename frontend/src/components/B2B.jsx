import React, { useState } from "react";
import { motion } from "framer-motion";
import { ArrowUpRight, Building2, Sparkles, CheckCircle2 } from "lucide-react";
import { createB2BLead } from "@/lib/api";
import { IDS } from "@/constants/testIds";

const businessTypes = [
  { value: "interior_designer", label: "Interior Designer / Studio" },
  { value: "hotel", label: "Luxury Hotel / Resort" },
  { value: "salon", label: "Premium Salon / Spa" },
  { value: "retailer", label: "Boutique Retailer" },
  { value: "other", label: "Other" },
];

export const B2B = () => {
  const [form, setForm] = useState({
    full_name: "", company: "", email: "", phone: "",
    business_type: "interior_designer", dimensions: "", quantity: "", message: "",
  });
  const [status, setStatus] = useState("idle"); // idle | submitting | success | error
  const [errorMsg, setErrorMsg] = useState("");

  const update = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setStatus("submitting");
    setErrorMsg("");
    try {
      const payload = {
        ...form,
        quantity: form.quantity ? parseInt(form.quantity, 10) : null,
      };
      await createB2BLead(payload);
      setStatus("success");
    } catch (err) {
      setStatus("error");
      setErrorMsg(err?.response?.data?.detail?.[0]?.msg || "Please check your details and try again.");
    }
  };

  return (
    <section id="b2b" data-testid={IDS.b2b.section} className="relative bg-ink-950 py-24 md:py-40 overflow-hidden">
      <div className="absolute -top-20 right-0 w-[600px] h-[600px] rounded-full bg-gold/5 blur-3xl" />
      <div className="max-w-[1440px] mx-auto px-6 md:px-12 lg:px-16 grid lg:grid-cols-12 gap-12 lg:gap-20">
        <div className="lg:col-span-5">
          <div className="flex items-center gap-3 mb-6">
            <span className="gold-line w-10" />
            <span className="text-[10px] uppercase tracking-luxury text-gold-soft">Trade & B2B Atelier</span>
          </div>
          <h2 className="font-serif text-4xl md:text-5xl lg:text-6xl leading-[0.95] text-cream text-balance">
            Bespoke, at <span className="italic font-display text-gold">portfolio</span> scale.
          </h2>
          <p className="mt-8 text-base text-cream/70 font-light leading-relaxed max-w-md">
            We work directly with interior designers, luxury hotels, salons and boutique retailers.
            Custom dimensions, palettes matched to your moodboard, exclusive edition batches — and a
            dedicated atelier contact.
          </p>

          <div className="mt-12 space-y-6">
            {[
              { icon: Building2, k: "Bulk & project pricing", v: "Discreet trade rates from 3+ pieces." },
              { icon: Sparkles, k: "Fully custom dimensions", v: "From petite entry mirrors to gallery walls." },
              { icon: CheckCircle2, k: "White-glove logistics", v: "Insured pan-India dispatch. Global on request." },
            ].map((b) => (
              <div key={b.k} className="flex gap-4">
                <div className="p-2.5 border border-gold/20 h-fit">
                  <b.icon className="w-4 h-4 text-gold" />
                </div>
                <div>
                  <div className="font-serif text-lg text-cream">{b.k}</div>
                  <div className="text-sm text-cream/50 mt-1">{b.v}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="lg:col-span-7">
          {status === "success" ? (
            <motion.div
              data-testid={IDS.b2b.success}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="hairline p-12 text-center"
            >
              <div className="inline-flex p-4 border border-gold/30 mb-6">
                <CheckCircle2 className="w-6 h-6 text-gold" />
              </div>
              <h3 className="font-serif text-3xl text-cream">Your enquiry has landed.</h3>
              <p className="mt-4 text-cream/60 max-w-md mx-auto font-light">
                Our atelier lead will be in touch within one business day with a moodboard, timeline and trade pricing.
              </p>
              <button
                onClick={() => { setStatus("idle"); setForm({ ...form, message: "", dimensions: "", quantity: "" }); }}
                className="mt-8 text-xs uppercase tracking-luxury text-gold border-b border-gold/40 pb-1"
              >
                Submit another
              </button>
            </motion.div>
          ) : (
            <form
              data-testid={IDS.b2b.form}
              onSubmit={submit}
              className="hairline p-8 md:p-10 space-y-6"
            >
              <div className="grid sm:grid-cols-2 gap-6">
                <Field label="Full name">
                  <input required data-testid={IDS.b2b.name} value={form.full_name} onChange={update("full_name")} className={inputCls} />
                </Field>
                <Field label="Company / Studio">
                  <input required data-testid={IDS.b2b.company} value={form.company} onChange={update("company")} className={inputCls} />
                </Field>
                <Field label="Email">
                  <input required type="email" data-testid={IDS.b2b.email} value={form.email} onChange={update("email")} className={inputCls} />
                </Field>
                <Field label="Phone">
                  <input required data-testid={IDS.b2b.phone} value={form.phone} onChange={update("phone")} className={inputCls} />
                </Field>
                <Field label="Business type">
                  <select data-testid={IDS.b2b.type} value={form.business_type} onChange={update("business_type")} className={inputCls}>
                    {businessTypes.map((b) => (
                      <option key={b.value} value={b.value} className="bg-ink-900">{b.label}</option>
                    ))}
                  </select>
                </Field>
                <Field label="Quantity (approx.)">
                  <input type="number" min="1" data-testid={IDS.b2b.quantity} value={form.quantity} onChange={update("quantity")} className={inputCls} placeholder="e.g. 6" />
                </Field>
                <div className="sm:col-span-2">
                  <Field label="Custom dimensions (optional)">
                    <input data-testid={IDS.b2b.dimensions} value={form.dimensions} onChange={update("dimensions")} className={inputCls} placeholder='e.g. 3×5 ft rectangular, champagne palette' />
                  </Field>
                </div>
                <div className="sm:col-span-2">
                  <Field label="Project brief (optional)">
                    <textarea rows={4} data-testid={IDS.b2b.message} value={form.message} onChange={update("message")} className={`${inputCls} resize-none`} placeholder="Tell us about the space, palette, and timeline…" />
                  </Field>
                </div>
              </div>

              {status === "error" && (
                <div className="text-xs text-red-400">{errorMsg}</div>
              )}

              <button
                type="submit"
                disabled={status === "submitting"}
                data-testid={IDS.b2b.submit}
                className="group inline-flex items-center justify-between gap-6 w-full sm:w-auto bg-gold text-ink-950 px-7 py-5 text-xs uppercase tracking-luxury hover:bg-cream transition-colors disabled:opacity-60"
              >
                <span>{status === "submitting" ? "Sending…" : "Request an atelier callback"}</span>
                <ArrowUpRight className="w-4 h-4 group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
              </button>
            </form>
          )}
        </div>
      </div>
    </section>
  );
};

const inputCls =
  "w-full bg-transparent border-b border-white/15 focus:border-gold focus:outline-none py-3 text-sm text-cream placeholder-cream/30 font-light";

const Field = ({ label, children }) => (
  <label className="block">
    <span className="text-[10px] uppercase tracking-luxury text-cream/50">{label}</span>
    <div className="mt-1.5">{children}</div>
  </label>
);

export default B2B;
