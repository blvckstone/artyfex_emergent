import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Home, ShoppingBag, Heart, User, Store } from "lucide-react";
import { useCart } from "@/context/CartContext";
import { useAuth } from "@/context/AuthContext";
import { useWishlist } from "@/context/WishlistContext";

function TabItem({ testid, label, Icon, activeState, badge, onClick, to }) {
  const content = (
    <>
      <div className="relative">
        <Icon className={`w-5 h-5 mx-auto transition-colors ${activeState ? "text-gold" : "text-cream/70"}`} />
        {badge != null && badge > 0 && (
          <span className="absolute -top-1.5 -right-2 min-w-[16px] h-[16px] px-1 rounded-full bg-gold text-ink-950 text-[9px] font-semibold flex items-center justify-center">{badge}</span>
        )}
      </div>
      <div className={`mt-1 text-[10px] tracking-wide uppercase transition-colors ${activeState ? "text-gold" : "text-cream/60"}`}>{label}</div>
    </>
  );
  const cls = "flex-1 flex flex-col items-center justify-center py-2";
  if (to) return <Link data-testid={testid} to={to} className={cls}>{content}</Link>;
  return <button data-testid={testid} onClick={onClick} className={cls}>{content}</button>;
}

export default function MobileTabBar() {
  const loc = useLocation();
  const nav = useNavigate();
  const { setIsOpen: openCart, count } = useCart();
  const { user, openAuth } = useAuth();
  const { items: wishItems } = useWishlist();
  const wishCount = (wishItems && wishItems.length) || 0;

  if (loc.pathname.startsWith("/admin")) return null;

  const active = (path) => (path === "/" ? loc.pathname === "/" : loc.pathname.startsWith(path));

  return (
    <>
      <div aria-hidden className="lg:hidden h-[64px]" />
      <nav
        data-testid="mobile-tab-bar"
        className="lg:hidden fixed bottom-0 inset-x-0 z-50 backdrop-blur bg-ink-950/95 border-t border-white/10"
        style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
        aria-label="Primary"
      >
        <div className="flex items-stretch">
          <TabItem testid="tab-home" label="Home" Icon={Home} activeState={active("/") && !loc.hash} to="/" />
          <TabItem testid="tab-shop" label="Shop" Icon={Store} activeState={active("/shop") || active("/product")} to="/shop" />
          <TabItem testid="tab-cart" label="Cart" Icon={ShoppingBag} activeState={false} badge={count} onClick={() => openCart(true)} />
          <TabItem testid="tab-wishlist" label="Saved" Icon={Heart} activeState={active("/account") && (loc.search.includes("tab=wishlist"))} badge={wishCount} onClick={() => (user ? nav("/account?tab=wishlist") : openAuth("login"))} />
          <TabItem testid="tab-account" label="Account" Icon={User} activeState={active("/account") && !loc.search.includes("tab=wishlist")} onClick={() => (user ? nav("/account") : openAuth("login"))} />
        </div>
      </nav>
    </>
  );
}
