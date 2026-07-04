import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast, Toaster } from "sonner";
import { LogOut, Package, ShoppingBag, Users, Star, LayoutGrid, Plus, Trash2, Loader2, RotateCcw, UserCircle, MessageSquare, Send, X, Search, Tag, AlertTriangle, Edit2 } from "lucide-react";

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

const empty = { slug: "", name: "", tagline: "", description: "", price_inr: 0, mrp_inr: 0, size: "", craft_hours: 24, materials: "", hero_image: "", gallery: "", variants: '[\n  {"key":"gold-standard","label":"Gold · Standard","hex":"#D4AF37","image":"","size":"","stock":5,"price_inr":null,"mrp_inr":null}\n]', stock: 5, is_hero: false };

export default function AdminPage() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || "");
  const [tab, setTab] = useState("dashboard");
  const [stats, setStats] = useState(null);
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [leads, setLeads] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [returns, setReturns] = useState([]);
  const [users, setUsers] = useState([]);
  const [userSearch, setUserSearch] = useState("");
  const [userDetail, setUserDetail] = useState(null);
  const [coupons, setCoupons] = useState([]);
  const [failedPayments, setFailedPayments] = useState([]);
  const [couponEditing, setCouponEditing] = useState(null); // null | coupon obj | "new"
  const [editing, setEditing] = useState(null); // null | product obj | "new"
  const [saving, setSaving] = useState(false);

  const authed = useAuthedApi(token);

  const reload = React.useCallback(async () => {
    if (!token) return;
    try {
      const [s, p, o, l, r, rt, u, c, fp] = await Promise.all([
        authed.get("/admin/stats"), authed.get("/products"),
        authed.get("/admin/orders"), authed.get("/admin/leads"), authed.get("/reviews"),
        authed.get("/admin/returns"), authed.get("/admin/users"),
        authed.get("/admin/coupons"), authed.get("/admin/failed-payments"),
      ]);
      setStats(s.data); setProducts(p.data); setOrders(o.data); setLeads(l.data);
      setReviews(r.data); setReturns(rt.data); setUsers(u.data);
      setCoupons(c.data); setFailedPayments(fp.data);
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
    { key: "users", label: "Customers", icon: UserCircle },
    { key: "leads", label: "B2B Leads", icon: Users },
    { key: "reviews", label: "Reviews", icon: Star },
    { key: "coupons", label: "Coupons", icon: Tag },
    { key: "failed", label: "Failed Payments", icon: AlertTriangle },
  ];

  const saveCoupon = async (form) => {
    setSaving(true);
    try {
      const payload = {
        code: (form.code || "").toUpperCase().trim(),
        type: form.type,
        value: Number(form.value),
        min_cart_inr: Number(form.min_cart_inr || 0),
        max_uses: form.max_uses === "" || form.max_uses === null || form.max_uses === undefined ? null : Number(form.max_uses),
        expires_at: form.expires_at || null,
        active: !!form.active,
        description: form.description || null,
      };
      if (form.id) {
        await authed.patch(`/admin/coupons/${form.id}`, payload);
      } else {
        await authed.post("/admin/coupons", payload);
      }
      toast.success(form.id ? "Coupon updated" : "Coupon created");
      setCouponEditing(null);
      reload();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Save failed");
    } finally { setSaving(false); }
  };

  const deleteCoupon = async (id) => {
    if (!window.confirm("Delete this coupon? Existing orders keep their discount.")) return;
    try {
      await authed.delete(`/admin/coupons/${id}`);
      toast.success("Coupon deleted");
      reload();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Delete failed");
    }
  };

  const openUserDetail = async (email) => {
    try {
      const { data } = await authed.get(`/admin/users/${encodeURIComponent(email)}`);
      setUserDetail(data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not load user");
    }
  };

  const sendMessage = async (email, subject, body) => {
    await authed.post("/admin/messages", { user_email: email, subject, body });
    toast.success("Message sent to customer");
    if (userDetail && userDetail.user.email === email) {
      openUserDetail(email);
    }
    reload();
  };

  const filteredUsers = users.filter((u) => {
    if (!userSearch.trim()) return true;
    const q = userSearch.toLowerCase();
    return (
      u.email?.toLowerCase().includes(q) ||
      u.name?.toLowerCase().includes(q) ||
      (u.phone || "").toLowerCase().includes(q)
    );
  });

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

        {tab === "users" && (
          <>
            <div className="flex items-end justify-between flex-wrap gap-4">
              <div>
                <h1 className="font-serif text-4xl">Customers</h1>
                <div className="mt-2 text-xs text-cream/40">{users.length} registered · click a row to view full history & send a personal message</div>
              </div>
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-cream/40" />
                <input
                  data-testid="admin-users-search"
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  placeholder="Search by name, email or phone…"
                  className="pl-9 pr-3 py-2.5 bg-ink-950 border border-white/15 focus:border-gold text-sm text-cream w-80 max-w-full outline-none"
                />
              </div>
            </div>
            <div className="mt-6 hairline overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/5 text-[10px] uppercase tracking-luxury text-cream/40">
                    <th className="px-4 py-3 text-left font-normal">Customer</th>
                    <th className="px-4 py-3 text-left font-normal">Contact</th>
                    <th className="px-4 py-3 text-right font-normal">Orders</th>
                    <th className="px-4 py-3 text-right font-normal">Lifetime spend</th>
                    <th className="px-4 py-3 text-left font-normal">Last order</th>
                    <th className="px-4 py-3 text-right font-normal">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.length === 0 && (
                    <tr><td colSpan={6} className="px-4 py-8 text-center text-cream/40">No customers match your search.</td></tr>
                  )}
                  {filteredUsers.map((u) => (
                    <tr
                      key={u.email}
                      data-testid={`admin-user-row-${u.email}`}
                      className="border-b border-white/5 hover:bg-white/5 cursor-pointer transition-colors"
                      onClick={() => openUserDetail(u.email)}
                    >
                      <td className="px-4 py-4">
                        <div className="font-serif text-cream">{u.name}</div>
                        <div className="text-[10px] uppercase tracking-luxury text-cream/40 mt-0.5">Since {new Date(u.created_at).toLocaleDateString()}</div>
                      </td>
                      <td className="px-4 py-4">
                        <div className="text-cream/80 text-xs">{u.email}</div>
                        <div className="text-cream/50 text-xs mt-0.5">{u.phone || "—"}</div>
                      </td>
                      <td className="px-4 py-4 text-right text-cream">{u.orders_count}</td>
                      <td className="px-4 py-4 text-right text-gold font-serif">{formatINR(u.total_spent_inr)}</td>
                      <td className="px-4 py-4 text-xs text-cream/60">{u.last_order_at ? new Date(u.last_order_at).toLocaleDateString() : "—"}</td>
                      <td className="px-4 py-4 text-right">
                        <button
                          data-testid={`admin-user-message-${u.email}`}
                          onClick={(e) => { e.stopPropagation(); openUserDetail(u.email); }}
                          className="inline-flex items-center gap-1.5 text-[10px] uppercase tracking-luxury text-gold hover:text-cream border border-gold/40 px-3 py-1.5"
                        >
                          <MessageSquare className="w-3 h-3" /> View · Message
                          {u.messages_count > 0 && <span className="ml-1 text-cream/50">({u.messages_count})</span>}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {userDetail && (
              <UserDetailDrawer detail={userDetail} onClose={() => setUserDetail(null)} onSendMessage={sendMessage} />
            )}
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

        {tab === "coupons" && (
          <>
            <div className="flex justify-between items-center mb-6">
              <h1 className="font-serif text-4xl">Coupons</h1>
              <button data-testid="admin-add-coupon" onClick={()=>setCouponEditing({ code: "", type: "percentage", value: 10, min_cart_inr: 0, max_uses: "", expires_at: "", active: true, description: "" })} className="inline-flex items-center gap-2 bg-gold text-ink-950 px-4 py-2.5 text-xs uppercase tracking-luxury">
                <Plus className="w-3.5 h-3.5" /> New coupon
              </button>
            </div>
            {coupons.length === 0 ? (
              <div className="hairline p-8 text-center text-cream/50">No coupons yet. Create one to give customers a discount at checkout.</div>
            ) : (
              <div className="grid gap-3">
                {coupons.map((c) => {
                  const expired = c.expires_at && new Date(c.expires_at) < new Date();
                  const exhausted = c.max_uses !== null && c.max_uses !== undefined && c.used_count >= c.max_uses;
                  return (
                    <div key={c.id} data-testid={`admin-coupon-${c.code}`} className="hairline p-4 flex flex-wrap items-center gap-4">
                      <div className="flex-1 min-w-[220px]">
                        <div className="flex items-center gap-3">
                          <span className="font-mono text-gold text-lg tracking-wider">{c.code}</span>
                          {!c.active && <span className="text-[10px] uppercase tracking-luxury text-red-400 border border-red-400/40 px-2 py-0.5">Disabled</span>}
                          {expired && <span className="text-[10px] uppercase tracking-luxury text-yellow-400 border border-yellow-400/40 px-2 py-0.5">Expired</span>}
                          {exhausted && <span className="text-[10px] uppercase tracking-luxury text-yellow-400 border border-yellow-400/40 px-2 py-0.5">Sold out</span>}
                        </div>
                        <div className="text-xs text-cream/60 mt-1">
                          {c.type === "percentage" ? `${c.value}% off` : `${formatINR(c.value)} off`}
                          {c.min_cart_inr > 0 ? ` · min cart ${formatINR(c.min_cart_inr)}` : ""}
                          {c.max_uses !== null && c.max_uses !== undefined ? ` · ${c.used_count}/${c.max_uses} used` : ` · ${c.used_count} used`}
                          {c.expires_at ? ` · expires ${new Date(c.expires_at).toLocaleDateString()}` : ""}
                        </div>
                        {c.description && <div className="text-xs text-cream/40 mt-1 italic">{c.description}</div>}
                      </div>
                      <button
                        data-testid={`admin-coupon-edit-${c.code}`}
                        onClick={() => setCouponEditing({ ...c, expires_at: c.expires_at ? c.expires_at.split("T")[0] : "", max_uses: c.max_uses ?? "" })}
                        className="text-xs text-gold hover:text-cream border border-gold/30 px-3 py-1.5 inline-flex items-center gap-1.5"
                      ><Edit2 className="w-3 h-3" /> Edit</button>
                      <button data-testid={`admin-coupon-delete-${c.code}`} onClick={()=>deleteCoupon(c.id)} className="text-red-400 hover:text-red-300 p-2"><Trash2 className="w-4 h-4" /></button>
                    </div>
                  );
                })}
              </div>
            )}
            {couponEditing && <CouponEditor initial={couponEditing} onCancel={()=>setCouponEditing(null)} onSave={saveCoupon} saving={saving} />}
          </>
        )}

        {tab === "failed" && (
          <>
            <h1 className="font-serif text-4xl">Failed Payments</h1>
            <p className="mt-2 text-sm text-cream/50">Every failed Razorpay attempt is logged here so you can proactively reach out to customers who abandoned checkout.</p>
            {failedPayments.length === 0 ? (
              <div className="mt-8 hairline p-8 text-center text-cream/50">No failed payments logged. ✨</div>
            ) : (
              <div className="mt-6 grid gap-3">
                {failedPayments.map((f) => (
                  <div key={f.id} data-testid={`admin-failed-${f.id}`} className="hairline p-4">
                    <div className="flex flex-wrap items-center gap-4">
                      <div className="min-w-[180px]">
                        <div className="text-red-400 text-xs uppercase tracking-luxury flex items-center gap-1.5">
                          <AlertTriangle className="w-3 h-3" /> {f.error_code || "PAYMENT_FAILED"}
                        </div>
                        <div className="text-[11px] text-cream/40 mt-1">
                          {new Date(f.created_at).toLocaleString()}
                          {f.attempt > 1 ? ` · attempt ${f.attempt}` : ""}
                        </div>
                      </div>
                      <div className="flex-1 min-w-[240px]">
                        <div className="text-sm text-cream/80">{f.error_description || "No description"}</div>
                        <div className="text-xs text-cream/50 mt-1">
                          {f.customer_name || "Unknown"}
                          {f.customer_email ? ` · ${f.customer_email}` : ""}
                          {f.customer_phone ? ` · ${f.customer_phone}` : ""}
                        </div>
                        {f.order_number && (
                          <div className="text-[10px] uppercase tracking-luxury text-cream/40 mt-1">
                            Order · <span className="font-mono normal-case tracking-normal text-cream/60">{f.order_number}</span>
                          </div>
                        )}
                      </div>
                      <div className="text-cream font-serif text-lg">{formatINR(f.amount_inr)}</div>
                      {f.customer_email && (
                        <a
                          data-testid={`admin-failed-contact-${f.id}`}
                          href={`mailto:${f.customer_email}?subject=${encodeURIComponent("Your ArtyFex order")}&body=${encodeURIComponent("Hi " + (f.customer_name || "") + ",\nWe noticed your payment did not go through. Would you like our help completing it?")}`}
                          className="text-xs text-gold hover:text-cream border border-gold/30 px-3 py-1.5"
                        >Contact</a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
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
          <div className="sm:col-span-2"><Fld label='Variants JSON — supports size/stock/price_inr/mrp_inr per variant (Shopify-style)'><textarea rows={6} value={f.variants} onChange={upd("variants")} className={`${inp} font-mono text-xs`} /></Fld></div>
          <label className="flex items-center gap-2 text-sm text-cream/70"><input type="checkbox" checked={!!f.is_hero} onChange={upd("is_hero")} /> Mark as hero product</label>
        </div>
        <button disabled={saving} onClick={()=>onSave(f)} className="mt-8 w-full bg-gold text-ink-950 py-4 text-xs uppercase tracking-luxury hover:bg-cream disabled:opacity-60">
          {saving ? <Loader2 className="w-4 h-4 animate-spin inline" /> : "Save product"}
        </button>
      </div>
    </div>
  );
}

function CouponEditor({ initial, onCancel, onSave, saving }) {
  const [f, setF] = useState(initial);
  const upd = (k) => (e) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  const submit = (e) => {
    e.preventDefault();
    onSave(f);
  };
  return (
    <div className="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4" onClick={onCancel}>
      <form onSubmit={submit} className="bg-ink-900 border border-white/10 w-[min(560px,95vw)] max-h-[90vh] overflow-y-auto p-8" onClick={(e)=>e.stopPropagation()} data-testid="admin-coupon-editor">
        <div className="flex justify-between items-center">
          <h3 className="font-serif text-2xl">{f.id ? "Edit coupon" : "New coupon"}</h3>
          <button type="button" onClick={onCancel} className="text-cream/50 hover:text-cream text-sm">Cancel</button>
        </div>
        <div className="mt-6 grid sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <Fld label="Code (uppercase, unique)">
              <input data-testid="admin-coupon-code" value={f.code} onChange={upd("code")} className={`${inp} font-mono uppercase tracking-wider`} required placeholder="WELCOME10" />
            </Fld>
          </div>
          <Fld label="Type">
            <select data-testid="admin-coupon-type" value={f.type} onChange={upd("type")} className={inp}>
              <option value="percentage">Percentage (%)</option>
              <option value="flat">Flat (₹)</option>
            </select>
          </Fld>
          <Fld label={f.type === "percentage" ? "Value (%)" : "Value (₹)"}>
            <input data-testid="admin-coupon-value" type="number" min="0" step={f.type === "percentage" ? "1" : "50"} value={f.value} onChange={upd("value")} className={inp} required />
          </Fld>
          <Fld label="Min cart (₹, optional)">
            <input data-testid="admin-coupon-min" type="number" min="0" step="500" value={f.min_cart_inr} onChange={upd("min_cart_inr")} className={inp} />
          </Fld>
          <Fld label="Max uses (blank = unlimited)">
            <input data-testid="admin-coupon-max" type="number" min="0" value={f.max_uses ?? ""} onChange={upd("max_uses")} className={inp} placeholder="Unlimited" />
          </Fld>
          <Fld label="Expires on (optional)">
            <input data-testid="admin-coupon-expires" type="date" value={f.expires_at || ""} onChange={upd("expires_at")} className={inp} />
          </Fld>
          <label className="flex items-center gap-2 text-sm text-cream/70 mt-6">
            <input data-testid="admin-coupon-active" type="checkbox" checked={!!f.active} onChange={upd("active")} className="accent-gold" /> Active
          </label>
          <div className="sm:col-span-2">
            <Fld label="Description (shown to customer)">
              <input data-testid="admin-coupon-description" value={f.description || ""} onChange={upd("description")} className={inp} placeholder="10% off for new collectors." />
            </Fld>
          </div>
        </div>
        <button data-testid="admin-coupon-save" disabled={saving} className="mt-8 w-full bg-gold text-ink-950 py-4 text-xs uppercase tracking-luxury hover:bg-cream disabled:opacity-60">
          {saving ? <Loader2 className="w-4 h-4 animate-spin inline" /> : (f.id ? "Save changes" : "Create coupon")}
        </button>
      </form>
    </div>
  );
}

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


const inp = "w-full bg-ink-950 border border-white/15 focus:border-gold focus:outline-none px-3 py-2 text-sm text-cream outline-none";
const Fld = ({ label, children }) => (<label className="block"><span className="text-[10px] uppercase tracking-luxury text-cream/50">{label}</span><div className="mt-1.5">{children}</div></label>);
const formatDate = (iso) => (iso ? new Date(iso).toLocaleString() : "—");

function UserDetailDrawer({ detail, onClose, onSendMessage }) {
  const { user, orders, returns, messages, wishlist_count } = detail;
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);
  const totalSpent = orders.filter((o) => !["pending_payment", "cancelled", "payment_failed"].includes(o.status)).reduce((s, o) => s + (o.total_inr || 0), 0);
  const canSend = subject.trim().length > 0 && body.trim().length > 0;

  const submit = async (e) => {
    e.preventDefault();
    if (!canSend) return;
    setSending(true);
    try {
      await onSendMessage(user.email, subject.trim(), body.trim());
      setSubject(""); setBody("");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Send failed");
    } finally { setSending(false); }
  };

  return (
    <div className="fixed inset-0 z-[90] bg-black/70 backdrop-blur-sm flex justify-end" onClick={onClose} data-testid="admin-user-drawer">
      <div className="w-[min(720px,100vw)] h-full bg-ink-900 border-l border-white/10 overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="sticky top-0 z-10 bg-ink-900 border-b border-white/10 px-8 py-6 flex items-start gap-4">
          <div className="flex-1 min-w-0">
            <div className="text-[10px] uppercase tracking-luxury text-gold-soft">Customer profile</div>
            <h2 className="mt-1 font-serif text-3xl text-cream truncate">{user.name}</h2>
            <div className="text-xs text-cream/50 mt-1 truncate">{user.email} · {user.phone || "no phone"}</div>
          </div>
          <button data-testid="admin-user-drawer-close" onClick={onClose} className="p-2 text-cream/50 hover:text-cream">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="px-8 py-6">
          <div className="grid grid-cols-3 gap-3">
            <SmallStat label="Orders" value={orders.length} />
            <SmallStat label="Lifetime" value={`₹${totalSpent.toLocaleString("en-IN")}`} accent />
            <SmallStat label="Wishlist" value={wishlist_count} />
          </div>

          {/* Send message */}
          <form onSubmit={submit} className="mt-8 hairline p-6 bg-ink-950/40" data-testid="admin-message-form">
            <div className="text-[10px] uppercase tracking-luxury text-gold-soft mb-1">Send a personal message</div>
            <p className="text-xs text-cream/50 mb-4">Appears on the customer&apos;s account dashboard with an unread badge.</p>
            <div className="space-y-3">
              <input
                data-testid="admin-message-subject"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="Subject (e.g. Thank you for your recent order)"
                className={inp}
              />
              <textarea
                data-testid="admin-message-body"
                value={body}
                onChange={(e) => setBody(e.target.value)}
                rows={4}
                placeholder="Write your personal note to the customer…"
                className={inp}
              />
              <button
                data-testid="admin-message-send"
                type="submit"
                disabled={!canSend || sending}
                className="inline-flex items-center gap-2 bg-gold text-ink-950 px-5 py-2.5 text-xs uppercase tracking-luxury disabled:opacity-40 disabled:cursor-not-allowed hover:bg-cream"
              >
                {sending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                {sending ? "Sending…" : "Send message"}
              </button>
            </div>
          </form>

          {/* Message history */}
          <div className="mt-8">
            <div className="text-[10px] uppercase tracking-luxury text-cream/40 mb-3">Message history ({messages.length})</div>
            <div className="grid gap-2">
              {messages.length === 0 && <div className="text-xs text-cream/40 italic">No messages sent yet.</div>}
              {messages.map((m) => (
                <div key={m.id} className="hairline p-4" data-testid={`admin-user-msg-${m.id}`}>
                  <div className="flex items-baseline gap-3 flex-wrap">
                    <div className="font-serif text-lg text-cream">{m.subject}</div>
                    <div className="text-[10px] uppercase tracking-luxury ml-auto text-cream/40">
                      {formatDate(m.created_at)}
                    </div>
                  </div>
                  <div className="mt-2 text-sm text-cream/70 whitespace-pre-wrap">{m.body}</div>
                  <div className="mt-2 text-[10px] uppercase tracking-luxury">
                    {m.read ? <span className="text-emerald-400/70">Read {m.read_at ? `· ${formatDate(m.read_at)}` : ""}</span> : <span className="text-yellow-400/70">Unread</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Orders history */}
          <div className="mt-8">
            <div className="text-[10px] uppercase tracking-luxury text-cream/40 mb-3">Orders ({orders.length})</div>
            <div className="grid gap-2">
              {orders.length === 0 && <div className="text-xs text-cream/40 italic">No orders yet.</div>}
              {orders.map((o) => (
                <div key={o.order_number} className="hairline p-4 flex items-center gap-4 flex-wrap">
                  <div>
                    <div className="text-gold font-mono text-xs">{o.order_number}</div>
                    <div className="text-[10px] text-cream/40">{formatDate(o.created_at)}</div>
                  </div>
                  <div className="text-[10px] uppercase tracking-luxury text-cream/60">{o.status.replace(/_/g, " ")}</div>
                  <div className="ml-auto font-serif text-cream">{formatINR(o.total_inr)}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Returns history */}
          {returns.length > 0 && (
            <div className="mt-8">
              <div className="text-[10px] uppercase tracking-luxury text-cream/40 mb-3">Returns ({returns.length})</div>
              <div className="grid gap-2">
                {returns.map((r) => (
                  <div key={r.id} className="hairline p-4 flex items-center gap-3 flex-wrap">
                    <div className="text-xs text-gold font-mono">{r.order_number}</div>
                    <div className="text-xs text-cream/60 flex-1 truncate">{r.reason}</div>
                    <div className="text-[10px] uppercase tracking-luxury text-cream/50">{r.status}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SmallStat({ label, value, accent }) {
  return (
    <div className="hairline p-4 bg-ink-950/40">
      <div className="text-[10px] uppercase tracking-luxury text-cream/40">{label}</div>
      <div className={`mt-1 font-serif text-2xl ${accent ? "text-gold" : "text-cream"}`}>{value}</div>
    </div>
  );
}
