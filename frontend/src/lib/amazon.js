/**
 * Amazon listings for pieces that are sold both here and on Amazon.
 *
 * Keyed by product slug. `product.amazon_url` (set in Admin → Products) always
 * wins, so new uploads never need this file — it only backfills pieces that
 * were listed on Amazon before the field existed.
 *
 * Match method: the Amazon brand page for ArtyFex was read, and each listing
 * title was matched to the website piece with the same colour / shape / finish.
 * Unmatched pieces are deliberately absent rather than guessed — a wrong link
 * sends a buyer to a different mirror.
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
};

/** The Amazon link for a product: the one saved on the product, else the table above. */
export function amazonUrlFor(product) {
  if (!product) return "";
  const direct = (product.amazon_url || "").toString().trim();
  if (direct) return direct;
  return AMAZON_LISTING_LINKS[product.slug] || "";
}
