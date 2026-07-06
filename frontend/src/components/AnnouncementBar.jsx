import React, { useState } from "react";
import { X } from "lucide-react";

/**
 * Slim announcement bar rendered above the Navbar.
 * Fully controlled by homepage CMS settings: text, colors, optional link.
 */
export default function AnnouncementBar({ content }) {
  const [dismissed, setDismissed] = useState(false);
  if (!content || !content.enabled || dismissed) return null;
  const bg = content.bg_color || "#0a0a0a";
  const color = content.text_color || "#D4AF37";
  const link = (content.link_url || "").trim();
  const label = (content.link_label || "").trim();

  return (
    <div
      data-testid="announcement-bar"
      className="w-full text-center text-[10px] md:text-[11px] uppercase tracking-luxury py-2 px-4 border-b border-white/5 relative"
      style={{ backgroundColor: bg, color }}
    >
      <span>{content.text}</span>
      {link && label && (
        <a href={link} className="ml-3 underline underline-offset-2 hover:opacity-80">
          {label} →
        </a>
      )}
      <button
        aria-label="Dismiss"
        onClick={() => setDismissed(true)}
        className="absolute right-2 top-1/2 -translate-y-1/2 p-1 opacity-60 hover:opacity-100"
      >
        <X className="w-3 h-3" />
      </button>
    </div>
  );
}
