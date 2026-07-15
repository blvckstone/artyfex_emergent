import React, { useEffect, useState } from "react";
import { Plus, Trash2, ShieldCheck, Loader2, Mail } from "lucide-react";
import { toast } from "sonner";

/**
 * WhitelistCard
 *
 * Admin Settings card that lists whitelisted Google accounts allowed to log
 * into the Admin Panel via "Continue with Google". Built-in owner emails
 * (iblvckstone@gmail.com, virusisstandhere@gmail.com) are shown as readonly.
 */
export default function WhitelistCard({ authed }) {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newEmail, setNewEmail] = useState("");
  const [newNote, setNewNote] = useState("");
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await authed.get("/admin/whitelist");
      setEntries(data || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to load whitelist");
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const addEntry = async (e) => {
    e.preventDefault();
    if (!newEmail.trim()) return;
    setSaving(true);
    try {
      await authed.post("/admin/whitelist", { email: newEmail.trim().toLowerCase(), note: newNote.trim() });
      setNewEmail(""); setNewNote("");
      toast.success("Email whitelisted");
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to whitelist");
    } finally { setSaving(false); }
  };

  const remove = async (wl) => {
    if (wl.readonly) { toast.error("Built-in owner emails cannot be removed"); return; }
    if (!window.confirm(`Remove ${wl.email} from admin whitelist?`)) return;
    try {
      await authed.delete(`/admin/whitelist/${wl.id}`);
      toast.success("Removed");
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to remove");
    }
  };

  return (
    <div data-testid="admin-whitelist-card" className="hairline p-6 bg-ink-900">
      <div className="flex items-center gap-2 text-gold">
        <ShieldCheck className="w-4 h-4" />
        <h3 className="font-serif text-xl">Admin Google Access</h3>
      </div>
      <p className="mt-1 text-xs text-cream/50">
        Only these Google accounts can sign in via <span className="text-gold">Continue with Google</span> on the admin login page.
      </p>

      <form onSubmit={addEntry} className="mt-5 grid sm:grid-cols-[1fr_1fr_auto] gap-2 items-end">
        <label className="block">
          <span className="text-[10px] uppercase tracking-luxury text-cream/50">Email</span>
          <input
            type="email"
            required
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
            placeholder="admin@example.com"
            className="mt-1 w-full bg-ink-950 border border-white/15 focus:border-gold px-3 py-2 text-sm text-cream outline-none"
            data-testid="whitelist-email-input"
          />
        </label>
        <label className="block">
          <span className="text-[10px] uppercase tracking-luxury text-cream/50">Note (optional)</span>
          <input
            type="text"
            value={newNote}
            onChange={(e) => setNewNote(e.target.value)}
            placeholder="Ops lead"
            className="mt-1 w-full bg-ink-950 border border-white/15 focus:border-gold px-3 py-2 text-sm text-cream outline-none"
            data-testid="whitelist-note-input"
          />
        </label>
        <button
          type="submit"
          disabled={saving}
          className="px-4 py-2 bg-gold text-ink-950 hover:bg-cream text-xs uppercase tracking-luxury disabled:opacity-60 inline-flex items-center gap-2"
          data-testid="whitelist-add-btn"
        >
          {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />} Whitelist
        </button>
      </form>

      <div className="mt-6 space-y-2">
        {loading ? (
          <div className="text-xs text-cream/40">Loading…</div>
        ) : entries.length === 0 ? (
          <div className="text-xs text-cream/40 italic">No emails whitelisted yet.</div>
        ) : (
          entries.map((wl) => (
            <div key={wl.id} className="flex items-center gap-3 border border-white/5 px-3 py-2" data-testid={`whitelist-row-${wl.email}`}>
              <Mail className="w-3.5 h-3.5 text-gold/70" />
              <div className="flex-1 min-w-0">
                <div className="text-sm text-cream truncate">{wl.email}</div>
                {wl.note && <div className="text-[10px] text-cream/40 truncate">{wl.note}</div>}
              </div>
              {wl.readonly && (
                <span className="text-[10px] uppercase tracking-luxury text-gold/60 border border-gold/30 px-2 py-0.5">Built-in</span>
              )}
              {!wl.readonly && (
                <button
                  type="button"
                  onClick={() => remove(wl)}
                  className="text-red-400/70 hover:text-red-400 p-1"
                  data-testid={`whitelist-remove-${wl.email}`}
                  aria-label="Remove"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
