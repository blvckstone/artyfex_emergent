import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast, Toaster } from "sonner";
import { LogOut, Package, ShoppingBag, Users, Star, LayoutGrid, Plus, Trash2, Loader2, RotateCcw } from "lucide-react";

const TOKEN_KEY = "artyfex_admin_token";

const formatINR = (n) => `₹${(n || 0).toLocaleString("en-IN")}`;

function LoginView({ onLogin }) {
  const [email, setEmail] = useState("admin@artyfex.in");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post("/admin/login", { email, password });
      localStorage.setItem(TOKEN_KEY, data.token);
      onLogin(data.token);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Invalid credentials");
    } finally { setLoading(false); }
  };
  return (
    <div className="min-h-screen bg-ink-950 flex items-center justify-center p-6">
      <form onSubmit={submit} className="w-full max-w-md hairline p-10 bg-ink-900">
        <div className="text-[10px] uppercase tracking-luxury text-gold-soft">ArtyFex</div>
        <h1 className="mt-2 font-serif text-4xl text-cream">Atelier <span className="italic text-gold">Admin</span></h1>
        <div className="mt-8 space-y-5">
          <label className="block">
            <span className="text-[10px] uppercase tracking-luxury text-cream/50">Email</span>
            <input data-testid="admin-login-email" required type="email" value={email} onChange={(e)=>setEmail(e.target.value)}
              className="mt-1.5 w-full bg-ink-950 border border-white/15 focus:border-gold px-3 py-2.5 text-sm text-cream outline-none" />
          </label>
          <label className="block">
            <span className="text-[10px] uppercase tracking-luxury text-cream/50">Password</span>
            <input data-testid="admin-login-password" required type="password" value={password} onChange={(e)=>setPassword(e.target.value)}
              className="mt-1.5 w-full bg-ink-950 border border-white/15 focus:border-gold px-3 py-2.5 text-sm text-cream outline-none" />
          </label>
        </div>
        <button data-testid="admin-login-submit" disabled={loading} className="mt-8 w-full bg-gold text-ink-950 py-4 text-xs uppercase tracking-luxury hover:bg-cream disabled:opacity-60">
          {loading ? "Signing in…" : "Sign in to atelier"}
        </button>
      </form>
    </div>
  );
}

function useAuthedApi(token) {
  return React.useMemo(() => {
    const inst = api.create ? api.create() : api;
    // set header for this axios instance
    inst.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    return inst;
  }, [token]);
}

const empty = { slug: "", name: "", tagline: "", description: "", price_inr: 0, mrp_inr: 0, size: "", craft_hours: 24, materials: "", hero_image: "", gallery: "", variants: '[{"key":"gold","label":"Gold","hex":"#D4AF37","image":""}]', stock: 5, is_hero: false };

export default function AdminPage() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || "");
  const [tab, setTab] = useState("dashboard");
  const [stats, setStats] = useState(null);
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [leads, setLeads] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [returns, setReturns] = useState([]);
  const [editing, setEditing] = useState(null); // null | product obj | "new"
  const [saving, setSaving] = useState(false);

  const authed = useAuthedApi(token);

  const reload = React.useCallback(async () => {
    if (!token) return;
    try {
      const [s, p, o, l, r, rt] = await Promise.all([
        authed.get("/admin/stats"), authed.get("/products"),
        authed.get("/admin/orders"), authed.get("/admin/leads"), authed.get("/reviews"),
        authed.get("/admin/returns"),
      ]);
      setStats(s.data); setProducts(p.data); setOrders(o.data); setLeads(l.data); setReviews(r.data); setReturns(rt.data);
    } catch (err) {
      if (err?.response?.status === 401) { localStorage.removeItem(TOKEN_KEY); setToken(""); }
    }
  }, [token, authed]);

  useEffect(() => { reload(); }, [reload]);

  if (!token) return (<><LoginView onLogin={setToken} /><Toaster theme="dark" position="bottom-center" /></>);

  const logout = () => { localStorage.removeItem(TOKEN_KEY); setToken(""); };

  const saveProduct = async (form) => {
    setSaving(true);
    try {
      const payload = {
        ...form,
        price_inr: Number(form.price_inr), mrp_inr: Number(form.mrp_inr),
        craft_hours: Number(form.craft_hours), stock: Number(form.stock),
        materials: typeof form.materials === "string" ? form.materials.split("\n").map(s=>s.trim()).filter(Boolean) : form.materials,
        gallery: typeof form.gallery === "string" ? form.gallery.split("\n").map(s=>s.trim()).filter(Boolean) : form.gallery,
        variants: typeof form.variants === "string" ? JSON.parse(form.variants) : form.variants,
      };
      if (form.id) await authed.put(`/admin/products/${form.id}`, payload);
      else await authed.post("/admin/products", payload);
      toast.success("Product saved");
      setEditing(null); reload();
    } catch (err) {
      toast.error(err?.response?.data?.detail?.[0]?.msg || err?.response?.data?.detail || "Save failed");
    } finally { setSaving(false); }
  };

  const deleteProduct = async (id) => {
    if (!window.confirm("Delete this product?")) return;
    await authed.delete(`/admin/products/${id}`);
    toast.success("Deleted"); reload();
  };

  const updateOrderStatus = async (num, status) => {
    await authed.patch(`/admin/orders/${num}`, { status });
    toast.success(`Order → ${status}`); reload();
  };

  const updateLeadStatus = async (id, status) => {
    await authed.patch(`/admin/leads/${id}`, { status });
    reload();
  };

  const tabs = [
    { key: "dashboard", label: "Dashboard", icon: LayoutGrid },
    { key: "products", label: "Products", icon: Package },
    { key: "orders", label: "Orders", icon: ShoppingBag },
    { key: "returns", label: "Returns", icon: RotateCcw },
    { key: "leads", label: "B2B Leads", icon: Users },
    { key: "reviews", label: "Reviews", icon: Star },
  ];

  const updateReturnStatus = async (id, patch) => {
    try {
      await authed.patch(`/admin/returns/${id}`, patch);
      toast.success("Return updated");
      reload();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Update failed");
    }
  };

  return (
    <div className="min-h-screen bg-ink-950 text-cream flex">
      <aside className="w-60 border-r border-white/5 p-6 hidden md:flex flex-col">
        <div className="font-serif text-2xl">Arty<span className="italic text-gold">Fex</span></div>
        <div className="text-[10px] uppercase tracking-luxury text-cream/40 mt-1">Atelier Admin</div>
        <nav className="mt-10 flex flex-col gap-1">
          {tabs.map((t) => (
            <button key={t.key} data-testid={`admin-tab-${t.key}`} onClick={()=>setTab(t.key)}
              className={`flex items-center gap-3 px-3 py-2.5 text-sm transition-colors ${tab===t.key?"bg-gold/10 text-gold":"text-cream/60 hover:text-cream"}`}>
              <t.icon className="w-4 h-4" />{t.label}
            </button>
          ))}
        </nav>
        <button data-testid="admin-logout" onClick={logout} className="mt-auto flex items-center gap-2 text-xs text-cream/50 hover:text-red-400"><LogOut className="w-4 h-4" />Sign out</button>
      </aside>

      <main className="flex-1 p-6 md:p-10 max-w-[1400px]">
        <div className="md:hidden flex gap-2 mb-6 overflow-x-auto">
          {tabs.map((t) => (
            <button key={t.key} onClick={()=>setTab(t.key)} className={`px-3 py-2 text-xs uppercase tracking-luxury border ${tab===t.key?"border-gold text-gold":"border-white/10 text-cream/60"}`}>{t.label}</button>
          ))}
        </div>

        {tab === "dashboard" && (
          <>
            <h1 className="font-serif text-4xl">Dashboard</h1>
            <div className="mt-8 grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <Stat label="Revenue" value={formatINR(stats?.revenue_inr)} accent />
              <Stat label="Orders" value={stats?.orders_confirmed ?? 0} sub={`${stats?.orders_total ?? 0} total`} />
              <Stat label="Products" value={stats?.products_total ?? 0} />
              <Stat label="New B2B leads" value={stats?.leads_new ?? 0} />
            </div>
          </>
        )}

        {tab === "products" && (
          <>
            <div className="flex justify-between items-center mb-6">
              <h1 className="font-serif text-4xl">Products</h1>
              <button data-testid="admin-add-product" onClick={()=>setEditing({...empty})} className="inline-flex items-center gap-2 bg-gold text-ink-950 px-4 py-2.5 text-xs uppercase tracking-luxury"><Plus className="w-3.5 h-3.5" />New</button>
            </div>
            <div className="grid gap-3">
              {products.map((p) => (
                <div key={p.id} className="hairline p-4 flex items-center gap-4">
                  <img src={p.hero_image} alt="" className="w-16 h-20 object-cover border border-white/10" />
                  <div className="flex-1 min-w-0">
                    <div className="font-serif text-lg truncate">{p.name}</div>
                    <div className="text-xs text-cream/50">{p.size} · Stock {p.stock}</div>
                  </div>
                  <div className="text-cream">{formatINR(p.price_inr)}</div>
                  <button onClick={()=>setEditing({...p, materials: p.materials.join("\n"), gallery: p.gallery.join("\n"), variants: JSON.stringify(p.variants, null, 2)})} className="text-xs text-gold hover:text-cream border border-gold/30 px-3 py-1.5">Edit</button>
                  <button onClick={()=>deleteProduct(p.id)} className="text-red-400 hover:text-red-300 p-2"><Trash2 className="w-4 h-4" /></button>
                </div>
              ))}
            </div>
            {editing && <ProductEditor initial={editing} onCancel={()=>setEditing(null)} onSave={saveProduct} saving={saving} />}
          </>
        )}

        {tab === "orders" && (
          <>
            <h1 className="font-serif text-4xl">Orders</h1>
            <div className="mt-6 grid gap-3">
              {orders.length === 0 && <div className="text-cream/40 text-sm">No orders yet.</div>}
              {orders.map((o) => (
                <div key={o.order_number} className="hairline p-4">
                  <div className="flex flex-wrap items-center gap-4">
                    <div>
                      <div className="text-gold font-mono text-sm">{o.order_number}</div>
                      <div className="text-xs text-cream/50">{new Date(o.created_at).toLocaleString()}</div>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm">{o.customer.name} · {o.customer.phone}</div>
                      <div className="text-xs text-cream/50 truncate">{o.customer.address}, {o.customer.city} — {o.customer.pincode}</div>
                    </div>
                    <div className="text-cream">{formatINR(o.total_inr)}</div>
                    <select value={o.status} onChange={(e)=>updateOrderStatus(o.order_number, e.target.value)}
                      className="bg-ink-950 border border-white/15 text-xs text-cream px-3 py-2 uppercase tracking-luxury">
                      {["pending_payment","confirmed","packed","shipped","delivered","cancelled","payment_failed"].map(s=>(
                        <option key={s} value={s}>{s.replace(/_/g," ")}</option>
                      ))}
                    </select>
                  </div>
                  <div className="mt-3 text-xs text-cream/50">
                    {o.items.length} item(s) · Payment: {o.payment_method}
                    {o.razorpay_payment_id && ` · rzp: ${o.razorpay_payment_id}`}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {tab === "leads" && (
          <>
            <h1 className="font-serif text-4xl">B2B Leads</h1>
            <div className="mt-6 grid gap-3">
              {leads.length === 0 && <div className="text-cream/40 text-sm">No leads yet.</div>}
              {leads.map((l) => (
                <div key={l.id} className="hairline p-4">
                  <div className="flex flex-wrap items-center gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="font-serif text-lg">{l.full_name} <span className="text-cream/40 text-sm">· {l.company}</span></div>
                      <div className="text-xs text-cream/50">{l.email} · {l.phone} · {l.business_type}</div>
                    </div>
                    <select value={l.status} onChange={(e)=>updateLeadStatus(l.id, e.target.value)} className="bg-ink-950 border border-white/15 text-xs px-3 py-2 uppercase tracking-luxury">
                      {["new","contacted","quoted","won","lost"].map(s=>(<option key={s} value={s}>{s}</option>))}
                    </select>
                  </div>
                  {l.message && <div className="mt-3 text-sm text-cream/70">&ldquo;{l.message}&rdquo;</div>}
                  <div className="mt-2 text-xs text-cream/40">Dimensions: {l.dimensions || "—"} · Qty: {l.quantity || "—"}</div>
                </div>
              ))}
            </div>
          </>
        )}

        {tab === "returns" && (
          <>
            <h1 className="font-serif text-4xl">Returns</h1>
            <div className="mt-2 text-xs text-cream/40">3-day strict window from delivery date · approve/reject with genuine assessment</div>
            <div className="mt-6 grid gap-3">
              {returns.length === 0 && <div className="text-cream/40 text-sm">No return requests yet.</div>}
              {returns.map((r) => (
                <ReturnRow key={r.id} r={r} onUpdate={updateReturnStatus} />
              ))}
            </div>
          </>
        )}

        {tab === "reviews" && (
          <>
            <h1 className="font-serif text-4xl">Reviews</h1>
            <div className="mt-6 grid gap-3">
              {reviews.map((r) => (
                <div key={r.id} className="hairline p-4 flex gap-4">
                  {r.image && <img src={r.image} alt="" className="w-16 h-16 object-cover" />}
                  <div className="flex-1 min-w-0">
                    <div className="font-serif text-lg">{r.title} <span className="text-gold text-sm">· {r.rating}★</span></div>
                    <div className="text-xs text-cream/50">{r.author} · {r.location}</div>
                    <div className="text-sm text-cream/70 mt-2 line-clamp-2">{r.body}</div>
                  </div>
                  <button onClick={async()=>{await authed.delete(`/admin/reviews/${r.id}`); toast.success("Deleted"); reload();}} className="text-red-400 p-2"><Trash2 className="w-4 h-4" /></button>
                </div>
              ))}
            </div>
          </>
        )}
      </main>
      <Toaster theme="dark" position="bottom-center" />
    </div>
  );
}

function Stat({ label, value, sub, accent }) {
  return (
    <div className="hairline p-6 bg-ink-900">
      <div className="text-[10px] uppercase tracking-luxury text-cream/50">{label}</div>
      <div className={`font-serif text-4xl mt-2 ${accent?"text-gold":"text-cream"}`}>{value}</div>
      {sub && <div className="text-xs text-cream/40 mt-1">{sub}</div>}
    </div>
  );
}

function ProductEditor({ initial, onCancel, onSave, saving }) {
  const [f, setF] = useState(initial);
  const upd = (k) => (e) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  return (
    <div className="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4" onClick={onCancel}>
      <div className="bg-ink-900 border border-white/10 w-[min(760px,95vw)] max-h-[90vh] overflow-y-auto p-8" onClick={(e)=>e.stopPropagation()}>
        <div className="flex justify-between items-center">
          <h3 className="font-serif text-2xl">{initial.id ? "Edit product" : "New product"}</h3>
          <button onClick={onCancel} className="text-cream/50 hover:text-cream text-sm">Cancel</button>
        </div>
        <div className="mt-6 grid sm:grid-cols-2 gap-4">
          <Fld label="Slug"><input value={f.slug} onChange={upd("slug")} className={inp} required /></Fld>
          <Fld label="Name"><input value={f.name} onChange={upd("name")} className={inp} required /></Fld>
          <Fld label="Tagline"><input value={f.tagline} onChange={upd("tagline")} className={inp} required /></Fld>
          <Fld label="Size"><input value={f.size} onChange={upd("size")} className={inp} required /></Fld>
          <Fld label="Price (₹)"><input type="number" value={f.price_inr} onChange={upd("price_inr")} className={inp} required /></Fld>
          <Fld label="MRP (₹)"><input type="number" value={f.mrp_inr} onChange={upd("mrp_inr")} className={inp} required /></Fld>
          <Fld label="Craft hours"><input type="number" value={f.craft_hours} onChange={upd("craft_hours")} className={inp} /></Fld>
          <Fld label="Stock"><input type="number" value={f.stock} onChange={upd("stock")} className={inp} /></Fld>
          <div className="sm:col-span-2"><Fld label="Hero image URL"><input value={f.hero_image} onChange={upd("hero_image")} className={inp} required /></Fld></div>
          <div className="sm:col-span-2"><Fld label="Description"><textarea rows={3} value={f.description} onChange={upd("description")} className={inp} /></Fld></div>
          <div className="sm:col-span-2"><Fld label="Materials (one per line)"><textarea rows={4} value={f.materials} onChange={upd("materials")} className={inp} /></Fld></div>
          <div className="sm:col-span-2"><Fld label="Gallery URLs (one per line)"><textarea rows={3} value={f.gallery} onChange={upd("gallery")} className={inp} /></Fld></div>
          <div className="sm:col-span-2"><Fld label="Variants JSON"><textarea rows={4} value={f.variants} onChange={upd("variants")} className={`${inp} font-mono text-xs`} /></Fld></div>
          <label className="flex items-center gap-2 text-sm text-cream/70"><input type="checkbox" checked={!!f.is_hero} onChange={upd("is_hero")} /> Mark as hero product</label>
        </div>
        <button disabled={saving} onClick={()=>onSave(f)} className="mt-8 w-full bg-gold text-ink-950 py-4 text-xs uppercase tracking-luxury hover:bg-cream disabled:opacity-60">
          {saving ? <Loader2 className="w-4 h-4 animate-spin inline" /> : "Save product"}
        </button>
      </div>
    </div>
  );
}
const inp = "w-full bg-ink-950 border border-white/15 focus:border-gold focus:outline-none px-3 py-2 text-sm text-cream outline-none";
const Fld = ({ label, children }) => (<label className="block"><span className="text-[10px] uppercase tracking-luxury text-cream/50">{label}</span><div className="mt-1.5">{children}</div></label>);

function ReturnRow({ r, onUpdate }) {
  const [notes, setNotes] = useState(r.admin_notes || "");
  const [genuine, setGenuine] = useState(r.is_genuine === null || r.is_genuine === undefined ? "" : String(r.is_genuine));
  const isFinal = ["approved", "rejected", "refunded"].includes(r.status);
  const daysSinceDelivery = r.order_delivered_at
    ? Math.floor((Date.now() - new Date(r.order_delivered_at).getTime()) / 86400000)
    : null;
  return (
    <div className="hairline p-5" data-testid={`admin-return-${r.id}`}>
      <div className="flex flex-wrap items-start gap-4">
        <div className="min-w-[180px]">
          <div className="text-gold font-mono text-sm">{r.order_number}</div>
          <div className="text-xs text-cream/50 mt-0.5">{r.order_customer_name || r.user_email}</div>
          {r.order_customer_phone && <div className="text-xs text-cream/40">{r.order_customer_phone}</div>}
          <div className="text-xs text-cream/40 mt-1">Requested {new Date(r.created_at).toLocaleDateString()}</div>
          {daysSinceDelivery !== null && (
            <div className={`text-[10px] uppercase tracking-luxury mt-1 ${daysSinceDelivery <= 3 ? "text-emerald-400/70" : "text-red-400/70"}`}>
              {daysSinceDelivery}d since delivery
            </div>
          )}
        </div>

        <div className="flex-1 min-w-[220px]">
          <div className="text-sm text-cream"><span className="text-cream/50">Reason:</span> {r.reason}</div>
          {r.details && <div className="mt-1 text-xs text-cream/60 italic">&ldquo;{r.details}&rdquo;</div>}
          {r.damage_image_url && (
            <a href={r.damage_image_url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-xs text-gold border-b border-gold/40" data-testid={`admin-return-evidence-${r.id}`}>
              View damage evidence →
            </a>
          )}
          {r.packaging_confirmed ? (
            <div className="mt-2 text-[10px] uppercase tracking-luxury text-emerald-400/70">Packaging confirmed by customer</div>
          ) : (
            <div className="mt-2 text-[10px] uppercase tracking-luxury text-red-400/70">Packaging NOT confirmed</div>
          )}
        </div>

        <div className={`text-xs uppercase tracking-luxury px-3 py-1.5 border ${
          r.status === "approved" ? "border-emerald-400/30 text-emerald-400" :
          r.status === "rejected" ? "border-red-400/30 text-red-400" :
          r.status === "refunded" ? "border-gold/40 text-gold" :
          "border-yellow-400/30 text-yellow-400"
        }`}>{r.status}</div>
      </div>

      {!isFinal && (
        <div className="mt-4 grid md:grid-cols-[1fr_auto_auto] gap-3 items-start border-t border-white/5 pt-4">
          <div className="grid sm:grid-cols-2 gap-3">
            <label className="block">
              <span className="text-[10px] uppercase tracking-luxury text-cream/50">Assessment</span>
              <select
                data-testid={`admin-return-genuine-${r.id}`}
                value={genuine}
                onChange={(e) => setGenuine(e.target.value)}
                className={`mt-1.5 ${inp}`}
              >
                <option value="">— Select —</option>
                <option value="true">Genuine claim</option>
                <option value="false">Not genuine / fees apply</option>
              </select>
            </label>
            <label className="block">
              <span className="text-[10px] uppercase tracking-luxury text-cream/50">Notes to customer</span>
              <input
                data-testid={`admin-return-notes-${r.id}`}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Visible on customer's Returns tab"
                className={`mt-1.5 ${inp}`}
              />
            </label>
          </div>
          <button
            data-testid={`admin-return-reject-${r.id}`}
            onClick={() => onUpdate(r.id, { status: "rejected", is_genuine: genuine === "" ? null : genuine === "true", admin_notes: notes || null })}
            className="px-4 py-2.5 border border-red-400/30 text-red-400 hover:bg-red-400/10 text-xs uppercase tracking-luxury"
          >
            Reject
          </button>
          <button
            data-testid={`admin-return-approve-${r.id}`}
            onClick={() => onUpdate(r.id, { status: "approved", is_genuine: genuine === "" ? null : genuine === "true", admin_notes: notes || null })}
            className="px-4 py-2.5 bg-gold text-ink-950 hover:bg-cream text-xs uppercase tracking-luxury"
          >
            Approve
          </button>
        </div>
      )}

      {isFinal && (
        <div className="mt-4 border-t border-white/5 pt-3 text-xs text-cream/60 space-y-1">
          {r.is_genuine === true && <div className="text-emerald-400/80">✓ Marked genuine · full refund eligible</div>}
          {r.is_genuine === false && <div className="text-red-400/80">✗ Marked non-genuine · restocking / repair fees apply</div>}
          {r.admin_notes && <div>Note to customer: <span className="text-cream/80">{r.admin_notes}</span></div>}
          {r.status === "approved" && (
            <button
              data-testid={`admin-return-refund-${r.id}`}
              onClick={() => onUpdate(r.id, { status: "refunded" })}
              className="mt-2 px-3 py-1.5 border border-gold/40 text-gold hover:bg-gold/10 text-[10px] uppercase tracking-luxury"
            >
              Mark refunded
            </button>
          )}
        </div>
      )}
    </div>
  );
}
