/**
 * Share previews for product pages.
 *
 * The shop is a single-page app, so /product/<slug> served the same HTML shell
 * for every piece and every share (WhatsApp, Instagram, X, Facebook) showed the
 * ArtyFex logo instead of the mirror. Those crawlers do not run JavaScript, so
 * the tags have to be in the HTML they receive.
 *
 * vercel.json rewrites /product/:slug here. We fetch the piece from the API,
 * fetch the built index.html, swap the title/description/OG/Twitter tags for
 * that piece, and return it. React then boots as usual on top of it.
 *
 * If anything fails the untouched shell is returned, so a hiccup here can never
 * take a product page down.
 */
const SITE = "https://www.artyfex.in";
const BACKEND = process.env.REACT_APP_BACKEND_URL || "https://artyfex-backend.onrender.com";
const FALLBACK_IMAGE = SITE + "/brand/icon-512.png";

const esc = (s) =>
  String(s == null ? "" : s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

function absolute(url) {
  if (!url) return "";
  if (/^https?:\/\//i.test(url)) return url;
  return SITE + (url.charAt(0) === "/" ? url : "/" + url);
}

function metaBlock(p, url) {
  const image = absolute(p.hero_image) || FALLBACK_IMAGE;
  const title = p.name + " — Luxury Handmade Resin Mirror | ArtyFex Mumbai";
  const description = (
    ((p.tagline || "") + " " + (p.description || "")).replace(/\s+/g, " ").trim() ||
    p.name + " · handmade luxury mirror by ArtyFex, Mumbai. Insured white-glove delivery."
  ).slice(0, 200);
  return [
    "<title>" + esc(title) + "</title>",
    '<link rel="canonical" href="' + esc(url) + '" />',
    '<meta name="description" content="' + esc(description) + '" />',
    '<meta property="og:type" content="product" />',
    '<meta property="og:site_name" content="ArtyFex" />',
    '<meta property="og:locale" content="en_IN" />',
    '<meta property="og:url" content="' + esc(url) + '" />',
    '<meta property="og:title" content="' + esc(p.name) + '" />',
    '<meta property="og:description" content="' + esc(description) + '" />',
    '<meta property="og:image" content="' + esc(image) + '" />',
    '<meta property="og:image:secure_url" content="' + esc(image) + '" />',
    '<meta property="og:image:alt" content="' + esc(p.name) + '" />',
    '<meta name="twitter:card" content="summary_large_image" />',
    '<meta name="twitter:title" content="' + esc(p.name) + '" />',
    '<meta name="twitter:description" content="' + esc(description) + '" />',
    '<meta name="twitter:image" content="' + esc(image) + '" />',
  ].join("\n        ");
}

module.exports = async function handler(req, res) {
  const origin = "https://" + (req.headers["x-forwarded-host"] || req.headers.host || "www.artyfex.in");
  const slug = (req.query && req.query.slug) || "";

  let shell = "";
  try {
    const shellRes = await fetch(origin + "/index.html?og=1", { headers: { "user-agent": "artyfex-og" } });
    shell = await shellRes.text();
  } catch (e) {
    res.status(302).setHeader("Location", "/index.html");
    res.end();
    return;
  }

  let product = null;
  if (slug) {
    try {
      const r = await fetch(BACKEND + "/api/products/" + encodeURIComponent(slug), {
        headers: { accept: "application/json" },
      });
      if (r.ok) product = await r.json();
    } catch (e) {
      product = null;
    }
  }

  res.setHeader("Content-Type", "text/html; charset=utf-8");

  if (!product || !product.name) {
    res.setHeader("Cache-Control", "public, max-age=0, s-maxage=60");
    res.status(200).send(shell);
    return;
  }

  const url = SITE + "/product/" + slug;
  const cleaned = shell
    .replace(/\s*<meta\s[^>]*?(?:property|name)="(?:og:[^"]+|twitter:[^"]+)"[^>]*>/gi, "")
    .replace(/<title>[\s\S]*?<\/title>/i, "")
    .replace(/<link rel="canonical"[^>]*>/i, "");
  const page = cleaned.replace("</head>", "        " + metaBlock(product, url) + "\n    </head>");

  res.setHeader("Cache-Control", "public, max-age=0, s-maxage=600, stale-while-revalidate=86400");
  res.status(200).send(page);
};
