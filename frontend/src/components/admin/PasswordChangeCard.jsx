import React, { useState } from "react";
import { toast } from "sonner";
import { Loader2, Lock } from "lucide-react";

const inp = "w-full bg-ink-950 border border-white/15 focus:border-gold focus:outline-none px-3 py-2.5 text-sm text-cream outline-none";

export default function PasswordChangeCard({ authed }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [saving, setSaving] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (next !== confirm) { toast.error("New passwords do not match"); return; }
    if (next.length < 8) { toast.error("New password must be at least 8 characters"); return; }
    setSaving(true);
    try {
      await authed.patch("/admin/me/password", { current_password: current, new_password: next });
      toast.success("Password updated — next login will use the new password");
      setCurrent(""); setNext(""); setConfirm("");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Password change failed");
    } finally { setSaving(false); }
  };

  return (
    <form onSubmit={submit} className="hairline p-6 bg-ink-900/50 max-w-lg" data-testid="admin-password-card">
      <div className="flex items-center gap-2 mb-4">
        <Lock className="w-4 h-4 text-gold" />
        <div className="text-[10px] uppercase tracking-luxury text-gold-soft">Reset admin password</div>
      </div>
      <div className="space-y-3">
        <label className="block"><span className="text-[10px] uppercase tracking-luxury text-cream/50">Current password</span><input type="password" data-testid="admin-pw-current" required value={current} onChange={(e) => setCurrent(e.target.value)} className={`${inp} mt-1.5`} /></label>
        <label className="block"><span className="text-[10px] uppercase tracking-luxury text-cream/50">New password</span><input type="password" data-testid="admin-pw-new" required value={next} onChange={(e) => setNext(e.target.value)} className={`${inp} mt-1.5`} /></label>
        <label className="block"><span className="text-[10px] uppercase tracking-luxury text-cream/50">Confirm new password</span><input type="password" data-testid="admin-pw-confirm" required value={confirm} onChange={(e) => setConfirm(e.target.value)} className={`${inp} mt-1.5`} /></label>
      </div>
      <button data-testid="admin-pw-submit" type="submit" disabled={saving} className="mt-6 inline-flex items-center gap-2 bg-gold text-ink-950 px-6 py-3 text-xs uppercase tracking-luxury hover:bg-cream disabled:opacity-60">
        {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Lock className="w-3.5 h-3.5" />}
        {saving ? "Saving…" : "Update password"}
      </button>
    </form>
  );
}
