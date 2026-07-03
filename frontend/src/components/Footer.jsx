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
                { Icon: Instagram, href: "https://www.instagram.com/artyfex.in", label: "Instagram" },
                { Icon: PinterestIcon, href: "https://in.pinterest.com/artyfexin/", label: "Pinterest" },
                { Icon: AmazonIcon, href: "https://www.amazon.in/s?k=ArtyFex&ref=bl_dp_s_web_0", label: "Amazon" },
              ].map(({ Icon, href, label }, i) => (
                <a key={i} href={href} target="_blank" rel="noreferrer" aria-label={label} className="p-3 border border-white/10 hover:border-gold hover:text-gold transition-colors">
                  <Icon className="w-4 h-4" />
                </a>
              ))}
              <a href="https://wa.me/919970107760?text=Hi%20ArtyFex%20—%20I%27m%20interested%20in%20your%20mirrors" target="_blank" rel="noreferrer" aria-label="WhatsApp" className="p-3 border border-gold/40 text-gold hover:bg-gold hover:text-ink-950 transition-colors">
                <WhatsAppIcon className="w-4 h-4" />
              </a>
            </div>
          </div>

          <FooterCol title="Atelier">
            <a href="/#craft">The Craft</a>
            <Link to="/shop">The Collection</Link>
            <a href="/#reviews">Collectors</a>
            <a href="/#b2b">Trade / B2B</a>
            <Link to="/admin">Admin Panel</Link>
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
const AmazonIcon = (props) => (
  <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
    <path d="M15.93 15.61c-2.16 1.6-5.29 2.45-7.99 2.45-3.78 0-7.19-1.4-9.76-3.72-.2-.18-.02-.44.23-.29 2.79 1.63 6.24 2.6 9.82 2.6 2.4 0 5.02-.5 7.44-1.53.37-.16.68.24.26.49zm.9-1.03c-.28-.36-1.83-.17-2.52-.09-.2.02-.24-.15-.05-.29 1.24-.87 3.27-.62 3.51-.33.24.29-.06 2.32-1.23 3.28-.18.15-.35.07-.27-.13.26-.66.85-2.08.56-2.44zM8.83 6.19c0-.63.05-1.09-.28-1.55-.24-.36-.7-.6-1.11-.6-.75 0-1.42.4-1.58 1.19-.03.18-.16.35-.34.36l-1.9-.21c-.16-.03-.34-.16-.29-.4.44-2.3 2.51-2.99 4.36-2.99.95 0 2.18.25 2.93.97.95.89.86 2.08.86 3.37v3.06c0 .92.38 1.32.74 1.81.12.17.15.38-.01.51-.4.34-1.11.95-1.5 1.3-.13.11-.31.11-.45.03-.63-.52-.74-.77-1.09-1.27-1.04 1.06-1.78 1.38-3.13 1.38-1.6 0-2.85-.98-2.85-2.95 0-1.54.83-2.59 2.02-3.1 1.03-.45 2.47-.53 3.57-.66V6.19zm-.4 3.86c0 .7.02 1.28-.34 1.9-.29.5-.75.81-1.26.81-.7 0-1.11-.53-1.11-1.32 0-1.55 1.39-1.83 2.71-1.83v.44z"/>
  </svg>
);
const WhatsAppIcon = (props) => (
  <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
  </svg>
);

export default Footer;
