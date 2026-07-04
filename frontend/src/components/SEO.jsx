import { useEffect } from "react";

/**
 * SEO
 * A lightweight, zero-dependency head manager.
 * Sets document.title, description, canonical, robots and OG/Twitter tags for the
 * current page. Adds/updates JSON-LD structured data via a script tag with a
 * stable id so it's cleanly replaced on route change.
 *
 * Usage:
 *   <SEO
 *     title="About | ArtyFex"
 *     description="A Mumbai atelier of 100% handmade resin & crystal mirrors."
 *     path="/about"
 *     jsonLd={{ '@context': 'https://schema.org', '@type': 'Organization', ... }}
 *   />
 */
export default function SEO({
  title,
  description,
  path,
  image,
  jsonLd,
  robots = "index,follow",
  type = "website",
}) {
  useEffect(() => {
    const baseUrl = "https://www.artyfex.in";
    const url = baseUrl + (path || (typeof window !== "undefined" ? window.location.pathname : ""));
    const img = image || `${baseUrl}/brand/og-cover.jpg`;

    if (title) document.title = title;

    const upsertMeta = (attr, key, content) => {
      if (content == null) return;
      let el = document.head.querySelector(`meta[${attr}="${key}"]`);
      if (!el) {
        el = document.createElement("meta");
        el.setAttribute(attr, key);
        document.head.appendChild(el);
      }
      el.setAttribute("content", content);
    };

    const upsertLink = (rel, href) => {
      let el = document.head.querySelector(`link[rel="${rel}"]`);
      if (!el) {
        el = document.createElement("link");
        el.setAttribute("rel", rel);
        document.head.appendChild(el);
      }
      el.setAttribute("href", href);
    };

    upsertMeta("name", "description", description);
    upsertMeta("name", "robots", robots);
    upsertLink("canonical", url);

    // Open Graph
    upsertMeta("property", "og:title", title);
    upsertMeta("property", "og:description", description);
    upsertMeta("property", "og:url", url);
    upsertMeta("property", "og:type", type);
    upsertMeta("property", "og:image", img);
    upsertMeta("property", "og:site_name", "ArtyFex");

    // Twitter
    upsertMeta("name", "twitter:card", "summary_large_image");
    upsertMeta("name", "twitter:title", title);
    upsertMeta("name", "twitter:description", description);
    upsertMeta("name", "twitter:image", img);

    // JSON-LD structured data
    const scriptId = "seo-jsonld";
    let script = document.getElementById(scriptId);
    if (jsonLd) {
      if (!script) {
        script = document.createElement("script");
        script.id = scriptId;
        script.type = "application/ld+json";
        document.head.appendChild(script);
      }
      script.textContent = JSON.stringify(jsonLd);
    } else if (script) {
      script.remove();
    }
    // No cleanup — next page's <SEO> will overwrite these values, keeping crawler-friendly
  }, [title, description, path, image, robots, type, JSON.stringify(jsonLd || null)]);

  return null;
}
