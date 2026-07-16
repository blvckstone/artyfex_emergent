import React, { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { FileText, Plus, Trash2, ChevronUp, ChevronDown, Eye, EyeOff, Save, X, Type, AlignLeft, Image as ImageIcon, Link2, List as ListIcon, Loader2 } from "lucide-react";
import CloudinaryUpload from "@/components/admin/CloudinaryUpload";

const emptyPage = () => ({
  slug: "",
  title: "",
  meta_title: "",
  meta_description: "",
  blocks: [],
  published: true,
  show_in_header: false,
  show_in_footer: true,
  header_order: 100,
});

/**
 * PagesTab — admin view for the Dynamic-Page CMS (Phase B5).
 * Left column: list of pages with toggles for published / show-in-header.
 * Right column: block-based editor for the currently selected page.
 */
export default function PagesTab({ authed }) {
  const [pages, setPages] = useState([]);
  const [selected, setSelected] = useState(null); // full page object being edited
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await authed.get("/admin/pages");
      setPages(data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not load pages");
    } finally {
      setLoading(false);
    }
  }, [authed]);

  useEffect(() => { reload(); }, [reload]);

  const createNew = () => setSelected({ ...emptyPage(), _isNew: true });

  const savePage = async () => {
    if (!selected) return;
    if (!selected.title.trim()) { toast.error("Title is required"); return; }
    setSaving(true);
    try {
      const payload = {
        slug: selected.slug || selected.title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""),
        title: selected.title,
        meta_title: selected.meta_title || selected.title,
        meta_description: selected.meta_description || "",
        blocks: selected.blocks || [],
        published: !!selected.published,
        show_in_header: !!selected.show_in_header,
        show_in_footer: !!selected.show_in_footer,
        header_order: Number(selected.header_order || 100),
      };
      if (selected._isNew) {
        const { data } = await authed.post("/admin/pages", payload);
        toast.success("Page created");
        setSelected(data);
      } else {
        const { data } = await authed.patch(`/admin/pages/${selected.id}`, payload);
        toast.success("Page saved");
        setSelected(data);
      }
      reload();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const deletePage = async (id) => {
    if (!window.confirm("Delete this page permanently? Any header/footer links will disappear.")) return;
    try {
      await authed.delete(`/admin/pages/${id}`);
      toast.success("Page deleted");
      if (selected?.id === id) setSelected(null);
      reload();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Delete failed");
    }
  };

  const togglePublish = async (page) => {
    try {
      await authed.patch(`/admin/pages/${page.id}`, { ...page, published: !page.published });
      reload();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Toggle failed");
    }
  };

  const toggleHeader = async (page) => {
    try {
      await authed.patch(`/admin/pages/${page.id}`, { ...page, show_in_header: !page.show_in_header });
      reload();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Toggle failed");
    }
  };

  const move = async (idx, dir) => {
    const next = [...pages];
    const target = idx + dir;
    if (target < 0 || target >= next.length) return;
    [next[idx], next[target]] = [next[target], next[idx]];
    setPages(next);
    try {
      await authed.post("/admin/pages/reorder", { ids: next.map((p) => p.id) });
    } catch (err) {
      toast.error("Reorder failed");
      reload();
    }
  };

  return (
    <>
      <div className="flex justify-between items-center mb-6 flex-wrap gap-3">
        <div>
          <h1 className="font-serif text-4xl">Pages</h1>
          <div className="mt-2 text-xs text-cream/50">Manage every static page on your site. Toggle publish, header visibility, drag order, or edit content block-by-block.</div>
        </div>
        <button
          data-testid="pages-new"
          onClick={createNew}
          className="inline-flex items-center gap-2 bg-gold text-ink-950 px-4 py-2.5 text-xs uppercase tracking-luxury hover:bg-cream"
        >
          <Plus className="w-3.5 h-3.5" /> New page
        </button>
      </div>

      <div className="grid lg:grid-cols-[minmax(0,360px)_1fr] gap-6">
        {/* -------- Left: pages list -------- */}
        <div className="hairline bg-ink-900/40 max-h-[80vh] overflow-y-auto">
          {loading ? (
            <div className="p-6 text-cream/40 text-xs"><Loader2 className="w-3.5 h-3.5 animate-spin inline" /> Loading pages…</div>
          ) : pages.length === 0 ? (
            <div className="p-6 text-cream/40 text-sm">No pages yet. Click <em>New page</em> to create one.</div>
          ) : (
            <div className="divide-y divide-white/5">
              {pages.map((p, idx) => (
                <div
                  key={p.id}
                  data-testid={`page-row-${p.slug}`}
                  className={`p-4 cursor-pointer transition-colors ${selected?.id === p.id ? "bg-gold/10" : "hover:bg-white/5"}`}
                  onClick={() => setSelected(p)}
                >
                  <div className="flex items-start gap-2">
                    <FileText className="w-4 h-4 text-gold/60 shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-cream truncate">{p.title}</div>
                      <div className="text-[10px] text-cream/40 mt-0.5 font-mono truncate">/p/{p.slug}</div>
                      <div className="mt-2 flex flex-wrap items-center gap-1.5">
                        {p.published ? (
                          <span className="text-[9px] uppercase tracking-luxury text-emerald-400 border border-emerald-400/40 px-1.5 py-0.5">Live</span>
                        ) : (
                          <span className="text-[9px] uppercase tracking-luxury text-yellow-400 border border-yellow-400/40 px-1.5 py-0.5">Draft</span>
                        )}
                        {p.show_in_header && (
                          <span className="text-[9px] uppercase tracking-luxury text-gold border border-gold/40 px-1.5 py-0.5">Header</span>
                        )}
                        {p.show_in_footer && (
                          <span className="text-[9px] uppercase tracking-luxury text-cream/50 border border-cream/20 px-1.5 py-0.5">Footer</span>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-col gap-1">
                      <button
                        onClick={(e) => { e.stopPropagation(); move(idx, -1); }}
                        disabled={idx === 0}
                        className="p-1 text-cream/40 hover:text-gold disabled:opacity-20"
                        title="Move up"
                      ><ChevronUp className="w-3.5 h-3.5" /></button>
                      <button
                        onClick={(e) => { e.stopPropagation(); move(idx, 1); }}
                        disabled={idx === pages.length - 1}
                        className="p-1 text-cream/40 hover:text-gold disabled:opacity-20"
                        title="Move down"
                      ><ChevronDown className="w-3.5 h-3.5" /></button>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    <button
                      data-testid={`page-toggle-publish-${p.slug}`}
                      onClick={(e) => { e.stopPropagation(); togglePublish(p); }}
                      className={`text-[10px] uppercase tracking-luxury px-2 py-1 border inline-flex items-center gap-1 ${p.published ? "border-emerald-400/40 text-emerald-400" : "border-yellow-400/40 text-yellow-400"}`}
                    >
                      {p.published ? <><Eye className="w-3 h-3" /> Live</> : <><EyeOff className="w-3 h-3" /> Draft</>}
                    </button>
                    <button
                      data-testid={`page-toggle-header-${p.slug}`}
                      onClick={(e) => { e.stopPropagation(); toggleHeader(p); }}
                      className={`text-[10px] uppercase tracking-luxury px-2 py-1 border ${p.show_in_header ? "border-gold text-gold" : "border-white/10 text-cream/60"}`}
                    >{p.show_in_header ? "In header" : "Not in header"}</button>
                    <button
                      onClick={(e) => { e.stopPropagation(); deletePage(p.id); }}
                      className="text-red-400 hover:text-red-300 p-1 border border-red-400/20"
                      title="Delete page"
                    ><Trash2 className="w-3 h-3" /></button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* -------- Right: editor -------- */}
        <div>
          {!selected ? (
            <div className="hairline p-10 text-center text-cream/50 text-sm">
              Select a page from the list to edit it, or click <em>New page</em> to create one.
            </div>
          ) : (
            <PageEditor
              page={selected}
              onChange={setSelected}
              onSave={savePage}
              onCancel={() => setSelected(null)}
              saving={saving}
            />
          )}
        </div>
      </div>
    </>
  );
}

// ================================================================================
// -------- Block-based Page Editor --------
// ================================================================================
function PageEditor({ page, onChange, onSave, onCancel, saving }) {
  const upd = (k, v) => onChange({ ...page, [k]: v });
  const blocks = page.blocks || [];

  const updateBlock = (idx, patch) => {
    const next = [...blocks];
    next[idx] = { ...next[idx], ...patch };
    upd("blocks", next);
  };
  const removeBlock = (idx) => {
    const next = blocks.filter((_, i) => i !== idx);
    upd("blocks", next);
  };
  const moveBlock = (idx, dir) => {
    const target = idx + dir;
    if (target < 0 || target >= blocks.length) return;
    const next = [...blocks];
    [next[idx], next[target]] = [next[target], next[idx]];
    upd("blocks", next);
  };
  const addBlock = (type) => {
    const seed = { type };
    if (type === "heading") { seed.level = 2; seed.text = "Section heading"; }
    if (type === "paragraph") { seed.html = "Write something meaningful here."; }
    if (type === "image") { seed.url = ""; seed.alt = ""; seed.caption = ""; }
    if (type === "cta") { seed.text = "Learn more"; seed.url = "/contact"; }
    if (type === "list") { seed.items = ["First point", "Second point"]; }
    if (type === "quote") { seed.text = "Something quotable."; }
    if (type === "divider") { /* nothing */ }
    upd("blocks", [...blocks, seed]);
  };

  return (
    <div className="hairline bg-ink-900/40 p-6" data-testid="page-editor">
      {/* Meta */}
      <div className="grid sm:grid-cols-2 gap-4">
        <Field label="Title" hint="Shown at the top of the page + in header/footer nav.">
          <input
            data-testid="page-title"
            value={page.title || ""}
            onChange={(e) => upd("title", e.target.value)}
            className={inp}
            placeholder="e.g. Privacy Policy"
          />
        </Field>
        <Field label="URL slug" hint="Lowercase, dashes only. Auto-generated from title if left blank.">
          <input
            data-testid="page-slug"
            value={page.slug || ""}
            onChange={(e) => upd("slug", e.target.value)}
            className={`${inp} font-mono`}
            placeholder="privacy-policy"
          />
        </Field>
        <Field label="SEO title" hint="What appears in the browser tab and Google results.">
          <input
            value={page.meta_title || ""}
            onChange={(e) => upd("meta_title", e.target.value)}
            className={inp}
            placeholder="Privacy Policy · ArtyFex"
          />
        </Field>
        <Field label="SEO description" hint="120–160 chars. What Google shows below the title.">
          <input
            value={page.meta_description || ""}
            onChange={(e) => upd("meta_description", e.target.value)}
            className={inp}
            placeholder="How ArtyFex collects, uses and protects your personal data…"
          />
        </Field>
      </div>

      {/* Visibility toggles */}
      <div className="mt-5 flex flex-wrap gap-4 text-sm">
        <Toggle label="Published (live on site)" testid="page-published" value={!!page.published} onChange={(v) => upd("published", v)} />
        <Toggle label="Show link in header" testid="page-header" value={!!page.show_in_header} onChange={(v) => upd("show_in_header", v)} />
        <Toggle label="Show link in footer" testid="page-footer" value={!!page.show_in_footer} onChange={(v) => upd("show_in_footer", v)} />
      </div>

      {/* Blocks */}
      <div className="mt-8">
        <div className="text-[10px] uppercase tracking-luxury text-gold-soft mb-3">Content blocks · {blocks.length}</div>
        <div className="space-y-3">
          {blocks.length === 0 && (
            <div className="text-xs text-cream/40 italic">No blocks yet. Add your first block below.</div>
          )}
          {blocks.map((b, i) => (
            <BlockRow
              key={i}
              block={b}
              onUpdate={(patch) => updateBlock(i, patch)}
              onRemove={() => removeBlock(i)}
              onMoveUp={() => moveBlock(i, -1)}
              onMoveDown={() => moveBlock(i, 1)}
              isFirst={i === 0}
              isLast={i === blocks.length - 1}
            />
          ))}
        </div>

        {/* Add block toolbar */}
        <div className="mt-6 flex flex-wrap gap-2">
          <AddBtn onClick={() => addBlock("heading")} icon={Type} label="Heading" />
          <AddBtn onClick={() => addBlock("paragraph")} icon={AlignLeft} label="Paragraph" />
          <AddBtn onClick={() => addBlock("image")} icon={ImageIcon} label="Image" />
          <AddBtn onClick={() => addBlock("list")} icon={ListIcon} label="Bullet list" />
          <AddBtn onClick={() => addBlock("cta")} icon={Link2} label="CTA button" />
          <AddBtn onClick={() => addBlock("quote")} icon={Type} label="Pull quote" />
          <AddBtn onClick={() => addBlock("divider")} icon={AlignLeft} label="Divider" />
        </div>
      </div>

      {/* Save row */}
      <div className="mt-8 flex flex-wrap items-center gap-3 border-t border-white/10 pt-6">
        <button
          data-testid="page-save"
          onClick={onSave}
          disabled={saving}
          className="inline-flex items-center gap-2 bg-gold text-ink-950 px-5 py-2.5 text-xs uppercase tracking-luxury hover:bg-cream disabled:opacity-60"
        >
          {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
          {saving ? "Saving…" : "Save page"}
        </button>
        {page.id && (
          <a
            href={`/p/${page.slug}`}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 text-xs uppercase tracking-luxury border border-white/15 text-cream/70 hover:text-gold hover:border-gold/40 px-4 py-2.5"
          ><Eye className="w-3.5 h-3.5" /> View live</a>
        )}
        <button
          onClick={onCancel}
          className="ml-auto text-xs uppercase tracking-luxury text-cream/50 hover:text-cream"
        >Close</button>
      </div>
    </div>
  );
}

function BlockRow({ block, onUpdate, onRemove, onMoveUp, onMoveDown, isFirst, isLast }) {
  const label = ({
    heading: "Heading", paragraph: "Paragraph", image: "Image", list: "Bullet list",
    cta: "Call-to-action", quote: "Pull quote", divider: "Divider",
  })[block.type] || block.type;

  return (
    <div className="border border-white/10 bg-ink-950/50 p-4" data-testid={`block-${block.type}`}>
      <div className="flex items-center gap-2 mb-3">
        <span className="text-[10px] uppercase tracking-luxury text-gold-soft">{label}</span>
        <div className="ml-auto flex items-center gap-1">
          <button onClick={onMoveUp} disabled={isFirst} className="p-1 text-cream/50 hover:text-gold disabled:opacity-20"><ChevronUp className="w-3.5 h-3.5" /></button>
          <button onClick={onMoveDown} disabled={isLast} className="p-1 text-cream/50 hover:text-gold disabled:opacity-20"><ChevronDown className="w-3.5 h-3.5" /></button>
          <button onClick={onRemove} className="p-1 text-red-400/70 hover:text-red-300"><Trash2 className="w-3.5 h-3.5" /></button>
        </div>
      </div>

      {block.type === "heading" && (
        <div className="grid sm:grid-cols-[auto_1fr] gap-3">
          <select value={block.level || 2} onChange={(e) => onUpdate({ level: Number(e.target.value) })} className={inp}>
            <option value={1}>H1</option>
            <option value={2}>H2</option>
            <option value={3}>H3</option>
            <option value={4}>H4</option>
          </select>
          <input value={block.text || ""} onChange={(e) => onUpdate({ text: e.target.value })} className={inp} placeholder="Heading text" />
        </div>
      )}

      {block.type === "paragraph" && (
        <>
          <textarea rows={4} value={block.html || ""} onChange={(e) => onUpdate({ html: e.target.value })} className={inp} placeholder="Write your paragraph. Basic HTML is allowed (e.g. <strong>, <em>, <a>)." />
          <div className="text-[10px] text-cream/40 mt-1">Tip: use <span className="font-mono">&lt;strong&gt;</span>, <span className="font-mono">&lt;em&gt;</span>, and <span className="font-mono">&lt;a href=&quot;…&quot;&gt;</span> for emphasis and links.</div>
        </>
      )}

      {block.type === "image" && (
        <div className="space-y-3">
          <CloudinaryUpload
            value={block.url || ""}
            onChange={(u) => onUpdate({ url: u })}
            folder="artyfex/pages"
            label="Drop image or click to upload"
            testid={`block-img-${block.type}`}
          />
          <input value={block.url || ""} onChange={(e) => onUpdate({ url: e.target.value })} className={`${inp} font-mono text-xs`} placeholder="or paste a URL" />
          <input value={block.alt || ""} onChange={(e) => onUpdate({ alt: e.target.value })} className={inp} placeholder="Alt text (for SEO + screen readers)" />
          <input value={block.caption || ""} onChange={(e) => onUpdate({ caption: e.target.value })} className={inp} placeholder="Caption (optional)" />
        </div>
      )}

      {block.type === "list" && (
        <div className="space-y-2">
          {(block.items || []).map((it, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <input
                value={it}
                onChange={(e) => {
                  const next = [...(block.items || [])];
                  next[idx] = e.target.value;
                  onUpdate({ items: next });
                }}
                className={inp}
                placeholder={`List item #${idx + 1}`}
              />
              <button
                onClick={() => onUpdate({ items: (block.items || []).filter((_, i) => i !== idx) })}
                className="p-2 text-red-400/70 hover:text-red-300"
              ><X className="w-3.5 h-3.5" /></button>
            </div>
          ))}
          <button
            onClick={() => onUpdate({ items: [...(block.items || []), ""] })}
            className="text-[10px] uppercase tracking-luxury text-gold border border-gold/30 px-3 py-1.5 hover:bg-gold/10"
          >+ Add item</button>
        </div>
      )}

      {block.type === "cta" && (
        <div className="grid sm:grid-cols-2 gap-3">
          <input value={block.text || ""} onChange={(e) => onUpdate({ text: e.target.value })} className={inp} placeholder="Button label (e.g. Contact us)" />
          <input value={block.url || ""} onChange={(e) => onUpdate({ url: e.target.value })} className={inp} placeholder="Link URL (e.g. /contact or https://…)" />
        </div>
      )}

      {block.type === "quote" && (
        <textarea rows={2} value={block.text || ""} onChange={(e) => onUpdate({ text: e.target.value })} className={inp} placeholder="Pull-quote text" />
      )}

      {block.type === "divider" && (
        <div className="text-xs text-cream/50 italic">A thin decorative divider will appear here.</div>
      )}
    </div>
  );
}

const inp = "w-full bg-ink-950 border border-white/15 focus:border-gold focus:outline-none px-3 py-2 text-sm text-cream outline-none";
const Field = ({ label, hint, children }) => (
  <label className="block">
    <span className="text-[10px] uppercase tracking-luxury text-cream/50">{label}</span>
    <div className="mt-1.5">{children}</div>
    {hint && <div className="text-[10px] text-cream/40 mt-1">{hint}</div>}
  </label>
);
const AddBtn = ({ onClick, icon: Icon, label }) => (
  <button
    onClick={onClick}
    className="inline-flex items-center gap-1.5 text-[10px] uppercase tracking-luxury border border-white/15 text-cream/70 hover:border-gold hover:text-gold px-3 py-2"
  ><Icon className="w-3 h-3" /> {label}</button>
);
const Toggle = ({ label, value, onChange, testid }) => (
  <label className="inline-flex items-center gap-2 cursor-pointer" data-testid={testid}>
    <input type="checkbox" checked={!!value} onChange={(e) => onChange(e.target.checked)} className="accent-gold w-4 h-4" />
    <span className="text-cream/80 text-sm">{label}</span>
  </label>
);
