import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast, Toaster } from "sonner";
import { LogOut, Package, ShoppingBag, Users, Star, LayoutGrid, Plus, Trash2, Loader2, RotateCcw, UserCircle, MessageSquare, Send, X, Search, Tag, AlertTriangle, Edit2, Settings as SettingsIcon, Truck, Palette, ShieldCheck, Percent, FileText, Download } from "lucide-react";
import HomepageEditor from "@/components/admin/HomepageEditor";
import ShippingEditor from "@/components/admin/ShippingEditor";
import AnalyticsDashboard from "@/components/admin/AnalyticsDashboard";
import EmployeesTab from "@/components/admin/EmployeesTab";
import PasswordChangeCard from "@/components/admin/PasswordChangeCard";
import CustomersTab from "@/components/admin/CustomersTab";
import GstManagementTab from "@/components/admin/GstManagementTab";
import WhitelistCard from "@/components/admin/WhitelistCard";
import BroadcastCard from "@/components/admin/BroadcastCard";
import OrderNotifyDialog from "@/components/admin/OrderNotifyDialog";
import CloudinaryUpload from "@/components/admin/CloudinaryUpload";
import PagesTab from "@/components/admin/PagesTab";

const TOKEN_KEY = "artyfex_admin_token";

const formatINR = (n) => `₹${(n || 0).toLocaleString("en-IN")}`;

function LoginView({ onLogin }) {
  const [email, setEmail] = useState("admin@artyfex.in");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [gLoading, setGLoading] = useState(false);

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

  // Emergent Google OAuth → session_id lands on /admin#session_id=…
  const startGoogle = () => {
    const returnUrl = `${window.location.origin}/admin`;
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(returnUrl)}`;
  };

  useEffect(() => {
    const hash = window.location.hash || "";
    if (!hash.includes("session_id=")) return;
    const sid = new URLSearchParams(hash.replace(/^#/, "")).get("session_id");
    if (!sid) return;
    // Clean hash so refresh doesn't retry
    window.history.replaceState({}, "", window.location.pathname);
    (async () => {
      setGLoading(true);
      try {
        const { data } = await api.post("/admin/auth/google", { session_id: sid });
        localStorage.setItem(TOKEN_KEY, data.token);
        toast.success(`Signed in as ${data.admin?.email || "admin"}`);
        onLogin(data.token);
      } catch (err) {
        toast.error(err?.response?.data?.detail || "Google admin sign-in failed");
      } finally { setGLoading(false); }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen bg-ink-950 flex items-center justify-center p-6">
      <form onSubmit={submit} className="w-full max-w-md hairline p-10 bg-ink-900">
        <div className="text-[10px] uppercase tracking-luxury text-gold-soft">ArtyFex</div>
        <h1 className="mt-2 font-serif text-4xl text-cream">Atelier <span className="italic text-gold">Admin</span></h1>

        <button
          type="button"
          onClick={startGoogle}
          disabled={gLoading}
          data-testid="admin-google-login"
          className="mt-8 w-full inline-flex items-center justify-center gap-3 bg-cream text-ink-950 py-3.5 text-xs uppercase tracking-luxury hover:bg-white disabled:opacity-60"
        >
          {gLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <svg width="16" height="16" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
              <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
              <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
              <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
            </svg>
          )}
          {gLoading ? "Verifying…" : "Continue with Google"}
        </button>

        <div className="mt-6 flex items-center gap-4">
          <div className="flex-1 h-px bg-white/10"></div>
          <span className="text-[10px] uppercase tracking-luxury text-cream/40">or with password</span>
          <div className="flex-1 h-px bg-white/10"></div>
        </div>

        <div className="mt-6 space-y-5">
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

const empty = { slug: "", name: "", tagline: "", description: "", price_inr: 0, mrp_inr: 0, size: "", craft_hours: 24, materials: "", hero_image: "", gallery: "", variants: [{ key: "default", label: "Default", hex: "#333333", image: "", size: "", stock: 5, price_inr: null, mrp_inr: null }], has_variations: false, stock: 5, is_hero: false, category: "", hsn_code: "", sku: "", weight_grams: "", length_cm: "", width_cm: "", height_cm: "", tags: "", variation_options: [] };

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
  const [settings, setSettings] = useState({ review_prompt_days: 7 });
  const [couponEditing, setCouponEditing] = useState(null); // null | coupon obj | "new"
  const [editing, setEditing] = useState(null); // null | product obj | "new"
  const [saving, setSaving] = useState(false);
  const [me, setMe] = useState(null); // current admin (for RBAC gating)
  const [categories, setCategories] = useState([]); // Phase A — product categories for editor dropdown
  const [notifyOrder, setNotifyOrder] = useState(null); // order object for custom email dialog

  // ---- Pagination + filter state (added Jul 2025 for 1000+ scale) ----
  const [prodQuery, setProdQuery] = useState("");
  const [prodCategory, setProdCategory] = useState("");
  const [prodStockFilter, setProdStockFilter] = useState(""); // "" | "low" | "out"
  const [prodPage, setProdPage] = useState(1);
  const PROD_PAGE_SIZE = 12;

  const [orderQuery, setOrderQuery] = useState("");
  const [orderStatus, setOrderStatus] = useState("");
  const [orderPage, setOrderPage] = useState(1);
  const ORDER_PAGE_SIZE = 10;

  const [reviewQuery, setReviewQuery] = useState("");
  const [reviewRating, setReviewRating] = useState("");
  const [reviewFeatured, setReviewFeatured] = useState("");
  const [reviewPage, setReviewPage] = useState(1);
  const REVIEW_PAGE_SIZE = 10;

  const [failedQuery, setFailedQuery] = useState("");
  const [failedPage, setFailedPage] = useState(1);
  const FAILED_PAGE_SIZE = 10;

  const [userStatusFilter, setUserStatusFilter] = useState(""); // "" | "blocked" | "active"
  const [userPage, setUserPage] = useState(1);
  const USER_PAGE_SIZE = 10;

  const authed = useAuthedApi(token);

  // Fetch current admin identity + permissions
  useEffect(() => {
    if (!token) { setMe(null); return; }
    authed.get("/admin/me")
      .then(({ data }) => setMe(data))
      .catch((err) => {
        if (err?.response?.status === 401) { localStorage.removeItem(TOKEN_KEY); setToken(""); }
      });
  }, [token, authed]);

  const hasPerm = (p) => !!me && (me.role === "owner" || (me.permissions || []).includes(p));

  // Auto-fallback if current tab is not accessible for this admin's permissions
  useEffect(() => {
    if (!me) return;
    const allowed = [
      ["dashboard", "view_analytics", false],
      ["homepage", "manage_homepage", false],
      ["pages", "manage_homepage", false],
      ["products", "manage_products", false],
      ["orders", "manage_orders", false],
      ["shipping", "manage_shipping", false],
      ["gst", "manage_gst", false],
      ["returns", "manage_returns", false],
      ["users", "manage_customers", false],
      ["leads", "manage_leads", false],
      ["reviews", "manage_reviews", false],
      ["coupons", "manage_coupons", false],
      ["failed", "view_analytics", false],
      ["employees", "manage_employees", true],
      ["settings", null, false],
    ].filter(([, perm, ownerOnly]) => {
      if (ownerOnly && me.role !== "owner") return false;
      if (!perm) return true;
      return me.role === "owner" || (me.permissions || []).includes(perm);
    }).map((t) => t[0]);
    if (allowed.length && !allowed.includes(tab)) {
      setTab(allowed[0]);
    }
    // eslint-disable-next-line
  }, [me]);

  const reload = React.useCallback(async () => {
    if (!token) return;
    try {
      const [s, p, o, l, r, rt, u, c, fp, st, cats] = await Promise.all([
        authed.get("/admin/stats"), authed.get("/products"),
        authed.get("/admin/orders"), authed.get("/admin/leads"), authed.get("/reviews"),
        authed.get("/admin/returns"), authed.get("/admin/users"),
        authed.get("/admin/coupons"), authed.get("/admin/failed-payments"),
        authed.get("/admin/settings"),
        authed.get("/admin/product-categories").catch(() => ({ data: [] })),
      ]);
      setStats(s.data); setProducts(p.data); setOrders(o.data); setLeads(l.data);
      setReviews(r.data); setReturns(rt.data); setUsers(u.data);
      setCoupons(c.data); setFailedPayments(fp.data); setSettings(st.data);
      setCategories(cats.data || []);
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
      const variantsArr = Array.isArray(form.variants) ? form.variants : (typeof form.variants === "string" ? JSON.parse(form.variants) : []);
      // If product has no variations, collapse to a single default variant so backend model is happy.
      const finalVariants = form.has_variations
        ? variantsArr.map((v) => ({
            key: v.key || (v.label || "variant").toLowerCase().replace(/\s+/g, "-"),
            label: v.label || "Variant",
            hex: v.hex || "#333333",
            image: v.image || "",
            size: v.size || "",
            stock: Number(v.stock ?? 0),
            price_inr: v.price_inr === "" || v.price_inr == null ? null : Number(v.price_inr),
            mrp_inr: v.mrp_inr === "" || v.mrp_inr == null ? null : Number(v.mrp_inr),
          }))
        : [{ key: "default", label: "Default", hex: "#333333", image: form.hero_image || "", size: form.size || "", stock: Number(form.stock || 0), price_inr: null, mrp_inr: null }];

      const { has_variations, ...rest } = form;
      const parseTags = (t) => Array.isArray(t) ? t : (typeof t === "string" ? t.split(",").map((s) => s.trim()).filter(Boolean) : []);
      const numOrNull = (v) => (v === "" || v === null || v === undefined ? null : Number(v));
      const payload = {
        ...rest,
        price_inr: Number(form.price_inr), mrp_inr: Number(form.mrp_inr),
        craft_hours: Number(form.craft_hours), stock: Number(form.stock),
        materials: typeof form.materials === "string" ? form.materials.split("\n").map(s=>s.trim()).filter(Boolean) : form.materials,
        gallery: typeof form.gallery === "string" ? form.gallery.split("\n").map(s=>s.trim()).filter(Boolean) : form.gallery,
        variants: finalVariants,
        // Phase A commerce/GST/logistics fields
        category: form.category || null,
        hsn_code: (form.hsn_code || "").toString().trim() || null,
        sku: (form.sku || "").toString().trim() || null,
        weight_grams: numOrNull(form.weight_grams),
        length_cm: numOrNull(form.length_cm),
        width_cm: numOrNull(form.width_cm),
        height_cm: numOrNull(form.height_cm),
        tags: parseTags(form.tags),
        // Task 3 — Extra variation options (Shape/Frame/Thickness/Gift Wrap/Care Kit/Mount)
        variation_options: (Array.isArray(form.variation_options) ? form.variation_options : [])
          .filter((o) => (o.key || o.label) && Array.isArray(o.values) && o.values.length > 0)
          .map((o) => ({
            key: (o.key || o.label || "").toLowerCase().replace(/\s+/g, "_").replace(/[^a-z0-9_]/g, ""),
            label: o.label || o.key,
            type: o.type || "select",
            required: !!o.required,
            help_text: o.help_text || null,
            values: (o.values || [])
              .filter((v) => v.key || v.label)
              .map((v) => ({
                key: (v.key || v.label || "").toLowerCase().replace(/\s+/g, "_").replace(/[^a-z0-9_]/g, ""),
                label: v.label || v.key,
                hex: v.hex || null,
                image: v.image || null,
                price_delta_inr: Number(v.price_delta_inr || 0),
                is_default: !!v.is_default,
              })),
          })),
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

  const updateOrderTracking = async (num, patch) => {
    try {
      await authed.patch(`/admin/orders/${num}/tracking`, patch);
      toast.success("Tracking updated");
      reload();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Update failed");
    }
  };

  const nimbusShip = async (num) => {
    try {
      const res = await authed.post(`/admin/orders/${num}/nimbuspost/ship`);
      toast.success(`Shipment created · AWB ${res?.data?.awb || "—"}`);
      reload();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "NimbusPost shipment failed");
    }
  };
  const nimbusTrack = async (num) => {
    try {
      const res = await authed.get(`/admin/orders/${num}/nimbuspost/track`);
      const status = res?.data?.data?.status || res?.data?.data?.data?.status || JSON.stringify(res?.data?.data).slice(0, 180);
      toast.success(`Live status: ${status || "See console"}`);
      // eslint-disable-next-line no-console
      console.log("NimbusPost tracking:", res?.data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Tracking failed");
    }
  };
  const nimbusCancel = async (num) => {
    if (!window.confirm("Cancel this NimbusPost shipment? Wallet balance is auto-refunded by NimbusPost if not yet manifested.")) return;
    try {
      await authed.post(`/admin/orders/${num}/nimbuspost/cancel`);
      toast.success("Shipment cancelled");
      reload();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Cancel failed");
    }
  };


  const updateLeadStatus = async (id, status) => {
    await authed.patch(`/admin/leads/${id}`, { status });
    reload();
  };

  const allTabs = [
    { key: "dashboard", label: "Dashboard", icon: LayoutGrid, perm: "view_analytics" },
    { key: "homepage", label: "Homepage", icon: Palette, perm: "manage_homepage" },
    { key: "pages", label: "Pages / Legal", icon: FileText, perm: "manage_homepage" },
    { key: "products", label: "Products", icon: Package, perm: "manage_products" },
    { key: "orders", label: "Orders", icon: ShoppingBag, perm: "manage_orders" },
    { key: "shipping", label: "Shipping", icon: Truck, perm: "manage_shipping" },
    { key: "gst", label: "GST", icon: Percent, perm: "manage_gst" },
    { key: "returns", label: "Returns", icon: RotateCcw, perm: "manage_returns" },
    { key: "users", label: "Customers", icon: UserCircle, perm: "manage_customers" },
    { key: "leads", label: "B2B Leads", icon: Users, perm: "manage_leads" },
    { key: "reviews", label: "Reviews", icon: Star, perm: "manage_reviews" },
    { key: "coupons", label: "Coupons", icon: Tag, perm: "manage_coupons" },
    { key: "failed", label: "Failed Payments", icon: AlertTriangle, perm: "view_analytics" },
    { key: "employees", label: "Employees", icon: ShieldCheck, perm: "manage_employees", ownerOnly: true },
    { key: "settings", label: "Settings", icon: SettingsIcon }, // always accessible (for password change)
  ];
  const tabs = allTabs.filter((t) => {
    if (t.ownerOnly && me?.role !== "owner") return false;
    if (!t.perm) return true;
    return hasPerm(t.perm);
  });

  const saveSettings = async (val) => {
    setSaving(true);
    try {
      const { data } = await authed.patch("/admin/settings", { review_prompt_days: Number(val) });
      setSettings(data);
      toast.success("Settings saved");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Save failed");
    } finally { setSaving(false); }
  };

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

  const filteredUsers = users; // legacy — real filtering happens inline in the Customers tab

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
          <AnalyticsDashboard authed={authed} />
        )}

        {tab === "products" && (
          <>
            <div className="flex justify-between items-center mb-6 flex-wrap gap-3">
              <h1 className="font-serif text-4xl">Products</h1>
              <button data-testid="admin-add-product" onClick={()=>setEditing({...empty})} className="inline-flex items-center gap-2 bg-gold text-ink-950 px-4 py-2.5 text-xs uppercase tracking-luxury"><Plus className="w-3.5 h-3.5" />New</button>
            </div>
            {/* Filter bar */}
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <div className="relative flex-1 min-w-[220px]">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-cream/40" />
                <input
                  data-testid="admin-products-search"
                  value={prodQuery}
                  onChange={(e)=>{setProdQuery(e.target.value); setProdPage(1);}}
                  placeholder="Search by name, tagline, SKU or HSN…"
                  className="pl-9 pr-3 py-2.5 bg-ink-950 border border-white/15 focus:border-gold text-sm text-cream w-full outline-none"
                />
              </div>
              <select
                data-testid="admin-products-category"
                value={prodCategory}
                onChange={(e)=>{setProdCategory(e.target.value); setProdPage(1);}}
                className="bg-ink-950 border border-white/15 text-cream text-xs uppercase tracking-luxury px-3 py-2.5"
              >
                <option value="">All categories</option>
                {categories.map((c)=>(<option key={c.slug} value={c.slug}>{c.name}</option>))}
              </select>
              <select
                data-testid="admin-products-stock"
                value={prodStockFilter}
                onChange={(e)=>{setProdStockFilter(e.target.value); setProdPage(1);}}
                className="bg-ink-950 border border-white/15 text-cream text-xs uppercase tracking-luxury px-3 py-2.5"
              >
                <option value="">Any stock</option>
                <option value="low">Low stock (≤ 3)</option>
                <option value="out">Out of stock</option>
                <option value="ok">In stock (&gt; 3)</option>
              </select>
              {(prodQuery || prodCategory || prodStockFilter) && (
                <button
                  onClick={()=>{setProdQuery(""); setProdCategory(""); setProdStockFilter(""); setProdPage(1);}}
                  className="text-[10px] uppercase tracking-luxury text-cream/60 hover:text-gold border border-white/10 px-3 py-2"
                >Clear</button>
              )}
            </div>
            {(() => {
              const q = prodQuery.trim().toLowerCase();
              const filtered = products.filter((p) => {
                if (q) {
                  const hay = [p.name, p.tagline, p.sku, p.hsn_code, (p.tags || []).join(" ")].join(" ").toLowerCase();
                  if (!hay.includes(q)) return false;
                }
                if (prodCategory && p.category !== prodCategory) return false;
                const stock = Number(p.stock || 0);
                if (prodStockFilter === "low" && !(stock > 0 && stock <= 3)) return false;
                if (prodStockFilter === "out" && stock !== 0) return false;
                if (prodStockFilter === "ok" && stock <= 3) return false;
                return true;
              });
              const pages = Math.max(1, Math.ceil(filtered.length / PROD_PAGE_SIZE));
              const page = Math.min(prodPage, pages);
              const slice = filtered.slice((page - 1) * PROD_PAGE_SIZE, page * PROD_PAGE_SIZE);
              return (
                <>
                  <div className="text-[10px] uppercase tracking-luxury text-cream/40 mb-3">
                    Showing {slice.length} of {filtered.length} · {products.length} total
                  </div>
                  <div className="grid gap-3">
                    {slice.length === 0 && (
                      <div className="text-cream/40 text-sm italic py-6">No products match your filters.</div>
                    )}
                    {slice.map((p) => (
                      <div key={p.id} className="hairline p-4 flex items-center gap-4 flex-wrap">
                        <img src={p.hero_image} alt="" className="w-16 h-20 object-cover border border-white/10" />
                        <div className="flex-1 min-w-0">
                          <div className="font-serif text-lg truncate">{p.name}</div>
                          <div className="text-xs text-cream/50 flex flex-wrap gap-x-2">
                            <span>{p.size}</span>
                            <span className={Number(p.stock)===0 ? "text-red-400" : Number(p.stock)<=3 ? "text-yellow-400" : ""}>Stock {p.stock}</span>
                            {p.category && <span className="text-cream/40">· {p.category}</span>}
                            {p.hsn_code && <span className="text-cream/40 font-mono">· HSN {p.hsn_code}</span>}
                            {p.sku && <span className="text-cream/40 font-mono">· {p.sku}</span>}
                          </div>
                        </div>
                        <div className="text-cream">{formatINR(p.price_inr)}</div>
                        <button onClick={()=>{
                          const hasVar = !(p.variants?.length === 1 && (p.variants[0].key === "default" || p.variants[0].label === "Default"));
                          setEditing({
                            ...p,
                            materials: p.materials.join("\n"),
                            gallery: p.gallery.join("\n"),
                            variants: Array.isArray(p.variants) ? p.variants : [],
                            has_variations: hasVar,
                            category: p.category || "",
                            hsn_code: p.hsn_code || "",
                            sku: p.sku || "",
                            weight_grams: p.weight_grams ?? "",
                            length_cm: p.length_cm ?? "",
                            width_cm: p.width_cm ?? "",
                            height_cm: p.height_cm ?? "",
                            tags: Array.isArray(p.tags) ? p.tags.join(", ") : (p.tags || ""),
                            variation_options: Array.isArray(p.variation_options) ? p.variation_options : [],
                          });
                        }} className="text-xs text-gold hover:text-cream border border-gold/30 px-3 py-1.5">Edit</button>
                        <button onClick={()=>deleteProduct(p.id)} className="text-red-400 hover:text-red-300 p-2"><Trash2 className="w-4 h-4" /></button>
                      </div>
                    ))}
                  </div>
                  {pages > 1 && (
                    <Pager page={page} pages={pages} onChange={setProdPage} testid="admin-products-pager" />
                  )}
                </>
              );
            })()}
            {editing && <ProductEditor initial={editing} categories={categories} onCancel={()=>setEditing(null)} onSave={saveProduct} saving={saving} />}
          </>
        )}

        {tab === "orders" && (
          <>
            <div className="flex flex-wrap items-end justify-between gap-3">
              <h1 className="font-serif text-4xl">Orders</h1>
              <BulkInvoiceDownloader authed={authed} />
            </div>
            <div className="mt-4 mb-4 flex flex-wrap items-center gap-2">
              <div className="relative flex-1 min-w-[220px]">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-cream/40" />
                <input
                  data-testid="admin-orders-search"
                  value={orderQuery}
                  onChange={(e)=>{setOrderQuery(e.target.value); setOrderPage(1);}}
                  placeholder="Search by order #, name, email, phone or product…"
                  className="pl-9 pr-3 py-2.5 bg-ink-950 border border-white/15 focus:border-gold text-sm text-cream w-full outline-none"
                />
              </div>
              <select
                data-testid="admin-orders-status"
                value={orderStatus}
                onChange={(e)=>{setOrderStatus(e.target.value); setOrderPage(1);}}
                className="bg-ink-950 border border-white/15 text-cream text-xs uppercase tracking-luxury px-3 py-2.5"
              >
                <option value="">All statuses</option>
                {["pending_payment", "confirmed", "packed", "shipped", "delivered", "cancelled", "payment_failed"].map((s)=>(
                  <option key={s} value={s}>{s.replace(/_/g," ")}</option>
                ))}
              </select>
              {(orderQuery || orderStatus) && (
                <button
                  onClick={()=>{setOrderQuery(""); setOrderStatus(""); setOrderPage(1);}}
                  className="text-[10px] uppercase tracking-luxury text-cream/60 hover:text-gold border border-white/10 px-3 py-2"
                >Clear</button>
              )}
            </div>
            {(() => {
              const q = orderQuery.trim().toLowerCase();
              const filtered = orders.filter((o) => {
                if (orderStatus && o.status !== orderStatus) return false;
                if (!q) return true;
                const c = o.customer || {};
                const items = (o.items || []).map((i)=>i.name || i.product_name || "").join(" ");
                const hay = [o.order_number, c.name, c.email, c.phone, o.coupon_code, items].filter(Boolean).join(" ").toLowerCase();
                return hay.includes(q);
              });
              const pages = Math.max(1, Math.ceil(filtered.length / ORDER_PAGE_SIZE));
              const page = Math.min(orderPage, pages);
              const slice = filtered.slice((page - 1) * ORDER_PAGE_SIZE, page * ORDER_PAGE_SIZE);
              return (
                <>
                  <div className="text-[10px] uppercase tracking-luxury text-cream/40 mb-3">
                    Showing {slice.length} of {filtered.length} · {orders.length} total
                  </div>
                  <div className="grid gap-3">
                    {slice.length === 0 && <div className="text-cream/40 text-sm italic py-6">No orders match your filters.</div>}
                    {slice.map((o) => (
                      <OrderRow key={o.order_number} o={o} onStatus={updateOrderStatus} onTracking={updateOrderTracking} onNotify={setNotifyOrder} onNimbusShip={nimbusShip} onNimbusTrack={nimbusTrack} onNimbusCancel={nimbusCancel} />
                    ))}
                  </div>
                  {pages > 1 && (
                    <Pager page={page} pages={pages} onChange={setOrderPage} testid="admin-orders-pager" />
                  )}
                </>
              );
            })()}
          </>
        )}

        {tab === "homepage" && (
          <HomepageEditor authed={authed} />
        )}

        {tab === "pages" && (
          <PagesTab authed={authed} />
        )}

        {tab === "shipping" && (
          <>
            <ShippingEditor authed={authed} api={api} />
            <NimbusPostCard authed={authed} />
          </>
        )}

        {tab === "gst" && (
          <GstManagementTab authed={authed} />
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
            <CustomerInsightsPanels authed={authed} />
            <div className="flex items-end justify-between flex-wrap gap-4 mt-8">
              <div>
                <h1 className="font-serif text-4xl">Customers</h1>
                <div className="mt-2 text-xs text-cream/40">{users.length} registered · click a row to view full history &amp; send a personal message</div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-cream/40" />
                  <input
                    data-testid="admin-users-search"
                    value={userSearch}
                    onChange={(e) => { setUserSearch(e.target.value); setUserPage(1); }}
                    placeholder="Search by name, email or phone…"
                    className="pl-9 pr-3 py-2.5 bg-ink-950 border border-white/15 focus:border-gold text-sm text-cream w-80 max-w-full outline-none"
                  />
                </div>
                <select
                  data-testid="admin-users-status"
                  value={userStatusFilter}
                  onChange={(e)=>{setUserStatusFilter(e.target.value); setUserPage(1);}}
                  className="bg-ink-950 border border-white/15 text-cream text-xs uppercase tracking-luxury px-3 py-2.5"
                >
                  <option value="">All customers</option>
                  <option value="active">Active only</option>
                  <option value="blocked">Blocked only</option>
                </select>
              </div>
            </div>
            {(() => {
              const q = userSearch.trim().toLowerCase();
              const filtered = users.filter((u) => {
                if (userStatusFilter === "blocked" && !u.blocked) return false;
                if (userStatusFilter === "active" && u.blocked) return false;
                if (!q) return true;
                return (
                  u.email?.toLowerCase().includes(q) ||
                  u.name?.toLowerCase().includes(q) ||
                  (u.phone || "").toLowerCase().includes(q)
                );
              });
              const pages = Math.max(1, Math.ceil(filtered.length / USER_PAGE_SIZE));
              const page = Math.min(userPage, pages);
              const slice = filtered.slice((page - 1) * USER_PAGE_SIZE, page * USER_PAGE_SIZE);
              return (
                <>
                  <div className="text-[10px] uppercase tracking-luxury text-cream/40 mt-4 mb-2">
                    Showing {slice.length} of {filtered.length} · {users.length} total
                  </div>
                  <div className="hairline overflow-x-auto">
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
                        {slice.length === 0 && (
                          <tr><td colSpan={6} className="px-4 py-8 text-center text-cream/40">No customers match your search.</td></tr>
                        )}
                        {slice.map((u) => (
                          <tr
                            key={u.email}
                            data-testid={`admin-user-row-${u.email}`}
                            className={`border-b border-white/5 hover:bg-white/5 cursor-pointer transition-colors ${u.blocked ? "opacity-60" : ""}`}
                            onClick={() => openUserDetail(u.email)}
                          >
                            <td className="px-4 py-4">
                              <div className="font-serif text-cream flex items-center gap-2">
                                {u.name}
                                {u.blocked && (
                                  <span className="text-[9px] uppercase tracking-luxury text-red-400 border border-red-400/40 px-1.5 py-0.5">Blocked</span>
                                )}
                              </div>
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
                              <div className="inline-flex items-center gap-1.5 flex-wrap justify-end">
                                <button
                                  data-testid={`admin-user-message-${u.email}`}
                                  onClick={(e) => { e.stopPropagation(); openUserDetail(u.email); }}
                                  className="inline-flex items-center gap-1.5 text-[10px] uppercase tracking-luxury text-gold hover:text-cream border border-gold/40 px-2 py-1"
                                >
                                  <MessageSquare className="w-3 h-3" /> View
                                  {u.messages_count > 0 && <span className="ml-1 text-cream/50">({u.messages_count})</span>}
                                </button>
                                <button
                                  data-testid={`admin-user-block-${u.email}`}
                                  onClick={async (e) => {
                                    e.stopPropagation();
                                    const nextBlocked = !u.blocked;
                                    if (!window.confirm(nextBlocked ? `Block ${u.email}? They will not be able to log in.` : `Unblock ${u.email}?`)) return;
                                    try {
                                      await authed.patch(`/admin/users/${encodeURIComponent(u.email)}`, { blocked: nextBlocked });
                                      toast.success(nextBlocked ? "Customer blocked" : "Customer unblocked");
                                      reload();
                                    } catch (err) {
                                      toast.error(err?.response?.data?.detail || "Update failed");
                                    }
                                  }}
                                  className={`text-[10px] uppercase tracking-luxury px-2 py-1 border ${u.blocked ? "border-emerald-400/40 text-emerald-400 hover:bg-emerald-400/10" : "border-yellow-400/40 text-yellow-400 hover:bg-yellow-400/10"}`}
                                >{u.blocked ? "Unblock" : "Block"}</button>
                                <button
                                  data-testid={`admin-user-delete-${u.email}`}
                                  onClick={async (e) => {
                                    e.stopPropagation();
                                    if (!window.confirm(`Delete customer ${u.email}? Orders will be preserved for records, but the account will be removed.`)) return;
                                    try {
                                      await authed.delete(`/admin/users/${encodeURIComponent(u.email)}`);
                                      toast.success("Customer deleted");
                                      reload();
                                    } catch (err) {
                                      toast.error(err?.response?.data?.detail || "Delete failed");
                                    }
                                  }}
                                  className="text-red-400 hover:text-red-300 p-1.5 border border-red-400/30"
                                  title="Delete customer"
                                ><Trash2 className="w-3 h-3" /></button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {pages > 1 && (
                    <Pager page={page} pages={pages} onChange={setUserPage} testid="admin-users-pager" />
                  )}
                </>
              );
            })()}
            {userDetail && (
              <UserDetailDrawer detail={userDetail} onClose={() => setUserDetail(null)} onSendMessage={sendMessage} />
            )}
          </>
        )}

        {tab === "reviews" && (
          <>
            <h1 className="font-serif text-4xl">Reviews</h1>
            <p className="mt-2 text-sm text-cream/50">Toggle the ⭐ star to mark a review as <em>featured</em>. Featured reviews are shown on the homepage.</p>
            <div className="mt-4 mb-4 flex flex-wrap items-center gap-2">
              <div className="relative flex-1 min-w-[220px]">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-cream/40" />
                <input
                  data-testid="admin-reviews-search"
                  value={reviewQuery}
                  onChange={(e)=>{setReviewQuery(e.target.value); setReviewPage(1);}}
                  placeholder="Search by title, author, location or body…"
                  className="pl-9 pr-3 py-2.5 bg-ink-950 border border-white/15 focus:border-gold text-sm text-cream w-full outline-none"
                />
              </div>
              <select
                data-testid="admin-reviews-rating"
                value={reviewRating}
                onChange={(e)=>{setReviewRating(e.target.value); setReviewPage(1);}}
                className="bg-ink-950 border border-white/15 text-cream text-xs uppercase tracking-luxury px-3 py-2.5"
              >
                <option value="">Any rating</option>
                {[5,4,3,2,1].map((n)=>(<option key={n} value={n}>{n} stars</option>))}
              </select>
              <select
                data-testid="admin-reviews-featured"
                value={reviewFeatured}
                onChange={(e)=>{setReviewFeatured(e.target.value); setReviewPage(1);}}
                className="bg-ink-950 border border-white/15 text-cream text-xs uppercase tracking-luxury px-3 py-2.5"
              >
                <option value="">All</option>
                <option value="yes">Featured only</option>
                <option value="no">Not featured</option>
              </select>
              {(reviewQuery || reviewRating || reviewFeatured) && (
                <button
                  onClick={()=>{setReviewQuery(""); setReviewRating(""); setReviewFeatured(""); setReviewPage(1);}}
                  className="text-[10px] uppercase tracking-luxury text-cream/60 hover:text-gold border border-white/10 px-3 py-2"
                >Clear</button>
              )}
            </div>
            {(() => {
              const q = reviewQuery.trim().toLowerCase();
              const filtered = reviews.filter((r) => {
                if (reviewRating && Number(r.rating) !== Number(reviewRating)) return false;
                if (reviewFeatured === "yes" && !r.featured) return false;
                if (reviewFeatured === "no" && r.featured) return false;
                if (!q) return true;
                const hay = [r.title, r.author, r.location, r.body].filter(Boolean).join(" ").toLowerCase();
                return hay.includes(q);
              });
              const pages = Math.max(1, Math.ceil(filtered.length / REVIEW_PAGE_SIZE));
              const page = Math.min(reviewPage, pages);
              const slice = filtered.slice((page - 1) * REVIEW_PAGE_SIZE, page * REVIEW_PAGE_SIZE);
              return (
                <>
                  <div className="text-[10px] uppercase tracking-luxury text-cream/40 mb-3">
                    Showing {slice.length} of {filtered.length} · {reviews.length} total
                  </div>
                  <div className="grid gap-3">
                    {slice.length === 0 && <div className="text-cream/40 text-sm italic py-6">No reviews match your filters.</div>}
                    {slice.map((r) => (
                      <div key={r.id} className={`hairline p-4 flex gap-4 ${r.featured ? "border-gold/40" : ""}`} data-testid={`admin-review-row-${r.id}`}>
                        {r.image && <img src={r.image} alt="" className="w-16 h-16 object-cover" />}
                        <div className="flex-1 min-w-0">
                          <div className="font-serif text-lg">{r.title} <span className="text-gold text-sm">· {r.rating}★</span> {r.featured && <span className="text-[10px] uppercase tracking-luxury text-gold ml-2">Featured</span>}</div>
                          <div className="text-xs text-cream/50">{r.author} · {r.location}</div>
                          <div className="text-sm text-cream/70 mt-2 line-clamp-2">{r.body}</div>
                        </div>
                        <button
                          onClick={async () => {
                            try {
                              await authed.patch(`/admin/reviews/${r.id}`, { featured: !r.featured });
                              toast.success(!r.featured ? "Marked as featured" : "Removed from featured");
                              reload();
                            } catch (err) {
                              toast.error("Update failed");
                            }
                          }}
                          className={`p-2 border transition-colors ${r.featured ? "border-gold text-gold hover:bg-gold/10" : "border-white/20 text-cream/40 hover:border-gold hover:text-gold"}`}
                          title={r.featured ? "Unfeature" : "Feature on homepage"}
                          data-testid={`admin-review-feature-toggle-${r.id}`}
                        >
                          <Star className={`w-4 h-4 ${r.featured ? "fill-current" : ""}`} />
                        </button>
                        <button onClick={async()=>{
                          if (!window.confirm("Delete this review?")) return;
                          await authed.delete(`/admin/reviews/${r.id}`); toast.success("Deleted"); reload();
                        }} className="text-red-400 p-2"><Trash2 className="w-4 h-4" /></button>
                      </div>
                    ))}
                  </div>
                  {pages > 1 && (
                    <Pager page={page} pages={pages} onChange={setReviewPage} testid="admin-reviews-pager" />
                  )}
                </>
              );
            })()}
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
            <div className="mt-4 mb-4 flex flex-wrap items-center gap-2">
              <div className="relative flex-1 min-w-[220px]">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-cream/40" />
                <input
                  data-testid="admin-failed-search"
                  value={failedQuery}
                  onChange={(e)=>{setFailedQuery(e.target.value); setFailedPage(1);}}
                  placeholder="Search by email, phone, name, order # or error code…"
                  className="pl-9 pr-3 py-2.5 bg-ink-950 border border-white/15 focus:border-gold text-sm text-cream w-full outline-none"
                />
              </div>
              {failedQuery && (
                <button
                  onClick={()=>{setFailedQuery(""); setFailedPage(1);}}
                  className="text-[10px] uppercase tracking-luxury text-cream/60 hover:text-gold border border-white/10 px-3 py-2"
                >Clear</button>
              )}
            </div>
            {failedPayments.length === 0 ? (
              <div className="mt-8 hairline p-8 text-center text-cream/50">No failed payments logged. ✨</div>
            ) : (() => {
              const q = failedQuery.trim().toLowerCase();
              const filtered = failedPayments.filter((f) => {
                if (!q) return true;
                const hay = [f.customer_name, f.customer_email, f.customer_phone, f.order_number, f.error_code, f.error_description].filter(Boolean).join(" ").toLowerCase();
                return hay.includes(q);
              });
              const pages = Math.max(1, Math.ceil(filtered.length / FAILED_PAGE_SIZE));
              const page = Math.min(failedPage, pages);
              const slice = filtered.slice((page - 1) * FAILED_PAGE_SIZE, page * FAILED_PAGE_SIZE);
              return (
                <>
                  <div className="text-[10px] uppercase tracking-luxury text-cream/40 mb-3">
                    Showing {slice.length} of {filtered.length} · {failedPayments.length} total
                  </div>
                  <div className="grid gap-3">
                    {slice.length === 0 && <div className="text-cream/40 text-sm italic py-6">No failed payments match your search.</div>}
                    {slice.map((f) => (
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
                          <button
                            data-testid={`admin-failed-delete-${f.id}`}
                            onClick={async () => {
                              if (!window.confirm("Delete this failed payment log? This can't be undone.")) return;
                              try {
                                await authed.delete(`/admin/failed-payments/${f.id}`);
                                toast.success("Deleted");
                                reload();
                              } catch (err) {
                                toast.error(err?.response?.data?.detail || "Delete failed");
                              }
                            }}
                            className="text-red-400 hover:text-red-300 p-2"
                            title="Delete log"
                          ><Trash2 className="w-4 h-4" /></button>
                        </div>
                      </div>
                    ))}
                  </div>
                  {pages > 1 && (
                    <Pager page={page} pages={pages} onChange={setFailedPage} testid="admin-failed-pager" />
                  )}
                </>
              );
            })()}
          </>
        )}
        {tab === "settings" && (
          <>
            <h1 className="font-serif text-4xl">Settings</h1>
            <p className="mt-2 text-sm text-cream/50">Fine-tune how the storefront behaves for logged-in customers.</p>
            <div className="mt-8 hairline p-6 max-w-xl">
              <div className="text-[10px] uppercase tracking-luxury text-gold-soft">Automated Reviews</div>
              <div className="mt-2 font-serif text-2xl text-cream">Review-prompt delay</div>
              <p className="mt-2 text-sm text-cream/60">
                After a piece is delivered, we wait this many days before asking the collector for their review. Set to 0 to prompt immediately.
              </p>
              <div className="mt-6 flex items-center gap-3">
                <input
                  type="number"
                  min="0"
                  max="90"
                  value={settings.review_prompt_days ?? 7}
                  onChange={(e) => setSettings({ ...settings, review_prompt_days: e.target.value })}
                  data-testid="admin-settings-review-days"
                  className="w-24 bg-ink-950 border border-white/15 focus:border-gold outline-none px-3 py-2.5 text-cream text-lg text-center font-serif"
                />
                <span className="text-sm text-cream/60">days after delivery</span>
                <button
                  data-testid="admin-settings-save"
                  onClick={() => saveSettings(settings.review_prompt_days)}
                  disabled={saving}
                  className="ml-auto bg-gold text-ink-950 px-5 py-2.5 text-xs uppercase tracking-luxury hover:bg-cream disabled:opacity-60"
                >
                  {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin inline" /> : "Save"}
                </button>
              </div>
            </div>

            {/* Admin password reset */}
            <div className="mt-8">
              <PasswordChangeCard authed={authed} />
            </div>

            {/* Admin Google whitelist */}
            <div className="mt-8">
              <WhitelistCard authed={authed} />
            </div>

            {/* Broadcast email */}
            <div className="mt-8">
              <BroadcastCard authed={authed} />
            </div>
          </>
        )}

        {tab === "employees" && (
          <EmployeesTab authed={authed} me={me} />
        )}
      </main>
      {notifyOrder && (
        <OrderNotifyDialog authed={authed} order={notifyOrder} onClose={() => setNotifyOrder(null)} />
      )}
      <Toaster theme="dark" position="bottom-center" />
    </div>
  );
}

function CustomerInsightsPanels({ authed }) {
  const [couponData, setCouponData] = useState({ codes: [], customers: [] });
  const [wishlistData, setWishlistData] = useState({ total_wishlists: 0, by_customer: [], by_product: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authed) return;
    Promise.all([
      authed.get("/admin/analytics/coupon-usage"),
      authed.get("/admin/analytics/wishlist-usage"),
    ])
      .then(([c, w]) => { setCouponData(c.data); setWishlistData(w.data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [authed]);

  if (loading) return <div className="text-cream/40 text-xs"><Loader2 className="w-3.5 h-3.5 animate-spin inline" /> Loading insights…</div>;

  return (
    <div className="grid lg:grid-cols-2 gap-4">
      <div className="hairline p-5 bg-ink-900/50" data-testid="customer-coupon-panel">
        <div className="flex items-center gap-2 mb-3">
          <Tag className="w-4 h-4 text-gold" />
          <div className="text-[10px] uppercase tracking-luxury text-gold-soft">Coupons used per customer</div>
        </div>
        {couponData.customers.length === 0 ? (
          <div className="text-sm text-cream/40">No coupons have been used yet.</div>
        ) : (
          <div className="max-h-64 overflow-y-auto pr-2 divide-y divide-white/5">
            {couponData.customers.map((row, i) => (
              <div key={`${row.customer_email}-${row.code}-${i}`} className="flex items-center gap-3 py-2 text-sm">
                <div className="flex-1 min-w-0">
                  <div className="text-cream/90 truncate">{row.customer_name || row.customer_email}</div>
                  <div className="text-[10px] text-cream/40">{row.customer_email}</div>
                </div>
                <span className="font-mono text-gold text-xs">{row.code}</span>
                <span className="text-cream/70 text-xs w-8 text-right">{row.uses}×</span>
                <span className="text-cream/40 text-[10px] w-24 text-right">−₹{row.total_discount_inr.toLocaleString("en-IN")}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="hairline p-5 bg-ink-900/50" data-testid="customer-wishlist-panel">
        <div className="flex items-center gap-2 mb-3">
          <Star className="w-4 h-4 text-gold" />
          <div className="text-[10px] uppercase tracking-luxury text-gold-soft">Wishlists per customer · {wishlistData.total_wishlists} saves</div>
        </div>
        {wishlistData.by_customer.length === 0 ? (
          <div className="text-sm text-cream/40">Nothing wishlisted yet.</div>
        ) : (
          <div className="max-h-64 overflow-y-auto pr-2 divide-y divide-white/5">
            {wishlistData.by_customer.map((c) => (
              <div key={c.user_email} className="py-2 text-sm">
                <div className="flex justify-between items-center">
                  <span className="text-cream/90 truncate">{c.user_email}</span>
                  <span className="text-gold text-xs">{c.count} item{c.count === 1 ? "" : "s"}</span>
                </div>
                <div className="mt-1 text-[11px] text-cream/50 truncate">
                  {c.items.map((i) => i.product_name).join(" · ")}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
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

function ProductEditor({ initial, categories = [], onCancel, onSave, saving }) {
  const [f, setF] = useState(initial);
  const upd = (k) => (e) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  const variants = Array.isArray(f.variants) ? f.variants : [];
  const options = Array.isArray(f.variation_options) ? f.variation_options : [];

  const updVariant = (idx, field) => (e) => {
    const v = e && e.target ? (e.target.type === "checkbox" ? e.target.checked : e.target.value) : e;
    setF((prev) => {
      const arr = [...(prev.variants || [])];
      arr[idx] = { ...arr[idx], [field]: v };
      return { ...prev, variants: arr };
    });
  };
  const addVariant = () => setF((prev) => ({
    ...prev,
    variants: [...(prev.variants || []), { key: "", label: "", hex: "#D4AF37", image: "", size: "", stock: 5, price_inr: null, mrp_inr: null }],
  }));
  const removeVariant = (idx) => setF((prev) => ({ ...prev, variants: (prev.variants || []).filter((_, i) => i !== idx) }));

  /* Task 3 — variation_options helpers (Shape / Frame / Thickness / Gift Wrap / Care Kit / Mount) */
  const addOption = (preset) => setF((prev) => ({
    ...prev,
    variation_options: [
      ...(prev.variation_options || []),
      preset || { key: "", label: "New option", type: "select", required: false, help_text: "", values: [] },
    ],
  }));
  const updOption = (oi, field, val) => setF((prev) => {
    const arr = [...(prev.variation_options || [])];
    arr[oi] = { ...arr[oi], [field]: val };
    return { ...prev, variation_options: arr };
  });
  const removeOption = (oi) => setF((prev) => ({
    ...prev,
    variation_options: (prev.variation_options || []).filter((_, i) => i !== oi),
  }));
  const addOptionValue = (oi) => setF((prev) => {
    const arr = [...(prev.variation_options || [])];
    const vals = [...(arr[oi]?.values || [])];
    vals.push({ key: "", label: "", hex: "", image: "", price_delta_inr: 0 });
    arr[oi] = { ...arr[oi], values: vals };
    return { ...prev, variation_options: arr };
  });
  const updOptionValue = (oi, vi, field, val) => setF((prev) => {
    const arr = [...(prev.variation_options || [])];
    const vals = [...(arr[oi]?.values || [])];
    vals[vi] = { ...vals[vi], [field]: val };
    arr[oi] = { ...arr[oi], values: vals };
    return { ...prev, variation_options: arr };
  });
  const removeOptionValue = (oi, vi) => setF((prev) => {
    const arr = [...(prev.variation_options || [])];
    arr[oi] = { ...arr[oi], values: (arr[oi]?.values || []).filter((_, i) => i !== vi) };
    return { ...prev, variation_options: arr };
  });

  /* Presets requested by the atelier (Task 3) — one-click add so the uploader
     never has to think about the correct key/label/type. */
  const OPTION_PRESETS = [
    { key: "shape",     label: "Shape",     type: "select", help_text: "Product outline: round, square, oval, freeform.",
      values: [
        { key: "round",  label: "Round",  price_delta_inr: 0 },
        { key: "square", label: "Square", price_delta_inr: 0 },
        { key: "oval",   label: "Oval",   price_delta_inr: 0 },
      ] },
    { key: "frame",     label: "Frame",     type: "select", help_text: "With a decorative border or borderless.",
      values: [
        { key: "borderless", label: "Borderless", price_delta_inr: 0 },
        { key: "bordered",   label: "With Border", price_delta_inr: 1500 },
      ] },
    { key: "thickness", label: "Thickness", type: "select", help_text: "Thickness of the resin pour.",
      values: [
        { key: "standard", label: "Standard (12 mm)", price_delta_inr: 0 },
        { key: "premium",  label: "Premium (18 mm)",  price_delta_inr: 1200 },
      ] },
    { key: "gift_wrap", label: "Gift Wrap", type: "toggle", help_text: "Adds premium gift packaging + handwritten note.",
      values: [
        { key: "no",  label: "No",  price_delta_inr: 0, is_default: true },
        { key: "yes", label: "Yes · Premium wrap", price_delta_inr: 500 },
      ] },
    { key: "care_kit",  label: "Care Kit",  type: "toggle", help_text: "Add resin care + microfibre cleaning cloth set.",
      values: [
        { key: "no",  label: "No",  price_delta_inr: 0, is_default: true },
        { key: "yes", label: "Yes · Add care kit", price_delta_inr: 750 },
      ] },
    { key: "mount",     label: "Mounting",  type: "select", help_text: "Pre-installed wall hardware or tabletop stand.",
      values: [
        { key: "wall_mount",  label: "Wall Mount (hardware pre-installed)", price_delta_inr: 0 },
        { key: "tabletop",    label: "Tabletop Stand", price_delta_inr: 600 },
      ] },
  ];

  return (
    <div className="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4" onClick={onCancel}>
      <div className="bg-ink-900 border border-white/10 w-[min(880px,95vw)] max-h-[90vh] overflow-y-auto p-8" onClick={(e)=>e.stopPropagation()} data-testid="product-editor-modal">
        <div className="flex justify-between items-center">
          <h3 className="font-serif text-2xl">{initial.id ? "Edit product" : "New product"}</h3>
          <button onClick={onCancel} className="text-cream/50 hover:text-cream text-sm">Cancel</button>
        </div>

        <div className="mt-6 grid sm:grid-cols-2 gap-4">
          <Fld label="Slug (URL, e.g. obsidian-aurora)"><input value={f.slug} onChange={upd("slug")} className={inp} required data-testid="pe-slug" /></Fld>
          <Fld label="Product name"><input value={f.name} onChange={upd("name")} className={inp} required data-testid="pe-name" /></Fld>
          <Fld label="Tagline"><input value={f.tagline} onChange={upd("tagline")} className={inp} required /></Fld>
          <Fld label="Size / dimensions"><input value={f.size} onChange={upd("size")} className={inp} required /></Fld>
          <Fld label="Price (₹)"><input type="number" value={f.price_inr} onChange={upd("price_inr")} className={inp} required data-testid="pe-price" /></Fld>
          <Fld label="MRP (₹)"><input type="number" value={f.mrp_inr} onChange={upd("mrp_inr")} className={inp} required data-testid="pe-mrp" /></Fld>
          <Fld label="Craft hours"><input type="number" value={f.craft_hours} onChange={upd("craft_hours")} className={inp} /></Fld>
          <Fld label="Stock (base)"><input type="number" value={f.stock} onChange={upd("stock")} className={inp} data-testid="pe-stock" /></Fld>
        </div>

        <div className="mt-6 grid gap-4">
          <Fld label="Main image" hint="Shown on shop cards and as the hero on the product page.">
            <CloudinaryUpload
              value={f.hero_image}
              onChange={(url) => setF({ ...f, hero_image: url })}
              folder="artyfex/products"
              label="Drop main image or click to upload"
              testid="pe-hero-image"
            />
            <input value={f.hero_image} onChange={upd("hero_image")} className={`${inp} mt-2 font-mono text-xs`} required data-testid="pe-hero-image-url" placeholder="or paste Cloudinary/CDN URL" />
          </Fld>
          <Fld label="Gallery images" hint="Extra photos shown in the gallery under the main image.">
            <CloudinaryUpload
              value={(f.gallery || "").split("\n").map(s => s.trim()).filter(Boolean)}
              onChange={(urls) => setF({ ...f, gallery: (urls || []).join("\n") })}
              multiple
              folder="artyfex/products"
              label="Drop gallery images or click to upload"
              testid="pe-gallery"
            />
            <textarea rows={2} value={f.gallery} onChange={upd("gallery")} className={`${inp} mt-2 font-mono text-xs`} placeholder="or paste one URL per line" data-testid="pe-gallery-urls" />
          </Fld>
          <Fld label="Description"><textarea rows={3} value={f.description} onChange={upd("description")} className={inp} /></Fld>
          <Fld label="Materials (one per line)"><textarea rows={3} value={f.materials} onChange={upd("materials")} className={inp} /></Fld>
        </div>

        {/* Phase A · Commerce, Tax & Logistics fields */}
        <div className="mt-8 border border-white/10 p-5 bg-ink-950/40">
          <div className="text-[10px] uppercase tracking-luxury text-gold-soft flex items-center gap-2">
            <Percent className="w-3 h-3" /> Commerce · Tax · Logistics
          </div>
          <div className="mt-1 text-xs text-cream/50">Category &amp; HSN drive the GST calculation at checkout. Weight and packaging dimensions power shipping quotes.</div>

          <div className="mt-6 grid sm:grid-cols-2 gap-4">
            <Fld label="Category" hint="Manage the list under the GST tab → Categories.">
              <select value={f.category || ""} onChange={upd("category")} className={inp} data-testid="pe-category">
                <option value="">— Uncategorised —</option>
                {categories.filter((c) => c.active !== false).map((c) => (
                  <option key={c.slug} value={c.slug} className="bg-ink-900">{c.name}</option>
                ))}
              </select>
            </Fld>
            <Fld label="HSN code" hint="4–8 digit Harmonised System of Nomenclature. Priority target for GST lookup.">
              <input list="pe-hsn-datalist" value={f.hsn_code || ""} onChange={upd("hsn_code")} className={`${inp} font-mono`} placeholder="e.g. 7009" data-testid="pe-hsn" />
              <datalist id="pe-hsn-datalist">
                <option value="7009">Mirrors (glass)</option>
                <option value="9701">Handmade paintings / art</option>
                <option value="3926">Articles of plastics / resin</option>
                <option value="9403">Furniture</option>
                <option value="9405">Lamps &amp; lighting</option>
                <option value="4414">Wooden frames</option>
                <option value="6913">Ceramic ornaments</option>
              </datalist>
            </Fld>
            <Fld label="SKU (Stock Keeping Unit)" hint="Internal reference — e.g. ARF-OBS-2X3.">
              <input value={f.sku || ""} onChange={upd("sku")} className={`${inp} font-mono`} placeholder="ARF-XXX-0001" data-testid="pe-sku" />
            </Fld>
            <Fld label="Weight (grams)" hint="Used by the shipping engine.">
              <input type="number" min="0" value={f.weight_grams ?? ""} onChange={upd("weight_grams")} className={inp} placeholder="e.g. 8500" data-testid="pe-weight" />
            </Fld>
          </div>

          <div className="mt-4">
            <div className="text-[10px] uppercase tracking-luxury text-cream/50 mb-2">Package dimensions (cm)</div>
            <div className="grid grid-cols-3 gap-3">
              <Fld label="Length"><input type="number" min="0" step="0.1" value={f.length_cm ?? ""} onChange={upd("length_cm")} className={inp} data-testid="pe-length" /></Fld>
              <Fld label="Width"><input type="number" min="0" step="0.1" value={f.width_cm ?? ""} onChange={upd("width_cm")} className={inp} data-testid="pe-width" /></Fld>
              <Fld label="Height"><input type="number" min="0" step="0.1" value={f.height_cm ?? ""} onChange={upd("height_cm")} className={inp} data-testid="pe-height" /></Fld>
            </div>
          </div>

          <div className="mt-4">
            <Fld label="Tags (comma separated)" hint="Free-form labels e.g. bestseller, gifting, oversized.">
              <input value={f.tags || ""} onChange={upd("tags")} className={inp} placeholder="signature, statement, geode" data-testid="pe-tags" />
            </Fld>
          </div>
        </div>

        {/* Variations toggle */}
        <div className="mt-8 border border-white/10 p-5 bg-ink-950/40">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={!!f.has_variations}
              onChange={(e) => setF({ ...f, has_variations: e.target.checked, variants: e.target.checked ? (variants.length > 0 && !(variants[0]?.key === "default") ? variants : [{ key: "", label: "", hex: "#D4AF37", image: "", size: "", stock: 5, price_inr: null, mrp_inr: null }]) : [] })}
              className="accent-gold w-4 h-4"
              data-testid="pe-has-variations"
            />
            <div>
              <div className="text-sm text-cream">Product has colour swatches?</div>
              <div className="text-xs text-cream/50">Tick only if the buyer must pick a colour (e.g. gold / silver / rose). Leave unticked for one-of-one pieces or if colour doesn&apos;t apply — the colour picker will be hidden on the product page.</div>
            </div>
          </label>

          {f.has_variations && (
            <div className="mt-6 space-y-4" data-testid="pe-variations-editor">
              <div className="text-[10px] uppercase tracking-luxury text-gold-soft">Colour swatches · {variants.length}</div>
              {variants.length === 0 && (
                <div className="text-xs text-cream/50">No colour swatches yet. Click &quot;+ Add colour&quot; to add one.</div>
              )}
              {variants.map((v, idx) => (
                <div key={idx} className="border border-white/10 p-4 bg-ink-900" data-testid={`pe-variant-row-${idx}`}>
                  <div className="flex items-center justify-between mb-3">
                    <div className="text-xs text-cream/60">Variation {idx + 1}</div>
                    <button type="button" onClick={() => removeVariant(idx)} className="text-red-400 hover:text-red-300 p-1" data-testid={`pe-variant-remove-${idx}`}>
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  <div className="grid sm:grid-cols-2 gap-3">
                    <Fld label="Label (shown to buyers, e.g. 'Signature Gold · 2 ft')">
                      <input value={v.label || ""} onChange={updVariant(idx, "label")} className={inp} data-testid={`pe-variant-label-${idx}`} />
                    </Fld>
                    <Fld label="Internal key (auto = slug of label)">
                      <input value={v.key || ""} onChange={updVariant(idx, "key")} onBlur={(e)=>{ if (!e.target.value && v.label) updVariant(idx,"key")({ target:{ value: v.label.toLowerCase().replace(/\s+/g,"-").replace(/[^a-z0-9\-]/g,"") }}); }} className={inp} placeholder="e.g. signature-gold-2ft" />
                    </Fld>
                    <Fld label="Size (optional, e.g. 24 in / 2 ft)">
                      <input value={v.size || ""} onChange={updVariant(idx, "size")} className={inp} />
                    </Fld>
                    <Fld label="Colour" hint="Pick a colour — the swatch is shown to buyers.">
                      <div className="flex items-center gap-2">
                        <input type="color" value={v.hex || "#333333"} onChange={updVariant(idx, "hex")} className="w-12 h-10 border border-white/15 bg-ink-950 cursor-pointer" />
                        <input value={v.hex || ""} onChange={updVariant(idx, "hex")} className={`${inp} font-mono`} placeholder="#D4AF37" />
                      </div>
                    </Fld>
                    <Fld label="Stock available">
                      <input type="number" min="0" value={v.stock ?? 0} onChange={updVariant(idx, "stock")} className={inp} data-testid={`pe-variant-stock-${idx}`} />
                    </Fld>
                    <Fld label="Price override (₹) — blank = use base price">
                      <input type="number" min="0" value={v.price_inr ?? ""} onChange={updVariant(idx, "price_inr")} className={inp} placeholder="Same as base" />
                    </Fld>
                    <div className="sm:col-span-2">
                      <Fld label="MRP override (₹) — blank = use base MRP">
                        <input type="number" min="0" value={v.mrp_inr ?? ""} onChange={updVariant(idx, "mrp_inr")} className={inp} placeholder="Same as base MRP" />
                      </Fld>
                    </div>
                    <div className="sm:col-span-2">
                      <Fld label="Image for this variation" hint="Shown when the buyer picks this variation.">
                        <CloudinaryUpload
                          value={v.image || ""}
                          onChange={(url) => updVariant(idx, "image")({ target: { value: url } })}
                          folder="artyfex/products/variants"
                          label="Drop variation image or click to upload"
                          testid={`pe-variant-image-${idx}`}
                        />
                        <input value={v.image || ""} onChange={updVariant(idx, "image")} className={`${inp} mt-2 font-mono text-xs`} placeholder="or paste URL" data-testid={`pe-variant-image-url-${idx}`} />
                      </Fld>
                    </div>
                  </div>
                </div>
              ))}
              <button type="button" onClick={addVariant} className="inline-flex items-center gap-2 text-xs uppercase tracking-luxury border border-gold/40 text-gold px-4 py-2.5 hover:bg-gold/10" data-testid="pe-add-variation">
                <Plus className="w-3.5 h-3.5" /> Add colour
              </button>
            </div>
          )}
        </div>

        {/* ----------------------------------------------------------------
         * Task 3 — Extra variation options
         * (Shape / Frame / Thickness / Gift Wrap / Care Kit / Mounting …)
         * Distinct from colour swatches: buyers can pick one value per option
         * and the choice snapshots into the order line (visible in Admin
         * order details) with a cumulative price delta.
         * ---------------------------------------------------------------- */}
        <div className="mt-6 border border-white/10 p-5 bg-ink-950/40">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <div className="text-sm text-cream">Extra option groups (shape · frame · thickness · gift wrap · care kit · mount)</div>
              <div className="text-xs text-cream/50 mt-1 max-w-2xl">
                Optional. Add any option group the buyer must choose <em>in addition</em> to colour.
                Each option can have a price delta (e.g. Gift Wrap +₹500). Selected values will be
                saved onto the order and shown in <b>Admin → Orders → View details</b>.
              </div>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {OPTION_PRESETS.filter(p => !(options || []).some(o => o.key === p.key)).map((p) => (
                <button
                  key={p.key}
                  type="button"
                  onClick={() => addOption(p)}
                  data-testid={`pe-add-preset-${p.key}`}
                  className="text-[10px] uppercase tracking-luxury text-gold-soft border border-gold/25 px-2.5 py-1 hover:bg-gold/10"
                >+ {p.label}</button>
              ))}
              <button
                type="button"
                onClick={() => addOption()}
                data-testid="pe-add-option-custom"
                className="text-[10px] uppercase tracking-luxury text-cream/70 border border-white/15 px-2.5 py-1 hover:text-gold hover:border-gold/40"
              >+ Custom</button>
            </div>
          </div>

          {options.length === 0 && (
            <div className="mt-4 text-[11px] text-cream/40 italic">No extra options yet. Click a preset above to add one, or &ldquo;+ Custom&rdquo; for a free-form option.</div>
          )}

          <div className="mt-4 space-y-3">
            {options.map((opt, oi) => (
              <div key={oi} className="border border-white/10 bg-ink-900 p-4" data-testid={`pe-option-${oi}`}>
                <div className="flex flex-wrap items-center gap-3 mb-3">
                  <input
                    value={opt.label || ""}
                    onChange={(e) => updOption(oi, "label", e.target.value)}
                    onBlur={(e) => { if (!opt.key && e.target.value) updOption(oi, "key", e.target.value.toLowerCase().replace(/\s+/g, "_").replace(/[^a-z0-9_]/g, "")); }}
                    placeholder="Option label — e.g. Shape"
                    className="bg-ink-950 border border-white/15 focus:border-gold text-sm text-cream px-3 py-2 outline-none flex-1 min-w-[160px]"
                    data-testid={`pe-option-label-${oi}`}
                  />
                  <input
                    value={opt.key || ""}
                    onChange={(e) => updOption(oi, "key", e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, ""))}
                    placeholder="key (auto)"
                    className="bg-ink-950 border border-white/15 focus:border-gold text-xs font-mono text-cream/70 px-3 py-2 outline-none w-32"
                  />
                  <select
                    value={opt.type || "select"}
                    onChange={(e) => updOption(oi, "type", e.target.value)}
                    className="bg-ink-950 border border-white/15 text-xs uppercase tracking-luxury text-cream px-3 py-2 outline-none"
                  >
                    <option value="select">Dropdown</option>
                    <option value="toggle">Add-on toggle</option>
                  </select>
                  <label className="flex items-center gap-1.5 text-[10px] uppercase tracking-luxury text-cream/60">
                    <input type="checkbox" checked={!!opt.required} onChange={(e) => updOption(oi, "required", e.target.checked)} className="accent-gold" /> Required
                  </label>
                  <button type="button" onClick={() => removeOption(oi)} className="text-red-400 hover:text-red-300 p-1" data-testid={`pe-option-remove-${oi}`}>
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
                <input
                  value={opt.help_text || ""}
                  onChange={(e) => updOption(oi, "help_text", e.target.value)}
                  placeholder="Help note shown to buyer (optional)"
                  className="w-full bg-ink-950 border border-white/10 text-[11px] italic text-cream/60 px-3 py-1.5 outline-none focus:border-gold mb-3"
                />
                {/* Values */}
                <div className="space-y-1.5">
                  {(opt.values || []).map((v, vi) => (
                    <div key={vi} className="grid grid-cols-[1fr_1fr_80px_100px_auto] gap-2 items-center">
                      <input
                        value={v.label || ""}
                        onChange={(e) => updOptionValue(oi, vi, "label", e.target.value)}
                        onBlur={(e) => { if (!v.key && e.target.value) updOptionValue(oi, vi, "key", e.target.value.toLowerCase().replace(/\s+/g, "_").replace(/[^a-z0-9_]/g, "")); }}
                        placeholder="Value label — e.g. Round"
                        className="bg-ink-950 border border-white/10 text-xs text-cream px-2.5 py-1.5 outline-none focus:border-gold"
                        data-testid={`pe-option-${oi}-value-${vi}`}
                      />
                      <input
                        value={v.key || ""}
                        onChange={(e) => updOptionValue(oi, vi, "key", e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, ""))}
                        placeholder="key"
                        className="bg-ink-950 border border-white/10 text-[11px] font-mono text-cream/60 px-2.5 py-1.5 outline-none focus:border-gold"
                      />
                      <input
                        type="number" min="0"
                        value={v.price_delta_inr ?? 0}
                        onChange={(e) => updOptionValue(oi, vi, "price_delta_inr", parseInt(e.target.value || "0", 10))}
                        title="Price delta (₹) — added to product price if selected"
                        className="bg-ink-950 border border-white/10 text-xs font-mono text-gold px-2 py-1.5 outline-none focus:border-gold"
                      />
                      {opt.type !== "toggle" ? (
                        <input
                          type="color"
                          value={v.hex || "#050505"}
                          onChange={(e) => updOptionValue(oi, vi, "hex", e.target.value)}
                          title="Swatch colour (optional)"
                          className="bg-ink-950 border border-white/10 h-8 w-full cursor-pointer"
                        />
                      ) : <div />}
                      <button type="button" onClick={() => removeOptionValue(oi, vi)} className="text-red-400 hover:text-red-300 p-1">
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                  <button type="button" onClick={() => addOptionValue(oi)} className="text-[10px] uppercase tracking-luxury text-gold-soft hover:text-gold border border-white/10 px-2.5 py-1 mt-1" data-testid={`pe-option-${oi}-add-value`}>
                    + Add value
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ------- Task 3 — Product uploader help notes (always visible) ------- */}
        <div className="mt-6 border border-gold/25 bg-gold/5 p-4 text-[11px] text-cream/70 leading-relaxed" data-testid="pe-help-notes">
          <div className="flex items-center gap-2 text-gold text-[10px] uppercase tracking-luxury mb-2">
            <AlertTriangle className="w-3 h-3" /> Notes for product uploader
          </div>
          <ul className="list-disc pl-5 space-y-1.5">
            <li><b>Colour swatches</b> are for products the buyer chooses a colour finish on. If your piece has only one colour, leave this <em>unticked</em> — the colour picker will not appear.</li>
            <li><b>Extra option groups</b> (Shape, Frame, Thickness, Gift Wrap, Care Kit, Mount, or Custom) let the buyer pick <em>additional</em> variations. Each value can add ₹ to the price via &ldquo;Price delta&rdquo;.</li>
            <li>Set an option <b>Required</b> to force the buyer to choose a value before checkout (e.g. Shape). Add-on toggles (Gift Wrap, Care Kit) are usually optional.</li>
            <li>Everything the buyer picks is <b>snapshotted onto the order</b> — you will see it under Admin → Orders → View details for every line item.</li>
            <li>When multiple products share the same option set (e.g. all mirrors have the same Shape / Frame choices), use the same preset buttons on each product for consistency. In future you&apos;ll be able to save & re-apply option templates.</li>
            <li>Prices are always in whole rupees (₹). GST is added on top automatically per your HSN / Category rules under the GST tab.</li>
          </ul>
        </div>

        <label className="mt-6 flex items-center gap-2 text-sm text-cream/70">
          <input type="checkbox" checked={!!f.is_hero} onChange={upd("is_hero")} /> Mark as hero product (appears in the main hero showcase)
        </label>

        <button disabled={saving} onClick={()=>onSave(f)} className="mt-8 w-full bg-gold text-ink-950 py-4 text-xs uppercase tracking-luxury hover:bg-cream disabled:opacity-60" data-testid="pe-save">
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

function OrderRow({ o, onStatus, onTracking, onNotify, onNimbusShip, onNimbusTrack, onNimbusCancel }) {
  const [trackingId, setTrackingId] = useState(o.tracking_id || "");
  const [trackingUrl, setTrackingUrl] = useState(o.tracking_url || "");
  const [trackingCarrier, setTrackingCarrier] = useState(o.tracking_carrier || "");
  const [showTracking, setShowTracking] = useState(!!o.tracking_id);
  const [expanded, setExpanded] = useState(false);
  const [saving, setSaving] = useState(false);

  const c = o.customer || {};
  const addrLine = [c.line1 || c.address, c.line2, c.landmark].filter(Boolean).join(", ");
  const stateLine = [c.city, c.state, c.pincode].filter(Boolean).join(" · ");

  const saveTracking = async () => {
    setSaving(true);
    try {
      await onTracking(o.order_number, {
        tracking_id: trackingId || null,
        tracking_url: trackingUrl || null,
        tracking_carrier: trackingCarrier || null,
      });
    } finally { setSaving(false); }
  };

  const itemsCount = (o.items || []).reduce((s, i) => s + (i.quantity || 1), 0);
  const gstTotal = o.gst_total_inr || 0;
  const gstIntra = (o.igst_inr || 0) === 0 && ((o.cgst_inr || 0) + (o.sgst_inr || 0)) > 0;

  return (
    <div className="hairline p-4" data-testid={`admin-order-${o.order_number}`}>
      <div className="flex flex-wrap items-center gap-4">
        <div>
          <div className="text-gold font-mono text-sm">{o.order_number}</div>
          <div className="text-xs text-cream/50">{new Date(o.created_at).toLocaleString()}</div>
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm">{c.name} · <a href={`mailto:${c.email}`} className="text-cream/70 hover:text-gold">{c.email}</a> · <a href={`tel:${c.phone}`} className="text-cream/70 hover:text-gold">{c.phone}</a></div>
          <div className="text-xs text-cream/50 truncate">{addrLine}</div>
          <div className="text-xs text-cream/40 truncate">{stateLine}{c.country && c.country !== "India" ? ` · ${c.country}` : ""}</div>
        </div>
        <div className="text-right">
          <div className="text-cream text-lg font-serif">₹{(o.total_inr || 0).toLocaleString("en-IN")}</div>
          <div className="text-[10px] text-cream/40 uppercase tracking-luxury">{itemsCount} item{itemsCount === 1 ? "" : "s"}</div>
        </div>
        <select value={o.status} onChange={(e) => onStatus(o.order_number, e.target.value)}
          className="bg-ink-950 border border-white/15 text-xs text-cream px-3 py-2 uppercase tracking-luxury"
          data-testid={`admin-order-status-${o.order_number}`}>
          {["pending_payment", "confirmed", "packed", "shipped", "delivered", "cancelled", "payment_failed"].map(s => (
            <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
          ))}
        </select>
      </div>

      {/* Meta row */}
      <div className="mt-3 flex items-center gap-3 flex-wrap text-xs text-cream/50">
        <span>Payment: <span className="text-cream/70">{o.payment_method}</span></span>
        {o.razorpay_payment_id && <span>· rzp: <span className="font-mono text-cream/70">{o.razorpay_payment_id}</span></span>}
        {o.coupon_code && (
          <span className="text-gold border border-gold/30 px-2 py-0.5 uppercase tracking-luxury text-[10px]">
            Coupon · {o.coupon_code} (-₹{(o.discount_inr || 0).toLocaleString("en-IN")})
          </span>
        )}
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          data-testid={`admin-order-expand-${o.order_number}`}
          className="text-[10px] uppercase tracking-luxury text-cream/60 hover:text-gold border border-white/10 px-3 py-1"
        >
          {expanded ? "Hide details" : "View details"}
        </button>
        <InvoiceButton orderNumber={o.order_number} />
        <button
          type="button"
          onClick={() => onNotify?.(o)}
          data-testid={`admin-order-notify-${o.order_number}`}
          className="text-[10px] uppercase tracking-luxury text-gold border border-gold/30 px-3 py-1 hover:bg-gold/10 inline-flex items-center gap-1.5"
        >
          Email customer
        </button>
        <button
          type="button"
          data-testid={`admin-order-toggle-tracking-${o.order_number}`}
          onClick={() => setShowTracking((v) => !v)}
          className="ml-auto text-[10px] uppercase tracking-luxury text-gold border border-gold/30 px-3 py-1 hover:bg-gold/10"
        >
          {o.tracking_id ? `Tracking: ${o.tracking_id}` : (showTracking ? "Hide tracking" : "Add tracking")}
        </button>
      </div>

      {/* Expanded market-standard details */}
      {expanded && (
        <div className="mt-4 border-t border-white/5 pt-4 grid gap-4 md:grid-cols-[2fr_1fr]" data-testid={`admin-order-details-${o.order_number}`}>
          <div>
            <div className="text-[10px] uppercase tracking-luxury text-cream/40 mb-2">Line items · {(o.items || []).length}</div>
            <div className="space-y-2">
              {(o.items || []).map((it, idx) => {
                const lineTotal = it.line_total_inr ?? ((it.price_inr || 0) * (it.quantity || 1));
                return (
                  <div key={idx} className="flex items-start gap-3 bg-ink-950/60 border border-white/5 p-2 text-xs">
                    {it.product_image ? (
                      // eslint-disable-next-line
                      <img src={it.product_image} alt="" className="w-14 h-14 object-cover border border-white/10 shrink-0" />
                    ) : (
                      <div className="w-14 h-14 border border-white/10 bg-ink-950 flex items-center justify-center text-cream/30 text-[9px] shrink-0">no img</div>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="text-cream truncate">{it.product_name || it.name || `Item ${idx + 1}`}</div>
                      <div className="text-cream/50 text-[10px] mt-0.5 flex flex-wrap gap-x-2">
                        {(it.variant_label || it.variant_key) && (
                          <span className="inline-flex items-center gap-1">
                            {it.variant_hex && <span className="w-2.5 h-2.5 border border-white/20 inline-block" style={{ backgroundColor: it.variant_hex }} />}
                            Variant: <span className="text-cream/70">{it.variant_label || it.variant_key}</span>
                          </span>
                        )}
                        {it.size && <span>Size: <span className="text-cream/70">{it.size}</span></span>}
                        <span>Qty: <span className="text-cream/70">{it.quantity}</span></span>
                      </div>
                      <div className="text-cream/40 text-[10px] mt-0.5 flex flex-wrap gap-x-2">
                        {it.product_category && <span>Category: <span className="text-cream/60">{it.product_category}</span></span>}
                        {it.product_sku && <span>SKU: <span className="font-mono text-cream/60">{it.product_sku}</span></span>}
                        {it.product_hsn_code && <span>HSN: <span className="font-mono text-cream/60">{it.product_hsn_code}</span></span>}
                      </div>
                      {/* Task 3 — Selected variation options (Shape / Frame / Gift Wrap / Care Kit / Mount…) */}
                      {it.selected_options_labels && Object.keys(it.selected_options_labels).length > 0 && (
                        <div className="mt-1.5 flex flex-wrap gap-1.5">
                          {Object.entries(it.selected_options_labels).map(([k, v]) => (
                            <span
                              key={k}
                              className="inline-flex items-center gap-1 text-[10px] bg-gold/10 border border-gold/30 text-gold-soft px-2 py-0.5"
                              title="Customer-selected option"
                            >
                              <span className="uppercase tracking-luxury text-[9px] text-gold-soft/70">{k}:</span>
                              <span className="text-cream">{v}</span>
                            </span>
                          ))}
                          {(it.options_price_delta_inr || 0) > 0 && (
                            <span className="inline-flex items-center text-[10px] bg-ink-950 border border-white/10 text-cream/70 px-2 py-0.5">
                              add-ons: <span className="text-gold ml-1 font-mono">+₹{(it.options_price_delta_inr).toLocaleString("en-IN")}</span>
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-cream/70 font-mono">₹{(it.price_inr || 0).toLocaleString("en-IN")}</div>
                      <div className="text-cream/40 text-[10px]">× {it.quantity} = <span className="text-cream/70">₹{lineTotal.toLocaleString("en-IN")}</span></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
          <div className="text-xs">
            <div className="text-[10px] uppercase tracking-luxury text-cream/40 mb-2">Totals</div>
            <div className="space-y-1">
              <Row2 k="Subtotal" v={`₹${(o.subtotal_inr || 0).toLocaleString("en-IN")}`} />
              {(o.discount_inr || 0) > 0 && <Row2 k={`Discount${o.coupon_code ? ` (${o.coupon_code})` : ""}`} v={`- ₹${(o.discount_inr || 0).toLocaleString("en-IN")}`} accent />}
              <Row2 k="Shipping" v={`₹${(o.shipping_inr || 0).toLocaleString("en-IN")}`} />
              {gstTotal > 0 && <Row2 k={gstIntra ? "GST (CGST+SGST)" : "GST (IGST)"} v={`₹${gstTotal.toLocaleString("en-IN")}`} />}
              <div className="pt-2 mt-2 border-t border-white/5 flex items-center justify-between">
                <span className="text-cream/70 uppercase tracking-luxury text-[10px]">Total paid</span>
                <span className="text-gold font-serif text-lg">₹{(o.total_inr || 0).toLocaleString("en-IN")}</span>
              </div>
              {gstTotal > 0 && (
                <div className="text-[10px] text-cream/40 mt-2 leading-relaxed">
                  {gstIntra ? (<>CGST ₹{(o.cgst_inr || 0).toLocaleString("en-IN")} + SGST ₹{(o.sgst_inr || 0).toLocaleString("en-IN")}</>) : (<>IGST ₹{(o.igst_inr || 0).toLocaleString("en-IN")}</>)}
                </div>
              )}
              {o.delivered_at && <div className="text-[10px] text-cream/40 mt-3">Delivered · {new Date(o.delivered_at).toLocaleString()}</div>}
              {o.tracking_updated_at && <div className="text-[10px] text-cream/40">Tracking updated · {new Date(o.tracking_updated_at).toLocaleString()}</div>}
            </div>
          </div>
        </div>
      )}

      {showTracking && (
        <div className="mt-3 grid sm:grid-cols-[1fr_1fr_1.5fr_auto] gap-2 items-end border-t border-white/5 pt-3">
          <label className="block">
            <span className="text-[10px] uppercase tracking-luxury text-cream/50">Carrier</span>
            <input data-testid={`admin-order-carrier-${o.order_number}`} value={trackingCarrier} onChange={(e) => setTrackingCarrier(e.target.value)} placeholder="BlueDart / DTDC / Delhivery" className="mt-1 w-full bg-ink-950 border border-white/15 focus:border-gold px-3 py-2 text-sm text-cream outline-none" />
          </label>
          <label className="block">
            <span className="text-[10px] uppercase tracking-luxury text-cream/50">Tracking ID</span>
            <input data-testid={`admin-order-trackingid-${o.order_number}`} value={trackingId} onChange={(e) => setTrackingId(e.target.value)} placeholder="e.g. DTDC1234567" className="mt-1 w-full bg-ink-950 border border-white/15 focus:border-gold px-3 py-2 text-sm text-cream outline-none font-mono" />
          </label>
          <label className="block">
            <span className="text-[10px] uppercase tracking-luxury text-cream/50">Tracking URL (optional)</span>
            <input data-testid={`admin-order-trackingurl-${o.order_number}`} value={trackingUrl} onChange={(e) => setTrackingUrl(e.target.value)} placeholder="https://carrier.com/track/…" className="mt-1 w-full bg-ink-950 border border-white/15 focus:border-gold px-3 py-2 text-sm text-cream outline-none" />
          </label>
          <button
            data-testid={`admin-order-save-tracking-${o.order_number}`}
            onClick={saveTracking}
            disabled={saving}
            className="px-4 py-2 bg-gold text-ink-950 hover:bg-cream text-xs uppercase tracking-luxury disabled:opacity-60"
          >
            {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : "Save tracking"}
          </button>
        </div>
      )}

      {/* NimbusPost quick actions (Task 7 / Batch 4) */}
      {(onNimbusShip || onNimbusTrack || onNimbusCancel) && (
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-white/5 pt-3">
          <span className="text-[10px] uppercase tracking-luxury text-cream/40 mr-1">NimbusPost</span>
          {!o.tracking_id ? (
            <button
              type="button"
              data-testid={`nimbus-ship-${o.order_number}`}
              onClick={() => onNimbusShip?.(o.order_number)}
              className="text-[10px] uppercase tracking-luxury text-ink-950 bg-gold hover:bg-cream px-3 py-1"
            >
              Ship via NimbusPost
            </button>
          ) : (
            <>
              <span className="text-[10px] text-cream/60 font-mono">AWB {o.tracking_id}</span>
              <button
                type="button"
                data-testid={`nimbus-track-${o.order_number}`}
                onClick={() => onNimbusTrack?.(o.order_number)}
                className="text-[10px] uppercase tracking-luxury text-gold border border-gold/40 px-3 py-1 hover:bg-gold/10"
              >
                Live tracking
              </button>
              <button
                type="button"
                data-testid={`nimbus-cancel-${o.order_number}`}
                onClick={() => onNimbusCancel?.(o.order_number)}
                className="text-[10px] uppercase tracking-luxury text-red-300 border border-red-500/40 px-3 py-1 hover:bg-red-500/10"
              >
                Cancel shipment
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function Row2({ k, v, accent }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-cream/50">{k}</span>
      <span className={accent ? "text-gold font-mono" : "text-cream/80 font-mono"}>{v}</span>
    </div>
  );
}

function ReturnRow({ r, onUpdate }) {  const [notes, setNotes] = useState(r.admin_notes || "");
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

/**
 * Pager — reusable pagination footer.
 * Shows Prev · [1] [2] … · Next
 * Keeps things compact when there are many pages.
 */
function Pager({ page, pages, onChange, testid = "pager" }) {
  if (!pages || pages <= 1) return null;
  const nums = [];
  const push = (n) => { if (n >= 1 && n <= pages && !nums.includes(n)) nums.push(n); };
  push(1); push(pages);
  for (let d = -2; d <= 2; d++) push(page + d);
  nums.sort((a, b) => a - b);
  const withGaps = [];
  nums.forEach((n, i) => {
    if (i > 0 && n - nums[i - 1] > 1) withGaps.push("…");
    withGaps.push(n);
  });
  return (
    <div className="mt-6 flex items-center justify-center gap-1 flex-wrap" data-testid={testid}>
      <button
        onClick={() => onChange(Math.max(1, page - 1))}
        disabled={page <= 1}
        data-testid={`${testid}-prev`}
        className="px-3 py-1.5 text-[10px] uppercase tracking-luxury border border-white/10 text-cream/70 hover:text-gold disabled:opacity-30"
      >Prev</button>
      {withGaps.map((n, i) => (
        n === "…" ? (
          <span key={`gap-${i}`} className="px-2 text-cream/40 text-xs">…</span>
        ) : (
          <button
            key={n}
            onClick={() => onChange(n)}
            data-testid={`${testid}-page-${n}`}
            className={`px-3 py-1.5 text-[10px] uppercase tracking-luxury border ${n === page ? "border-gold text-gold" : "border-white/10 text-cream/70 hover:text-gold"}`}
          >{n}</button>
        )
      ))}
      <button
        onClick={() => onChange(Math.min(pages, page + 1))}
        disabled={page >= pages}
        data-testid={`${testid}-next`}
        className="px-3 py-1.5 text-[10px] uppercase tracking-luxury border border-white/10 text-cream/70 hover:text-gold disabled:opacity-30"
      >Next</button>
    </div>
  );
}


/* --------------------------------------------------------------------------
 * Task 8 — GST invoice download helpers.
 * `InvoiceButton` is used inline on each OrderRow.
 * `BulkInvoiceDownloader` sits in the Orders tab header.
 * Both hit /api/admin/orders/... endpoints with the admin token and stream
 * the PDF / ZIP straight to the browser via a temporary blob URL.
 * -------------------------------------------------------------------------- */
function _fetchAndDownload(url, filename, adminToken) {
  return fetch(url, { headers: adminToken ? { Authorization: `Bearer ${adminToken}` } : {} })
    .then(async (r) => {
      if (!r.ok) {
        let msg = "Download failed";
        try { const j = await r.json(); if (j && j.detail) msg = j.detail; } catch (_) { /* ignore */ }
        throw new Error(msg);
      }
      const blob = await r.blob();
      const href = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = href;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(href), 60_000);
    });
}

function InvoiceButton({ orderNumber }) {
  const [busy, setBusy] = useState(false);
  const download = async () => {
    setBusy(true);
    try {
      const token = localStorage.getItem("artyfex_admin_token") || "";
      const backend = process.env.REACT_APP_BACKEND_URL || "";
      const url = `${backend}/api/admin/orders/${encodeURIComponent(orderNumber)}/invoice.pdf`;
      await _fetchAndDownload(url, `invoice-${orderNumber}.pdf`, token);
      toast.success("Invoice downloaded");
    } catch (e) {
      toast.error(e.message || "Invoice download failed");
    } finally { setBusy(false); }
  };
  return (
    <button
      type="button"
      onClick={download}
      disabled={busy}
      data-testid={`admin-order-invoice-${orderNumber}`}
      className="text-[10px] uppercase tracking-luxury text-gold hover:text-cream border border-gold/40 px-3 py-1 flex items-center gap-1 disabled:opacity-50"
      title="Download GST invoice (PDF)"
    >
      {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : <FileText className="w-3 h-3" />}
      Invoice
    </button>
  );
}

function BulkInvoiceDownloader({ authed }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [status, setStatus] = useState("");
  const download = async () => {
    setBusy(true);
    try {
      const token = localStorage.getItem("artyfex_admin_token") || "";
      const backend = process.env.REACT_APP_BACKEND_URL || "";
      const params = new URLSearchParams();
      if (dateFrom) params.set("date_from", dateFrom);
      if (dateTo) params.set("date_to", dateTo);
      if (status) params.set("status", status);
      const url = `${backend}/api/admin/orders/invoices.zip${params.toString() ? "?" + params.toString() : ""}`;
      const label = dateFrom || dateTo ? `invoices_${dateFrom || "all"}_to_${dateTo || "all"}.zip` : "invoices_all.zip";
      await _fetchAndDownload(url, label, token);
      toast.success("Invoices ZIP downloaded");
      setOpen(false);
    } catch (e) {
      toast.error(e.message || "Bulk download failed");
    } finally { setBusy(false); }
  };
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        data-testid="admin-orders-bulk-invoice"
        className="inline-flex items-center gap-2 border border-gold/50 text-gold text-xs uppercase tracking-luxury px-4 py-2.5 hover:bg-gold hover:text-ink-950 transition-colors"
        title="Bulk-download all GST invoices as ZIP (for CA / GST filing)"
      >
        <Download className="w-3.5 h-3.5" /> Download all invoices
      </button>
      {open && (
        <div className="fixed inset-0 z-[110] bg-black/70 flex items-center justify-center p-4" onClick={() => !busy && setOpen(false)}>
          <div className="bg-ink-950 border border-gold/30 w-full max-w-md p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-serif text-xl text-cream">Bulk Invoice Download</h3>
              <button onClick={() => setOpen(false)} className="text-cream/40 hover:text-red-400 text-xl leading-none">×</button>
            </div>
            <p className="text-xs text-cream/60 mb-4">Downloads every order&apos;s GST invoice as a single ZIP — for GST filing / ITR / CA hand-off. Leave filters empty to grab every order in the system.</p>
            <div className="grid grid-cols-2 gap-3 mb-3">
              <label className="block">
                <span className="text-[10px] uppercase tracking-luxury text-cream/60">From</span>
                <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} data-testid="admin-bulk-inv-from" className="mt-1 w-full bg-ink-900 border border-white/10 text-cream text-xs px-2 py-2 focus:border-gold outline-none" />
              </label>
              <label className="block">
                <span className="text-[10px] uppercase tracking-luxury text-cream/60">To</span>
                <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} data-testid="admin-bulk-inv-to" className="mt-1 w-full bg-ink-900 border border-white/10 text-cream text-xs px-2 py-2 focus:border-gold outline-none" />
              </label>
            </div>
            <label className="block mb-4">
              <span className="text-[10px] uppercase tracking-luxury text-cream/60">Status (optional)</span>
              <select value={status} onChange={(e) => setStatus(e.target.value)} data-testid="admin-bulk-inv-status" className="mt-1 w-full bg-ink-900 border border-white/10 text-cream text-xs px-2 py-2 focus:border-gold outline-none">
                <option value="">All statuses</option>
                {["pending_payment", "confirmed", "packed", "shipped", "delivered", "cancelled", "payment_failed"].map((s) => (
                  <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
                ))}
              </select>
            </label>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setOpen(false)}
                disabled={busy}
                className="text-xs uppercase tracking-luxury text-cream/60 px-4 py-2 hover:text-cream"
              >Cancel</button>
              <button
                type="button"
                onClick={download}
                disabled={busy}
                data-testid="admin-bulk-inv-go"
                className="text-xs uppercase tracking-luxury bg-gold text-ink-950 px-5 py-2.5 hover:bg-cream disabled:opacity-50 flex items-center gap-2"
              >
                {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                {busy ? "Building ZIP…" : "Download ZIP"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// -------------- NimbusPost config card (Task 7 / Batch 4) --------------
function NimbusPostCard({ authed }) {
  const [cfg, setCfg] = useState(null);
  const [warehouse, setWarehouse] = useState("");
  const [saving, setSaving] = useState(false);
  const [pin, setPin] = useState("110001");
  const [svc, setSvc] = useState(null);
  const [checking, setChecking] = useState(false);

  const load = async () => {
    try {
      const r = await authed.get("/admin/nimbuspost/config");
      setCfg(r.data);
      setWarehouse(r.data?.warehouse_name || "");
    } catch (err) {
      toast.error("Failed to load NimbusPost config");
    }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const save = async () => {
    setSaving(true);
    try {
      await authed.patch("/admin/nimbuspost/config", { warehouse_name: warehouse });
      toast.success("NimbusPost warehouse saved");
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const check = async () => {
    setChecking(true); setSvc(null);
    try {
      const r = await authed.post("/admin/nimbuspost/serviceability", { pincode: pin, cod: false, weight_g: 500 });
      setSvc(r.data);
    } catch (err) {
      setSvc({ error: err?.response?.data?.detail || "Serviceability failed" });
    } finally {
      setChecking(false);
    }
  };

  return (
    <div className="mt-8 hairline p-6" data-testid="nimbuspost-card">
      <div className="flex items-center gap-3">
        <h2 className="font-serif text-2xl">NimbusPost Courier</h2>
        {cfg && (
          <span className={`text-[10px] uppercase tracking-luxury px-2 py-0.5 border ${cfg.configured ? "text-gold border-gold/40" : "text-red-300 border-red-500/40"}`}>
            {cfg.configured ? `Connected · ${cfg.auth_mode}` : "Not configured"}
          </span>
        )}
      </div>
      <p className="mt-2 text-sm text-cream/60 max-w-2xl">
        Set the exact warehouse / pickup name registered on your NimbusPost dashboard.
        Once saved, every admin order card will show a <b>Ship via NimbusPost</b> button that creates an AWB and pushes tracking back to the customer.
      </p>

      <div className="mt-5 grid sm:grid-cols-[1fr_auto] gap-3 items-end">
        <label className="block">
          <span className="text-[10px] uppercase tracking-luxury text-cream/50">Warehouse / Pickup name (must match dashboard exactly)</span>
          <input
            data-testid="nimbus-warehouse-input"
            value={warehouse}
            onChange={(e) => setWarehouse(e.target.value)}
            placeholder="e.g. ArtyFex Mumbai Warehouse"
            className="mt-1 w-full bg-ink-950 border border-white/15 focus:border-gold px-3 py-2 text-sm text-cream outline-none"
          />
        </label>
        <button
          data-testid="nimbus-warehouse-save"
          onClick={save}
          disabled={saving}
          className="px-5 py-2 bg-gold text-ink-950 hover:bg-cream text-xs uppercase tracking-luxury disabled:opacity-60"
        >
          {saving ? "Saving…" : "Save"}
        </button>
      </div>

      <div className="mt-6 border-t border-white/5 pt-5">
        <div className="text-[10px] uppercase tracking-luxury text-cream/40">Serviceability check</div>
        <div className="mt-2 flex flex-wrap gap-2 items-center">
          <input
            data-testid="nimbus-svc-pin"
            value={pin}
            onChange={(e) => setPin(e.target.value)}
            placeholder="Pincode"
            className="bg-ink-950 border border-white/15 focus:border-gold px-3 py-2 text-sm text-cream outline-none font-mono w-40"
          />
          <button
            data-testid="nimbus-svc-check"
            onClick={check}
            disabled={checking}
            className="px-4 py-2 border border-gold/40 text-gold hover:bg-gold/10 text-xs uppercase tracking-luxury disabled:opacity-60"
          >
            {checking ? "Checking…" : "Check"}
          </button>
        </div>
        {svc && (
          <pre className="mt-3 text-[11px] text-cream/60 bg-ink-950/60 border border-white/5 p-3 overflow-auto max-h-56">{JSON.stringify(svc, null, 2)}</pre>
        )}
      </div>

      <div className="mt-5 text-[11px] text-cream/40 leading-relaxed">
        <b className="text-cream/60">Tips:</b> NimbusPost deducts wallet ₹ the instant an AWB is created — cancel before manifest to refund.
        Add funds at <span className="text-cream/60">nimbuspost.com → Wallet</span>.
        Auth mode is JWT (auto-refreshed every ~23h) with the legacy API key as fallback.
      </div>
    </div>
  );
}

