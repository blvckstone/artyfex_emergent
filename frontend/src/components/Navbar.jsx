import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ShoppingBag, Menu, X, User } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useCart } from "@/context/CartContext";
import { useAuth } from "@/context/AuthContext";
import { IDS } from "@/constants/testIds";

const links = [
  { id: IDS.nav.collection, label: "Shop", href: "/shop", route: true },
  { id: IDS.nav.craft, label: "The Craft", href: "/#craft" },
  { id: IDS.nav.reviews, label: "Reviews", href: "/#reviews" },
  { id: IDS.nav.b2b, label: "Trade / B2B", href: "/#b2b" },
];

export const Navbar = () => {
  const { setIsOpen, count } = useCart();
  const { user, openAuth } = useAuth();
  const nav = useNavigate();
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <motion.header
      initial={{ y: -30, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
      className={`fixed top-0 inset-x-0 z-50 transition-all duration-500 ${
        scrolled ? "glass" : "bg-transparent"
      }`}
    >
      <div className="max-w-[1440px] mx-auto px-6 md:px-12 lg:px-16 flex items-center justify-between h-20">
        <Link
          to="/"
          data-testid={IDS.nav.logo}
          className="font-serif text-2xl md:text-3xl tracking-tight text-cream flex items-baseline gap-1"
        >
          Arty<span className="italic text-gold">Fex</span>
        </Link>

        <nav className="hidden lg:flex items-center gap-10">
          {links.map((l) =>
            l.route ? (
              <Link
                key={l.href}
                to={l.href}
                data-testid={l.id}
                className="text-xs uppercase tracking-luxury text-cream/70 hover:text-gold transition-colors duration-300"
              >
                {l.label}
              </Link>
            ) : (
              <a
                key={l.href}
                href={l.href}
                data-testid={l.id}
                className="text-xs uppercase tracking-luxury text-cream/70 hover:text-gold transition-colors duration-300"
              >
                {l.label}
              </a>
            ),
          )}
        </nav>

        <div className="flex items-center gap-3">
          <button
            data-testid="nav-account"
            onClick={() => user ? nav("/account") : openAuth("login")}
            className="inline-flex items-center gap-2 text-xs uppercase tracking-luxury px-3 md:px-4 py-2.5 md:py-3 border border-white/10 hover:border-gold/40 text-cream/80 hover:text-gold transition-all"
          >
            <User className="w-3.5 h-3.5" /> <span className="hidden sm:inline">{user ? user.name.split(" ")[0] : "Sign in"}</span>
          </button>
          <button
            data-testid={IDS.nav.cartToggle}
            onClick={() => setIsOpen(true)}
            className="relative p-2.5 border border-white/10 hover:border-gold/40 transition-colors group"
            aria-label="Open cart"
          >
            <ShoppingBag className="w-4 h-4 text-cream group-hover:text-gold" />
            <AnimatePresence>
              {count > 0 && (
                <motion.span
                  key={count}
                  initial={{ scale: 0.5, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0.5, opacity: 0 }}
                  data-testid={IDS.nav.cartCount}
                  className="absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] px-1 rounded-full bg-gold text-ink-950 text-[10px] font-semibold flex items-center justify-center"
                >
                  {count}
                </motion.span>
              )}
            </AnimatePresence>
          </button>
          <button
            onClick={() => setMobileOpen((v) => !v)}
            className="lg:hidden p-2.5 border border-white/10 text-cream"
            aria-label="Menu"
          >
            {mobileOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="lg:hidden overflow-hidden glass border-t border-white/5"
          >
            <div className="px-6 py-6 flex flex-col gap-4">
              {links.map((l) =>
                l.route ? (
                  <Link
                    key={l.href}
                    to={l.href}
                    onClick={() => setMobileOpen(false)}
                    className="text-sm uppercase tracking-luxury text-cream/80 hover:text-gold"
                  >
                    {l.label}
                  </Link>
                ) : (
                  <a
                    key={l.href}
                    href={l.href}
                    onClick={() => setMobileOpen(false)}
                    className="text-sm uppercase tracking-luxury text-cream/80 hover:text-gold"
                  >
                    {l.label}
                  </a>
                ),
              )}
              <button
                data-testid="nav-account-mobile"
                onClick={() => { setMobileOpen(false); user ? nav("/account") : openAuth("login"); }}
                className="text-left text-sm uppercase tracking-luxury text-gold border-t border-white/5 pt-4 mt-2"
              >
                {user ? `Your account (${user.name.split(" ")[0]})` : "Sign in / Create account"}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.header>
  );
};

export default Navbar;
