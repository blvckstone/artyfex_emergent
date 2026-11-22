/**
 * Amazon listings for pieces that are sold both here and on Amazon.
 *
 * Keyed by product slug. `product.amazon_url` (set in Admin → Products) always
 * wins, so new uploads never need this file — it only backfills pieces that
 * were listed on Amazon before the field existed.
 *
 * Match method: the ArtyFex seller's own Amazon catalogue was read
 * (https://www.amazon.in/s?k=ArtyFex&rh=p_6%3AANQAW6V3OL50U — 25 live listings)
 * and each listing was matched to the website piece by product wording, colour,
 * shape and price. Pieces that are not on Amazon are absent on purpose rather
 * than guessed — a wrong link sends a buyer to a different mirror.
 *
 * Some slugs are used by two different products (a known catalogue bug), so the
 * name rules below take priority over the slug table for those.
 */
export const AMAZON_LISTING_LINKS = {
  // Gold & Teal 2x3 ft
  "gold-teal-mirror": "https://www.amazon.in/dp/B0H2HZ6XFV",
  // Golden Geode 2x2 ft
  "golden-geode-mirror": "https://www.amazon.in/dp/B0FZL52TJZ",
  // Gold, White & Aqua geode 2x2 ft
  "geode-gold-white-aqua-mirror": "https://www.amazon.in/dp/B0FPCLVFP6",
  // Pink & Gold round epoxy 2x2 ft
  "round-pink-golden-epoxy-mirror": "https://www.amazon.in/dp/B0G5ZCQDMQ",
  // Black & gold geode, round
  "black-gold-geode-resin-round-wall-mirror": "https://www.amazon.in/dp/B0HK4N3BCS",
  // Black & gold geode, decorative round
  "black-gold-geode-resin-decorative-round-wall-mirror": "https://www.amazon.in/dp/B0HLWCXP26",
  // Emerald green geode, round
  "emerald-green-geode-handmade-resin-wall-mirror": "https://www.amazon.in/dp/B0HM3SSH3Y",
  // Pink & gold geode wall mirror
  "vibrant-pink-gold-resin-geode-wall-mirror": "https://www.amazon.in/dp/B0HKJZT6M6",
  // Golden drip round wall mirror
  "handmade-golden-drip-resin-round-wall-mirror": "https://www.amazon.in/dp/B0HL4RL1D2",
  // Turquoise & gold geode, round
  "turquoise-geode-luxe-handmade-resin-wall-mirr": "https://www.amazon.in/dp/B0HLXRN8T6",
  // Blue geode evil-eye, round
  "handcrafted-blue-geode-resin-evil-eye-wall-mirror": "https://www.amazon.in/dp/B0HLZWDRH4",
  // Green geode glitter, round
  "handmade-green-geode-resin-glitter-wall-mirror": "https://www.amazon.in/dp/B0HPP4569V",
  // Pearl & seashell floral round (2x2, wall or tabletop)
  "pearl-shell-luxe-round-mirror": "https://www.amazon.in/dp/B0HK8CB5KL",
  // Ocean wave, blue & turquoise with gold
  "handmade-ocean-wave-resin-art-round-mirror": "https://www.amazon.in/dp/B0HKZC2CX5",
  // Navy blue crescent with iridescent crystal
  "handcrafted-navy-blue-crystal-resin-decorative-wall-mirror": "https://www.amazon.in/dp/B0HLZHNP1Z",
  // Handmade pink geode 60x60 cm
  "pink-geode-handmade-resin-wall-mirror": "https://www.amazon.in/dp/B0HM41RKMX",
  // Pink & silver geode
  "luxury-handmade-geode-resin-wall-mirror-pink-silver": "https://www.amazon.in/dp/B0HL93MNPS",
  // Golden glitter geometric
  "golden-glitter-resin-designer-wall-mirror": "https://www.amazon.in/dp/B0HP1YH793",
  // Glossy black geode with silver & gold (18x24)
  "black-geode-resin-wall-mirror": "https://www.amazon.in/dp/B0HK156WJ5",
  // Purple geode with red-orange accents and gold embellishments
  "handmade-purple-geode-resin-decorative-mirror": "https://www.amazon.in/dp/B0HLQBFQS8",
  // Blue & silver geode, golden border, seashell accents (blue pentagon)
  "oceanic-blue-geode-resin-wall-mirror": "https://www.amazon.in/dp/B0HM7P2F9V",
  // Blue gold round geode with crystal embellishments
  "oceanic-blue-gold-resin-round-mirror": "https://www.amazon.in/dp/B0HL4R7GHS",
};

/**
 * Name-keyed links, checked before the slug table. Needed because the slug
 * `handmade-geode-resin-round-wall-mirror` is shared by two different mirrors.
 * Matched on a lowercase substring of the product name.
 */
const AMAZON_LINKS_BY_NAME = [
  // "handmade-geode-resin-round-wall-mirror-blue-gold-crystal"
  ["blue-gold-crystal", "https://www.amazon.in/dp/B0HL4R7GHS"],
  // "Handmade Geode Resin Round Wall Mirror — Blue & Turquoise with Gold Accents"
  ["blue & turquoise", "https://www.amazon.in/dp/B0HL6PRTXR"],
];

/** The Amazon link for a product: the one saved on the product, else the tables above. */
export function amazonUrlFor(product) {
  if (!product) return "";
  const direct = (product.amazon_url || "").toString().trim();
  if (direct) return direct;
  const name = (product.name || "").toString().toLowerCase();
  if (name) {
    const byName = AMAZON_LINKS_BY_NAME.find(([needle]) => name.includes(needle));
    if (byName) return byName[1];
  }
  return AMAZON_LISTING_LINKS[product.slug] || "";
}
