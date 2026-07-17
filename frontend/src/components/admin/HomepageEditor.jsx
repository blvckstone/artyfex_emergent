import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2, Save, Image as ImageIcon, Megaphone, Sparkles, Star, Hammer, LayoutGrid, MessageSquareQuote, AlertTriangle, Grid3x3, Trophy, Menu, PlusCircle, Trash2 } from "lucide-react";
import CloudinaryUpload from "@/components/admin/CloudinaryUpload";

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
  const [productList, setProductList] = useState([]);
  const [reviewList, setReviewList] = useState([]);

  useEffect(() => {
    if (!authed) return;
    authed.get("/admin/homepage").then(({ data }) => setData(data)).catch(() => toast.error("Could not load homepage settings"));
    authed.get("/products").then(({ data }) => setProductList(data)).catch(() => {});
    authed.get("/reviews").then(({ data }) => setReviewList(data)).catch(() => {});
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

  const updateCraftStep = (idx, field) => (e) => {
    setData((prev) => {
      const clone = JSON.parse(JSON.stringify(prev));
      if (!clone.craft) clone.craft = { steps: [] };
      if (!Array.isArray(clone.craft.steps)) clone.craft.steps = [];
      clone.craft.steps[idx] = { ...(clone.craft.steps[idx] || {}), [field]: e.target.value };
      return clone;
    });
  };

  const toggleInList = (path, id) => {
    setData((prev) => {
      const clone = JSON.parse(JSON.stringify(prev));
      const keys = path.split(".");
      let node = clone;
      for (let i = 0; i < keys.length - 1; i++) {
        if (node[keys[i]] === undefined || node[keys[i]] === null) node[keys[i]] = {};
        node = node[keys[i]];
      }
      const last = keys[keys.length - 1];
      const arr = Array.isArray(node[last]) ? [...node[last]] : [];
      const idx = arr.indexOf(id);
      if (idx >= 0) arr.splice(idx, 1); else arr.push(id);
      node[last] = arr;
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
          <div className="sm:col-span-2"><Fld label="Background image" hint="High-resolution ambient image. Displayed at ~40% opacity behind copy."><CloudinaryUpload value={data.hero.background_image} onChange={(url) => upd("hero.background_image")(url)} folder="artyfex/homepage" testid="cms-hero-bg" /><input value={data.hero.background_image} onChange={(e) => upd("hero.background_image")(e.target.value)} className={`${inp} mt-2 font-mono text-xs`} placeholder="or paste URL" /></Fld></div>
          <div className="sm:col-span-2"><Fld label="Mirror image" hint="The featured product/mirror shown on the right side."><CloudinaryUpload value={data.hero.mirror_image} onChange={(url) => upd("hero.mirror_image")(url)} folder="artyfex/homepage" testid="cms-hero-mirror" /><input value={data.hero.mirror_image} onChange={(e) => upd("hero.mirror_image")(e.target.value)} className={`${inp} mt-2 font-mono text-xs`} placeholder="or paste URL" /></Fld></div>
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
          <Fld label="Background image (optional)"><CloudinaryUpload value={data.sale_banner.image || ""} onChange={(url) => upd("sale_banner.image")(url)} folder="artyfex/homepage" testid="cms-sale-image" /><input value={data.sale_banner.image || ""} onChange={(e) => upd("sale_banner.image")(e.target.value)} className={`${inp} mt-2 font-mono text-xs`} placeholder="or paste URL" /></Fld>
          <Fld label="Background color"><input value={data.sale_banner.bg_color} onChange={(e) => upd("sale_banner.bg_color")(e.target.value)} className={inp} /></Fld>
          <Fld label="Text color"><input value={data.sale_banner.text_color} onChange={(e) => upd("sale_banner.text_color")(e.target.value)} className={inp} /></Fld>
          <Fld label="Accent color"><input value={data.sale_banner.accent_color} onChange={(e) => upd("sale_banner.accent_color")(e.target.value)} className={inp} /></Fld>
        </div>
      </Section>

      {/* Craft & Materials */}
      <Section icon={Hammer} title="Craft & Materials section" subtitle="The atelier storytelling block below the hero. Controls the left-side image, headline, body, and 4 process steps.">
        <div className="grid sm:grid-cols-2 gap-4">
          <Fld label="Eyebrow (small caps)"><input value={data.craft?.eyebrow || ""} onChange={(e) => upd("craft.eyebrow")(e.target.value)} className={inp} data-testid="cms-craft-eyebrow" /></Fld>
          <Fld label="Headline line 1"><input value={data.craft?.headline_line_1 || ""} onChange={(e) => upd("craft.headline_line_1")(e.target.value)} className={inp} /></Fld>
          <Fld label="Italic word / accent"><input value={data.craft?.headline_italic || ""} onChange={(e) => upd("craft.headline_italic")(e.target.value)} className={inp} /></Fld>
          <div className="sm:col-span-2"><Fld label="Body paragraph"><textarea rows={3} value={data.craft?.body || ""} onChange={(e) => upd("craft.body")(e.target.value)} className={inp} /></Fld></div>
          <div className="sm:col-span-2"><Fld label="Section image" hint="The 4:5 image shown on the left (above 'Craft & Materials')."><CloudinaryUpload value={data.craft?.section_image || ""} onChange={(url) => upd("craft.section_image")(url)} folder="artyfex/homepage" testid="cms-craft-image" /><input value={data.craft?.section_image || ""} onChange={(e) => upd("craft.section_image")(e.target.value)} className={`${inp} mt-2 font-mono text-xs`} placeholder="or paste URL" data-testid="cms-craft-image-url" /></Fld></div>
          <Fld label="Image overlay label (small caps)"><input value={data.craft?.image_overlay_label || ""} onChange={(e) => upd("craft.image_overlay_label")(e.target.value)} className={inp} /></Fld>
          <Fld label="Image overlay title"><input value={data.craft?.image_overlay_title || ""} onChange={(e) => upd("craft.image_overlay_title")(e.target.value)} className={inp} /></Fld>
        </div>
        <div className="mt-6">
          <div className="text-[10px] uppercase tracking-luxury text-cream/50 mb-2">Process steps (4 tiles)</div>
          <div className="grid sm:grid-cols-2 gap-3">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="border border-white/10 p-3 grid gap-2">
                <input placeholder="Title (e.g. 01 · Design)" value={data.craft?.steps?.[i]?.title || ""} onChange={updateCraftStep(i, "title")} className={inp} />
                <textarea rows={2} placeholder="Body" value={data.craft?.steps?.[i]?.body || ""} onChange={updateCraftStep(i, "body")} className={inp} />
              </div>
            ))}
          </div>
        </div>
      </Section>

      {/* Collection section */}
      <Section icon={LayoutGrid} title="Collection section" subtitle="Controls the 'Companion pieces' block. Tick the products you want to feature — leave all unchecked to auto-show every non-hero product.">
        <div className="grid sm:grid-cols-2 gap-4">
          <Fld label="Eyebrow (small caps)"><input value={data.collection_section?.eyebrow || ""} onChange={(e) => upd("collection_section.eyebrow")(e.target.value)} className={inp} /></Fld>
          <Fld label="Headline line 1"><input value={data.collection_section?.headline_line_1 || ""} onChange={(e) => upd("collection_section.headline_line_1")(e.target.value)} className={inp} /></Fld>
          <Fld label="Italic word / accent"><input value={data.collection_section?.headline_italic || ""} onChange={(e) => upd("collection_section.headline_italic")(e.target.value)} className={inp} /></Fld>
          <div className="sm:col-span-2"><Fld label="Subtitle"><textarea rows={2} value={data.collection_section?.subtitle || ""} onChange={(e) => upd("collection_section.subtitle")(e.target.value)} className={inp} /></Fld></div>
        </div>
        <div className="mt-6">
          <div className="text-[10px] uppercase tracking-luxury text-cream/50 mb-2">Featured products on homepage <span className="text-cream/30 normal-case">— {(data.collection_section?.featured_product_ids || []).length} selected. Leave empty to auto-show all non-hero.</span></div>
          {productList.length === 0 ? (
            <div className="text-xs text-cream/40">Loading products…</div>
          ) : (
            <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-3">
              {productList.map((p) => {
                const selected = (data.collection_section?.featured_product_ids || []).includes(p.id);
                return (
                  <button
                    key={p.id}
                    type="button"
                    data-testid={`cms-featured-product-${p.slug}`}
                    onClick={() => toggleInList("collection_section.featured_product_ids", p.id)}
                    className={`flex items-center gap-3 p-3 border text-left transition-all ${selected ? "border-gold bg-gold/10" : "border-white/10 hover:border-white/30"}`}
                  >
                    <img src={p.hero_image} alt="" className="w-12 h-12 object-cover flex-shrink-0" />
                    <div className="min-w-0 flex-1">
                      <div className="text-sm text-cream truncate">{p.name.split(" — ")[0]}</div>
                      <div className="text-[10px] uppercase tracking-luxury text-cream/40 truncate">{p.is_hero ? "Hero" : p.size}</div>
                    </div>
                    <input type="checkbox" checked={selected} readOnly className="accent-gold" />
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </Section>

      {/* Reviews section */}
      <Section icon={MessageSquareQuote} title="Verified Collectors reviews" subtitle="Homepage reviews block. Tick which reviews should appear — leave all unchecked to show every review.">
        <div className="grid sm:grid-cols-2 gap-4">
          <Fld label="Eyebrow (small caps)"><input value={data.reviews_section?.eyebrow || ""} onChange={(e) => upd("reviews_section.eyebrow")(e.target.value)} className={inp} /></Fld>
          <Fld label="Average rating (display only)"><input value={data.reviews_section?.average_rating || ""} onChange={(e) => upd("reviews_section.average_rating")(e.target.value)} className={inp} placeholder="4.98" /></Fld>
          <Fld label="Headline line 1"><input value={data.reviews_section?.headline_line_1 || ""} onChange={(e) => upd("reviews_section.headline_line_1")(e.target.value)} className={inp} /></Fld>
          <Fld label="Italic word / accent"><input value={data.reviews_section?.headline_italic || ""} onChange={(e) => upd("reviews_section.headline_italic")(e.target.value)} className={inp} /></Fld>
        </div>
        <div className="mt-6">
          <div className="text-[10px] uppercase tracking-luxury text-cream/50 mb-2">Featured reviews on homepage <span className="text-cream/30 normal-case">— {(data.reviews_section?.featured_review_ids || []).length} selected.</span></div>
          {reviewList.length === 0 ? (
            <div className="text-xs text-cream/40">No reviews yet.</div>
          ) : (
            <div className="grid sm:grid-cols-2 gap-3 max-h-[420px] overflow-y-auto pr-2">
              {reviewList.map((r) => {
                const selected = (data.reviews_section?.featured_review_ids || []).includes(r.id);
                return (
                  <button
                    key={r.id}
                    type="button"
                    data-testid={`cms-featured-review-${r.id}`}
                    onClick={() => toggleInList("reviews_section.featured_review_ids", r.id)}
                    className={`p-3 border text-left transition-all ${selected ? "border-gold bg-gold/10" : "border-white/10 hover:border-white/30"}`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-gold text-xs">{r.rating}★</span>
                      <input type="checkbox" checked={selected} readOnly className="accent-gold" />
                    </div>
                    <div className="text-sm text-cream mt-1 truncate">{r.title}</div>
                    <div className="text-xs text-cream/50 line-clamp-2 mt-1">{r.body}</div>
                    <div className="text-[10px] uppercase tracking-luxury text-cream/40 mt-2">{r.author} · {r.location}</div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </Section>

      {/* Category Mosaic (Curated worlds) */}
      <Section icon={Grid3x3} title="Category mosaic — 'Curated worlds'" subtitle="The bento-grid of category tiles on the homepage. Add/remove tiles, edit label + image (Cloudinary uploader). Toggle the whole section off if you don't need it.">
        <label className="flex items-center gap-2 text-sm text-cream/70 mb-4">
          <input type="checkbox" data-testid="cms-cat-enabled" checked={data.category_section?.enabled !== false} onChange={(e) => upd("category_section.enabled")(e.target.checked)} className="accent-gold" /> Show this section on homepage
        </label>
        <div className="grid sm:grid-cols-2 gap-4">
          <Fld label="Eyebrow (small caps)"><input value={data.category_section?.eyebrow || ""} onChange={(e) => upd("category_section.eyebrow")(e.target.value)} className={inp} /></Fld>
          <div />
          <Fld label="Headline line 1"><input value={data.category_section?.headline_line_1 || ""} onChange={(e) => upd("category_section.headline_line_1")(e.target.value)} className={inp} placeholder="Curated" /></Fld>
          <Fld label="Italic word / accent"><input value={data.category_section?.headline_italic || ""} onChange={(e) => upd("category_section.headline_italic")(e.target.value)} className={inp} placeholder="worlds" /></Fld>
          <Fld label="Headline line 2 (after italic)"><input value={data.category_section?.headline_line_2 || ""} onChange={(e) => upd("category_section.headline_line_2")(e.target.value)} className={inp} placeholder=" of luxury." /></Fld>
          <div className="sm:col-span-2"><Fld label="Subtitle"><textarea rows={2} value={data.category_section?.subtitle || ""} onChange={(e) => upd("category_section.subtitle")(e.target.value)} className={inp} /></Fld></div>
        </div>
        <div className="mt-6">
          <div className="flex items-center justify-between mb-3">
            <div className="text-[10px] uppercase tracking-luxury text-cream/50">Tiles ({(data.category_section?.tiles || []).length}) — leave empty to use luxury defaults</div>
            <button
              type="button"
              data-testid="cms-cat-add"
              onClick={() => {
                setData((prev) => {
                  const clone = JSON.parse(JSON.stringify(prev));
                  if (!clone.category_section) clone.category_section = { tiles: [] };
                  if (!Array.isArray(clone.category_section.tiles)) clone.category_section.tiles = [];
                  clone.category_section.tiles.push({ slug: "", label: "New tile", keyword: "", image: "" });
                  return clone;
                });
              }}
              className="inline-flex items-center gap-2 text-[10px] uppercase tracking-luxury text-gold hover:text-cream"
            ><PlusCircle className="w-3.5 h-3.5" /> Add tile</button>
          </div>
          <div className="grid gap-3">
            {(data.category_section?.tiles || []).map((t, i) => (
              <div key={i} className="grid sm:grid-cols-[80px_1fr_1fr_1fr_auto] gap-3 items-center border border-white/10 p-3">
                <div className="w-[80px] h-[80px] bg-ink-950 border border-white/10 overflow-hidden">
                  <CloudinaryUpload
                    value={t.image}
                    onChange={(url) => {
                      setData((prev) => {
                        const c = JSON.parse(JSON.stringify(prev));
                        c.category_section.tiles[i].image = url;
                        return c;
                      });
                    }}
                    folder="artyfex/homepage"
                    testid={`cms-cat-tile-${i}-img`}
                    label=""
                  />
                </div>
                <input placeholder="Slug (e.g. mirrors)" value={t.slug || ""} onChange={(e) => { setData((prev) => { const c = JSON.parse(JSON.stringify(prev)); c.category_section.tiles[i].slug = e.target.value; return c; }); }} className={inp} data-testid={`cms-cat-tile-${i}-slug`} />
                <input placeholder="Label (e.g. Luxury Mirrors)" value={t.label || ""} onChange={(e) => { setData((prev) => { const c = JSON.parse(JSON.stringify(prev)); c.category_section.tiles[i].label = e.target.value; return c; }); }} className={inp} data-testid={`cms-cat-tile-${i}-label`} />
                <input placeholder="Sub-keyword" value={t.keyword || ""} onChange={(e) => { setData((prev) => { const c = JSON.parse(JSON.stringify(prev)); c.category_section.tiles[i].keyword = e.target.value; return c; }); }} className={inp} />
                <button
                  type="button"
                  onClick={() => { setData((prev) => { const c = JSON.parse(JSON.stringify(prev)); c.category_section.tiles.splice(i, 1); return c; }); }}
                  data-testid={`cms-cat-tile-${i}-remove`}
                  className="text-red-400 hover:text-red-300 p-2"
                  title="Remove tile"
                ><Trash2 className="w-4 h-4" /></button>
              </div>
            ))}
          </div>
        </div>
      </Section>

      {/* Featured Carousel toggle */}
      <Section icon={LayoutGrid} title="Featured carousel — 'Editor's pick'" subtitle="Horizontal auto-scroll product carousel. Uses your live products list. Toggle to hide on homepage.">
        <label className="flex items-center gap-2 text-sm text-cream/70 mb-4">
          <input type="checkbox" data-testid="cms-featured-enabled" checked={data.featured_section?.enabled !== false} onChange={(e) => upd("featured_section.enabled")(e.target.checked)} className="accent-gold" /> Show this section on homepage
        </label>
        <div className="grid sm:grid-cols-3 gap-4">
          <Fld label="Eyebrow (small caps)"><input value={data.featured_section?.eyebrow || ""} onChange={(e) => upd("featured_section.eyebrow")(e.target.value)} className={inp} placeholder="Featured" /></Fld>
          <Fld label="Headline line 1"><input value={data.featured_section?.headline_line_1 || ""} onChange={(e) => upd("featured_section.headline_line_1")(e.target.value)} className={inp} placeholder="Editor's" /></Fld>
          <Fld label="Italic word / accent"><input value={data.featured_section?.headline_italic || ""} onChange={(e) => upd("featured_section.headline_italic")(e.target.value)} className={inp} placeholder="pick" /></Fld>
        </div>
      </Section>

      {/* Why ArtyFex — animated stats */}
      <Section icon={Trophy} title="'Why ArtyFex' — animated stat cards" subtitle="Row of animated counter cards. Edit each stat's icon, value, suffix, label and note. Toggle to hide.">
        <label className="flex items-center gap-2 text-sm text-cream/70 mb-4">
          <input type="checkbox" data-testid="cms-why-enabled" checked={data.why_section?.enabled !== false} onChange={(e) => upd("why_section.enabled")(e.target.checked)} className="accent-gold" /> Show this section on homepage
        </label>
        <div className="grid sm:grid-cols-2 gap-4">
          <Fld label="Eyebrow (small caps)"><input value={data.why_section?.eyebrow || ""} onChange={(e) => upd("why_section.eyebrow")(e.target.value)} className={inp} /></Fld>
          <div />
          <Fld label="Headline line 1"><input value={data.why_section?.headline_line_1 || ""} onChange={(e) => upd("why_section.headline_line_1")(e.target.value)} className={inp} /></Fld>
          <Fld label="Italic word / accent"><input value={data.why_section?.headline_italic || ""} onChange={(e) => upd("why_section.headline_italic")(e.target.value)} className={inp} /></Fld>
          <Fld label="Headline line 2 (after italic)"><input value={data.why_section?.headline_line_2 || ""} onChange={(e) => upd("why_section.headline_line_2")(e.target.value)} className={inp} /></Fld>
          <div />
          <div className="sm:col-span-2"><Fld label="Subtitle"><textarea rows={2} value={data.why_section?.subtitle || ""} onChange={(e) => upd("why_section.subtitle")(e.target.value)} className={inp} /></Fld></div>
        </div>
        <div className="mt-6">
          <div className="text-[10px] uppercase tracking-luxury text-cream/50 mb-2">4 stat cards</div>
          <div className="grid sm:grid-cols-2 gap-3">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="border border-white/10 p-3 grid gap-2">
                <div className="grid grid-cols-2 gap-2">
                  <select
                    className={inp}
                    value={data.why_section?.stats?.[i]?.icon || "sparkles"}
                    onChange={(e) => { setData((prev) => { const c = JSON.parse(JSON.stringify(prev)); if (!c.why_section.stats) c.why_section.stats = []; c.why_section.stats[i] = { ...(c.why_section.stats[i] || {}), icon: e.target.value }; return c; }); }}
                    data-testid={`cms-why-stat-${i}-icon`}
                  >
                    <option value="sparkles">Sparkles</option>
                    <option value="award">Award</option>
                    <option value="shield">Shield</option>
                    <option value="truck">Truck</option>
                  </select>
                  <input placeholder="Suffix (e.g. +, /1, mo)" value={data.why_section?.stats?.[i]?.suffix || ""} onChange={(e) => { setData((prev) => { const c = JSON.parse(JSON.stringify(prev)); c.why_section.stats[i] = { ...(c.why_section.stats[i] || {}), suffix: e.target.value }; return c; }); }} className={inp} />
                </div>
                <input type="number" placeholder="Value (integer)" value={data.why_section?.stats?.[i]?.value ?? ""} onChange={(e) => { setData((prev) => { const c = JSON.parse(JSON.stringify(prev)); c.why_section.stats[i] = { ...(c.why_section.stats[i] || {}), value: Number(e.target.value) || 0 }; return c; }); }} className={inp} data-testid={`cms-why-stat-${i}-value`} />
                <input placeholder="Label (e.g. Artisan hours per piece)" value={data.why_section?.stats?.[i]?.label || ""} onChange={(e) => { setData((prev) => { const c = JSON.parse(JSON.stringify(prev)); c.why_section.stats[i] = { ...(c.why_section.stats[i] || {}), label: e.target.value }; return c; }); }} className={inp} />
                <input placeholder="Sub-note (small text)" value={data.why_section?.stats?.[i]?.note || ""} onChange={(e) => { setData((prev) => { const c = JSON.parse(JSON.stringify(prev)); c.why_section.stats[i] = { ...(c.why_section.stats[i] || {}), note: e.target.value }; return c; }); }} className={inp} />
              </div>
            ))}
          </div>
        </div>
      </Section>

      {/* Header nav toggles */}
      <Section icon={Menu} title="Header navigation — show/hide default tabs" subtitle="Toggle which built-in tabs appear in the desktop + mobile header. (CMS pages have their own show-in-header toggle in the Pages tab.)">
        <div className="grid sm:grid-cols-2 gap-3">
          {[
            { key: "show_shop", label: "Shop" },
            { key: "show_craft", label: "The Craft" },
            { key: "show_reviews", label: "Reviews" },
            { key: "show_b2b", label: "Trade / B2B" },
          ].map((l) => (
            <label key={l.key} className="flex items-center gap-3 border border-white/10 p-3 text-sm text-cream/70">
              <input
                type="checkbox"
                data-testid={`cms-nav-${l.key}`}
                checked={data.nav_default_links?.[l.key] !== false}
                onChange={(e) => upd(`nav_default_links.${l.key}`)(e.target.checked)}
                className="accent-gold"
              />
              <span>{l.label}</span>
            </label>
          ))}
        </div>
        <p className="mt-4 text-xs text-cream/40">Tip: to add or reorder <em>custom</em> pages in the header, use the <strong>Pages</strong> tab.</p>
      </Section>

      {/* Important note */}
      <Section icon={AlertTriangle} title="Footer — Important note" subtitle="The disclaimer paragraph shown just above the giant ArtyFex watermark in the footer.">
        <div className="grid sm:grid-cols-2 gap-4">
          <label className="flex items-center gap-2 text-sm text-cream/70">
            <input type="checkbox" data-testid="cms-note-enabled" checked={data.important_note?.enabled !== false} onChange={(e) => upd("important_note.enabled")(e.target.checked)} className="accent-gold" /> Show important note in footer
          </label>
          <div />
          <Fld label="Small caps label"><input value={data.important_note?.label || ""} onChange={(e) => upd("important_note.label")(e.target.value)} className={inp} placeholder="Important note" /></Fld>
          <div />
          <div className="sm:col-span-2"><Fld label="Body text"><textarea rows={4} value={data.important_note?.body || ""} onChange={(e) => upd("important_note.body")(e.target.value)} className={inp} data-testid="cms-note-body" /></Fld></div>
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
