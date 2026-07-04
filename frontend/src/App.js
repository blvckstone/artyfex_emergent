import React, { useEffect, useState } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import { CartProvider, useCart } from "@/context/CartContext";
import { AuthProvider } from "@/context/AuthContext";
import { WishlistProvider } from "@/context/WishlistContext";
import { fetchProducts, fetchReviews } from "@/lib/api";
import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
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
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    Promise.all([fetchProducts(), fetchReviews()])
      .then(([p, r]) => { setProducts(p); setReviews(r); })
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
        title="ArtyFex — Handmade Resin & Crystal Mirrors | Mumbai Atelier"
        description="ArtyFex is a Mumbai atelier of 100% handmade resin art & crystal stone mirrors. Statement 2×3 ft geode mirrors and companion pieces for luxury interiors."
        path="/"
        jsonLd={{
          "@context": "https://schema.org",
          "@type": "Organization",
          "name": "ArtyFex",
          "url": "https://www.artyfex.in",
          "logo": "https://www.artyfex.in/brand/logo.svg",
          "description": "Mumbai atelier of 100% handmade resin & crystal stone mirrors.",
          "founder": { "@type": "Person", "name": "Maloni" },
          "sameAs": ["https://www.instagram.com/artyfex", "https://www.facebook.com/artyfex"],
          "contactPoint": [
            { "@type": "ContactPoint", "email": "artyfex@artyfex.in", "telephone": "+91-99701-07760", "contactType": "customer service", "areaServed": "IN" },
            { "@type": "ContactPoint", "email": "artyfex.in@gmail.com", "contactType": "customer service", "areaServed": "IN" },
          ],
        }}
      />
      <Navbar />
      <main>
        <Hero />
        <ProductShowcase product={hero} />
        <Craftsmanship />
        <Collection products={products} />
        <Reviews reviews={reviews} />
        <B2B />
      </main>
      <Footer />
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
