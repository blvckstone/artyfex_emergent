import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2, Plus, Trash2, Save, ShieldCheck, X } from "lucide-react";

const inp = "w-full bg-ink-950 border border-white/15 focus:border-gold focus:outline-none px-3 py-2.5 text-sm text-cream outline-none";

const PERM_LABELS = {
  manage_products: "Products",
  manage_orders: "Orders",
  manage_returns: "Returns",
  manage_customers: "Customers",
  manage_reviews: "Reviews",
  manage_leads: "B2B leads",
  manage_coupons: "Coupons",
  manage_homepage: "Homepage CMS",
  manage_shipping: "Shipping",
  view_analytics: "Analytics",
  manage_employees: "Employees / RBAC",
};

export default function EmployeesTab({ authed, me }) {
  const [employees, setEmployees] = useState([]);
  const [allPerms, setAllPerms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ email: "", password: "", display_name: "", permissions: [] });
  const [editingId, setEditingId] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const [empRes, permRes] = await Promise.all([
        authed.get("/admin/employees"),
        authed.get("/admin/permissions"),
      ]);
      setEmployees(empRes.data);
      setAllPerms(permRes.data.all || []);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to load employees");
    } finally { setLoading(false); }
  };

  useEffect(() => { if (authed) load(); /* eslint-disable-next-line */ }, [authed]);

  const isOwner = me?.role === "owner";

  const resetForm = () => setForm({ email: "", password: "", display_name: "", permissions: [] });

  const togglePerm = (p) => {
    setForm((prev) => ({
      ...prev,
      permissions: prev.permissions.includes(p)
        ? prev.permissions.filter((x) => x !== p)
        : [...prev.permissions, p],
    }));
  };

  const create = async () => {
    if (!form.email || !form.password) { toast.error("Email and password are required"); return; }
    setCreating(true);
    try {
      await authed.post("/admin/employees", form);
      toast.success("Employee created");
      resetForm();
      setShowForm(false);
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Create failed");
    } finally { setCreating(false); }
  };

  const update = async (id, payload) => {
    try {
      await authed.patch(`/admin/employees/${id}`, payload);
      toast.success("Updated");
      load();
      setEditingId(null);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Update failed");
    }
  };

  const remove = async (id) => {
    if (!window.confirm("Delete this employee? They will lose access immediately.")) return;
    try {
      await authed.delete(`/admin/employees/${id}`);
      toast.success("Employee removed");
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Delete failed");
    }
  };

  if (!isOwner) {
    return <div className="text-cream/40 text-sm">Only the owner can manage employees.</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-serif text-4xl">Employees</h1>
          <p className="mt-2 text-sm text-cream/50">Create sub-accounts with limited privileges. Owner keeps full access at all times.</p>
        </div>
        <button onClick={() => setShowForm((v) => !v)} data-testid="employees-new" className="inline-flex items-center gap-2 bg-gold text-ink-950 px-5 py-3 text-xs uppercase tracking-luxury hover:bg-cream">
          {showForm ? <X className="w-3.5 h-3.5" /> : <Plus className="w-3.5 h-3.5" />} {showForm ? "Cancel" : "Add employee"}
        </button>
      </div>

      {showForm && (
        <div className="hairline p-6 bg-ink-900/50" data-testid="employees-form">
          <div className="text-[10px] uppercase tracking-luxury text-gold-soft mb-4">New employee</div>
          <div className="grid sm:grid-cols-3 gap-3">
            <label className="block"><span className="text-[10px] uppercase tracking-luxury text-cream/50">Email</span><input data-testid="employees-email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className={`${inp} mt-1.5`} /></label>
            <label className="block"><span className="text-[10px] uppercase tracking-luxury text-cream/50">Display name</span><input value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} className={`${inp} mt-1.5`} /></label>
            <label className="block"><span className="text-[10px] uppercase tracking-luxury text-cream/50">Password</span><input data-testid="employees-password" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className={`${inp} mt-1.5`} /></label>
          </div>
          <div className="mt-4">
            <div className="text-[10px] uppercase tracking-luxury text-cream/50 mb-2">Permissions</div>
            <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-2">
              {allPerms.map((p) => (
                <label key={p} className="flex items-center gap-2 text-sm text-cream/80 border border-white/10 px-3 py-2 cursor-pointer hover:border-gold/40">
                  <input type="checkbox" checked={form.permissions.includes(p)} onChange={() => togglePerm(p)} className="accent-gold" />
                  {PERM_LABELS[p] || p}
                </label>
              ))}
            </div>
          </div>
          <div className="mt-6 flex justify-end">
            <button data-testid="employees-create" onClick={create} disabled={creating} className="inline-flex items-center gap-2 bg-gold text-ink-950 px-6 py-3 text-xs uppercase tracking-luxury hover:bg-cream disabled:opacity-60">
              {creating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
              {creating ? "Creating…" : "Create employee"}
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-cream/40 text-sm"><Loader2 className="w-4 h-4 animate-spin inline" /> Loading…</div>
      ) : employees.length === 0 ? (
        <div className="hairline p-10 text-center text-cream/40">No employees yet. Add one to delegate operations.</div>
      ) : (
        <div className="space-y-3">
          {employees.map((e) => (
            <EmployeeRow key={e.id} emp={e} allPerms={allPerms} onSave={(patch) => update(e.id, patch)} onDelete={() => remove(e.id)} isEditing={editingId === e.id} setEditing={setEditingId} />
          ))}
        </div>
      )}
    </div>
  );
}

function EmployeeRow({ emp, allPerms, onSave, onDelete, isEditing, setEditing }) {
  const [perms, setPerms] = useState(emp.permissions || []);
  const [displayName, setDisplayName] = useState(emp.display_name || "");
  const [password, setPassword] = useState("");

  useEffect(() => {
    if (isEditing) {
      setPerms(emp.permissions || []);
      setDisplayName(emp.display_name || "");
      setPassword("");
    }
  }, [isEditing, emp]);

  const toggle = (p) => setPerms((prev) => prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]);

  const save = () => {
    const patch = { display_name: displayName, permissions: perms };
    if (password) patch.password = password;
    onSave(patch);
  };

  return (
    <div className="hairline p-5" data-testid={`employee-row-${emp.id}`}>
      <div className="flex items-center gap-3 flex-wrap">
        <div>
          <div className="text-sm text-cream">{emp.display_name || emp.email}</div>
          <div className="text-xs text-cream/50">{emp.email}</div>
        </div>
        <div className="text-[10px] uppercase tracking-luxury text-gold/70 ml-2 border border-gold/30 px-2 py-1">{emp.role}</div>
        <div className="ml-auto flex gap-2">
          {isEditing ? (
            <>
              <button onClick={save} data-testid={`employee-save-${emp.id}`} className="inline-flex items-center gap-1.5 bg-gold text-ink-950 px-4 py-2 text-xs uppercase tracking-luxury hover:bg-cream"><Save className="w-3 h-3" /> Save</button>
              <button onClick={() => setEditing(null)} className="px-4 py-2 border border-white/15 text-xs uppercase tracking-luxury text-cream/60">Cancel</button>
            </>
          ) : (
            <>
              <button onClick={() => setEditing(emp.id)} data-testid={`employee-edit-${emp.id}`} className="px-4 py-2 border border-white/15 text-xs uppercase tracking-luxury text-cream/70 hover:border-gold hover:text-gold">Edit</button>
              <button onClick={onDelete} data-testid={`employee-delete-${emp.id}`} className="p-2 text-red-400/70 hover:text-red-400 border border-red-500/30"><Trash2 className="w-4 h-4" /></button>
            </>
          )}
        </div>
      </div>

      {!isEditing && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {(emp.permissions || []).length === 0 && <span className="text-xs text-cream/40">No permissions assigned</span>}
          {(emp.permissions || []).map((p) => (
            <span key={p} className="text-[10px] uppercase tracking-luxury border border-white/10 px-2 py-1 text-cream/70">{PERM_LABELS[p] || p}</span>
          ))}
        </div>
      )}

      {isEditing && (
        <div className="mt-4 space-y-4 border-t border-white/5 pt-4">
          <div className="grid sm:grid-cols-2 gap-3">
            <label className="block"><span className="text-[10px] uppercase tracking-luxury text-cream/50">Display name</span><input value={displayName} onChange={(e) => setDisplayName(e.target.value)} className={`${inp} mt-1.5`} /></label>
            <label className="block"><span className="text-[10px] uppercase tracking-luxury text-cream/50">New password (leave blank to keep)</span><input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className={`${inp} mt-1.5`} /></label>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-luxury text-cream/50 mb-2">Permissions</div>
            <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-2">
              {allPerms.map((p) => (
                <label key={p} className="flex items-center gap-2 text-sm text-cream/80 border border-white/10 px-3 py-2 cursor-pointer hover:border-gold/40">
                  <input type="checkbox" data-testid={`employee-${emp.id}-perm-${p}`} checked={perms.includes(p)} onChange={() => toggle(p)} className="accent-gold" />
                  {PERM_LABELS[p] || p}
                </label>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
