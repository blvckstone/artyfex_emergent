import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2, Save, Image as ImageIcon, Megaphone, Sparkles, Star } from "lucide-react";

const inp = "w-full bg-ink-950 border border-white/15 focus:border-gold focus:outline-none px-3 py-2.5 text-sm text-cream outline-none";
const Fld = ({ label, children, hint }) => (
  <label className="block">
    <span className="text-[10px] uppercase tracking-luxury text-cream/50">{label}</span>
    <div className="mt-1.5">{children}</div>
    {hint && <div className="mt-1 text-[10px] text-cream/40">{hint}</div>}
  </label>
);

function Section({ icon: Icon, title, subtitle, children }) {
  return (
    <div className="hairline p-6 md:p-8 bg-ink-900/50">
      <div className="flex items-center gap-3 mb-2">
        <Icon className="w-4 h-4 text-gold" />
        <div className="text-[10px] uppercase tracking-luxury text-gold-soft">{title}</div>
      </div>
      {subtitle && <p className="text-xs text-cream/50 mb-6">{subtitle}</p>}
      {children}
    </div>
  );
}

export default function HomepageEditor({ authed }) {
  const [data, setData] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!authed) return;
    authed.get("/admin/homepage").then(({ data }) => setData(data)).catch(() => toast.error("Could not load homepage settings"));
  }, [authed]);

  if (!data) return <div className="text-cream/40 text-sm"><Loader2 className="w-4 h-4 animate-spin inline" /> Loading homepage settings…</div>;

  const upd = (path) => (value) => {
    setData((prev) => {
      const clone = JSON.parse(JSON.stringify(prev));
      const keys = path.split(".");
      let node = clone;
      for (let i = 0; i < keys.length - 1; i++) node = node[keys[i]];
      node[keys[keys.length - 1]] = value;
      return clone;
    });
  };

  const updateStat = (idx, field) => (e) => {
    setData((prev) => {
      const clone = JSON.parse(JSON.stringify(prev));
      if (!clone.hero.stats) clone.hero.stats = [];
      clone.hero.stats[idx] = { ...clone.hero.stats[idx], [field]: e.target.value };
      return clone;
    });
  };

  const save = async () => {
    setSaving(true);
    try {
      const { data: saved } = await authed.patch("/admin/homepage", data);
      setData(saved);
      toast.success("Homepage updated — refresh the storefront to see changes");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Save failed");
    } finally { setSaving(false); }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-serif text-4xl">Homepage CMS</h1>
          <p className="mt-2 text-sm text-cream/50">Control the announcement bar, hero, and sale banner. Colours accept any CSS value (hex, rgb, named).</p>
        </div>
        <button data-testid="admin-homepage-save" onClick={save} disabled={saving} className="inline-flex items-center gap-2 bg-gold text-ink-950 px-6 py-3 text-xs uppercase tracking-luxury hover:bg-cream disabled:opacity-60">
          {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
          {saving ? "Saving…" : "Save changes"}
        </button>
      </div>

      {/* Announcement */}
      <Section icon={Megaphone} title="Announcement bar" subtitle="Slim strip above the navbar. Use it for shipping perks, flash sales, or store notices.">
        <div className="grid sm:grid-cols-2 gap-4">
          <label className="flex items-center gap-2 text-sm text-cream/70">
            <input type="checkbox" data-testid="cms-announce-enabled" checked={!!data.announcement.enabled} onChange={(e) => upd("announcement.enabled")(e.target.checked)} className="accent-gold" /> Enabled
          </label>
          <div />
          <div className="sm:col-span-2"><Fld label="Message"><input data-testid="cms-announce-text" value={data.announcement.text} onChange={(e) => upd("announcement.text")(e.target.value)} className={inp} /></Fld></div>
          <Fld label="Background color"><input value={data.announcement.bg_color} onChange={(e) => upd("announcement.bg_color")(e.target.value)} className={inp} placeholder="#0a0a0a" /></Fld>
          <Fld label="Text color"><input value={data.announcement.text_color} onChange={(e) => upd("announcement.text_color")(e.target.value)} className={inp} placeholder="#D4AF37" /></Fld>
          <Fld label="Link URL (optional)"><input value={data.announcement.link_url || ""} onChange={(e) => upd("announcement.link_url")(e.target.value)} className={inp} placeholder="/shop" /></Fld>
          <Fld label="Link label (optional)"><input value={data.announcement.link_label || ""} onChange={(e) => upd("announcement.link_label")(e.target.value)} className={inp} placeholder="Shop now" /></Fld>
        </div>
      </Section>

      {/* Hero */}
      <Section icon={Sparkles} title="Hero section" subtitle="Text, colours and imagery of the cinematic hero. The italic word is highlighted in your accent color.">
        <div className="grid sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2"><Fld label="Eyebrow line"><input data-testid="cms-hero-eyebrow" value={data.hero.eyebrow} onChange={(e) => upd("hero.eyebrow")(e.target.value)} className={inp} /></Fld></div>
          <Fld label="Headline line 1"><input value={data.hero.headline_line_1} onChange={(e) => upd("hero.headline_line_1")(e.target.value)} className={inp} /></Fld>
          <Fld label="Italic word (accent)" hint="Rendered in the accent color as italic emphasis."><input value={data.hero.headline_italic} onChange={(e) => upd("hero.headline_italic")(e.target.value)} className={inp} /></Fld>
          <Fld label="Headline line 2"><input value={data.hero.headline_line_2} onChange={(e) => upd("hero.headline_line_2")(e.target.value)} className={inp} /></Fld>
          <Fld label="Headline line 3"><input value={data.hero.headline_line_3} onChange={(e) => upd("hero.headline_line_3")(e.target.value)} className={inp} /></Fld>
          <div className="sm:col-span-2"><Fld label="Sub-headline"><textarea rows={3} value={data.hero.subheadline} onChange={(e) => upd("hero.subheadline")(e.target.value)} className={inp} /></Fld></div>
          <Fld label="Primary CTA text"><input value={data.hero.primary_cta_text} onChange={(e) => upd("hero.primary_cta_text")(e.target.value)} className={inp} /></Fld>
          <Fld label="Primary CTA link"><input value={data.hero.primary_cta_link} onChange={(e) => upd("hero.primary_cta_link")(e.target.value)} className={inp} placeholder="#product or /shop" /></Fld>
          <Fld label="Secondary CTA text"><input value={data.hero.secondary_cta_text} onChange={(e) => upd("hero.secondary_cta_text")(e.target.value)} className={inp} /></Fld>
          <Fld label="Secondary CTA link"><input value={data.hero.secondary_cta_link} onChange={(e) => upd("hero.secondary_cta_link")(e.target.value)} className={inp} /></Fld>
          <div className="sm:col-span-2"><Fld label="Background image URL" hint="High-resolution ambient image. Displayed at ~40% opacity behind copy."><input value={data.hero.background_image} onChange={(e) => upd("hero.background_image")(e.target.value)} className={inp} /></Fld></div>
          <div className="sm:col-span-2"><Fld label="Mirror image URL" hint="The featured product/mirror shown on the right side."><input value={data.hero.mirror_image} onChange={(e) => upd("hero.mirror_image")(e.target.value)} className={inp} /></Fld></div>
          <Fld label="Edition label"><input value={data.hero.edition_label} onChange={(e) => upd("hero.edition_label")(e.target.value)} className={inp} /></Fld>
          <Fld label="Edition text"><input value={data.hero.edition_text} onChange={(e) => upd("hero.edition_text")(e.target.value)} className={inp} /></Fld>
          <Fld label="Text color"><input value={data.hero.text_color} onChange={(e) => upd("hero.text_color")(e.target.value)} className={inp} /></Fld>
          <Fld label="Accent color"><input value={data.hero.accent_color} onChange={(e) => upd("hero.accent_color")(e.target.value)} className={inp} /></Fld>
        </div>
        <div className="mt-6">
          <div className="text-[10px] uppercase tracking-luxury text-cream/50 mb-2">Stats (3 tiles)</div>
          <div className="grid sm:grid-cols-3 gap-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="border border-white/10 p-3 grid gap-2">
                <input placeholder="Value (e.g. 120)" value={data.hero.stats?.[i]?.k || ""} onChange={updateStat(i, "k")} className={inp} />
                <input placeholder="Label (e.g. artisan hours)" value={data.hero.stats?.[i]?.v || ""} onChange={updateStat(i, "v")} className={inp} />
              </div>
            ))}
          </div>
        </div>
      </Section>

      {/* Sale banner */}
      <Section icon={Star} title="Sale / feature banner" subtitle="Rendered between the collection grid and reviews. Perfect for seasonal edits.">
        <div className="grid sm:grid-cols-2 gap-4">
          <label className="flex items-center gap-2 text-sm text-cream/70">
            <input type="checkbox" data-testid="cms-sale-enabled" checked={!!data.sale_banner.enabled} onChange={(e) => upd("sale_banner.enabled")(e.target.checked)} className="accent-gold" /> Enabled
          </label>
          <div />
          <Fld label="Title"><input value={data.sale_banner.title} onChange={(e) => upd("sale_banner.title")(e.target.value)} className={inp} /></Fld>
          <Fld label="CTA text"><input value={data.sale_banner.cta_text} onChange={(e) => upd("sale_banner.cta_text")(e.target.value)} className={inp} /></Fld>
          <div className="sm:col-span-2"><Fld label="Subtitle"><textarea rows={2} value={data.sale_banner.subtitle} onChange={(e) => upd("sale_banner.subtitle")(e.target.value)} className={inp} /></Fld></div>
          <Fld label="CTA link"><input value={data.sale_banner.cta_link} onChange={(e) => upd("sale_banner.cta_link")(e.target.value)} className={inp} placeholder="/shop" /></Fld>
          <Fld label="Background image (optional)"><input value={data.sale_banner.image || ""} onChange={(e) => upd("sale_banner.image")(e.target.value)} className={inp} /></Fld>
          <Fld label="Background color"><input value={data.sale_banner.bg_color} onChange={(e) => upd("sale_banner.bg_color")(e.target.value)} className={inp} /></Fld>
          <Fld label="Text color"><input value={data.sale_banner.text_color} onChange={(e) => upd("sale_banner.text_color")(e.target.value)} className={inp} /></Fld>
          <Fld label="Accent color"><input value={data.sale_banner.accent_color} onChange={(e) => upd("sale_banner.accent_color")(e.target.value)} className={inp} /></Fld>
        </div>
      </Section>

      {/* Custom CSS */}
      <Section icon={ImageIcon} title="Developer overrides" subtitle="Optional raw CSS injected on the homepage. Use for one-off polish; leave empty otherwise.">
        <textarea data-testid="cms-custom-css" rows={5} value={data.custom_css || ""} onChange={(e) => upd("custom_css")(e.target.value)} placeholder="/* .my-class { color: gold; } */" className={`${inp} font-mono text-xs`} />
      </Section>

      <div className="flex justify-end">
        <button data-testid="admin-homepage-save-bottom" onClick={save} disabled={saving} className="inline-flex items-center gap-2 bg-gold text-ink-950 px-6 py-3 text-xs uppercase tracking-luxury hover:bg-cream disabled:opacity-60">
          {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
          {saving ? "Saving…" : "Save changes"}
        </button>
      </div>
    </div>
  );
}
