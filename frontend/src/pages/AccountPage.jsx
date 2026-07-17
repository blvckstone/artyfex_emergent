import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useWishlist } from "@/context/WishlistContext";
import { useCart } from "@/context/CartContext";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Package, RotateCcw, User, LogOut, Loader2, Heart, ShoppingBag, X, Mail, Save, Star } from "lucide-react";
import { toast } from "sonner";
import { useReviewPrompts } from "@/context/ReviewPromptContext";

const formatINR = (n) => `₹${(n || 0).toLocaleString("en-IN")}`;

const statusColor = (s) => ({
  pending_payment: "text-yellow-400", confirmed: "text-blue-300", packed: "text-blue-300",
  shipped: "text-purple-300", delivered: "text-gold", cancelled: "text-red-400", payment_failed: "text-red-400",
  requested: "text-yellow-400", approved: "text-emerald-400", rejected: "text-red-400",
  received: "text-blue-300", refunded: "text-gold",
}[s] || "text-cream");

const VALID_TABS = new Set(["orders", "messages", "wishlist", "profile", "returns"]);

export default function AccountPage() {
  const { user, ready, logout, openAuth, authedApi, updateProfile } = useAuth();
  const { items: wishItems, toggle: toggleWish, refresh: refreshWish } = useWishlist();
  const { addItem } = useCart();
  const { prompts: reviewPrompts, setModalOpen: openReviewModal } = useReviewPrompts();
  const nav = useNavigate();
  const location = useLocation();
  const initialTab = (() => {
    const q = new URLSearchParams(location.search).get("tab");
    return q && VALID_TABS.has(q) ? q : "orders";
  })();
  const [tab, setTab] = useState(initialTab);
  const [orders, setOrders] = useState([]);
  const [returns, setReturns] = useState([]);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [returnFor, setReturnFor] = useState(null);

  // Sync tab if query param changes (e.g., user clicks Saved on tab-bar while on Account)
  useEffect(() => {
    const q = new URLSearchParams(location.search).get("tab");
    if (q && VALID_TABS.has(q) && q !== tab) setTab(q);
  }, [location.search, tab]);

  const unreadCount = useMemo(() => messages.filter((m) => !m.read).length, [messages]);

  useEffect(() => {
    if (ready && !user) openAuth("login");
  }, [ready, user, openAuth]);

  useEffect(() => {
    if (!user) return;
    const a = authedApi();
    Promise.all([a.get("/me/orders"), a.get("/me/returns"), a.get("/me/messages")])
      .then(([o, r, m]) => { setOrders(o.data); setReturns(r.data); setMessages(m.data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user, authedApi]);

  const markMessageRead = async (id) => {
    try {
      await authedApi().patch(`/me/messages/${id}/read`);
      setMessages((arr) => arr.map((m) => (m.id === id ? { ...m, read: true } : m)));
    } catch { /* silent */ }
  };

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
    { key: "messages", label: "Updates", icon: Mail, badge: unreadCount },
    { key: "wishlist", label: "Wishlist", icon: Heart },
    { key: "profile", label: "Profile", icon: User },
    { key: "returns", label: "Returns", icon: RotateCcw },
  ];

  const submitReturn = async (order_number, payload) => {
    try {
      const a = authedApi();
      const { data } = await a.post("/me/returns", { order_number, ...payload });
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

        <div className="mt-10 flex gap-2 border-b border-white/5 overflow-x-auto">
          {tabs.map((t) => (
            <button key={t.key} data-testid={`account-tab-${t.key}`} onClick={() => setTab(t.key)}
              className={`relative flex items-center gap-2 px-4 py-3 text-xs uppercase tracking-luxury border-b-2 -mb-px whitespace-nowrap ${tab===t.key?"border-gold text-gold":"border-transparent text-cream/50"}`}>
              <t.icon className="w-3.5 h-3.5" />{t.label}
              {t.badge > 0 && (
                <>
                  <span data-testid={`account-tab-dot-${t.key}`} className="ml-1 w-2 h-2 rounded-full bg-gold animate-pulse" aria-hidden="true" />
                  <span data-testid={`account-tab-badge-${t.key}`} className="sr-only">{t.badge} unread</span>
                </>
              )}
            </button>
          ))}
        </div>

        {!loading && unreadCount > 0 && tab !== "messages" && (
          <button
            data-testid="account-unread-banner"
            onClick={() => setTab("messages")}
            className="mt-6 w-full flex items-center gap-3 border border-gold/40 bg-gold/5 hover:bg-gold/10 px-5 py-3 text-left transition-colors"
          >
            <Mail className="w-4 h-4 text-gold" />
            <span className="text-sm text-cream">
              You have <span className="text-gold font-medium">{unreadCount}</span> unread update{unreadCount === 1 ? "" : "s"} from our atelier
            </span>
            <span className="ml-auto text-[10px] uppercase tracking-luxury text-gold">Read now →</span>
          </button>
        )}

        {reviewPrompts.length > 0 && (
          <button
            data-testid="account-review-prompt-card"
            onClick={() => openReviewModal(true)}
            className="mt-6 w-full flex items-center gap-3 border border-gold/40 bg-gradient-to-r from-gold/5 to-transparent hover:from-gold/10 px-5 py-3 text-left transition-colors"
          >
            <Star className="w-4 h-4 text-gold" fill="currentColor" />
            <span className="text-sm text-cream">
              {reviewPrompts.length === 1
                ? <>Rate your <span className="italic text-gold">{reviewPrompts[0].product_name.split(" — ")[0]}</span> — delivered {reviewPrompts[0].days_since_delivery} days ago</>
                : <>{reviewPrompts.length} pieces are awaiting your reflection</>}
            </span>
            <span className="ml-auto text-[10px] uppercase tracking-luxury text-gold">Share now →</span>
          </button>
        )}

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
                  <div className="mt-3 text-xs text-cream/50">
                    {o.items.length} item(s) · {o.customer.city}
                    {o.customer.state ? `, ${o.customer.state}` : ""} · {o.customer.pincode}
                  </div>
                  {(o.tracking_id || o.tracking_url) && (
                    <div className="mt-4 border-t border-gold/20 pt-4 flex flex-wrap items-center gap-3 bg-gold/5 -mx-6 -mb-6 px-6 py-4">
                      <div className="text-[10px] uppercase tracking-luxury text-gold-soft">Tracking</div>
                      {o.tracking_carrier && <div className="text-xs text-cream/70">{o.tracking_carrier}</div>}
                      {o.tracking_id && (
                        <div className="font-mono text-sm text-gold" data-testid={`order-tracking-${o.order_number}`}>
                          {o.tracking_id}
                        </div>
                      )}
                      {o.tracking_url && (
                        <a
                          href={o.tracking_url}
                          target="_blank"
                          rel="noreferrer"
                          data-testid={`order-track-link-${o.order_number}`}
                          className="ml-auto text-[10px] uppercase tracking-luxury text-gold border border-gold/40 px-3 py-1.5 hover:bg-gold hover:text-ink-950 transition-colors"
                        >
                          Track shipment →
                        </a>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {!loading && tab === "returns" && (
            <div className="grid gap-6">
              {/* Eligible orders (delivered, within 3-day window, no open return) */}
              {(() => {
                const openReturnOrders = new Set(returns.filter((r) => ["requested", "approved", "received"].includes(r.status)).map((r) => r.order_number));
                const eligible = orders.filter((o) => {
                  if (o.status !== "delivered") return false;
                  const deliveredAt = o.delivered_at ? new Date(o.delivered_at) : null;
                  if (!deliveredAt) return false;
                  const daysSince = Math.floor((Date.now() - deliveredAt.getTime()) / 86400000);
                  return daysSince <= 3 && !openReturnOrders.has(o.order_number);
                });
                return (
                  <div className="hairline p-6" data-testid="returns-init-section">
                    <div className="text-[10px] uppercase tracking-luxury text-gold-soft">Request a return</div>
                    <p className="mt-2 text-xs text-cream/50">Returns must be raised within <span className="text-cream">3 days of delivery.</span> Original packaging is required. Damage evidence needed for damaged items.</p>
                    {eligible.length === 0 ? (
                      <div className="mt-4 text-sm text-cream/50">No orders are currently eligible for return.</div>
                    ) : (
                      <div className="mt-4 grid gap-2">
                        {eligible.map((o) => {
                          const deliveredAt = new Date(o.delivered_at);
                          const daysSince = Math.floor((Date.now() - deliveredAt.getTime()) / 86400000);
                          const daysLeft = 3 - daysSince;
                          return (
                            <div key={o.order_number} className="flex items-center gap-3 flex-wrap border border-white/5 p-3">
                              <div className="text-gold font-mono text-sm">{o.order_number}</div>
                              <div className="text-xs text-cream/50">{o.items.length} item(s) · {formatINR(o.total_inr)}</div>
                              <div className="text-[10px] uppercase tracking-luxury text-emerald-400/70 ml-auto">
                                {daysLeft} day{daysLeft === 1 ? "" : "s"} left
                              </div>
                              <button
                                data-testid={`returns-init-${o.order_number}`}
                                onClick={() => setReturnFor(o)}
                                className="text-[10px] uppercase tracking-luxury text-gold border border-gold/40 px-3 py-1.5 hover:bg-gold hover:text-ink-950 transition-colors"
                              >
                                Start return
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })()}

              {/* Existing return requests */}
              <div>
                <div className="text-[10px] uppercase tracking-luxury text-cream/40 mb-3">Your return requests</div>
                <div className="grid gap-4">
                  {returns.length === 0 && <div className="hairline p-10 text-center text-cream/40">No return requests yet.</div>}
                  {returns.map((r) => (
                    <div key={r.id} className="hairline p-6" data-testid={`account-return-${r.id}`}>
                      <div className="flex items-center gap-4 flex-wrap">
                        <div className="text-gold font-mono text-sm">{r.order_number}</div>
                        <div className="text-xs text-cream/40">{new Date(r.created_at).toLocaleDateString()}</div>
                        <div className={`text-xs uppercase tracking-luxury ml-auto ${statusColor(r.status)}`}>{r.status}</div>
                      </div>
                      <div className="mt-3 text-sm"><span className="text-cream/50">Reason:</span> {r.reason}</div>
                      {r.details && <div className="mt-1 text-sm text-cream/70 italic">&ldquo;{r.details}&rdquo;</div>}
                      {r.damage_image_url && (
                        <div className="mt-2 text-xs">
                          <a href={r.damage_image_url} target="_blank" rel="noreferrer" className="text-gold hover:text-cream underline underline-offset-2">
                            View damage evidence →
                          </a>
                        </div>
                      )}
                      {r.is_genuine === false && (
                        <div className="mt-3 text-xs uppercase tracking-luxury text-red-400/80">Marked non-genuine — restocking fees may apply</div>
                      )}
                      {r.is_genuine === true && (
                        <div className="mt-3 text-xs uppercase tracking-luxury text-emerald-400/80">Verified genuine — full refund eligible</div>
                      )}
                      {r.admin_notes && (
                        <div className="mt-3 border-t border-white/5 pt-3 text-sm text-cream/70">
                          <div className="text-[10px] uppercase tracking-luxury text-cream/40 mb-1">From atelier</div>
                          {r.admin_notes}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {!loading && tab === "wishlist" && (
            <div>
              {wishItems.length === 0 ? (
                <div className="hairline p-10 text-center text-cream/40">
                  Nothing saved yet. <Link to="/shop" className="text-gold hover:text-cream">Browse the collection →</Link>
                </div>
              ) : (
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                  {wishItems.map((w) => {
                    const p = w.product;
                    return (
                      <div key={w.product_id} className="group relative bg-ink-900 border border-white/5 hover:border-gold/30 transition-colors" data-testid={`account-wishlist-${p.slug}`}>
                        <Link to={`/product/${p.slug}`} className="block">
                          <div className="aspect-[4/5] overflow-hidden relative">
                            <img src={p.hero_image} alt={p.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-[1000ms]" />
                          </div>
                        </Link>
                        <button
                          data-testid={`account-wishlist-remove-${p.slug}`}
                          onClick={async () => { await toggleWish(p); refreshWish(); toast.success("Removed from wishlist"); }}
                          className="absolute top-3 right-3 w-8 h-8 flex items-center justify-center bg-black/60 border border-white/10 text-cream/70 hover:text-red-400 hover:border-red-400/40 backdrop-blur-md"
                          aria-label="Remove"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                        <div className="p-5">
                          <div className="text-[10px] uppercase tracking-luxury text-gold-soft">{p.size}</div>
                          <Link to={`/product/${p.slug}`} className="block mt-2 font-serif text-lg hover:text-gold">{p.name.split(" — ")[0]}</Link>
                          <div className="mt-3 flex items-center justify-between">
                            <div className="font-serif text-xl">₹{(p.price_inr || 0).toLocaleString("en-IN")}</div>
                            <button
                              data-testid={`account-wishlist-move-${p.slug}`}
                              onClick={() => { addItem(p, p.variants[0].key, 1); toast.success("Moved to cart"); }}
                              className="inline-flex items-center gap-2 text-[10px] uppercase tracking-luxury text-gold hover:text-cream border border-gold/40 px-3 py-2"
                            >
                              <ShoppingBag className="w-3 h-3" /> Move to cart
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {!loading && tab === "messages" && (
            <div className="grid gap-4">
              {messages.length === 0 && <div className="hairline p-10 text-center text-cream/40">No updates yet from the atelier.</div>}
              {messages.map((m) => (
                <div
                  key={m.id}
                  data-testid={`account-message-${m.id}`}
                  className={`hairline p-6 transition-colors ${!m.read ? "bg-gold/5 border-gold/30" : ""}`}
                >
                  <div className="flex items-center gap-3 flex-wrap">
                    {!m.read && <span data-testid={`account-message-unread-${m.id}`} className="w-2 h-2 rounded-full bg-gold animate-pulse" />}
                    <div className="font-serif text-xl text-cream">{m.subject}</div>
                    <div className="ml-auto text-[10px] uppercase tracking-luxury text-cream/40">{new Date(m.created_at).toLocaleString()}</div>
                  </div>
                  <div className="mt-3 text-sm text-cream/70 whitespace-pre-wrap leading-relaxed">{m.body}</div>
                  <div className="mt-4 text-[10px] uppercase tracking-luxury text-gold-soft">From the ArtyFex Atelier</div>
                  {!m.read && (
                    <button
                      data-testid={`account-message-mark-${m.id}`}
                      onClick={() => markMessageRead(m.id)}
                      className="mt-4 text-[10px] uppercase tracking-luxury text-gold hover:text-cream border-b border-gold/40 pb-0.5"
                    >
                      Mark as read
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {!loading && tab === "profile" && (
            <ProfileEditor user={user} updateProfile={updateProfile} />
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

function ProfileEditor({ user, updateProfile }) {
  const [name, setName] = useState(user.name || "");
  const [phone, setPhone] = useState(user.phone || "");
  const [saving, setSaving] = useState(false);
  const dirty = name.trim() !== (user.name || "") || phone.trim() !== (user.phone || "");

  const submit = async (e) => {
    e.preventDefault();
    if (!dirty) return;
    setSaving(true);
    try {
      await updateProfile({ name: name.trim(), phone: phone.trim() });
      toast.success("Profile updated");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Update failed");
    } finally { setSaving(false); }
  };

  return (
    <form onSubmit={submit} className="hairline p-8 max-w-xl" data-testid="profile-editor">
      <div className="text-[10px] uppercase tracking-luxury text-gold-soft mb-2">Your details</div>
      <p className="text-xs text-cream/50 mb-6">Update your name and phone. Email is your account identity and cannot be changed.</p>
      <div className="grid sm:grid-cols-2 gap-5">
        <label className="block">
          <span className="text-[10px] uppercase tracking-luxury text-cream/50">Name</span>
          <input
            data-testid="profile-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1.5 w-full bg-ink-950 border border-white/15 focus:border-gold px-3 py-2.5 text-sm text-cream outline-none"
            required
            minLength={2}
          />
        </label>
        <label className="block">
          <span className="text-[10px] uppercase tracking-luxury text-cream/50">Phone</span>
          <input
            data-testid="profile-phone"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            type="tel"
            placeholder="+91 98765 43210"
            className="mt-1.5 w-full bg-ink-950 border border-white/15 focus:border-gold px-3 py-2.5 text-sm text-cream outline-none"
          />
        </label>
        <div className="sm:col-span-2">
          <Info label="Email (read-only)" value={user.email} />
        </div>
      </div>
      <div className="mt-8 flex items-center gap-3">
        <button
          data-testid="profile-save"
          type="submit"
          disabled={!dirty || saving}
          className="inline-flex items-center gap-2 bg-gold text-ink-950 px-6 py-3 text-xs uppercase tracking-luxury disabled:opacity-40 disabled:cursor-not-allowed hover:bg-cream"
        >
          {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
          {saving ? "Saving…" : "Save changes"}
        </button>
        {dirty && !saving && <span className="text-xs text-cream/40">Unsaved changes</span>}
      </div>
    </form>
  );
}

function ReturnDialog({ order, onCancel, onSubmit }) {
  const [reason, setReason] = useState("Product damaged in transit");
  const [details, setDetails] = useState("");
  const [damageImageUrl, setDamageImageUrl] = useState("");
  const [packagingConfirmed, setPackagingConfirmed] = useState(false);
  const deliveredAt = order.delivered_at ? new Date(order.delivered_at) : null;
  const daysLeft = deliveredAt ? 3 - Math.floor((Date.now() - deliveredAt.getTime()) / 86400000) : 3;

  const canSubmit = packagingConfirmed && reason && (reason !== "Product damaged in transit" || damageImageUrl.trim().length > 0);

  return (
    <div className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4" onClick={onCancel}>
      <div className="bg-ink-900 border border-white/10 w-[min(560px,95vw)] max-h-[90vh] overflow-y-auto p-8" onClick={(e)=>e.stopPropagation()} data-testid="return-dialog">
        <h3 className="font-serif text-2xl">Request return</h3>
        <div className="mt-1 text-xs text-cream/50">Order {order.order_number} · <span className="text-gold">{daysLeft} day{daysLeft === 1 ? "" : "s"} left</span> in return window</div>

        <div className="mt-5 border border-red-500/30 bg-red-500/5 p-4 text-xs leading-relaxed text-cream/80">
          <div className="text-red-300 uppercase tracking-luxury text-[10px] mb-2 font-medium">Important — Packaging notice</div>
          The piece must be returned in <span className="text-cream font-medium">its original box, foam and outer wrap, exactly as received.</span> Any damage caused by improper repacking (chipped resin, cracked mirror, bent border) will be assessed by our atelier and repair/restocking fees will be deducted from your refund. Returns must be raised within <span className="text-cream font-medium">3 days of delivery.</span>
        </div>

        <div className="mt-6 space-y-4">
          <label className="block">
            <span className="text-[10px] uppercase tracking-luxury text-cream/50">Reason</span>
            <select data-testid="return-reason" value={reason} onChange={(e)=>setReason(e.target.value)} className="mt-1.5 w-full bg-ink-950 border border-white/15 focus:border-gold px-3 py-2.5 text-sm text-cream outline-none">
              {["Product damaged in transit","Not as described","Changed my mind","Wrong colour delivered","Other"].map(r=>(<option key={r} value={r} className="bg-ink-900">{r}</option>))}
            </select>
          </label>

          <label className="block">
            <span className="text-[10px] uppercase tracking-luxury text-cream/50">
              Damage evidence — image URL {reason === "Product damaged in transit" && <span className="text-red-300">*</span>}
            </span>
            <input
              data-testid="return-damage-url"
              type="url"
              placeholder="https://... (upload to Drive/Imgur then paste link)"
              value={damageImageUrl}
              onChange={(e)=>setDamageImageUrl(e.target.value)}
              className="mt-1.5 w-full bg-ink-950 border border-white/15 focus:border-gold px-3 py-2.5 text-sm text-cream outline-none"
            />
            <span className="mt-1 block text-[10px] text-cream/40">Please upload photos to Google Drive/Imgur/Dropbox and paste the shareable link. Include packaging and product angles.</span>
          </label>

          <label className="block">
            <span className="text-[10px] uppercase tracking-luxury text-cream/50">Details</span>
            <textarea data-testid="return-details" rows={4} value={details} onChange={(e)=>setDetails(e.target.value)} placeholder="Tell us what happened, where the damage is, etc." className="mt-1.5 w-full bg-ink-950 border border-white/15 focus:border-gold px-3 py-2.5 text-sm text-cream outline-none" />
          </label>

          <label className="flex items-start gap-3 text-xs text-cream/70 cursor-pointer" data-testid="return-packaging-label">
            <input
              data-testid="return-packaging-checkbox"
              type="checkbox"
              checked={packagingConfirmed}
              onChange={(e)=>setPackagingConfirmed(e.target.checked)}
              className="mt-0.5 accent-gold"
            />
            <span>I confirm the piece is still in its <span className="text-cream">original packaging</span> and I understand that fees will be deducted if it is returned damaged due to improper repacking.</span>
          </label>
        </div>

        <div className="mt-6 flex gap-3">
          <button onClick={onCancel} data-testid="return-cancel" className="flex-1 py-3 border border-white/15 text-xs uppercase tracking-luxury">Cancel</button>
          <button
            data-testid="return-submit"
            disabled={!canSubmit}
            onClick={()=>onSubmit(order.order_number, { reason, details, damage_image_url: damageImageUrl || null, packaging_confirmed: packagingConfirmed })}
            className="flex-1 bg-gold text-ink-950 py-3 text-xs uppercase tracking-luxury disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Submit request
          </button>
        </div>
      </div>
    </div>
  );
}
