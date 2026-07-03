import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Package, RotateCcw, User, LogOut, Loader2 } from "lucide-react";
import { toast } from "sonner";

const formatINR = (n) => `₹${(n || 0).toLocaleString("en-IN")}`;

const statusColor = (s) => ({
  pending_payment: "text-yellow-400", confirmed: "text-blue-300", packed: "text-blue-300",
  shipped: "text-purple-300", delivered: "text-gold", cancelled: "text-red-400", payment_failed: "text-red-400",
}[s] || "text-cream");

export default function AccountPage() {
  const { user, ready, logout, openAuth, authedApi } = useAuth();
  const nav = useNavigate();
  const [tab, setTab] = useState("orders");
  const [orders, setOrders] = useState([]);
  const [returns, setReturns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [returnFor, setReturnFor] = useState(null);

  useEffect(() => {
    if (ready && !user) openAuth("login");
  }, [ready, user, openAuth]);

  useEffect(() => {
    if (!user) return;
    const a = authedApi();
    Promise.all([a.get("/me/orders"), a.get("/me/returns")])
      .then(([o, r]) => { setOrders(o.data); setReturns(r.data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user, authedApi]);

  if (!ready) return <div className="min-h-screen bg-ink-950" />;
  if (!user) {
    return (
      <div className="min-h-screen bg-ink-950 text-cream">
        <Navbar />
        <div className="pt-40 text-center px-6">
          <h1 className="font-serif text-4xl">Please sign in</h1>
          <p className="mt-4 text-cream/50">Access your orders, returns and reviews.</p>
          <button onClick={() => openAuth("login")} className="mt-8 bg-gold text-ink-950 px-6 py-4 text-xs uppercase tracking-luxury">Sign in</button>
        </div>
      </div>
    );
  }

  const tabs = [
    { key: "orders", label: "Orders", icon: Package },
    { key: "returns", label: "Returns", icon: RotateCcw },
    { key: "profile", label: "Profile", icon: User },
  ];

  const submitReturn = async (order_number, reason, details) => {
    try {
      const a = authedApi();
      const { data } = await a.post("/me/returns", { order_number, reason, details });
      setReturns([data, ...returns]);
      setReturnFor(null);
      toast.success("Return requested. Our atelier will contact you within 24h.");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Unable to submit return.");
    }
  };

  return (
    <div className="min-h-screen bg-ink-950 text-cream">
      <Navbar />
      <div className="max-w-[1200px] mx-auto px-6 md:px-12 lg:px-16 pt-32 pb-24">
        <div className="flex items-end justify-between flex-wrap gap-6">
          <div>
            <div className="text-[10px] uppercase tracking-luxury text-gold-soft">Your Atelier</div>
            <h1 className="font-serif text-4xl md:text-5xl mt-2">Hello, <span className="italic text-gold">{user.name.split(" ")[0]}</span></h1>
          </div>
          <button data-testid="account-logout" onClick={() => { logout(); nav("/"); }} className="text-xs uppercase tracking-luxury text-cream/60 hover:text-red-400 flex items-center gap-2"><LogOut className="w-3.5 h-3.5" />Sign out</button>
        </div>

        <div className="mt-10 flex gap-2 border-b border-white/5">
          {tabs.map((t) => (
            <button key={t.key} data-testid={`account-tab-${t.key}`} onClick={() => setTab(t.key)}
              className={`flex items-center gap-2 px-4 py-3 text-xs uppercase tracking-luxury border-b-2 -mb-px ${tab===t.key?"border-gold text-gold":"border-transparent text-cream/50"}`}>
              <t.icon className="w-3.5 h-3.5" />{t.label}
            </button>
          ))}
        </div>

        <div className="mt-10">
          {loading && <div className="text-cream/40 text-sm"><Loader2 className="w-4 h-4 animate-spin inline" /> Loading…</div>}

          {!loading && tab === "orders" && (
            <div className="grid gap-4">
              {orders.length === 0 && <div className="hairline p-10 text-center text-cream/40">No orders yet. <a href="/shop" className="text-gold hover:text-cream">Browse the collection →</a></div>}
              {orders.map((o) => (
                <div key={o.order_number} className="hairline p-6">
                  <div className="flex flex-wrap items-center gap-4">
                    <div>
                      <div className="text-gold font-mono text-sm">{o.order_number}</div>
                      <div className="text-xs text-cream/50">{new Date(o.created_at).toLocaleString()}</div>
                    </div>
                    <div className={`text-xs uppercase tracking-luxury ml-auto ${statusColor(o.status)}`}>{o.status.replace(/_/g, " ")}</div>
                    <div className="font-serif text-2xl text-cream">{formatINR(o.total_inr)}</div>
                  </div>
                  <div className="mt-3 text-xs text-cream/50">{o.items.length} item(s) · {o.customer.city}, {o.customer.pincode}</div>
                  {(o.status === "delivered" || o.status === "shipped") && (
                    <button data-testid={`return-${o.order_number}`} onClick={() => setReturnFor(o)} className="mt-4 text-xs uppercase tracking-luxury text-gold border-b border-gold/40 pb-0.5">Request return</button>
                  )}
                </div>
              ))}
            </div>
          )}

          {!loading && tab === "returns" && (
            <div className="grid gap-4">
              {returns.length === 0 && <div className="hairline p-10 text-center text-cream/40">No return requests.</div>}
              {returns.map((r) => (
                <div key={r.id} className="hairline p-6">
                  <div className="flex items-center gap-4">
                    <div className="text-gold font-mono text-sm">{r.order_number}</div>
                    <div className={`text-xs uppercase tracking-luxury ml-auto ${statusColor(r.status)}`}>{r.status}</div>
                  </div>
                  <div className="mt-2 text-sm"><span className="text-cream/50">Reason:</span> {r.reason}</div>
                  {r.details && <div className="mt-1 text-sm text-cream/70">"{r.details}"</div>}
                </div>
              ))}
            </div>
          )}

          {!loading && tab === "profile" && (
            <div className="hairline p-8 max-w-xl">
              <div className="grid sm:grid-cols-2 gap-6">
                <Info label="Name" value={user.name} />
                <Info label="Email" value={user.email} />
                <Info label="Phone" value={user.phone || "—"} />
              </div>
            </div>
          )}
        </div>
      </div>

      {returnFor && <ReturnDialog order={returnFor} onCancel={() => setReturnFor(null)} onSubmit={submitReturn} />}
      <Footer />
    </div>
  );
}

function Info({ label, value }) {
  return (<div><div className="text-[10px] uppercase tracking-luxury text-cream/50">{label}</div><div className="mt-1 text-cream">{value}</div></div>);
}

function ReturnDialog({ order, onCancel, onSubmit }) {
  const [reason, setReason] = useState("Product damaged in transit");
  const [details, setDetails] = useState("");
  return (
    <div className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4" onClick={onCancel}>
      <div className="bg-ink-900 border border-white/10 w-[min(500px,95vw)] p-8" onClick={(e)=>e.stopPropagation()}>
        <h3 className="font-serif text-2xl">Request return</h3>
        <div className="mt-1 text-xs text-cream/50">Order {order.order_number}</div>
        <div className="mt-6 space-y-4">
          <label className="block">
            <span className="text-[10px] uppercase tracking-luxury text-cream/50">Reason</span>
            <select value={reason} onChange={(e)=>setReason(e.target.value)} className="mt-1.5 w-full bg-ink-950 border border-white/15 focus:border-gold px-3 py-2.5 text-sm text-cream outline-none">
              {["Product damaged in transit","Not as described","Changed my mind","Wrong colour delivered","Other"].map(r=>(<option key={r} value={r} className="bg-ink-900">{r}</option>))}
            </select>
          </label>
          <label className="block">
            <span className="text-[10px] uppercase tracking-luxury text-cream/50">Details</span>
            <textarea rows={4} value={details} onChange={(e)=>setDetails(e.target.value)} className="mt-1.5 w-full bg-ink-950 border border-white/15 focus:border-gold px-3 py-2.5 text-sm text-cream outline-none" />
          </label>
        </div>
        <div className="mt-6 flex gap-3">
          <button onClick={onCancel} className="flex-1 py-3 border border-white/15 text-xs uppercase tracking-luxury">Cancel</button>
          <button onClick={()=>onSubmit(order.order_number, reason, details)} className="flex-1 bg-gold text-ink-950 py-3 text-xs uppercase tracking-luxury">Submit</button>
        </div>
      </div>
    </div>
  );
}
