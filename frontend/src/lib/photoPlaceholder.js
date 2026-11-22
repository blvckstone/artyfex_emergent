/**
 * Branded stand-in for a product photo that the image host no longer serves.
 *
 * Cloudinary destroy() is permanent — a photo deleted there is gone for good
 * (no trash), so a dead URL can only ever render as a broken-image icon. Rather
 * than let the shop look broken, every storefront <img> falls back to this
 * self-contained SVG tile with the ArtyFex mark. It ships inside the JS bundle,
 * so it cannot itself fail to load.
 *
 * Usage: <img src={...} onError={onPhotoError} />
 */
export const PHOTO_PLACEHOLDER =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 500">' +
      '<rect width="400" height="500" fill="#0b0b0c"/>' +
      '<rect x="12" y="12" width="376" height="476" fill="none" stroke="#c8a96a" stroke-opacity="0.28"/>' +
      '<g fill="none" stroke="#c8a96a" stroke-opacity="0.55" stroke-width="2">' +
      '<circle cx="200" cy="232" r="46"/>' +
      '<path d="M200 198v68M166 232h68"/>' +
      "</g>" +
      '<text x="200" y="330" text-anchor="middle" fill="#c8a96a" fill-opacity="0.85"' +
      ' font-family="Georgia,serif" font-size="22" letter-spacing="6">ARTYFEX</text>' +
      '<text x="200" y="356" text-anchor="middle" fill="#e8e2d6" fill-opacity="0.45"' +
      ' font-family="Helvetica,Arial,sans-serif" font-size="11" letter-spacing="2">PHOTO BEING RESTORED</text>' +
      "</svg>"
  );

/** Swap a broken photo for the branded tile, exactly once per element. */
export function onPhotoError(event) {
  const img = event && event.currentTarget;
  if (!img || img.dataset.placeholderApplied === "1") return;
  img.dataset.placeholderApplied = "1";
  img.src = PHOTO_PLACEHOLDER;
}
