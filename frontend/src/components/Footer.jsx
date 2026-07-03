import React from "react";
import { Link } from "react-router-dom";
import { Instagram, Facebook } from "lucide-react";

export const Footer = () => {
  return (
    <footer className="relative bg-black text-cream border-t border-white/5">
      <div className="max-w-[1440px] mx-auto px-6 md:px-12 lg:px-16 pt-24 pb-10">
        <div className="grid lg:grid-cols-12 gap-16">
          <div className="lg:col-span-6">
            <h3 className="font-serif text-5xl md:text-6xl lg:text-7xl leading-[0.9] text-cream">
              Poured <span className="italic font-display text-gold">by hand</span>
              <br />in Mumbai.
            </h3>
            <p className="mt-8 max-w-md text-cream/50 font-light leading-relaxed">
              ArtyFex is a Mumbai-based atelier of handmade resin art & crystal stone mirrors.
              Trademark № 6432 · Class 20. Serving collectors, designers & luxury properties across India.
            </p>
            <div className="mt-8 flex gap-4">
              {[
                { Icon: Instagram, href: "https://instagram.com/artyfex" },
                { Icon: Facebook, href: "https://facebook.com/artyfex" },
                { Icon: PinterestIcon, href: "https://pinterest.com/artyfex" },
              ].map(({ Icon, href }, i) => (
                <a key={i} href={href} target="_blank" rel="noreferrer" className="p-3 border border-white/10 hover:border-gold hover:text-gold transition-colors">
                  <Icon className="w-4 h-4" />
                </a>
              ))}
            </div>
          </div>

          <FooterCol title="Atelier">
            <a href="#craft">The Craft</a>
            <a href="#collection">The Collection</a>
            <a href="#reviews">Collectors</a>
            <a href="#b2b">Trade / B2B</a>
          </FooterCol>

          <FooterCol title="Support">
            <a href="#">Order Tracking</a>
            <a href="#">Care Guide</a>
            <a href="#">Shipping & Returns</a>
            <a href="#">Contact Atelier</a>
          </FooterCol>

          <FooterCol title="Legal">
            <Link to="/policies/privacy">Privacy Policy</Link>
            <Link to="/policies/terms">Terms &amp; Conditions</Link>
            <Link to="/policies/refund">Returns &amp; Refunds</Link>
            <Link to="/policies/shipping">Shipping Policy</Link>
          </FooterCol>

          <FooterCol title="Contact">
            <span className="text-cream/70">Maloni Mahada</span>
            <span className="text-cream/50">Mumbai 400095</span>
            <a href="mailto:artyfex@artyfex.in" className="text-cream/70 hover:text-gold">artyfex@artyfex.in</a>
            <a href="tel:+919819973850" className="text-cream/70 hover:text-gold">+91 98199 73850</a>
          </FooterCol>
        </div>

        <div className="mt-16 pt-6 border-t border-white/5 text-xs text-cream/40 font-light leading-relaxed max-w-3xl">
          <span className="uppercase tracking-luxury text-gold-soft">Important note · </span>
          No inbuilt LED lighting is included with any ArtyFex mirror. Ambient light shown in
          product and lifestyle imagery is for styling visualisation only. Every piece is 100% handmade
          and one of one — subtle organic variations in resin currents and crystal placement are the
          signature of the atelier.
        </div>

        <div className="mt-10 pt-6 border-t border-white/5 flex flex-col md:flex-row justify-between gap-6">
          <div className="font-serif text-[10vw] lg:text-[8vw] leading-none text-cream/5 select-none pointer-events-none">
            ArtyFex
          </div>
        </div>
        <div className="flex flex-col md:flex-row justify-between gap-4 text-[10px] uppercase tracking-luxury text-cream/40">
          <span>© {new Date().getFullYear()} ArtyFex · All rights reserved</span>
          <div className="flex gap-6">
            <Link to="/policies/terms">Terms</Link>
            <Link to="/policies/privacy">Privacy</Link>
            <Link to="/policies/refund">Refunds</Link>
          </div>
        </div>
      </div>
    </footer>
  );
};

const FooterCol = ({ title, children }) => (
  <div className="lg:col-span-2">
    <div className="text-[10px] uppercase tracking-luxury text-gold-soft mb-6">{title}</div>
    <div className="flex flex-col gap-3 text-sm">
      {React.Children.map(children, (c) =>
        React.cloneElement(c, {
          className: `${c.props.className || ""} text-cream/60 hover:text-gold transition-colors`,
        }),
      )}
    </div>
  </div>
);

const PinterestIcon = (props) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" {...props}>
    <path d="M12 2a10 10 0 00-3.65 19.32c-.09-.78-.17-1.98.04-2.83.19-.77 1.2-4.92 1.2-4.92s-.31-.62-.31-1.53c0-1.44.83-2.51 1.87-2.51.88 0 1.31.66 1.31 1.45 0 .88-.56 2.2-.85 3.42-.24 1.03.51 1.86 1.52 1.86 1.83 0 3.23-1.93 3.23-4.71 0-2.46-1.77-4.18-4.3-4.18-2.93 0-4.65 2.2-4.65 4.47 0 .89.34 1.83.77 2.35.08.1.09.19.07.29-.08.31-.24.98-.28 1.12-.04.18-.14.22-.34.13-1.25-.58-2.03-2.4-2.03-3.86 0-3.14 2.29-6.03 6.6-6.03 3.47 0 6.17 2.47 6.17 5.78 0 3.45-2.18 6.24-5.2 6.24-1.02 0-1.98-.53-2.31-1.16l-.63 2.4c-.23.87-.85 1.96-1.26 2.62A10 10 0 1012 2z" />
  </svg>
);

export default Footer;
