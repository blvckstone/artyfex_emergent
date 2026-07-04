import React, { useState } from "react";

/**
 * BrandLogo
 * Drop a logo image into /public/brand/logo.svg (or logo.png) to enable the image
 * logo automatically. If the file is missing (or fails to load), a text logo
 * is shown as a graceful fallback.
 *
 * Custom logo path can be overridden via the `src` prop.
 */
export default function BrandLogo({
  src = "/brand/logo.svg",
  className = "",
  imgClassName = "",
  textClassName = "",
  alt = "ArtyFex",
}) {
  const [failed, setFailed] = useState(false);

  return (
    <span
      className={`inline-flex items-center gap-2 ${className}`}
      data-testid="brand-logo"
    >
      {!failed ? (
        <img
          src={src}
          alt={alt}
          onError={() => setFailed(true)}
          className={imgClassName || "h-8 md:h-10 w-auto object-contain"}
        />
      ) : (
        <span
          className={
            textClassName ||
            "font-serif text-2xl md:text-3xl tracking-tight text-cream flex items-baseline gap-1"
          }
        >
          Arty<span className="italic text-gold">Fex</span>
        </span>
      )}
    </span>
  );
}
