import React from "react";
import { useParams, useLocation, Navigate } from "react-router-dom";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import SEO from "@/components/SEO";

const SEO_META = {
  privacy: {
    title: "Privacy Policy | ArtyFex — Handmade Resin & Crystal Mirrors",
    description: "How ArtyFex collects, uses and protects your personal data. GDPR-friendly, PCI-DSS compliant checkout via Razorpay. Read our full privacy policy.",
  },
  terms: {
    title: "Terms & Conditions | ArtyFex",
    description: "Terms of purchase, warranty, care and intellectual-property rights for ArtyFex handmade mirrors. Governed by Indian law.",
  },
  refund: {
    title: "Returns & Refunds Policy | ArtyFex",
    description: "3-day return window, insured white-glove transit, and how to raise a return request for your handmade ArtyFex mirror.",
  },
  shipping: {
    title: "Shipping Policy | ArtyFex",
    description: "Pan-India insured white-glove shipping, made-to-order timelines and complimentary delivery on orders above ₹25,000.",
  },
};

const CONTENT = {
  privacy: {
    title: "Privacy Policy",
    sections: [
      ["Data we collect", "When you place an order or create an account, we collect your name, contact details, delivery address and order history. If you raise a return, any evidence links (e.g. Google Drive/Imgur URLs) you provide are stored alongside your return request. Payment card data is never stored on our servers — it is processed directly by Razorpay under PCI-DSS Level 1 compliance."],
      ["How we use it", "We use your information to fulfil orders, communicate delivery updates, evaluate return requests, respond to B2B enquiries, and personalise your experience. We do not sell your data to third parties, ever."],
      ["Cookies", "We use minimal, first-party cookies to keep your session logged in and remember your cart. Analytics cookies (privacy-preserving) may be used to understand aggregate site performance."],
      ["Your rights", "You may request access to, correction of, or deletion of your personal data at any time by writing to artyfex@artyfex.in. We will respond within 30 days."],
      ["Retention", "Order records — including any return requests, admin notes and damage-evidence links — are retained for 7 years for tax, warranty and dispute-resolution purposes. Account data is deleted within 30 days of an account deletion request, except where retention is legally required."],
      ["Returns handling", "Return requests are governed by our Returns & Refunds policy: a strict 3-day window from the delivery timestamp applies, and the piece must be returned in its original packaging. Any personal data submitted with a return request (evidence image link, damage description, packaging confirmation) is used only to evaluate that specific claim and is not shared with third parties beyond our courier partners when necessary."],
      ["Security", "All connections are encrypted over TLS 1.3. Passwords are stored using bcrypt. Access to production data is restricted to authorised personnel."],
    ],
  },
  terms: {
    title: "Terms & Conditions",
    sections: [
      ["Nature of goods", "Every ArtyFex mirror is 100% handmade. Subtle variations in resin flow, crystal placement and colour are inherent characteristics of hand-poured artwork and are not defects."],
      ["Order acceptance", "Orders are confirmed only after successful payment verification with Razorpay. We reserve the right to cancel and refund any order that we cannot fulfil within a reasonable time."],
      ["Craftsmanship", "Statement pieces (2×3 ft and above) require 100–120 hours of artisan labour. Standard dispatch is 5 business days for in-stock pieces and 4–6 weeks for made-to-order commissions."],
      ["Warranty", "Every ArtyFex mirror includes a 24-month warranty against structural defects (border detachment, delamination, frame issues) under normal indoor use. Warranty excludes accidental damage."],
      ["Care", "Wipe only with a soft, dry cloth. Avoid direct sunlight, alcohol-based cleaners and abrasive materials."],
      ["Intellectual property", "All designs, imagery and content on this site are © ArtyFex. Reproduction without permission is prohibited."],
      ["Governing law", "These terms are governed by the laws of India. Disputes fall under the exclusive jurisdiction of the courts of Mumbai, Maharashtra."],
    ],
  },
  refund: {
    title: "Returns & Refunds",
    sections: [
      ["3-day return window", "Return requests must be raised within 3 days of delivery (72 hours from the timestamp your parcel is marked delivered). Requests submitted after this window will be automatically declined and are not eligible for refund. This strict window allows us to investigate transit damage while the courier's insurance is still valid."],
      ["Eligibility", "Returns are considered only for pieces that arrive damaged in transit or are manifestly not as described. Made-to-order, bespoke commissions and B2B batch orders are non-returnable once poured. Change-of-mind returns are at our sole discretion and, if approved, will incur a restocking fee."],
      ["Original packaging is mandatory", "The piece must be returned in its original box, foam inserts and outer wrap, exactly as received. Improper repacking that causes damage — chipped resin, cracked mirror, bent border, torn foam — will be assessed by our atelier during inspection. Repair and restocking fees will be deducted from your refund at our sole discretion, and in cases of severe damage the return may be rejected entirely."],
      ["How to request", "Sign in to your account → Orders → Request return (visible only within the 3-day window). You must confirm the packaging condition, upload a shareable image link (Google Drive / Imgur / Dropbox) showing the damage, and describe the issue. Our atelier will approve or reject the request and mark it as genuine or non-genuine after review."],
      ["Assessment & refunds", "Approved genuine claims are refunded in full to the original payment method within 7–10 business days after we receive and inspect the returned piece. Non-genuine or partially damaged returns will be refunded net of restocking and repair fees. Rejection decisions are communicated with a written note on your Returns tab."],
      ["Non-returnable items", "Custom commissions, bespoke dimensions and B2B batch orders are non-returnable once poured."],
    ],
  },
  shipping: {
    title: "Shipping Policy",
    sections: [
      ["Standard dispatch", "In-stock pieces are dispatched within 5 business days from our Mumbai atelier via insured white-glove courier."],
      ["Made-to-order", "Custom and B2B orders take 4–6 weeks depending on dimensions and finish. You'll receive weekly progress updates and moodboard proofs."],
      ["Coverage", "We ship pan-India. International shipping is available on request — please email artyfex@artyfex.in for a quote."],
      ["Charges", "Complimentary shipping on orders ₹25,000 and above. Below that, a flat ₹1,499 handling fee applies."],
      ["Insurance", "Every piece is fully insured in transit. In the unlikely event of transit damage, please raise a return request within the 3-day window with photo evidence — we replace or refund at no additional cost."],
    ],
  },
};

// Map legacy short-link slugs → new CMS slugs (Phase B5).
// Any /policies/:slug that matches one of these keys is 301-redirected to /p/<new-slug>,
// so the admin CMS is the single source of truth for legal content.
const CMS_SLUG_ALIASES = {
  privacy: "privacy-policy",
  terms: "terms-and-conditions",
  refund: "refund-and-return-policy",
  shipping: "shipping-policy",
  cookie: "cookie-policy",
  cookies: "cookie-policy",
};

export default function LegalPage() {
  const { slug: routeSlug } = useParams();
  const { pathname } = useLocation();
  // Support short-link routes /terms and /privacy in addition to /policies/:slug
  const inferredSlug = pathname === "/terms" ? "terms" : pathname === "/privacy" ? "privacy" : routeSlug;
  const slug = inferredSlug || "privacy";
  const aliased = CMS_SLUG_ALIASES[slug];
  if (aliased) {
    // Send the browser to the CMS-backed dynamic page so the admin can edit it
    return <Navigate to={`/p/${aliased}`} replace />;
  }
  const doc = CONTENT[slug] || CONTENT.privacy;
  const seo = SEO_META[slug] || SEO_META.privacy;
  return (
    <div className="min-h-screen bg-ink-950 text-cream">
      <SEO
        title={seo.title}
        description={seo.description}
        path={`/policies/${slug}`}
        type="article"
        jsonLd={{
          "@context": "https://schema.org",
          "@type": "WebPage",
          "name": doc.title,
          "description": seo.description,
          "url": `https://www.artyfex.in/policies/${slug}`,
          "publisher": { "@type": "Organization", "name": "ArtyFex", "url": "https://www.artyfex.in" },
        }}
      />
      <Navbar />
      <div className="max-w-3xl mx-auto px-6 md:px-12 pt-32 pb-24">
        <div className="text-[10px] uppercase tracking-luxury text-gold-soft">ArtyFex Atelier</div>
        <h1 className="font-serif text-5xl md:text-6xl mt-3">{doc.title}</h1>
        <div className="mt-4 text-xs text-cream/40">Last updated · February 2026</div>
        <div className="mt-12 space-y-10">
          {doc.sections.map(([h, b], i) => (
            <section key={i}>
              <h2 className="font-serif text-2xl text-gold">{h}</h2>
              <p className="mt-3 text-cream/70 leading-relaxed font-light">{b}</p>
            </section>
          ))}
        </div>
        <div className="mt-16 text-sm text-cream/50">
          Questions? Write to <a href="mailto:artyfex@artyfex.in" className="text-gold hover:text-cream">artyfex@artyfex.in</a>.
        </div>
      </div>
      <Footer />
    </div>
  );
}
