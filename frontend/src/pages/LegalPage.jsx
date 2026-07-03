import React from "react";
import { useParams } from "react-router-dom";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

const CONTENT = {
  privacy: {
    title: "Privacy Policy",
    sections: [
      ["Data we collect", "When you place an order or create an account, we collect your name, contact details, delivery address and order history. Payment card data is never stored on our servers — it is processed directly by Razorpay under PCI-DSS Level 1 compliance."],
      ["How we use it", "We use your information to fulfil orders, communicate delivery updates, respond to B2B enquiries, and personalise your experience. We do not sell your data to third parties, ever."],
      ["Cookies", "We use minimal, first-party cookies to keep your session logged in and remember your cart. Analytics cookies (privacy-preserving) may be used to understand aggregate site performance."],
      ["Your rights", "You may request access to, correction of, or deletion of your personal data at any time by writing to artyfex@artyfex.in. We will respond within 30 days."],
      ["Retention", "Order records are retained for 7 years for tax and warranty purposes. Account data is deleted within 30 days of account deletion request."],
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
      ["Eligibility", "Returns are accepted within 7 days of delivery for pieces damaged in transit or manifestly not as described. Made-to-order and custom commissions are non-returnable."],
      ["Process", "Sign in to your account → Orders → Request return. Our atelier will respond within 24 hours with a reverse-pickup slot."],
      ["Refunds", "Approved refunds are credited to the original payment method within 7–10 business days after we receive and inspect the returned piece."],
      ["Damaged in transit", "Please email photos of the packaging and damaged product to artyfex@artyfex.in within 48 hours of delivery for expedited replacement."],
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
      ["Insurance", "Every piece is fully insured in transit. In the unlikely event of transit damage, we replace at no additional cost."],
    ],
  },
};

export default function LegalPage() {
  const { slug } = useParams();
  const doc = CONTENT[slug] || CONTENT.privacy;
  return (
    <div className="min-h-screen bg-ink-950 text-cream">
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
