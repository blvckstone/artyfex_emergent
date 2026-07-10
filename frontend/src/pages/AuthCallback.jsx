import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, AlertCircle } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

/**
 * AuthCallback
 * ------------
 * Landing route after our custom Google OAuth flow (Phase B).
 * The backend redirects here with a URL fragment like:
 *   #token=<jwt>&email=...&name=...&picture=...&next=/account
 * or on failure:
 *   #error=<code>
 *
 * We parse it, hand the JWT to AuthContext, then bounce to `next` (default /account).
 */
export default function AuthCallback() {
  const navigate = useNavigate();
  const { applyGoogleSession } = useAuth();
  const hasProcessed = useRef(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const raw = window.location.hash?.startsWith("#") ? window.location.hash.slice(1) : window.location.hash;
    if (!raw) {
      setError("Missing session — please try signing in again.");
      return;
    }

    const params = new URLSearchParams(raw);
    const errCode = params.get("error");
    if (errCode) {
      const map = {
        missing_code: "Google did not return an authorisation code.",
        invalid_state: "Sign-in link expired. Please try again.",
        token_exchange_failed: "Google rejected the sign-in. Please try again.",
        no_email: "Your Google account did not share an email.",
        server_not_configured: "Google sign-in is not yet configured on the server.",
      };
      const msg = map[errCode] || `Sign-in failed (${errCode}).`;
      setError(msg);
      toast.error(msg);
      return;
    }

    const token = params.get("token");
    const email = params.get("email");
    const name = params.get("name") || "";
    const picture = params.get("picture") || "";
    const next = params.get("next") || "/account";

    if (!token || !email) {
      setError("Missing token — please try signing in again.");
      return;
    }

    applyGoogleSession(token, { name, email, phone: "", picture });
    toast.success(`Welcome, ${(name && name.split(" ")[0]) || "friend"}`);
    // Clean the fragment so a refresh does not re-process.
    window.history.replaceState({}, document.title, window.location.pathname);
    navigate(next, { replace: true });
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
