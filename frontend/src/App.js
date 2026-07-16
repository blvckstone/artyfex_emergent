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
import DynamicPage from "@/pages/DynamicPage";
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
        title="Luxury Handmade Resin Mirrors, Modern Art & Bespoke Furniture · ArtyFex Mumbai"
        description="Shop luxury handmade mirrors, modern resin art, statement wall pieces and bespoke furniture. Every ArtyFex piece is hand-poured in Mumbai — one-of-a-kind, made-to-order, insured white-glove delivery across India."
        path="/"
        jsonLd={{
          "@context": "https://schema.org",
          "@graph": [
            {
              "@type": "Organization",
              "@id": "https://www.artyfex.in/#organization",
              "name": "ArtyFex",
              "alternateName": ["ArtyFex Atelier", "ArtyFex India"],
              "url": "https://www.artyfex.in",
              "logo": "https://www.artyfex.in/brand/logo.svg",
              "description": "Luxury Mumbai atelier of 100% handmade resin & crystal mirrors, modern art and bespoke furniture. Made-to-order, insured delivery.",
              "founder": { "@type": "Person", "name": "Maloni Mahada" },
              "foundingDate": "2019",
              "areaServed": { "@type": "Country", "name": "India" },
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
                { "@type": "ContactPoint", "email": "artyfex@artyfex.in", "telephone": "+91-99701-07760", "contactType": "customer service", "areaServed": "IN", "availableLanguage": ["en", "hi"] },
                { "@type": "ContactPoint", "email": "artyfex.in@gmail.com", "contactType": "customer service", "areaServed": "IN" },
              ],
            },
            {
              "@type": "WebSite",
              "@id": "https://www.artyfex.in/#website",
              "url": "https://www.artyfex.in",
              "name": "ArtyFex",
              "publisher": { "@id": "https://www.artyfex.in/#organization" },
              "inLanguage": "en-IN",
              "potentialAction": {
                "@type": "SearchAction",
                "target": "https://www.artyfex.in/shop?q={search_term_string}",
                "query-input": "required name=search_term_string",
              },
            },
            {
              "@type": "Store",
              "@id": "https://www.artyfex.in/#store",
              "name": "ArtyFex Atelier",
              "image": "https://www.artyfex.in/brand/og-cover.jpg",
              "priceRange": "₹₹₹",
              "url": "https://www.artyfex.in",
              "telephone": "+91-99701-07760",
              "address": {
                "@type": "PostalAddress",
                "streetAddress": "Malad West",
                "addressLocality": "Mumbai",
                "postalCode": "400095",
                "addressRegion": "Maharashtra",
                "addressCountry": "IN",
              },
              "makesOffer": [
                { "@type": "Offer", "itemOffered": { "@type": "Product", "name": "Handmade Resin Mirrors" } },
                { "@type": "Offer", "itemOffered": { "@type": "Product", "name": "Bespoke Modern Furniture" } },
              ],
            },
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
        <Route path="/p/:slug" element={<DynamicPage />} />
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
