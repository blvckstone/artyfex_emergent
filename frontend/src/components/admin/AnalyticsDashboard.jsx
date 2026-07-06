import React, { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import {
  Package, ShoppingBag, IndianRupee, Users, AlertTriangle, RotateCcw,
  CheckCircle2, XCircle, TrendingUp, Star, Activity, Eye, Loader2, RefreshCw, Boxes, Ticket,
} from "lucide-react";

const formatINR = (n) => `₹${(Number(n) || 0).toLocaleString("en-IN")}`;

function KpiCard({ icon: Icon, label, value, sub, tone = "cream", testid }) {
  const toneCls = { gold: "text-gold", red: "text-red-400", emerald: "text-emerald-400", cream: "text-cream" }[tone] || "text-cream";
  return (
    <div className="hairline p-5 bg-ink-900/50" data-testid={testid}>
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-luxury text-cream/50">
        <Icon className="w-3.5 h-3.5 text-gold" /> {label}
      </div>
      <div className={`mt-3 font-serif text-3xl ${toneCls}`}>{value}</div>
      {sub && <div className="mt-1 text-[11px] text-cream/40">{sub}</div>}
    </div>
  );
}

function MiniChart({ series }) {
  // Simple SVG bar chart for 30-day orders + revenue
  if (!series || !series.length) return null;
  const maxOrders = Math.max(1, ...series.map((s) => s.orders));
  const maxRevenue = Math.max(1, ...series.map((s) => s.revenue_inr));
  const W = 640, H = 160, PAD = 24;
  const barW = (W - PAD * 2) / series.length - 3;
  return (
    <div className="hairline p-5 bg-ink-900/50">
      <div className="flex items-center justify-between mb-3">
        <div className="text-[10px] uppercase tracking-luxury text-gold-soft">Last 30 days</div>
        <div className="text-[10px] text-cream/40 flex gap-3">
          <span className="inline-flex items-center gap-1"><span className="w-2 h-2 bg-gold inline-block" /> revenue</span>
          <span className="inline-flex items-center gap-1"><span className="w-2 h-2 bg-cream/40 inline-block" /> orders</span>
        </div>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
        {series.map((s, i) => {
          const hR = ((s.revenue_inr / maxRevenue) * (H - PAD * 2)) || 1;
          const hO = ((s.orders / maxOrders) * (H - PAD * 2)) || 0;
          const x = PAD + i * (barW + 3);
          const yR = H - PAD - hR;
          const yO = H - PAD - hO;
          return (
            <g key={s.date}>
              <title>{`${s.date}: ₹${s.revenue_inr.toLocaleString("en-IN")} · ${s.orders} orders`}</title>
              <rect x={x} y={yR} width={barW} height={hR} fill="#D4AF37" opacity="0.85" />
              <rect x={x + barW / 2 - 1} y={yO} width={2} height={hO} fill="#f5efdf" opacity="0.5" />
            </g>
          );
        })}
        <line x1={PAD} x2={W - PAD} y1={H - PAD} y2={H - PAD} stroke="#333" strokeWidth="0.5" />
      </svg>
      <div className="mt-1 flex justify-between text-[9px] text-cream/40">
        <span>{series[0]?.date?.slice(5)}</span>
        <span>{series[Math.floor(series.length / 2)]?.date?.slice(5)}</span>
        <span>{series[series.length - 1]?.date?.slice(5)}</span>
      </div>
    </div>
  );
}

function AlertsPanel({ alerts }) {
  if (!alerts) return null;
  const lowStock = alerts.low_stock_products || [];
  const oldPending = alerts.old_pending_returns || [];
  const failed = alerts.recent_failed_payments_1h || 0;
  const total = lowStock.length + oldPending.length + (failed > 0 ? 1 : 0);

  return (
    <div className="hairline p-5 bg-ink-900/50">
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle className="w-4 h-4 text-gold" />
        <div className="text-[10px] uppercase tracking-luxury text-gold-soft">System alerts</div>
        <span className="ml-auto text-xs text-cream/40">{total} active</span>
      </div>
      {total === 0 && <div className="text-sm text-cream/40 py-4">All clear — nothing needs your attention right now.</div>}
      <div className="space-y-3">
        {lowStock.length > 0 && (
          <div className="border-l-2 border-yellow-400/70 pl-3">
            <div className="text-xs text-yellow-400 uppercase tracking-luxury">{lowStock.length} low-stock product{lowStock.length === 1 ? "" : "s"}</div>
            <div className="mt-2 space-y-1">
              {lowStock.map((p) => (
                <div key={p.id} className="flex items-center gap-3 text-sm" data-testid={`alert-lowstock-${p.id}`}>
                  {p.image && <img src={p.image} alt="" className="w-8 h-8 object-cover" />}
                  <span className="text-cream/80 flex-1">{p.name}</span>
                  <span className={`text-xs font-mono ${p.stock_count <= 0 ? "text-red-400" : "text-yellow-400"}`}>
                    {p.stock_count <= 0 ? "OUT OF STOCK" : `${p.stock_count} left`}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
        {oldPending.length > 0 && (
          <div className="border-l-2 border-orange-400/70 pl-3">
            <div className="text-xs text-orange-400 uppercase tracking-luxury">{oldPending.length} return{oldPending.length === 1 ? "" : "s"} awaiting action &gt;48h</div>
            <div className="mt-2 space-y-1 text-xs text-cream/60">
              {oldPending.map((r) => (
                <div key={r.id}>{r.order_number} · {r.hours_old}h old</div>
              ))}
            </div>
          </div>
        )}
        {failed > 0 && (
          <div className="border-l-2 border-red-400/70 pl-3">
            <div className="text-xs text-red-400 uppercase tracking-luxury">{failed} failed payment{failed === 1 ? "" : "s"} in the last hour</div>
          </div>
        )}
      </div>
    </div>
  );
}

function LivePanel({ authed }) {
  const [live, setLive] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await authed.get("/admin/analytics/live");
      setLive(data);
    } catch { /* silent */ } finally { setLoading(false); }
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="hairline p-5 bg-ink-900/50" data-testid="live-panel">
      <div className="flex items-center gap-2 mb-3">
        <Activity className="w-4 h-4 text-emerald-400" />
        <div className="text-[10px] uppercase tracking-luxury text-gold-soft">Live analytics</div>
        <button onClick={load} className="ml-auto p-1 text-cream/40 hover:text-cream"><RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} /></button>
      </div>
      <div className="flex items-baseline gap-3">
        <div className="font-serif text-5xl text-emerald-400" data-testid="live-active-users">{live?.active_users ?? "–"}</div>
        <div className="text-xs text-cream/50">active users right now</div>
      </div>
      {live?.sessions_now_by_path?.length > 0 && (
        <div className="mt-4">
          <div className="text-[10px] uppercase tracking-luxury text-cream/40 mb-2">Now viewing</div>
          <div className="space-y-1">
            {live.sessions_now_by_path.slice(0, 5).map((p) => (
              <div key={p.path} className="flex justify-between text-xs">
                <span className="text-cream/70 truncate">{p.path}</span>
                <span className="text-cream/40 font-mono">{p.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {live?.top_pages_24h?.length > 0 && (
        <div className="mt-4 pt-4 border-t border-white/5">
          <div className="text-[10px] uppercase tracking-luxury text-cream/40 mb-2">Top pages · last 24h</div>
          <div className="space-y-1">
            {live.top_pages_24h.slice(0, 6).map((p) => (
              <div key={p.path} className="flex justify-between text-xs">
                <span className="text-cream/70 truncate">{p.path}</span>
                <span className="text-cream/40 font-mono">{p.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {live?.as_of && (
        <div className="mt-3 text-[10px] text-cream/30">as of {new Date(live.as_of).toLocaleTimeString()}</div>
      )}
    </div>
  );
}

export default function AnalyticsDashboard({ authed }) {
  const [data, setData] = useState(null);
  const [alerts, setAlerts] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [o, a] = await Promise.all([
        authed.get("/admin/analytics/overview"),
        authed.get("/admin/analytics/alerts"),
      ]);
      setData(o.data);
      setAlerts(a.data);
    } catch (err) {
      toast.error("Analytics unavailable");
    } finally { setLoading(false); }
  };

  useEffect(() => { if (authed) load(); /* eslint-disable-next-line */ }, [authed]);

  if (loading && !data) return <div className="text-cream/40 text-sm"><Loader2 className="w-4 h-4 animate-spin inline" /> Crunching numbers…</div>;
  if (!data) return null;

  const o = data.orders, r = data.returns, f = data.financials;

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-serif text-4xl">Dashboard</h1>
          <p className="mt-2 text-sm text-cream/50">A live pulse of the atelier.</p>
        </div>
        <button onClick={load} className="inline-flex items-center gap-2 text-xs uppercase tracking-luxury text-cream/60 border border-white/15 px-4 py-2 hover:border-gold hover:text-gold">
          <RefreshCw className="w-3 h-3" /> Refresh
        </button>
      </div>

      {/* KPI row 1 — Orders */}
      <div>
        <div className="text-[10px] uppercase tracking-luxury text-cream/40 mb-2">Orders & Returns</div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <KpiCard testid="kpi-orders-total" icon={ShoppingBag} label="Total orders" value={o.total} tone="cream" />
          <KpiCard testid="kpi-orders-active" icon={TrendingUp} label="Active" value={o.active} tone="gold" />
          <KpiCard testid="kpi-orders-success" icon={CheckCircle2} label="Delivered" value={o.successful} tone="emerald" />
          <KpiCard testid="kpi-orders-cancelled" icon={XCircle} label="Cancelled" value={o.cancelled} tone="red" />
          <KpiCard testid="kpi-returns-active" icon={RotateCcw} label="Active returns" value={r.active} tone="gold" />
          <KpiCard testid="kpi-returns-done" icon={CheckCircle2} label="Returns completed" value={r.completed} tone="emerald" />
        </div>
      </div>

      {/* KPI row 2 — Financials */}
      <div>
        <div className="text-[10px] uppercase tracking-luxury text-cream/40 mb-2">Financials & Inventory</div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <KpiCard testid="kpi-revenue" icon={IndianRupee} label="Total revenue" value={formatINR(f.revenue_inr)} tone="gold" />
          <KpiCard testid="kpi-products" icon={Boxes} label="Products" value={f.products_total} />
          <KpiCard testid="kpi-customers" icon={Users} label="Customers" value={f.customers_total} />
          <KpiCard testid="kpi-b2b" icon={Users} label="New B2B leads" value={f.b2b_leads_new} sub="last 30 days" />
          <KpiCard testid="kpi-failed" icon={AlertTriangle} label="Failed transactions" value={f.failed_transactions} tone="red" />
        </div>
      </div>

      {/* Chart + Live + Alerts */}
      <div className="grid lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2"><MiniChart series={data.series_30d} /></div>
        <LivePanel authed={authed} />
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <AlertsPanel alerts={alerts} />

        {/* Top products */}
        <div className="hairline p-5 bg-ink-900/50">
          <div className="flex items-center gap-2 mb-3">
            <Star className="w-4 h-4 text-gold" />
            <div className="text-[10px] uppercase tracking-luxury text-gold-soft">Top performing pieces</div>
          </div>
          <div className="space-y-2">
            {(data.top_products || []).map((p) => (
              <div key={p.id} className="flex items-center gap-3 border-b border-white/5 pb-2 last:border-b-0" data-testid={`top-product-${p.id}`}>
                {p.image && <img src={p.image} alt="" className="w-12 h-12 object-cover" />}
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-cream truncate">{p.name}</div>
                  <div className="text-[11px] text-cream/50 flex gap-3">
                    <span>{p.orders} orders</span>
                    <span>{formatINR(p.revenue_inr)}</span>
                    {p.review_count > 0 && <span className="text-gold">★ {p.avg_rating} ({p.review_count})</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Coupons summary */}
      {data.coupons_summary?.length > 0 && (
        <div className="hairline p-5 bg-ink-900/50">
          <div className="flex items-center gap-2 mb-3">
            <Ticket className="w-4 h-4 text-gold" />
            <div className="text-[10px] uppercase tracking-luxury text-gold-soft">Coupon uses</div>
          </div>
          <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-2">
            {data.coupons_summary.map((c) => (
              <div key={c.code} className="border border-white/10 p-3 flex items-center justify-between" data-testid={`coupon-total-${c.code}`}>
                <span className="font-mono text-sm text-gold">{c.code}</span>
                <span className="text-cream/70 text-xs">{c.uses} uses</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
