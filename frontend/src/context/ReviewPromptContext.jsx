import React, { createContext, useContext, useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";

const ReviewPromptContext = createContext(null);
const DISMISS_KEY = "artyfex_review_prompt_dismissed_v1"; // session-scoped

/**
 * ReviewPromptProvider
 * Fetches /api/me/review-prompts whenever the user changes.
 * `dismissForSession` hides the banner for the current browser tab session only —
 * cleared on next login or new session.
 */
export function ReviewPromptProvider({ children }) {
  const { user, token } = useAuth();
  const [prompts, setPrompts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [dismissed, setDismissed] = useState(() => {
    try { return sessionStorage.getItem(DISMISS_KEY) === "1"; } catch { return false; }
  });
  const [modalOpen, setModalOpen] = useState(false);

  const refresh = useCallback(async () => {
    if (!user || !token) { setPrompts([]); return; }
    setLoading(true);
    try {
      const { data } = await api.get("/me/review-prompts", { headers: { Authorization: `Bearer ${token}` } });
      setPrompts(Array.isArray(data) ? data : []);
    } catch {
      setPrompts([]);
    } finally {
      setLoading(false);
    }
  }, [user, token]);

  useEffect(() => { refresh(); }, [refresh]);

  const dismissForSession = () => {
    try { sessionStorage.setItem(DISMISS_KEY, "1"); } catch {}
    setDismissed(true);
  };

  const removePromptById = (product_id) => {
    setPrompts((p) => p.filter((x) => x.product_id !== product_id));
  };

  const value = useMemo(
    () => ({ prompts, loading, refresh, dismissed, dismissForSession, modalOpen, setModalOpen, removePromptById }),
    [prompts, loading, refresh, dismissed, modalOpen],
  );

  return <ReviewPromptContext.Provider value={value}>{children}</ReviewPromptContext.Provider>;
}

export const useReviewPrompts = () => {
  const ctx = useContext(ReviewPromptContext);
  if (!ctx) throw new Error("useReviewPrompts must be used inside ReviewPromptProvider");
  return ctx;
};
