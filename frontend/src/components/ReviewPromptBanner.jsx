import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Star, X, Sparkles } from "lucide-react";
import { useReviewPrompts } from "@/context/ReviewPromptContext";

/**
 * ReviewPromptBanner
 * A thin, elegant gold banner that appears near the top of the site whenever
 * the logged-in user has any product delivered N+ days ago that has not yet
 * been reviewed. Clicking "Share your reflection" opens the ReviewPromptModal
 * (see AccountPage where the modal is mounted).
 */
export default function ReviewPromptBanner() {
  const { prompts, dismissed, dismissForSession, setModalOpen } = useReviewPrompts();

  const show = !dismissed && prompts.length > 0;

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
          data-testid="review-prompt-banner"
          className="fixed left-0 right-0 top-[84px] md:top-[96px] z-[40] bg-gradient-to-r from-gold/20 via-gold/10 to-gold/20 border-y border-gold/30 backdrop-blur pointer-events-auto"
        >
          <div className="max-w-[1440px] mx-auto px-4 md:px-8 py-2.5 flex items-center gap-3">
            <div className="p-1.5 border border-gold/40 hidden sm:inline-flex">
              <Sparkles className="w-3.5 h-3.5 text-gold" />
            </div>
            <div className="flex-1 min-w-0 text-cream">
              <span className="text-xs md:text-sm font-serif">
                {prompts.length === 1 ? (
                  <>How are you enjoying your <span className="italic text-gold">{prompts[0].product_name.split(" — ")[0]}</span>?</>
                ) : (
                  <>{prompts.length} of your pieces are ready for their story to be shared.</>
                )}
              </span>
              <span className="ml-3 hidden md:inline text-[11px] text-cream/50 uppercase tracking-luxury">Rate & review to help fellow collectors.</span>
            </div>
            <button
              data-testid="review-prompt-cta"
              onClick={() => setModalOpen(true)}
              className="inline-flex items-center gap-2 bg-gold text-ink-950 px-4 py-1.5 text-[10px] md:text-xs uppercase tracking-luxury hover:bg-cream transition-colors"
            >
              <Star className="w-3 h-3" fill="currentColor" />
              Share your reflection
            </button>
            <button
              data-testid="review-prompt-dismiss"
              onClick={dismissForSession}
              aria-label="Dismiss"
              className="p-1.5 text-cream/60 hover:text-cream"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
