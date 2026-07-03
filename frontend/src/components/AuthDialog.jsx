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
    setLoading(true);
    try {
      if (mode === "login") await login(form.email, form.password);
      else await signup(form.name, form.email, form.password, form.phone);
      toast.success(`Welcome${mode === "signup" ? `, ${form.name}` : ""}`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Please check your credentials.");
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
