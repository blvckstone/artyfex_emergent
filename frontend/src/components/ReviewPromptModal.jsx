import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Star, X, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useReviewPrompts } from "@/context/ReviewPromptContext";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";

/**
 * ReviewPromptModal
 * Opens from the banner CTA (or from the Account page manually). Shows a card
 * per eligible product with 5-star rating + short title/body form. Submitting
 * calls POST /api/products/:slug/reviews and removes that item from the list.
 */
export default function ReviewPromptModal() {
  const { modalOpen, setModalOpen, prompts, removePromptById } = useReviewPrompts();
  const { token } = useAuth();
  const [busyFor, setBusyFor] = useState(null); // product_id being submitted
  const [drafts, setDrafts] = useState({}); // { [product_id]: { rating, title, body } }

  const setDraft = (pid, patch) =>
    setDrafts((d) => ({ ...d, [pid]: { rating: 5, title: "", body: "", ...(d[pid] || {}), ...patch } }));

  const submit = async (p) => {
    const draft = drafts[p.product_id] || { rating: 5, title: "", body: "" };
    if (!draft.title.trim() || !draft.body.trim()) {
      toast.error("Please add a short headline and your thoughts.");
      return;
    }
    setBusyFor(p.product_id);
    try {
      await api.post(
        `/products/${p.product_slug}/reviews`,
        { rating: draft.rating, title: draft.title, body: draft.body },
        { headers: { Authorization: `Bearer ${token}` } },
      );
      toast.success("Thank you for your reflection.");
      removePromptById(p.product_id);
      setDrafts((d) => { const c = { ...d }; delete c[p.product_id]; return c; });
      if (prompts.length <= 1) setModalOpen(false);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not submit review.");
    } finally {
      setBusyFor(null);
    }
  };

  return (
    <AnimatePresence>
      {modalOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setModalOpen(false)}
            className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-sm"
          />
          <motion.div
            initial={{ opacity: 0, y: 24, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.98 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            data-testid="review-prompt-modal"
            className="fixed inset-0 z-[110] flex items-start md:items-center justify-center p-4 md:p-8 overflow-y-auto pointer-events-none"
          >
            <div className="relative w-[min(720px,96vw)] bg-ink-900 border border-white/10 shadow-2xl pointer-events-auto my-8">
              <button
                onClick={() => setModalOpen(false)}
                className="absolute top-4 right-4 p-2 border border-white/10 hover:border-gold/50 z-10"
                aria-label="Close"
              >
                <X className="w-4 h-4 text-cream" />
              </button>
              <div className="p-8 md:p-10">
                <div className="text-[10px] uppercase tracking-luxury text-gold-soft">Your Reflections</div>
                <h2 className="mt-2 font-serif text-3xl md:text-4xl text-cream">Rate your recent pieces</h2>
                <p className="mt-3 text-sm text-cream/60 max-w-lg">
                  Your considered words help fellow collectors — and celebrate the artisans who shaped your piece.
                </p>

                {prompts.length === 0 ? (
                  <div className="mt-10 text-center text-cream/50 py-16">
                    You're all caught up. Thank you.
                  </div>
                ) : (
                  <div className="mt-8 grid gap-6">
                    {prompts.map((p) => {
                      const d = drafts[p.product_id] || { rating: 5, title: "", body: "" };
                      const submitting = busyFor === p.product_id;
                      return (
                        <div
                          key={p.product_id}
                          data-testid={`review-prompt-card-${p.product_slug}`}
                          className="border border-white/10 p-5 md:p-6 grid md:grid-cols-[112px_1fr] gap-5 bg-ink-950"
                        >
                          <div className="w-28 h-28 md:w-full md:h-28 overflow-hidden border border-white/10">
                            <img src={p.product_image} alt="" className="w-full h-full object-cover" />
                          </div>
                          <div className="min-w-0">
                            <div className="font-serif text-xl text-cream">{p.product_name.split(" — ")[0]}</div>
                            <div className="text-[10px] uppercase tracking-luxury text-cream/40 mt-1">
                              Delivered · {p.days_since_delivery} day{p.days_since_delivery === 1 ? "" : "s"} ago · Order {p.order_number}
                            </div>

                            {/* Stars */}
                            <div className="mt-4 flex items-center gap-1">
                              {[1, 2, 3, 4, 5].map((s) => (
                                <button
                                  key={s}
                                  type="button"
                                  data-testid={`review-star-${p.product_slug}-${s}`}
                                  onClick={() => setDraft(p.product_id, { rating: s })}
                                  className="p-1 -m-1"
                                  aria-label={`Rate ${s} stars`}
                                >
                                  <Star
                                    className={`w-6 h-6 transition-colors ${
                                      s <= d.rating ? "text-gold" : "text-cream/25"
                                    }`}
                                    fill={s <= d.rating ? "currentColor" : "none"}
                                  />
                                </button>
                              ))}
                              <span className="ml-2 text-xs text-cream/50">{d.rating} of 5</span>
                            </div>

                            <input
                              data-testid={`review-title-${p.product_slug}`}
                              value={d.title}
                              onChange={(e) => setDraft(p.product_id, { title: e.target.value })}
                              placeholder="A short headline (e.g. Breathtaking in daylight)"
                              className="mt-4 w-full bg-transparent border-b border-white/15 focus:border-gold outline-none py-2 text-sm text-cream placeholder-cream/30"
                            />
                            <textarea
                              data-testid={`review-body-${p.product_slug}`}
                              value={d.body}
                              onChange={(e) => setDraft(p.product_id, { body: e.target.value })}
                              placeholder="How does the piece live in your space?"
                              rows={3}
                              className="mt-3 w-full bg-transparent border border-white/10 focus:border-gold outline-none p-3 text-sm text-cream placeholder-cream/30 resize-none"
                            />
                            <div className="mt-4 flex justify-end">
                              <button
                                data-testid={`review-submit-${p.product_slug}`}
                                disabled={submitting}
                                onClick={() => submit(p)}
                                className="inline-flex items-center gap-2 bg-gold text-ink-950 px-5 py-2.5 text-xs uppercase tracking-luxury hover:bg-cream disabled:opacity-60"
                              >
                                {submitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : "Submit reflection"}
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
