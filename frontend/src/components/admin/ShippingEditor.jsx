import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2, Save, Truck, Plus, Trash2 } from "lucide-react";

const inp = "w-full bg-ink-950 border border-white/15 focus:border-gold focus:outline-none px-3 py-2.5 text-sm text-cream outline-none";
const Fld = ({ label, children, hint }) => (
  <label className="block">
    <span className="text-[10px] uppercase tracking-luxury text-cream/50">{label}</span>
    <div className="mt-1.5">{children}</div>
    {hint && <div className="mt-1 text-[10px] text-cream/40">{hint}</div>}
  </label>
);

const INDIAN_STATES = [
  "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
  "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
  "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
  "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
  "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
  "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
  "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
];

export default function ShippingEditor({ authed, api }) {
  const [data, setData] = useState(null);
  const [saving, setSaving] = useState(false);
  const [testState, setTestState] = useState("Maharashtra");
  const [testPincode, setTestPincode] = useState("400095");
  const [testSubtotal, setTestSubtotal] = useState(15000);
  const [testResult, setTestResult] = useState(null);

  useEffect(() => {
    if (!authed) return;
    authed.get("/admin/shipping-settings").then(({ data }) => setData(data)).catch(() => toast.error("Could not load shipping settings"));
  }, [authed]);

  if (!data) return <div className="text-cream/40 text-sm"><Loader2 className="w-4 h-4 animate-spin inline" /> Loading shipping…</div>;

  const upd = (k, v) => setData((prev) => ({ ...prev, [k]: v }));
  const updZone = (idx, field, value) => {
    setData((prev) => {
      const clone = { ...prev, zone_rates: [...(prev.zone_rates || [])] };
      clone.zone_rates[idx] = { ...clone.zone_rates[idx], [field]: value };
      return clone;
    });
  };
  const addZone = () => setData((p) => ({ ...p, zone_rates: [...(p.zone_rates || []), { name: "New zone", states: [], rate_inr: 999 }] }));
  const removeZone = (idx) => setData((p) => ({ ...p, zone_rates: p.zone_rates.filter((_, i) => i !== idx) }));

  const updBand = (idx, field, value) => {
    setData((prev) => {
      const clone = { ...prev, distance_bands: [...(prev.distance_bands || [])] };
      clone.distance_bands[idx] = { ...clone.distance_bands[idx], [field]: value };
      return clone;
    });
  };
  const addBand = () => setData((p) => ({ ...p, distance_bands: [...(p.distance_bands || []), { max_km: 500, rate_inr: 499 }] }));
  const removeBand = (idx) => setData((p) => ({ ...p, distance_bands: p.distance_bands.filter((_, i) => i !== idx) }));

  const save = async () => {
    setSaving(true);
    try {
      const payload = {
        ...data,
        flat_rate_inr: Number(data.flat_rate_inr) || 0,
        free_shipping_above_inr: Number(data.free_shipping_above_inr) || 0,
        distance_base_fee_inr: Number(data.distance_base_fee_inr) || 0,
        distance_per_km_inr: Number(data.distance_per_km_inr) || 0,
        zone_rates: (data.zone_rates || []).map((z) => ({
          name: z.name || "",
          states: Array.isArray(z.states) ? z.states : (z.states || "").split(",").map((s) => s.trim()).filter(Boolean),
          rate_inr: Number(z.rate_inr) || 0,
        })),
        distance_bands: (data.distance_bands || []).map((b) => ({ max_km: Number(b.max_km) || 0, rate_inr: Number(b.rate_inr) || 0 })),
      };
      const { data: saved } = await authed.patch("/admin/shipping-settings", payload);
      setData(saved);
      toast.success("Shipping settings saved");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Save failed");
    } finally { setSaving(false); }
  };

  const testCalc = async () => {
    try {
      const { data } = await api.post("/shipping/calculate", { subtotal_inr: Number(testSubtotal) || 0, state: testState, pincode: testPincode });
      setTestResult(data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Test failed");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-serif text-4xl">Shipping</h1>
          <p className="mt-2 text-sm text-cream/50">Configure how shipping is priced. Free-shipping threshold applies across all methods.</p>
        </div>
        <button data-testid="admin-shipping-save" onClick={save} disabled={saving} className="inline-flex items-center gap-2 bg-gold text-ink-950 px-6 py-3 text-xs uppercase tracking-luxury hover:bg-cream disabled:opacity-60">
          {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
          {saving ? "Saving…" : "Save changes"}
        </button>
      </div>

      <div className="hairline p-6 bg-ink-900/50">
        <div className="flex items-center gap-3 mb-4"><Truck className="w-4 h-4 text-gold" /><div className="text-[10px] uppercase tracking-luxury text-gold-soft">Method</div></div>
        <div className="grid sm:grid-cols-3 gap-3">
          {[
            { key: "flat", label: "Flat rate", desc: "Single fee across India" },
            { key: "zone", label: "Zone-based", desc: "Different fee per state group" },
            { key: "distance", label: "Distance-based", desc: "Auto-priced by km from Mumbai" },
          ].map((opt) => (
            <button
              key={opt.key}
              type="button"
              data-testid={`shipping-method-${opt.key}`}
              onClick={() => upd("method", opt.key)}
              className={`text-left p-4 border transition-colors ${data.method === opt.key ? "border-gold bg-gold/5" : "border-white/10 hover:border-white/30"}`}
            >
              <div className={`text-sm ${data.method === opt.key ? "text-gold" : "text-cream"}`}>{opt.label}</div>
              <div className="text-xs text-cream/50 mt-1">{opt.desc}</div>
            </button>
          ))}
        </div>

        <div className="mt-6 grid sm:grid-cols-2 gap-4">
          <Fld label="Free shipping above (₹)" hint="Applies to all methods. Set 0 to disable.">
            <input type="number" data-testid="shipping-free-above" value={data.free_shipping_above_inr} onChange={(e) => upd("free_shipping_above_inr", e.target.value)} className={inp} />
          </Fld>
          <Fld label="Origin state" hint="Used for distance calculations.">
            <input value={data.origin_state} onChange={(e) => upd("origin_state", e.target.value)} className={inp} />
          </Fld>
        </div>
      </div>

      {data.method === "flat" && (
        <div className="hairline p-6 bg-ink-900/50">
          <div className="text-[10px] uppercase tracking-luxury text-gold-soft mb-3">Flat rate</div>
          <Fld label="Rate (₹)"><input type="number" data-testid="shipping-flat-rate" value={data.flat_rate_inr} onChange={(e) => upd("flat_rate_inr", e.target.value)} className={inp} /></Fld>
        </div>
      )}

      {data.method === "zone" && (
        <div className="hairline p-6 bg-ink-900/50">
          <div className="flex items-center justify-between mb-3">
            <div className="text-[10px] uppercase tracking-luxury text-gold-soft">Zone rates</div>
            <button type="button" onClick={addZone} className="inline-flex items-center gap-1.5 text-xs text-gold border border-gold/40 px-3 py-1.5"><Plus className="w-3 h-3" /> Add zone</button>
          </div>
          <p className="text-xs text-cream/50 mb-4">Add states to each zone. Leave states empty on the last zone to make it the “rest of India” fallback.</p>
          <div className="space-y-3">
            {(data.zone_rates || []).map((z, idx) => (
              <div key={idx} className="border border-white/10 p-4 grid sm:grid-cols-[1fr_2fr_140px_40px] gap-3 items-end">
                <Fld label="Name"><input value={z.name} onChange={(e) => updZone(idx, "name", e.target.value)} className={inp} /></Fld>
                <Fld label="States" hint="Multi-select. Empty = fallback zone.">
                  <select multiple value={z.states || []} onChange={(e) => updZone(idx, "states", Array.from(e.target.selectedOptions).map((o) => o.value))} className={`${inp} h-28`}>
                    {INDIAN_STATES.map((s) => <option key={s} value={s} className="bg-ink-900">{s}</option>)}
                  </select>
                </Fld>
                <Fld label="Rate (₹)"><input type="number" value={z.rate_inr} onChange={(e) => updZone(idx, "rate_inr", e.target.value)} className={inp} /></Fld>
                <button type="button" onClick={() => removeZone(idx)} className="p-2 text-red-400 hover:text-red-300" title="Remove"><Trash2 className="w-4 h-4" /></button>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.method === "distance" && (
        <div className="hairline p-6 bg-ink-900/50">
          <div className="text-[10px] uppercase tracking-luxury text-gold-soft mb-3">Distance-based rates</div>
          <p className="text-xs text-cream/50 mb-4">Distance is derived from the customer’s state (approx km from your Mumbai origin). Use bands for tiered pricing; if no band matches we fall back to <span className="text-cream">base + ₹/km × distance</span>.</p>
          <div className="grid sm:grid-cols-2 gap-4">
            <Fld label="Base fee (₹)"><input type="number" value={data.distance_base_fee_inr} onChange={(e) => upd("distance_base_fee_inr", e.target.value)} className={inp} /></Fld>
            <Fld label="Per-km rate (₹)"><input type="number" step="0.1" value={data.distance_per_km_inr} onChange={(e) => upd("distance_per_km_inr", e.target.value)} className={inp} /></Fld>
          </div>
          <div className="mt-6">
            <div className="flex items-center justify-between mb-3">
              <div className="text-[10px] uppercase tracking-luxury text-cream/50">Distance bands (optional)</div>
              <button type="button" onClick={addBand} className="inline-flex items-center gap-1.5 text-xs text-gold border border-gold/40 px-3 py-1.5"><Plus className="w-3 h-3" /> Add band</button>
            </div>
            <div className="space-y-2">
              {(data.distance_bands || []).map((b, idx) => (
                <div key={idx} className="grid grid-cols-[1fr_1fr_40px] gap-3 items-end">
                  <Fld label="Up to (km)"><input type="number" value={b.max_km} onChange={(e) => updBand(idx, "max_km", e.target.value)} className={inp} /></Fld>
                  <Fld label="Rate (₹)"><input type="number" value={b.rate_inr} onChange={(e) => updBand(idx, "rate_inr", e.target.value)} className={inp} /></Fld>
                  <button type="button" onClick={() => removeBand(idx)} className="p-2 text-red-400 hover:text-red-300"><Trash2 className="w-4 h-4" /></button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Test calculator */}
      <div className="hairline p-6 bg-ink-900/50">
        <div className="text-[10px] uppercase tracking-luxury text-gold-soft mb-3">Test the calculator</div>
        <div className="grid sm:grid-cols-4 gap-3">
          <Fld label="Subtotal (₹)"><input type="number" value={testSubtotal} onChange={(e) => setTestSubtotal(e.target.value)} className={inp} /></Fld>
          <Fld label="State">
            <select value={testState} onChange={(e) => setTestState(e.target.value)} className={inp}>
              {INDIAN_STATES.map((s) => <option key={s} value={s} className="bg-ink-900">{s}</option>)}
            </select>
          </Fld>
          <Fld label="Pincode"><input value={testPincode} onChange={(e) => setTestPincode(e.target.value)} maxLength={6} className={inp} /></Fld>
          <div className="flex items-end">
            <button type="button" data-testid="shipping-test" onClick={testCalc} className="w-full bg-gold text-ink-950 py-2.5 text-xs uppercase tracking-luxury hover:bg-cream">Calculate</button>
          </div>
        </div>
        {testResult && (
          <div className="mt-4 text-sm text-cream/80 bg-ink-950 border border-white/10 p-4">
            <div className="flex items-baseline justify-between">
              <span className="text-cream/50 text-xs">Shipping</span>
              <span className="font-serif text-2xl text-gold">₹{Number(testResult.shipping_inr).toLocaleString("en-IN")}</span>
            </div>
            <div className="text-[11px] text-cream/50 mt-1">{testResult.notes} · method: {testResult.method}{testResult.free_shipping_applied ? " · free-shipping applied" : ""}</div>
          </div>
        )}
      </div>

      <div className="flex justify-end">
        <button data-testid="admin-shipping-save-bottom" onClick={save} disabled={saving} className="inline-flex items-center gap-2 bg-gold text-ink-950 px-6 py-3 text-xs uppercase tracking-luxury hover:bg-cream disabled:opacity-60">
          {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
          {saving ? "Saving…" : "Save changes"}
        </button>
      </div>
    </div>
  );
}
