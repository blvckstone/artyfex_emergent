import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Shield, CheckCircle2, Loader2, XCircle, AlertTriangle, RefreshCw, Mail } from "lucide-react";
import { useCart } from "@/context/CartContext";
import { api } from "@/lib/api";
import { IDS } from "@/constants/testIds";

const formatINR = (n) => `₹${(n || 0).toLocaleString("en-IN")}`;

const loadRazorpay = () =>
  new Promise((resolve) => {
    if (window.Razorpay) return resolve(true);
    const s = document.createElement("script");
    s.src = "https://checkout.razorpay.com/v1/checkout.js";
    s.onload = () => resolve(true);
    s.onerror = () => resolve(false);
    document.body.appendChild(s);
  });

const MAX_RETRIES = 3;

export const CheckoutDialog = ({ open, onClose }) => {
  const { items, subtotal, shipping, total, coupon, discount, clear } = useCart();
  const [step, setStep] = useState("form"); // form | processing | success | error
  const [orderNumber, setOrderNumber] = useState("");
  const [errorTitle, setErrorTitle] = useState("Payment could not be completed");
  const [errorMsg, setErrorMsg] = useState("");
  const [errorCode, setErrorCode] = useState("");
  const [attempts, setAttempts] = useState(0);
  const [lastOrderPayload, setLastOrderPayload] = useState(null);

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

  const logFailure = async (payload) => {
    try {
      await api.post("/payments/failed", payload);
    } catch { /* silent — logging failure must not block UX */ }
  };

  const failWith = ({ title, description, code, source, step: stepName, reason, order_number, rzp_order_id, rzp_payment_id }) => {
    setStep("error");
    setErrorTitle(title || "Payment could not be completed");
    setErrorMsg(description || "Please try again or use a different method.");
    setErrorCode(code || "");
    // Fire-and-forget log to backend
    logFailure({
      order_number: order_number || null,
      razorpay_order_id: rzp_order_id || null,
      razorpay_payment_id: rzp_payment_id || null,
      error_code: code || null,
      error_description: description || null,
      error_source: source || null,
      error_step: stepName || null,
      error_reason: reason || null,
      amount_inr: total || 0,
      customer_email: form.email || null,
      customer_name: form.name || null,
      customer_phone: form.phone || null,
      attempt: attempts + 1,
    });
  };

  const initiateCheckout = async (payload) => {
    setStep("processing");
    setAttempts((a) => a + 1);
    try {
      const ok = await loadRazorpay();
      if (!ok) {
        return failWith({
          title: "Payment gateway unavailable",
          description: "Razorpay could not be reached. Please check your internet connection and try again.",
          code: "RZP_LOAD_FAILED",
          source: "client",
        });
      }

      const res = await api.post("/orders", payload);
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
          } catch (verr) {
            failWith({
              title: "Payment received — verification failed",
              description: "Your payment was captured but our system could not verify it. Please save this order number and email atelier@artyfex.in — no charge will be lost.",
              code: verr?.response?.data?.detail || "VERIFY_FAILED",
              source: "backend",
              order_number: order.order_number,
              rzp_order_id: response.razorpay_order_id,
              rzp_payment_id: response.razorpay_payment_id,
            });
          }
        },
        modal: {
          ondismiss: () => {
            // User closed the Razorpay modal without paying — offer retry
            failWith({
              title: "Payment window closed",
              description: "You closed the payment window before completing the transaction. Your cart is still saved — retry when you're ready.",
              code: "USER_CANCELLED",
              source: "user",
              order_number: order.order_number,
              rzp_order_id: order.razorpay_order_id,
            });
          },
        },
      });
      rzp.on("payment.failed", (resp) => {
        const err = resp.error || {};
        failWith({
          title: "Payment declined",
          description: err.description || "Your payment was declined by the bank. Try a different card, UPI, or netbanking.",
          code: err.code || "PAYMENT_FAILED",
          source: err.source || "gateway",
          stepName: err.step || null,
          reason: err.reason || null,
          order_number: order.order_number,
          rzp_order_id: err.metadata?.order_id || order.razorpay_order_id,
          rzp_payment_id: err.metadata?.payment_id,
        });
      });
      rzp.open();
    } catch (err) {
      failWith({
        title: "Could not start checkout",
        description: err?.response?.data?.detail || err?.message || "An unexpected error occurred. Please try again.",
        code: err?.response?.status ? `HTTP_${err.response.status}` : "UNKNOWN",
        source: "backend",
      });
    }
  };

  const startPayment = async (e) => {
    e.preventDefault();
    const err = validate();
    if (err) {
      setStep("error");
      setErrorTitle("Please review your details");
      setErrorMsg(err);
      setErrorCode("VALIDATION");
      return;
    }
    const payload = {
      customer: form,
      items: items.map((i) => ({ product_id: i.product_id, variant_key: i.variant_key, quantity: i.quantity })),
      payment_method: "razorpay",
      subtotal_inr: subtotal,
      shipping_inr: shipping,
      total_inr: total,
      coupon_code: coupon?.code || null,
      discount_inr: discount || 0,
    };
    setLastOrderPayload(payload);
    initiateCheckout(payload);
  };

  const retryPayment = () => {
    if (!lastOrderPayload) { setStep("form"); return; }
    initiateCheckout(lastOrderPayload);
  };

  const close = () => {
    setStep("form"); setErrorMsg(""); setErrorTitle("Payment could not be completed"); setErrorCode("");
    setAttempts(0); setLastOrderPayload(null);
    onClose();
  };

  const tooManyAttempts = attempts >= MAX_RETRIES;

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-[90] bg-black/80 backdrop-blur-sm"
            onClick={step === "processing" ? undefined : close} />
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 pointer-events-none">
          <motion.div data-testid={IDS.checkout.dialog}
            initial={{ opacity: 0, y: 20, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 20, scale: 0.98 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            className="relative w-[min(920px,94vw)] max-h-[92vh] overflow-y-auto bg-ink-900 border border-white/10 shadow-2xl pointer-events-auto">
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
                          <div className="text-[10px] uppercase tracking-luxury text-cream/40">
                            {it.variant_label}{it.variant_size ? ` · ${it.variant_size}` : ""} · × {it.quantity}
                          </div>
                        </div>
                        <div className="text-sm text-cream">{formatINR(it.price_inr * it.quantity)}</div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-8 space-y-2 text-sm">
                    <div className="flex justify-between"><span className="text-cream/50">Subtotal</span><span className="text-cream">{formatINR(subtotal)}</span></div>
                    {discount > 0 && (
                      <div className="flex justify-between">
                        <span className="text-cream/50">Discount {coupon?.code ? `(${coupon.code})` : ""}</span>
                        <span className="text-gold">- {formatINR(discount)}</span>
                      </div>
                    )}
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
              <div data-testid="checkout-error-state" className="p-8 md:p-12 max-w-2xl mx-auto">
                {/* Prominent error banner */}
                <div className="border-l-4 border-red-500 bg-red-500/5 p-5 flex items-start gap-4">
                  <div className="p-2 border border-red-500/40 shrink-0">
                    <AlertTriangle className="w-5 h-5 text-red-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-serif text-2xl text-cream leading-tight">{errorTitle}</div>
                    <p data-testid={IDS.checkout.error} className="mt-2 text-sm text-cream/70 leading-relaxed">{errorMsg}</p>
                    {errorCode && (
                      <div className="mt-3 text-[10px] uppercase tracking-luxury text-cream/40">
                        Reference · <span className="text-cream/60 font-mono normal-case tracking-normal">{errorCode}</span>
                        {orderNumber ? <> · Order <span className="text-cream/60 font-mono normal-case tracking-normal">{orderNumber}</span></> : null}
                      </div>
                    )}
                  </div>
                </div>

                {/* Attempts / guidance */}
                {attempts > 0 && (
                  <div className="mt-4 text-[11px] text-cream/50 flex items-center gap-2">
                    <span className="inline-flex items-center gap-1">
                      <XCircle className="w-3 h-3" /> Attempt {attempts} of {MAX_RETRIES}
                    </span>
                    {tooManyAttempts && (
                      <span className="text-yellow-400">· Please try a different method or contact us.</span>
                    )}
                  </div>
                )}

                {/* Action buttons */}
                <div className="mt-6 flex flex-col sm:flex-row gap-3">
                  {!tooManyAttempts && lastOrderPayload && (
                    <button
                      data-testid="checkout-retry"
                      onClick={retryPayment}
                      className="inline-flex items-center justify-center gap-2 bg-gold text-ink-950 px-6 py-4 text-xs uppercase tracking-luxury hover:bg-cream transition-colors"
                    >
                      <RefreshCw className="w-3.5 h-3.5" /> Retry payment
                    </button>
                  )}
                  <button
                    data-testid="checkout-edit-details"
                    onClick={() => { setStep("form"); setErrorMsg(""); setErrorCode(""); }}
                    className="inline-flex items-center justify-center gap-2 border border-white/15 text-cream/80 px-6 py-4 text-xs uppercase tracking-luxury hover:border-gold/40 hover:text-gold transition-colors"
                  >
                    Edit details
                  </button>
                  {tooManyAttempts && (
                    <a
                      href={`mailto:atelier@artyfex.in?subject=Payment%20assistance%20-%20${encodeURIComponent(orderNumber || "New order")}&body=${encodeURIComponent("Hi ArtyFex, I need help completing my payment.\nOrder: " + (orderNumber || "N/A") + "\nError code: " + errorCode)}`}
                      data-testid="checkout-contact-support"
                      className="inline-flex items-center justify-center gap-2 border border-gold/40 text-gold px-6 py-4 text-xs uppercase tracking-luxury hover:bg-gold hover:text-ink-950 transition-colors"
                    >
                      <Mail className="w-3.5 h-3.5" /> Contact atelier
                    </a>
                  )}
                </div>

                <p className="mt-6 text-[11px] text-cream/40 leading-relaxed">
                  If your bank account was debited but the order still shows failed, do not worry — no double charge will occur.
                  Contact <a href="mailto:atelier@artyfex.in" className="text-gold hover:text-cream">atelier@artyfex.in</a> with the reference above and we will resolve within 24 hours.
                </p>
              </div>
            )}
          </motion.div>
          </div>
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
