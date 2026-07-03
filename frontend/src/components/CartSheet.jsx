import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Plus, Minus, Trash2, ShoppingBag } from "lucide-react";
import { useCart } from "@/context/CartContext";
import { IDS } from "@/constants/testIds";

const formatINR = (n) => `₹${n.toLocaleString("en-IN")}`;

export const CartSheet = ({ onCheckout }) => {
  const { isOpen, setIsOpen, items, updateQty, removeItem, subtotal, shipping, total } = useCart();

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setIsOpen(false)}
            className="fixed inset-0 z-[70] bg-black/70 backdrop-blur-sm"
          />
          <motion.aside
            data-testid={IDS.cart.sheet}
            initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 240 }}
            className="fixed top-0 right-0 h-full w-full sm:w-[440px] z-[80] bg-ink-900 border-l border-white/10 flex flex-col"
          >
            <div className="flex items-center justify-between p-6 border-b border-white/5">
              <div>
                <div className="text-[10px] uppercase tracking-luxury text-gold-soft">Your Atelier</div>
                <div className="font-serif text-2xl text-cream mt-1">Shopping Bag</div>
              </div>
              <button onClick={() => setIsOpen(false)} className="p-2 border border-white/10 hover:border-gold/50">
                <X className="w-4 h-4 text-cream" />
              </button>
            </div>

            {items.length === 0 ? (
              <div data-testid={IDS.cart.empty} className="flex-1 flex flex-col items-center justify-center px-8 text-center">
                <div className="p-5 border border-gold/20 mb-6"><ShoppingBag className="w-6 h-6 text-gold" /></div>
                <h3 className="font-serif text-2xl text-cream">Your atelier is empty</h3>
                <p className="text-sm text-cream/50 mt-3 font-light max-w-xs">
                  Every piece is 100% handpoured. Curate your first heirloom.
                </p>
                <button onClick={() => setIsOpen(false)} className="mt-8 text-xs uppercase tracking-luxury text-gold border-b border-gold/40 pb-1">
                  Browse the Collection
                </button>
              </div>
            ) : (
              <>
                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                  {items.map((it) => {
                    const key = `${it.product_id}-${it.variant_key}`;
                    return (
                      <div key={key} data-testid={IDS.cart.item(key)} className="flex gap-4 pb-6 border-b border-white/5">
                        <div className="w-24 h-28 shrink-0 overflow-hidden border border-white/10">
                          <img src={it.image} alt="" className="w-full h-full object-cover" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-serif text-lg text-cream leading-tight truncate">{it.product_name.split(" — ")[0]}</div>
                          <div className="text-[10px] uppercase tracking-luxury text-cream/40 mt-1">{it.variant_label}</div>
                          <div className="mt-3 font-serif text-cream">{formatINR(it.price_inr)}</div>
                          <div className="mt-3 flex items-center justify-between">
                            <div className="inline-flex items-center border border-white/10">
                              <button data-testid={IDS.cart.minus(key)} onClick={() => updateQty(it.product_id, it.variant_key, it.quantity - 1)} className="p-2 hover:bg-white/5" aria-label="minus">
                                <Minus className="w-3 h-3 text-cream" />
                              </button>
                              <span className="px-3 text-sm text-cream min-w-[28px] text-center">{it.quantity}</span>
                              <button data-testid={IDS.cart.plus(key)} onClick={() => updateQty(it.product_id, it.variant_key, it.quantity + 1)} className="p-2 hover:bg-white/5" aria-label="plus">
                                <Plus className="w-3 h-3 text-cream" />
                              </button>
                            </div>
                            <button data-testid={IDS.cart.remove(key)} onClick={() => removeItem(it.product_id, it.variant_key)} className="p-2 text-cream/40 hover:text-red-400" aria-label="remove">
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div className="p-6 border-t border-white/5 space-y-3">
                  <Row label="Subtotal" value={formatINR(subtotal)} testid={IDS.cart.subtotal} />
                  <Row
                    label="Shipping"
                    value={shipping === 0 ? "Complimentary" : formatINR(shipping)}
                    testid={IDS.cart.shipping}
                    accent={shipping === 0}
                  />
                  <div className="pt-3 border-t border-white/5 flex items-baseline justify-between">
                    <span className="text-[10px] uppercase tracking-luxury text-cream/50">Total</span>
                    <span data-testid={IDS.cart.total} className="font-serif text-3xl text-cream">{formatINR(total)}</span>
                  </div>
                  <button
                    data-testid={IDS.cart.checkout}
                    onClick={onCheckout}
                    className="mt-4 w-full bg-gold text-ink-950 px-6 py-5 text-xs uppercase tracking-luxury hover:bg-cream transition-colors"
                  >
                    Secure Checkout
                  </button>
                  <p className="text-[10px] text-center text-cream/40 uppercase tracking-luxury">
                    Stripe · Razorpay · UPI · Cards
                  </p>
                </div>
              </>
            )}
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
};

const Row = ({ label, value, testid, accent }) => (
  <div className="flex items-center justify-between text-sm">
    <span className="text-cream/50">{label}</span>
    <span data-testid={testid} className={accent ? "text-gold" : "text-cream"}>{value}</span>
  </div>
);

export default CartSheet;
