import { clsx } from "clsx";
import { twMerge } from "tailwind-merge"

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

/**
 * Batch 6 — de-duplicates a variants array for tile / card display.
 * - Collapses variants with the same hex + base label (before "·")
 * - Filters out placeholder "default" variants
 * - Returns [] when the product has no meaningful swatches (single/no variants,
 *   or only a "default" variant), so tiles can skip rendering the row.
 */
export function displayableVariants(variants) {
  if (!Array.isArray(variants) || variants.length === 0) return [];
  const seen = new Set();
  const cleaned = variants.filter((v) => {
    if (!v) return false;
    const baseLabel = ((v.label || "").split("·")[0] || "").trim().toLowerCase();
    const isDefault = (v.key || "").toLowerCase() === "default" || baseLabel === "default";
    if (isDefault) return false;
    const dedup = `${(v.hex || "").toLowerCase()}|${baseLabel}`;
    if (seen.has(dedup)) return false;
    seen.add(dedup);
    return true;
  });
  return cleaned.length > 1 ? cleaned : [];
}
