import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

export default function AuthDialog() {
  const { dialogOpen, setDialogOpen, dialogMode, login, signup } = useAuth();
  const [mode, setMode] = useState(dialogMode);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", phone: "", password: "" });

  React.useEffect(() => { setMode(dialogMode); }, [dialogMode, dialogOpen]);

  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    if (loading) return; // guard against double-submit which used to leave the modal blank
    setLoading(true);
    try {
      if (mode === "login") await login(form.email, form.password);
      else await signup(form.name, form.email, form.password, form.phone);
      toast.success(`Welcome${mode === "signup" ? `, ${form.name}` : ""}`);
    } catch (err) {
      // Surface every possible shape of failure so the user never sees a "blackout" spinner forever.
      const detail = err?.response?.data?.detail;
      const status = err?.response?.status;
      const msg = (typeof detail === "string" && detail)
        || (Array.isArray(detail) && detail[0]?.msg)
        || (status === 429 ? "Too many attempts — please wait a minute and try again." : null)
        || err?.message
        || "Please check your details and try again.";
      // eslint-disable-next-line no-console
      console.error("[auth] submit failed", { status, detail, err });
      toast.error(msg);
    } finally { setLoading(false); }
  };

  return (
    <AnimatePresence>
      {dialogOpen && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setDialogOpen(false)} className="fixed inset-0 z-[95] bg-black/80 backdrop-blur-sm" />
          <div className="fixed inset-0 z-[110] flex items-center justify-center p-4 pointer-events-none">
            <motion.div data-testid="auth-dialog"
              initial={{ opacity: 0, y: 20, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 20, scale: 0.98 }}
              className="relative w-[min(440px,95vw)] max-h-[92vh] overflow-y-auto bg-ink-900 border border-white/10 pointer-events-auto p-10">
              <button onClick={() => setDialogOpen(false)} className="absolute top-4 right-4 p-2 border border-white/10 hover:border-gold/50">
                <X className="w-4 h-4 text-cream" />
              </button>
              <div className="text-[10px] uppercase tracking-luxury text-gold-soft">ArtyFex Atelier</div>
              <h2 className="font-serif text-3xl text-cream mt-2">{mode === "login" ? "Welcome back" : "Create your account"}</h2>
              <p className="mt-2 text-sm text-cream/50 font-light">
                {mode === "login" ? "Access your orders, returns and collector reviews." : "Track orders, submit reviews, and save your details for future acquisitions."}
              </p>

              <form onSubmit={submit} className="mt-8 space-y-5">
                {mode === "signup" && (
                  <F label="Full name"><input required data-testid="auth-name" value={form.name} onChange={upd("name")} className={inp} /></F>
                )}
                <F label="Email"><input required type="email" data-testid="auth-email" value={form.email} onChange={upd("email")} className={inp} /></F>
                {mode === "signup" && (
                  <F label="Phone (optional)"><input data-testid="auth-phone" value={form.phone} onChange={upd("phone")} className={inp} /></F>
                )}
                <F label="Password"><input required type="password" minLength={6} data-testid="auth-password" value={form.password} onChange={upd("password")} className={inp} /></F>

                <button type="submit" disabled={loading} data-testid="auth-submit"
                  className="w-full bg-gold text-ink-950 py-4 text-xs uppercase tracking-luxury hover:bg-cream disabled:opacity-60">
                  {loading ? <Loader2 className="w-4 h-4 animate-spin inline" /> : (mode === "login" ? "Sign in" : "Create account")}
                </button>
              </form>

              <div className="mt-6 flex items-center gap-3">
                <span className="flex-1 h-px bg-white/10" />
                <span className="text-[10px] uppercase tracking-luxury text-cream/40">or</span>
                <span className="flex-1 h-px bg-white/10" />
              </div>

              <button
                type="button"
                data-testid="auth-google"
                onClick={() => {
                  // Phase B: custom Google OAuth (server redirect flow).
                  // Backend derives redirect_uri from THIS request (works on prod/preview/local without env vars).
                  // We also pass `origin` so the callback knows exactly which front-end to bounce back to.
                  const backend = process.env.REACT_APP_BACKEND_URL || "";
                  const next = window.location.pathname + window.location.search;
                  const origin = window.location.origin;
                  const url = `${backend}/api/auth/google/login?next=${encodeURIComponent(next)}&origin=${encodeURIComponent(origin)}`;
                  window.location.href = url;
                }}
                className="mt-4 w-full flex items-center justify-center gap-3 border border-white/15 bg-white text-ink-950 py-4 text-xs uppercase tracking-luxury hover:bg-cream transition-colors"
              >
                <GoogleGlyph className="w-4 h-4" />
                Continue with Google
              </button>

              <div className="mt-6 text-sm text-center text-cream/50">
                {mode === "login" ? (
                  <>New to ArtyFex? <button data-testid="auth-switch-signup" onClick={() => setMode("signup")} className="text-gold hover:text-cream">Create an account</button></>
                ) : (
                  <>Already have an account? <button data-testid="auth-switch-login" onClick={() => setMode("login")} className="text-gold hover:text-cream">Sign in</button></>
                )}
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}
const inp = "w-full bg-ink-950 border border-white/15 focus:border-gold outline-none px-3 py-2.5 text-sm text-cream";
const F = ({ label, children }) => (<label className="block"><span className="text-[10px] uppercase tracking-luxury text-cream/50">{label}</span><div className="mt-1.5">{children}</div></label>);

const GoogleGlyph = ({ className = "" }) => (
  <svg viewBox="0 0 24 24" className={className} xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
    <path d="M5.84 14.1c-.22-.66-.35-1.36-.35-2.1s.13-1.44.35-2.1V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.83z" fill="#FBBC05"/>
    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.83C6.71 7.31 9.14 5.38 12 5.38z" fill="#EA4335"/>
  </svg>
);
