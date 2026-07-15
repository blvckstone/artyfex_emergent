import React, { useState } from "react";
import { Send, Loader2, Megaphone } from "lucide-react";
import { toast } from "sonner";

/**
 * BroadcastCard
 * Send a custom broadcast email to all customers.
 * Uses POST /api/admin/broadcast.
 */
export default function BroadcastCard({ authed }) {
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!subject.trim() || !body.trim()) { toast.error("Subject and body are required"); return; }
    if (!window.confirm("Send this email to ALL customers?")) return;
    setSending(true);
    try {
      const { data } = await authed.post("/admin/broadcast", {
        subject: subject.trim(),
        body_html: body.trim().replace(/\n/g, "<br/>"),
        audience: "all_customers",
      });
      toast.success(`Queued for ${data.queued} customer${data.queued === 1 ? "" : "s"}`);
      setSubject(""); setBody("");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to send");
    } finally { setSending(false); }
  };

  return (
    <form onSubmit={submit} data-testid="broadcast-card" className="hairline p-6 bg-ink-900">
      <div className="flex items-center gap-2 text-gold">
        <Megaphone className="w-4 h-4" />
        <h3 className="font-serif text-xl">Broadcast to customers</h3>
      </div>
      <p className="mt-1 text-xs text-cream/50">Send a bespoke atelier update to every registered customer.</p>

      <label className="block mt-5">
        <span className="text-[10px] uppercase tracking-luxury text-cream/50">Subject</span>
        <input required value={subject} onChange={(e) => setSubject(e.target.value)}
          placeholder="e.g. Diwali collection · limited pieces"
          className="mt-1 w-full bg-ink-950 border border-white/15 focus:border-gold px-3 py-2 text-sm text-cream outline-none"
          data-testid="broadcast-subject" />
      </label>
      <label className="block mt-4">
        <span className="text-[10px] uppercase tracking-luxury text-cream/50">Message</span>
        <textarea required rows={5} value={body} onChange={(e) => setBody(e.target.value)}
          placeholder="Dear collector, our atelier is releasing…"
          className="mt-1 w-full bg-ink-950 border border-white/15 focus:border-gold px-3 py-2 text-sm text-cream outline-none resize-y"
          data-testid="broadcast-body" />
      </label>
      <div className="mt-5 flex items-center justify-end">
        <button type="submit" disabled={sending} className="inline-flex items-center gap-2 bg-gold text-ink-950 px-5 py-2.5 text-xs uppercase tracking-luxury hover:bg-cream disabled:opacity-60" data-testid="broadcast-send">
          {sending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />} Send broadcast
        </button>
      </div>
    </form>
  );
}
