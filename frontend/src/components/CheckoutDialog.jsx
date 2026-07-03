import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Shield, CheckCircle2, Loader2, XCircle } from "lucide-react";
import { useCart } from "@/context/CartContext";
import { api } from "@/lib/api";
import { IDS } from "@/constants/testIds";

const formatINR = (n) => `₹${n.toLocaleString("en-IN")}`;

const loadRazorpay = () =>
  new Promise((resolve) => {
    if (window.Razorpay) return resolve(true);
    const s = document.createElement("script");
    s.src = "https://checkout.razorpay.com/v1/checkout.js";
    s.onload = () => resolve(true);
    s.onerror = () => resolve(false);
    document.body.appendChild(s);
  });

export const CheckoutDialog = ({ open, onClose }) => {
  const { items, subtotal, shipping, total, clear } = useCart();
  const [step, setStep] = useState("form"); // form | processing | success | error
  const [orderNumber, setOrderNumber] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const [form, setForm] = useState({
    name: "", email: "", phone: "", address: "", city: "", pincode: "",
  });
  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const validate = () => {
    if (!form.name || !form.email || !form.phone || !form.address || !form.city || !form.pincode)
      return "Please complete your delivery details.";
    if (!/^\S+@\S+\.\S+$/.test(form.email)) return "Please enter a valid email.";
    if (form.phone.replace(/\D/g, "").length < 10) return "Please enter a valid phone number.";
    return null;
  };

  const startPayment = async (e) => {
    e.preventDefault();
    const err = validate();
    if (err) { setStep("error"); setErrorMsg(err); return; }
    setStep("processing");
    try {
      const ok = await loadRazorpay();
      if (!ok) throw new Error("Razorpay could not be loaded. Check your connection.");

      const res = await api.post("/orders", {
        customer: form,
        items: items.map((i) => ({ product_id: i.product_id, variant_key: i.variant_key, quantity: i.quantity })),
        payment_method: "razorpay",
        subtotal_inr: subtotal, shipping_inr: shipping, total_inr: total,
      });
      const { order, razorpay_key_id } = res.data;
      setOrderNumber(order.order_number);

      const rzp = new window.Razorpay({
        key: razorpay_key_id,
        amount: order.total_inr * 100,
        currency: "INR",
        name: "ArtyFex Atelier",
        description: `Order ${order.order_number}`,
        order_id: order.razorpay_order_id,
        prefill: { name: form.name, email: form.email, contact: form.phone },
        theme: { color: "#D4AF37" },
        handler: async (response) => {
          try {
            await api.post("/orders/verify", {
              order_number: order.order_number,
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            });
            setStep("success");
            clear();
          } catch {
            setStep("error");
            setErrorMsg("Payment succeeded but verification failed. Please contact atelier@artyfex.in.");
          }
        },
        modal: {
          ondismiss: () => { setStep("form"); },
        },
      });
      rzp.on("payment.failed", (resp) => {
        setStep("error");
        setErrorMsg(resp.error?.description || "Payment failed. Please try again.");
      });
      rzp.open();
    } catch (err) {
      setStep("error");
      setErrorMsg(err?.response?.data?.detail || err.message || "Unable to start checkout.");
    }
  };

  const close = () => { setStep("form"); setErrorMsg(""); onClose(); };

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-[90] bg-black/80 backdrop-blur-sm"
            onClick={step === "processing" ? undefined : close} />
          <motion.div data-testid={IDS.checkout.dialog}
            initial={{ opacity: 0, y: 20, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 20, scale: 0.98 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-[100] w-[min(920px,94vw)] max-h-[92vh] overflow-y-auto bg-ink-900 border border-white/10 shadow-2xl">
            {step !== "processing" && (
              <button onClick={close} className="absolute top-4 right-4 p-2 border border-white/10 hover:border-gold/50 z-10">
                <X className="w-4 h-4 text-cream" />
              </button>
            )}

            {step === "form" && (
              <form onSubmit={startPayment} className="grid md:grid-cols-5">
                <div className="md:col-span-3 p-8 md:p-10">
                  <div className="text-[10px] uppercase tracking-luxury text-gold-soft">Secure Checkout</div>
                  <h3 className="font-serif text-3xl md:text-4xl text-cream mt-2">Complete your acquisition</h3>
                  <div className="mt-8 grid sm:grid-cols-2 gap-5">
                    <F label="Full name"><input required data-testid={IDS.checkout.name} value={form.name} onChange={upd("name")} className={inp} /></F>
                    <F label="Email"><input required type="email" data-testid={IDS.checkout.email} value={form.email} onChange={upd("email")} className={inp} /></F>
                    <F label="Phone"><input required data-testid={IDS.checkout.phone} value={form.phone} onChange={upd("phone")} className={inp} /></F>
                    <F label="Pincode"><input required data-testid={IDS.checkout.pincode} value={form.pincode} onChange={upd("pincode")} className={inp} /></F>
                    <div className="sm:col-span-2"><F label="Address"><input required data-testid={IDS.checkout.address} value={form.address} onChange={upd("address")} className={inp} /></F></div>
                    <div className="sm:col-span-2"><F label="City"><input required data-testid={IDS.checkout.city} value={form.city} onChange={upd("city")} className={inp} /></F></div>
                  </div>
                  <div className="mt-8 flex items-center gap-2 text-[10px] uppercase tracking-luxury text-cream/50">
                    <Shield className="w-3 h-3 text-gold" /> Payments securely processed by Razorpay · Cards · UPI · Netbanking · Wallets
                  </div>
                </div>
                <aside className="md:col-span-2 bg-ink-950 p-8 md:p-10 border-t md:border-t-0 md:border-l border-white/5">
                  <div className="text-[10px] uppercase tracking-luxury text-gold-soft">Order Summary</div>
                  <div className="mt-6 space-y-4 max-h-64 overflow-y-auto pr-2">
                    {items.map((it) => (
                      <div key={`${it.product_id}-${it.variant_key}`} className="flex gap-3">
                        <div className="w-14 h-16 shrink-0 overflow-hidden border border-white/10">
                          <img src={it.image} alt="" className="w-full h-full object-cover" />
                        </div>
                        <div className="flex-1 text-sm">
                          <div className="text-cream font-serif leading-tight">{it.product_name.split(" — ")[0]}</div>
                          <div className="text-[10px] uppercase tracking-luxury text-cream/40">{it.variant_label} · × {it.quantity}</div>
                        </div>
                        <div className="text-sm text-cream">{formatINR(it.price_inr * it.quantity)}</div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-8 space-y-2 text-sm">
                    <div className="flex justify-between"><span className="text-cream/50">Subtotal</span><span className="text-cream">{formatINR(subtotal)}</span></div>
                    <div className="flex justify-between"><span className="text-cream/50">Shipping</span><span className={shipping === 0 ? "text-gold" : "text-cream"}>{shipping === 0 ? "Free" : formatINR(shipping)}</span></div>
                    <div className="pt-4 border-t border-white/5 flex items-baseline justify-between">
                      <span className="text-[10px] uppercase tracking-luxury text-cream/50">Total</span>
                      <span className="font-serif text-3xl text-cream">{formatINR(total)}</span>
                    </div>
                  </div>
                  <button type="submit" data-testid={IDS.checkout.payButton}
                    className="mt-8 w-full bg-gold text-ink-950 px-6 py-5 text-xs uppercase tracking-luxury hover:bg-cream transition-colors">
                    Pay {formatINR(total)}
                  </button>
                </aside>
              </form>
            )}

            {step === "processing" && (
              <div className="p-16 text-center">
                <Loader2 className="w-8 h-8 text-gold animate-spin mx-auto" />
                <div className="mt-6 font-serif text-2xl text-cream">Opening Razorpay…</div>
                <div className="mt-2 text-sm text-cream/50">Do not close this window.</div>
              </div>
            )}

            {step === "success" && (
              <div className="p-12 md:p-16 text-center max-w-lg mx-auto">
                <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", damping: 12 }} className="inline-flex p-4 border border-gold/40">
                  <CheckCircle2 className="w-8 h-8 text-gold" />
                </motion.div>
                <div data-testid={IDS.checkout.success} className="mt-8 font-serif text-4xl text-cream leading-tight">Your piece is on its way.</div>
                <p className="mt-4 text-cream/60 font-light">
                  Order <span data-testid={IDS.checkout.orderNumber} className="text-gold font-medium">{orderNumber}</span> · Confirmation sent to your inbox. Our atelier will hand-inspect and dispatch within 3–5 business days.
                </p>
                <button data-testid={IDS.checkout.continueShopping} onClick={close} className="mt-10 inline-flex text-xs uppercase tracking-luxury text-gold border-b border-gold/40 pb-1">Continue browsing</button>
              </div>
            )}

            {step === "error" && (
              <div className="p-12 text-center max-w-lg mx-auto">
                <div className="inline-flex p-4 border border-red-500/40"><XCircle className="w-8 h-8 text-red-400" /></div>
                <div className="mt-6 font-serif text-3xl text-cream">Payment could not be completed</div>
                <p data-testid={IDS.checkout.error} className="mt-3 text-sm text-cream/60">{errorMsg}</p>
                <button onClick={() => { setStep("form"); setErrorMsg(""); }} className="mt-8 text-xs uppercase tracking-luxury text-gold border-b border-gold/40 pb-1">Try again</button>
              </div>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

const inp = "w-full bg-ink-950 border border-white/15 focus:border-gold focus:outline-none px-3 py-2.5 text-sm text-cream placeholder-cream/30 font-light";
const F = ({ label, children }) => (
  <label className="block">
    <span className="text-[10px] uppercase tracking-luxury text-cream/50">{label}</span>
    <div className="mt-1.5">{children}</div>
  </label>
);

export default CheckoutDialog;
