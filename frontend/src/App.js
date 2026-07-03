import React, { useEffect, useState } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import { CartProvider, useCart } from "@/context/CartContext";
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
import AdminPage from "@/pages/AdminPage";

function Shell() {
  const [products, setProducts] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const { setIsOpen } = useCart();

  useEffect(() => {
    Promise.all([fetchProducts(), fetchReviews()])
      .then(([p, r]) => {
        setProducts(p);
        setReviews(r);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const hero = products.find((p) => p.is_hero) || products[0];

  const openCheckout = () => {
    setIsOpen(false);
    setTimeout(() => setCheckoutOpen(true), 250);
  };

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
    <div className="App relative">
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
      <CartSheet onCheckout={openCheckout} />
      <CheckoutDialog open={checkoutOpen} onClose={() => setCheckoutOpen(false)} />
      <Toaster position="bottom-center" theme="dark" />
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
            <CartProvider>
              <Shell />
            </CartProvider>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
