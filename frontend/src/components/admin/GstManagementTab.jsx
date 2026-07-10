import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Trash2, Loader2, Edit2, Percent, Tag as TagIcon, Hash, ShieldCheck, Info } from "lucide-react";

const inp = "mt-1.5 w-full bg-ink-950 border border-white/15 focus:border-gold outline-none px-3 py-2.5 text-sm text-cream";

function Fld({ label, children, hint }) {
  return (
    <label className="block">
      <span className="text-[10px] uppercase tracking-luxury text-cream/50">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-[10px] text-cream/40 italic">{hint}</span>}
    </label>
  );
}

const COMMON_HSN = [
  { code: "7009", label: "Mirrors (glass) — 18%" },
  { code: "9701", label: "Handmade paintings / art — 12%" },
  { code: "3926", label: "Articles of plastics / resin — 18%" },
  { code: "9403", label: "Furniture — 18%" },
  { code: "9405", label: "Lamps & lighting — 18%" },
  { code: "4414", label: "Wooden frames — 12%" },
  { code: "6913", label: "Ceramic ornaments — 12%" },
];

const COMMON_RATES = [0, 5, 12, 18, 28];

export default function GstManagementTab({ authed }) {
  const [rules, setRules] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [ruleEditing, setRuleEditing] = useState(null);
  const [catEditing, setCatEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const [view, setView] = useState("rules"); // rules | categories

  const reload = useCallback(async () => {
    if (!authed) return;
    setLoading(true);
    try {
      const [r, c] = await Promise.all([
        authed.get("/admin/gst-rules"),
        authed.get("/admin/product-categories"),
      ]);
      setRules(r.data || []);
      setCategories(c.data || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to load GST data");
    } finally {
      setLoading(false);
    }
  }, [authed]);

  useEffect(() => { reload(); }, [reload]);

  const saveRule = async (form) => {
    setSaving(true);
    try {
      const payload = {
        hsn_code: (form.hsn_code || "").trim() || null,
        category: (form.category || "").trim() || null,
        rate_percent: Number(form.rate_percent),
        description: form.description || null,
        active: !!form.active,
      };
      if (!payload.hsn_code && !payload.category) {
        toast.error("Choose an HSN code or a category");
        setSaving(false); return;
      }
      if (form.id) {
        await authed.patch(`/admin/gst-rules/${form.id}`, payload);
        toast.success("Rule updated");
      } else {
        await authed.post("/admin/gst-rules", payload);
        toast.success("Rule created");
      }
      setRuleEditing(null);
      reload();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const deleteRule = async (id) => {
    if (!window.confirm("Delete this GST rule? Existing orders keep their calculated tax.")) return;
    try {
      await authed.delete(`/admin/gst-rules/${id}`);
      toast.success("Rule deleted");
      reload();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Delete failed");
    }
  };

  const saveCategory = async (form) => {
    setSaving(true);
    try {
      const payload = {
        name: (form.name || "").trim(),
        slug: (form.slug || "").trim() || null,
        description: form.description || null,
        active: !!form.active,
      };
      if (!payload.name) { toast.error("Category name is required"); setSaving(false); return; }
      if (form.id) await authed.patch(`/admin/product-categories/${form.id}`, payload);
      else await authed.post("/admin/product-categories", payload);
      toast.success(form.id ? "Category updated" : "Category created");
      setCatEditing(null);
      reload();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const deleteCategory = async (id) => {
    if (!window.confirm("Delete this category? Products using it will fall back to HSN-only tax lookup.")) return;
    try {
      await authed.delete(`/admin/product-categories/${id}`);
      toast.success("Category deleted");
      reload();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Delete failed");
    }
  };

  if (loading) return (
    <div className="text-cream/40 text-sm"><Loader2 className="w-4 h-4 animate-spin inline mr-2" /> Loading GST management…</div>
  );

  return (
    <>
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-2 text-[10px] uppercase tracking-luxury text-gold-soft">
            <ShieldCheck className="w-3.5 h-3.5" /> GSTIN · 27AVGPK1480P1Z3 · Maharashtra
          </div>
          <h1 className="font-serif text-4xl mt-1">GST Management</h1>
          <div className="mt-2 text-xs text-cream/50 max-w-2xl">
            Map GST tax slabs to HSN codes or product categories. The cart engine reads HSN first,
            then category, and computes CGST + SGST for Maharashtra deliveries or IGST for the rest of India.
          </div>
        </div>
        <div className="flex gap-2">
          <button
            data-testid="gst-view-rules"
            onClick={() => setView("rules")}
            className={`px-4 py-2 text-xs uppercase tracking-luxury border ${view === "rules" ? "border-gold text-gold" : "border-white/10 text-cream/60"}`}
          >Tax rules</button>
          <button
            data-testid="gst-view-categories"
            onClick={() => setView("categories")}
            className={`px-4 py-2 text-xs uppercase tracking-luxury border ${view === "categories" ? "border-gold text-gold" : "border-white/10 text-cream/60"}`}
          >Categories</button>
        </div>
      </div>

      {view === "rules" && (
        <>
          <div className="mt-8 flex justify-between items-center">
            <div className="text-sm text-cream/70">{rules.length} active mapping{rules.length === 1 ? "" : "s"}</div>
            <button
              data-testid="gst-new-rule"
              onClick={() => setRuleEditing({ hsn_code: "", category: "", rate_percent: 18, description: "", active: true })}
              className="inline-flex items-center gap-2 bg-gold text-ink-950 px-4 py-2.5 text-xs uppercase tracking-luxury"
            ><Plus className="w-3.5 h-3.5" /> New rule</button>
          </div>
          <div className="mt-4 hairline overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/5 text-[10px] uppercase tracking-luxury text-cream/40">
                  <th className="px-4 py-3 text-left font-normal">Target</th>
                  <th className="px-4 py-3 text-left font-normal">Rate</th>
                  <th className="px-4 py-3 text-left font-normal">Description</th>
                  <th className="px-4 py-3 text-left font-normal">Status</th>
                  <th className="px-4 py-3 text-right font-normal">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rules.length === 0 && (
                  <tr><td colSpan={5} className="px-4 py-10 text-center text-cream/40">No rules yet — add one to start computing tax.</td></tr>
                )}
                {rules.map((r) => (
                  <tr key={r.id} data-testid={`gst-rule-row-${r.id}`} className="border-b border-white/5 hover:bg-white/5">
                    <td className="px-4 py-4">
                      {r.hsn_code ? (
                        <div className="flex items-center gap-2">
                          <Hash className="w-3.5 h-3.5 text-gold" />
                          <span className="font-mono text-gold">HSN {r.hsn_code}</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <TagIcon className="w-3.5 h-3.5 text-cream/60" />
                          <span className="text-cream/80 capitalize">{r.category}</span>
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-4">
                      <span className="inline-flex items-center gap-1 font-serif text-lg text-cream">
                        {r.rate_percent}<Percent className="w-3 h-3 text-gold" />
                      </span>
                    </td>
                    <td className="px-4 py-4 text-cream/70 text-xs">{r.description || "—"}</td>
                    <td className="px-4 py-4">
                      {r.active
                        ? <span className="text-[10px] uppercase tracking-luxury text-gold border border-gold/40 px-2 py-0.5">Active</span>
                        : <span className="text-[10px] uppercase tracking-luxury text-cream/40 border border-white/10 px-2 py-0.5">Disabled</span>}
                    </td>
                    <td className="px-4 py-4 text-right whitespace-nowrap">
                      <button
                        data-testid={`gst-rule-edit-${r.id}`}
                        onClick={() => setRuleEditing({ ...r })}
                        className="text-xs text-gold hover:text-cream border border-gold/30 px-3 py-1.5 inline-flex items-center gap-1.5 mr-2"
                      ><Edit2 className="w-3 h-3" /> Edit</button>
                      <button
                        data-testid={`gst-rule-delete-${r.id}`}
                        onClick={() => deleteRule(r.id)}
                        className="text-red-400 hover:text-red-300 p-2 inline-flex"
                      ><Trash2 className="w-3.5 h-3.5" /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-6 hairline p-5 bg-ink-900/50 flex gap-3 text-xs text-cream/60">
            <Info className="w-4 h-4 text-gold shrink-0" />
            <div>
              <strong className="text-cream">Priority:</strong> HSN code match &gt; Category match. Product without any match is treated as 0% (non-taxable).
              <br/><strong className="text-cream">Treatment:</strong> Prices are treated as <em>GST-inclusive</em> (as per Indian MRP norms) —
              tax is extracted from the listed price and appears as a distinct line on the invoice.
              <br/><strong className="text-cream">Split:</strong> Deliveries to Maharashtra are billed as CGST + SGST (half each), all other states as IGST (full rate).
            </div>
          </div>
        </>
      )}

      {view === "categories" && (
        <>
          <div className="mt-8 flex justify-between items-center">
            <div className="text-sm text-cream/70">{categories.length} categor{categories.length === 1 ? "y" : "ies"}</div>
            <button
              data-testid="cat-new"
              onClick={() => setCatEditing({ name: "", slug: "", description: "", active: true })}
              className="inline-flex items-center gap-2 bg-gold text-ink-950 px-4 py-2.5 text-xs uppercase tracking-luxury"
            ><Plus className="w-3.5 h-3.5" /> New category</button>
          </div>
          <div className="mt-4 grid gap-3">
            {categories.length === 0 && <div className="hairline p-8 text-center text-cream/40">No categories yet.</div>}
            {categories.map((c) => (
              <div key={c.id} data-testid={`cat-row-${c.slug}`} className="hairline p-4 flex flex-wrap items-center gap-4">
                <div className="flex-1 min-w-[200px]">
                  <div className="font-serif text-lg text-cream">{c.name}</div>
                  <div className="text-[10px] uppercase tracking-luxury text-cream/40 mt-0.5 font-mono">{c.slug}</div>
                  {c.description && <div className="text-xs text-cream/60 mt-1">{c.description}</div>}
                </div>
                {!c.active && <span className="text-[10px] uppercase tracking-luxury text-red-400 border border-red-400/40 px-2 py-0.5">Disabled</span>}
                <button
                  data-testid={`cat-edit-${c.slug}`}
                  onClick={() => setCatEditing({ ...c })}
                  className="text-xs text-gold hover:text-cream border border-gold/30 px-3 py-1.5 inline-flex items-center gap-1.5"
                ><Edit2 className="w-3 h-3" /> Edit</button>
                <button
                  data-testid={`cat-delete-${c.slug}`}
                  onClick={() => deleteCategory(c.id)}
                  className="text-red-400 hover:text-red-300 p-2"
                ><Trash2 className="w-4 h-4" /></button>
              </div>
            ))}
          </div>
        </>
      )}

      {ruleEditing && (
        <RuleEditor
          initial={ruleEditing}
          categories={categories}
          saving={saving}
          onCancel={() => setRuleEditing(null)}
          onSave={saveRule}
        />
      )}
      {catEditing && (
        <CategoryEditor
          initial={catEditing}
          saving={saving}
          onCancel={() => setCatEditing(null)}
          onSave={saveCategory}
        />
      )}
    </>
  );
}

function RuleEditor({ initial, categories, saving, onCancel, onSave }) {
  const [f, setF] = useState(initial);
  const [target, setTarget] = useState(initial.hsn_code ? "hsn" : "category");
  const upd = (k) => (e) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  const submit = (e) => {
    e.preventDefault();
    const payload = { ...f };
    if (target === "hsn") payload.category = "";
    else payload.hsn_code = "";
    onSave(payload);
  };

  return (
    <div className="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4" onClick={onCancel}>
      <form onSubmit={submit} className="bg-ink-900 border border-white/10 w-[min(560px,95vw)] max-h-[90vh] overflow-y-auto p-8" onClick={(e) => e.stopPropagation()} data-testid="gst-rule-editor">
        <div className="flex justify-between items-center">
          <h3 className="font-serif text-2xl">{f.id ? "Edit tax rule" : "New tax rule"}</h3>
          <button type="button" onClick={onCancel} className="text-cream/50 hover:text-cream text-sm">Cancel</button>
        </div>

        <div className="mt-6 space-y-5">
          <Fld label="Target — what does this rule apply to?">
            <div className="mt-1.5 flex gap-2">
              <button type="button" onClick={() => setTarget("hsn")} className={`flex-1 py-2.5 text-xs uppercase tracking-luxury border ${target === "hsn" ? "border-gold text-gold bg-gold/5" : "border-white/15 text-cream/60"}`}>HSN code</button>
              <button type="button" onClick={() => setTarget("category")} className={`flex-1 py-2.5 text-xs uppercase tracking-luxury border ${target === "category" ? "border-gold text-gold bg-gold/5" : "border-white/15 text-cream/60"}`}>Category</button>
            </div>
          </Fld>

          {target === "hsn" ? (
            <Fld label="HSN code" hint="Use the 4–8 digit HSN classification. Tap a suggestion to auto-fill.">
              <input required list="hsn-datalist" value={f.hsn_code || ""} onChange={upd("hsn_code")} className={inp} placeholder="e.g. 7009" data-testid="gst-rule-hsn" />
              <datalist id="hsn-datalist">
                {COMMON_HSN.map((h) => <option key={h.code} value={h.code}>{h.label}</option>)}
              </datalist>
            </Fld>
          ) : (
            <Fld label="Category">
              <select required value={f.category || ""} onChange={upd("category")} className={inp} data-testid="gst-rule-category">
                <option value="">Select a category…</option>
                {categories.map((c) => (
                  <option key={c.slug} value={c.slug} className="bg-ink-900">{c.name}</option>
                ))}
              </select>
            </Fld>
          )}

          <Fld label="Tax rate (%)">
            <div className="flex items-center gap-2">
              <input required type="number" min="0" max="100" step="0.01" value={f.rate_percent} onChange={upd("rate_percent")} className={`${inp} flex-1`} data-testid="gst-rule-rate" />
              <div className="flex gap-1">
                {COMMON_RATES.map((r) => (
                  <button key={r} type="button" onClick={() => setF({ ...f, rate_percent: r })}
                    className="text-[10px] uppercase tracking-luxury border border-white/10 hover:border-gold hover:text-gold px-2 py-2">
                    {r}%
                  </button>
                ))}
              </div>
            </div>
          </Fld>

          <Fld label="Description (internal)">
            <input value={f.description || ""} onChange={upd("description")} className={inp} placeholder="e.g. Mirrors — HSN 7009" data-testid="gst-rule-desc" />
          </Fld>

          <label className="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" checked={!!f.active} onChange={upd("active")} className="accent-gold w-4 h-4" data-testid="gst-rule-active" />
            <span className="text-sm text-cream">Active — rule participates in tax calculation</span>
          </label>
        </div>

        <button type="submit" disabled={saving} data-testid="gst-rule-save" className="mt-8 w-full bg-gold text-ink-950 py-4 text-xs uppercase tracking-luxury hover:bg-cream disabled:opacity-60">
          {saving ? <Loader2 className="w-4 h-4 animate-spin inline" /> : "Save rule"}
        </button>
      </form>
    </div>
  );
}

function CategoryEditor({ initial, saving, onCancel, onSave }) {
  const [f, setF] = useState(initial);
  const upd = (k) => (e) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  const submit = (e) => { e.preventDefault(); onSave(f); };
  return (
    <div className="fixed inset-0 z-[80] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4" onClick={onCancel}>
      <form onSubmit={submit} className="bg-ink-900 border border-white/10 w-[min(500px,95vw)] max-h-[90vh] overflow-y-auto p-8" onClick={(e) => e.stopPropagation()} data-testid="cat-editor">
        <div className="flex justify-between items-center">
          <h3 className="font-serif text-2xl">{f.id ? "Edit category" : "New category"}</h3>
          <button type="button" onClick={onCancel} className="text-cream/50 hover:text-cream text-sm">Cancel</button>
        </div>
        <div className="mt-6 space-y-5">
          <Fld label="Name">
            <input required value={f.name || ""} onChange={upd("name")} className={inp} data-testid="cat-name" />
          </Fld>
          <Fld label="Slug (URL-safe, auto-generated if blank)" hint="Lowercase, dashes. Used by GST rules & product forms.">
            <input value={f.slug || ""} onChange={upd("slug")} className={`${inp} font-mono`} placeholder="e.g. wall-art" data-testid="cat-slug" />
          </Fld>
          <Fld label="Description (optional)">
            <input value={f.description || ""} onChange={upd("description")} className={inp} data-testid="cat-desc" />
          </Fld>
          <label className="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" checked={!!f.active} onChange={upd("active")} className="accent-gold w-4 h-4" data-testid="cat-active" />
            <span className="text-sm text-cream">Active — appears in the product dropdown</span>
          </label>
        </div>
        <button type="submit" disabled={saving} data-testid="cat-save" className="mt-8 w-full bg-gold text-ink-950 py-4 text-xs uppercase tracking-luxury hover:bg-cream disabled:opacity-60">
          {saving ? <Loader2 className="w-4 h-4 animate-spin inline" /> : "Save category"}
        </button>
      </form>
    </div>
  );
}
