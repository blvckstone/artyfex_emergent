import React, { useEffect, useState } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import { CartProvider, useCart } from "@/context/CartContext";
import { AuthProvider } from "@/context/AuthContext";
import { WishlistProvider } from "@/context/WishlistContext";
import { fetchProducts, fetchReviews } from "@/lib/api";
import { fetchHomepage } from "@/lib/homepage";
import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import AnnouncementBar from "@/components/AnnouncementBar";
import SaleBanner from "@/components/SaleBanner";
import SessionTracker from "@/components/SessionTracker";
import ProductShowcase from "@/components/ProductShowcase";
import Craftsmanship from "@/components/Craftsmanship";
import Collection from "@/components/Collection";
import Reviews from "@/components/Reviews";
import B2B from "@/components/B2B";
import Footer from "@/components/Footer";
import CartSheet from "@/components/CartSheet";
import CheckoutDialog from "@/components/CheckoutDialog";
import AuthDialog from "@/components/AuthDialog";
import AdminPage from "@/pages/AdminPage";
import ShopPage from "@/pages/ShopPage";
import AccountPage from "@/pages/AccountPage";
import LegalPage from "@/pages/LegalPage";
import AboutPage from "@/pages/AboutPage";
import ContactPage from "@/pages/ContactPage";
import ProductPage from "@/pages/ProductPage";
import AuthCallback from "@/pages/AuthCallback";
import ReviewPromptBanner from "@/components/ReviewPromptBanner";
import ReviewPromptModal from "@/components/ReviewPromptModal";
import SEO from "@/components/SEO";
import { ReviewPromptProvider } from "@/context/ReviewPromptContext";

function Home() {
  const [products, setProducts] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [homepage, setHomepage] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    Promise.all([fetchProducts(), fetchReviews(), fetchHomepage().catch(() => null)])
      .then(([p, r, hp]) => { setProducts(p); setReviews(r); setHomepage(hp); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);
  const hero = products.find((p) => p.is_hero) || products[0];
  if (loading || !hero) {
    return (
      <div className="min-h-screen bg-ink-950 flex items-center justify-center">
        <div className="text-center">
          <div className="font-serif text-4xl text-cream">Arty<span className="italic text-gold">Fex</span></div>
          <div className="mt-4 text-[10px] uppercase tracking-luxury text-cream/40">Loading the atelier…</div>
        </div>
      </div>
    );
  }
  return (
    <>
      <SEO
        title="ArtyFex — Handmade Resin Art · Mirrors, Watches, Tables & Furniture | Mumbai"
        description="ArtyFex is a Mumbai atelier of 100% handmade resin art — statement mirrors, watches, tables and bespoke furniture. One-of-one pieces for luxury interiors."
        path="/"
        jsonLd={{
          "@context": "https://schema.org",
          "@type": "Organization",
          "name": "ArtyFex",
          "url": "https://www.artyfex.in",
          "logo": "https://www.artyfex.in/brand/logo.svg",
          "description": "Mumbai atelier of 100% handmade resin art — mirrors, watches, tables and bespoke furniture.",
          "founder": { "@type": "Person", "name": "Maloni Mahada" },
          "address": {
            "@type": "PostalAddress",
            "streetAddress": "Malad West",
            "addressLocality": "Mumbai",
            "postalCode": "400095",
            "addressRegion": "Maharashtra",
            "addressCountry": "IN",
          },
          "sameAs": ["https://www.instagram.com/artyfex", "https://www.facebook.com/artyfex"],
          "contactPoint": [
            { "@type": "ContactPoint", "email": "artyfex@artyfex.in", "telephone": "+91-99701-07760", "contactType": "customer service", "areaServed": "IN" },
            { "@type": "ContactPoint", "email": "artyfex.in@gmail.com", "contactType": "customer service", "areaServed": "IN" },
          ],
        }}
      />
      <Navbar announcement={homepage?.announcement} />
      <main>
        <Hero content={homepage?.hero} />
        <ProductShowcase product={hero} />
        <Craftsmanship content={homepage?.craft} />
        <Collection products={products} content={homepage?.collection_section} />
        <SaleBanner content={homepage?.sale_banner} />
        <Reviews reviews={reviews} content={homepage?.reviews_section} />
        <B2B />
      </main>
      <Footer importantNote={homepage?.important_note} />
    </>
  );
}

function StoreShell() {
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const { setIsOpen } = useCart();
  const openCheckout = () => { setIsOpen(false); setTimeout(() => setCheckoutOpen(true), 250); };
  return (
    <div className="App relative">
      <ReviewPromptBanner />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/shop" element={<ShopPage />} />
        <Route path="/product/:slug" element={<ProductPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/contact" element={<ContactPage />} />
        <Route path="/account" element={<AccountPage />} />
        <Route path="/policies/:slug" element={<LegalPage />} />
        <Route path="/terms" element={<LegalPage />} />
        <Route path="/privacy" element={<LegalPage />} />
        <Route path="/auth/callback" element={<AuthCallback />} />
      </Routes>
      <CartSheet onCheckout={openCheckout} />
      <CheckoutDialog open={checkoutOpen} onClose={() => setCheckoutOpen(false)} />
      <AuthDialog />
      <ReviewPromptModal />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <SessionTracker />
      <Routes>
        <Route path="/admin" element={<AdminPage />} />
        <Route
          path="/*"
          element={
            <AuthProvider>
              <WishlistProvider>
                <CartProvider>
                  <ReviewPromptProvider>
                    <StoreShell />
                  </ReviewPromptProvider>
                </CartProvider>
              </WishlistProvider>
            </AuthProvider>
          }
        />
      </Routes>
      <Toaster position="bottom-center" theme="dark" />
    </BrowserRouter>
  );
}
