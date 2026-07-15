import React, { useState } from "react";
import { X, Send, Loader2 } from "lucide-react";
import { toast } from "sonner";

/**
 * OrderNotifyDialog
 * Send a custom admin email to a specific order's customer.
 * Uses POST /api/admin/orders/{n}/notify.
 */
export default function OrderNotifyDialog({ authed, order, onClose }) {
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);

  if (!order) return null;
  const customer = order.customer || {};

  const submit = async (e) => {
    e.preventDefault();
    if (!subject.trim() || !body.trim()) { toast.error("Subject and body are required"); return; }
    setSending(true);
    try {
      await authed.post(`/admin/orders/${order.order_number}/notify`, {
        subject: subject.trim(),
        body_html: body.trim().replace(/\n/g, "<br/>"),
      });
      toast.success(`Email queued for ${customer.email || "customer"}`);
      onClose();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to send");
    } finally { setSending(false); }
  };

  return (
    <div className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4" role="dialog" data-testid="order-notify-dialog">
      <form onSubmit={submit} className="w-full max-w-lg hairline bg-ink-900 p-6">
        <div className="flex items-center gap-3">
          <div className="flex-1 min-w-0">
            <div className="text-[10px] uppercase tracking-luxury text-gold">Send custom update</div>
            <h2 className="font-serif text-2xl text-cream mt-0.5">To {customer.name || customer.email}</h2>
            <div className="text-xs text-cream/50 mt-1">Order · <span className="font-mono text-gold">{order.order_number}</span></div>
          </div>
          <button type="button" onClick={onClose} className="text-cream/60 hover:text-cream p-1"><X className="w-4 h-4" /></button>
        </div>
        <label className="block mt-5">
          <span className="text-[10px] uppercase tracking-luxury text-cream/50">Subject</span>
          <input
            required
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="e.g. Small update on your order"
            className="mt-1 w-full bg-ink-950 border border-white/15 focus:border-gold px-3 py-2 text-sm text-cream outline-none"
            data-testid="notify-subject"
          />
        </label>
        <label className="block mt-4">
          <span className="text-[10px] uppercase tracking-luxury text-cream/50">Message</span>
          <textarea
            required
            rows={6}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Dear customer, we wanted to let you know…"
            className="mt-1 w-full bg-ink-950 border border-white/15 focus:border-gold px-3 py-2 text-sm text-cream outline-none resize-y"
            data-testid="notify-body"
          />
        </label>
        <div className="mt-6 flex items-center justify-end gap-2">
          <button type="button" onClick={onClose} className="text-xs uppercase tracking-luxury text-cream/60 hover:text-cream px-4 py-2">Cancel</button>
          <button type="submit" disabled={sending} className="inline-flex items-center gap-2 bg-gold text-ink-950 px-5 py-2.5 text-xs uppercase tracking-luxury hover:bg-cream disabled:opacity-60" data-testid="notify-submit">
            {sending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />} Send email
          </button>
        </div>
      </form>
    </div>
  );
}
