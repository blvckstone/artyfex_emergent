import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, AlertCircle } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

/**
 * AuthCallback
 * ------------
 * Landed here after Emergent Google OAuth redirect. The session_id arrives in the URL
 * fragment (e.g. `#session_id=xxxx`). We exchange it server-side for our own JWT.
 *
 * REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
 */
export default function AuthCallback() {
  const navigate = useNavigate();
  const { applyGoogleSession } = useAuth();
  const hasProcessed = useRef(false);
  const [error, setError] = useState("");

  useEffect(() => {
    // Guard against React StrictMode double-invoke — synchronously mark processed
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const parseFragment = () => {
      const raw = window.location.hash?.startsWith("#") ? window.location.hash.slice(1) : window.location.hash;
      if (!raw) return {};
      const params = new URLSearchParams(raw);
      const obj = {};
      params.forEach((v, k) => { obj[k] = v; });
      return obj;
    };

    const run = async () => {
      const { session_id } = parseFragment();
      if (!session_id) {
        setError("Missing session — please try signing in again.");
        return;
      }
      try {
        const { data } = await api.post("/auth/google/session", { session_id });
        applyGoogleSession(data.token, data.user);
        toast.success(`Welcome, ${data.user?.name?.split(" ")[0] || "friend"}`);
        // Clean the fragment before navigating so a refresh does not re-process
        window.history.replaceState({}, document.title, window.location.pathname);
        navigate("/account", { replace: true });
      } catch (err) {
        const msg = err?.response?.data?.detail || err?.message || "Could not sign you in with Google.";
        setError(msg);
        toast.error(msg);
      }
    };
    run();
  }, [applyGoogleSession, navigate]);

  return (
    <div className="min-h-screen bg-ink-950 text-cream flex items-center justify-center p-6">
      <div className="max-w-md w-full text-center">
        {error ? (
          <>
            <div className="inline-flex p-3 border border-red-400/40 mb-6">
              <AlertCircle className="w-6 h-6 text-red-400" />
            </div>
            <h1 className="font-serif text-3xl">Sign-in failed</h1>
            <p className="mt-3 text-sm text-cream/60">{error}</p>
            <button
              onClick={() => navigate("/", { replace: true })}
              className="mt-8 inline-flex text-xs uppercase tracking-luxury text-gold border-b border-gold/40 pb-1"
            >
              Return home
            </button>
          </>
        ) : (
          <>
            <Loader2 className="w-8 h-8 text-gold animate-spin mx-auto" />
            <h1 className="mt-6 font-serif text-3xl">Signing you in…</h1>
            <p className="mt-3 text-sm text-cream/50">One moment while we open your atelier.</p>
          </>
        )}
      </div>
    </div>
  );
}
