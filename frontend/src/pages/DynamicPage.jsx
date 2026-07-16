import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import SEO from "@/components/SEO";
import { Loader2 } from "lucide-react";

/**
 * DynamicPage — public renderer for admin-managed CMS pages (Phase B5).
 * URL pattern: /p/:slug  (e.g. /p/privacy-policy).
 * Renders blocks in order. Fully SEO'd via <SEO />.
 */
export default function DynamicPage() {
  const { slug } = useParams();
  const [page, setPage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setNotFound(false);
    api.get(`/pages/${slug}`)
      .then(({ data }) => { if (!cancelled) setPage(data); })
      .catch(() => { if (!cancelled) setNotFound(true); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [slug]);

  return (
    <div className="min-h-screen bg-ink-950 text-cream">
      <SEO
        title={page?.meta_title || page?.title || "ArtyFex"}
        description={page?.meta_description || `Read ${page?.title || "our policy"} on ArtyFex.`}
        path={`/p/${slug}`}
      />
      <Navbar />
      <main className="pt-28 md:pt-32 pb-24 max-w-3xl mx-auto px-6 md:px-10">
        {loading ? (
          <div className="text-cream/40 text-sm py-16 text-center">
            <Loader2 className="w-4 h-4 animate-spin inline mr-2" /> Loading…
          </div>
        ) : notFound || !page ? (
          <div className="py-24 text-center">
            <div className="text-[10px] uppercase tracking-luxury text-gold-soft">404</div>
            <h1 className="mt-3 font-serif text-4xl">Page not found</h1>
            <p className="mt-3 text-cream/60 text-sm">The page you&apos;re looking for either doesn&apos;t exist or has been unpublished.</p>
            <Link to="/" className="mt-8 inline-block text-xs uppercase tracking-luxury text-gold border border-gold/40 px-6 py-3 hover:bg-gold/10">Back to home</Link>
          </div>
        ) : (
          <>
            <div className="text-[10px] uppercase tracking-luxury text-gold-soft">ArtyFex</div>
            <h1 className="mt-2 font-serif text-5xl leading-tight">{page.title}</h1>
            <div className="mt-3 text-xs text-cream/40">Last updated · {new Date(page.updated_at || Date.now()).toLocaleDateString("en-GB", { year: "numeric", month: "long", day: "numeric" })}</div>
            <div className="mt-12 space-y-6">
              {(page.blocks || []).map((b, i) => <Block key={i} block={b} />)}
            </div>
          </>
        )}
      </main>
      <Footer />
    </div>
  );
}

function Block({ block }) {
  switch (block.type) {
    case "heading": {
      const level = Math.min(4, Math.max(1, Number(block.level) || 2));
      const cls = {
        1: "font-serif text-4xl mt-10 mb-4",
        2: "font-serif text-2xl mt-10 mb-3 text-gold",
        3: "font-serif text-xl mt-8 mb-2",
        4: "text-lg mt-6 mb-2 uppercase tracking-luxury text-gold-soft text-sm",
      }[level];
      const Tag = `h${level}`;
      return <Tag className={cls}>{block.text}</Tag>;
    }
    case "paragraph":
      return (
        <p
          className="text-cream/80 leading-relaxed text-base"
          dangerouslySetInnerHTML={{ __html: block.html || "" }}
        />
      );
    case "image":
      return (
        <figure className="my-6">
          {block.url && (
            <img src={block.url} alt={block.alt || ""} className="w-full h-auto border border-white/10" loading="lazy" />
          )}
          {block.caption && <figcaption className="mt-2 text-xs text-cream/50 italic text-center">{block.caption}</figcaption>}
        </figure>
      );
    case "list":
      return (
        <ul className="list-disc list-outside pl-6 space-y-2 text-cream/80 marker:text-gold">
          {(block.items || []).map((it, i) => <li key={i}>{it}</li>)}
        </ul>
      );
    case "cta":
      return (
        <div className="my-6">
          <a
            href={block.url || "#"}
            className="inline-flex items-center gap-2 bg-gold text-ink-950 px-6 py-3 text-xs uppercase tracking-luxury hover:bg-cream"
          >{block.text || "Learn more"}</a>
        </div>
      );
    case "quote":
      return (
        <blockquote className="border-l-2 border-gold pl-6 py-2 text-lg italic text-cream/80">
          {block.text}
        </blockquote>
      );
    case "divider":
      return <hr className="my-8 border-white/10" />;
    default:
      return null;
  }
}
