import React, { useState, useRef, useCallback } from "react";
import { UploadCloud, X, Loader2, Image as ImageIcon } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";

/**
 * CloudinaryUpload
 *
 * Drag-drop image uploader that talks to Cloudinary directly (via signed params
 * fetched from our backend). Never proxies the file bytes through our server.
 *
 * Task 1 (Jul 2025):
 *   - Duplicate detection: SHA-1 of file bytes → passed to backend as public_id.
 *     Backend signs with overwrite=false so Cloudinary silently reuses the
 *     existing asset for identical files. No UI notification when it happens.
 *   - Deletion: when the user removes an image, we call DELETE /cloudinary/asset
 *     so we do not accumulate orphaned assets in Cloudinary.
 *
 * Props:
 *   value       string | string[]   — current URL(s)
 *   onChange    (urlOrUrls) => void — called with the new value
 *   multiple    boolean             — allow multiple files (returns string[])
 *   folder      string              — Cloudinary folder (must start with "artyfex")
 *   label       string              — label for the drop zone
 *   testid      string              — data-testid prefix
 *   compact     boolean             — thumbnail-only mode for inline grids
 */
async function _sha1Hex(file) {
  try {
    const buf = await file.arrayBuffer();
    const digest = await crypto.subtle.digest("SHA-1", buf);
    return Array.from(new Uint8Array(digest))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  } catch (_) {
    // Old browsers / non-secure contexts: fall back to a random id (no dedup)
    return null;
  }
}

async function _destroyOnCloudinary(url) {
  if (!url || typeof url !== "string" || !url.includes("res.cloudinary.com")) return;
  try {
    const adminToken = (typeof window !== "undefined") ? localStorage.getItem("artyfex_admin_token") : "";
    await api.delete(`/cloudinary/asset`, {
      params: { url },
      headers: adminToken ? { Authorization: `Bearer ${adminToken}` } : {},
    });
  } catch (err) {
    // Silent — the UI removal shouldn't fail because Cloudinary GC did.
    console.warn("Cloudinary destroy failed (ignored):", err?.response?.data?.detail || err?.message);
  }
}

export default function CloudinaryUpload({
  value,
  onChange,
  multiple = false,
  folder = "artyfex",
  label = "Drop image or click to upload",
  testid = "cldn",
  compact = false,
}) {
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const urls = multiple
    ? (Array.isArray(value) ? value : (value ? [value] : []))
    : (typeof value === "string" ? (value ? [value] : []) : []);

  const doUpload = useCallback(async (files) => {
    if (!files || !files.length) return;
    setUploading(true);
    // Snapshot the URL we're about to replace (single mode). Nov 2026: we no longer
    // delete the old file — the backend keeps it, because a replaced photo is still
    // recoverable while a deleted one is gone for good.
    const previousUrl = (!multiple && typeof value === "string") ? value : null;
    try {
      const uploaded = [];
      for (const file of files) {
        if (!file.type.startsWith("image/")) {
          toast.error(`${file.name} is not an image`);
          continue;
        }
        if (file.size > 10 * 1024 * 1024) {
          toast.error(`${file.name} exceeds 10 MB`);
          continue;
        }
        const contentHash = await _sha1Hex(file); // may be null on old browsers
        const adminToken = (typeof window !== "undefined") ? localStorage.getItem("artyfex_admin_token") : "";
        const { data: sig } = await api.get(`/cloudinary/signature`, {
          params: { folder, resource_type: "image", ...(contentHash ? { public_id: contentHash } : {}) },
          headers: adminToken ? { Authorization: `Bearer ${adminToken}` } : {},
        });
        const form = new FormData();
        form.append("file", file);
        form.append("api_key", sig.api_key);
        form.append("timestamp", sig.timestamp);
        form.append("signature", sig.signature);
        form.append("folder", sig.folder);
        if (sig.public_id) form.append("public_id", sig.public_id);
        if (sig.overwrite) form.append("overwrite", sig.overwrite);
        if (sig.invalidate) form.append("invalidate", sig.invalidate);
        const res = await fetch(
          `https://api.cloudinary.com/v1_1/${sig.cloud_name}/image/upload`,
          { method: "POST", body: form }
        );
        const data = await res.json();
        if (!res.ok || !data.secure_url) {
          throw new Error(data.error?.message || "Cloudinary upload failed");
        }
        // Nov 2026 — keep a permanent copy on our own server as well, so the
        // product no longer depends on the Cloudinary file staying alive.
        // If archiving fails we still save the Cloudinary URL (old behaviour).
        let savedUrl = data.secure_url;
        try {
          const { data: archived } = await api.post(
            `/admin/media/archive`,
            { url: data.secure_url },
            { headers: adminToken ? { Authorization: `Bearer ${adminToken}` } : {}, timeout: 90000 }
          );
          if (archived?.url) savedUrl = archived.url;
        } catch (err) {
          console.warn("Photo archive failed, keeping Cloudinary URL:", err?.response?.data?.detail || err?.message);
        }
        uploaded.push(savedUrl);
      }
      if (multiple) {
        onChange([...(Array.isArray(value) ? value : (value ? [value] : [])), ...uploaded]);
      } else {
        const newUrl = uploaded[uploaded.length - 1] || "";
        onChange(newUrl);
        // Delete the previous single-mode image ONLY if it's a Cloudinary URL
        // AND the new URL is different (i.e. not a dedup match returning the same asset).
        if (previousUrl && newUrl && previousUrl !== newUrl) {
          _destroyOnCloudinary(previousUrl);
        }
      }
      toast.success(`${uploaded.length} image${uploaded.length === 1 ? "" : "s"} uploaded`);
    } catch (err) {
      console.error("Cloudinary upload error", err);
      toast.error(err?.response?.data?.detail || err?.message || "Upload failed");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }, [multiple, value, onChange, folder]);

  const onFilesSelected = (e) => doUpload(Array.from(e.target.files || []));

  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    doUpload(Array.from(e.dataTransfer.files || []));
  };

  // Delete-then-clear helper used by the X button in both compact & regular modes.
  const removeAt = (idx) => {
    if (multiple) {
      const next = [...urls];
      const removed = next.splice(idx, 1)[0];
      onChange(next);
      if (removed) _destroyOnCloudinary(removed);
    } else {
      const removed = urls[0];
      onChange("");
      if (removed) _destroyOnCloudinary(removed);
    }
  };

  // COMPACT MODE: square thumbnail with hover-upload overlay.
  if (compact && !multiple) {
    const url = urls[0];
    return (
      <div
        data-testid={`${testid}-wrap`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={`group relative w-full h-full min-w-[80px] min-h-[80px] bg-ink-950 border ${dragOver ? "border-gold" : "border-white/15"} hover:border-gold/60 cursor-pointer overflow-hidden`}
        title={url ? "Click to replace image" : "Click to upload image"}
      >
        {url ? (
          // eslint-disable-next-line
          <img src={url} alt="" className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center text-cream/50 gap-1 p-2">
            <UploadCloud className="w-4 h-4 text-gold" />
            <span className="text-[9px] uppercase tracking-luxury text-center leading-tight">Upload</span>
          </div>
        )}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/55 transition-colors flex items-center justify-center pointer-events-none">
          {uploading ? (
            <Loader2 className="w-4 h-4 animate-spin text-gold" />
          ) : url ? (
            <UploadCloud className="w-4 h-4 text-gold opacity-0 group-hover:opacity-100 transition-opacity" />
          ) : null}
        </div>
        {url && (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); removeAt(0); }}
            className="absolute top-1 right-1 bg-black/70 hover:bg-red-500 text-white p-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
            aria-label="Remove image"
            data-testid={`${testid}-remove`}
          ><X className="w-3 h-3" /></button>
        )}
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={onFilesSelected}
          data-testid={`${testid}-input`}
        />
      </div>
    );
  }

  return (
    <div data-testid={`${testid}-wrap`} className="space-y-3">
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={`cursor-pointer border border-dashed ${dragOver ? "border-gold bg-gold/5" : "border-white/20"} bg-ink-950 hover:border-gold/50 transition-colors p-6 text-center`}
        data-testid={`${testid}-dropzone`}
      >
        {uploading ? (
          <div className="flex items-center justify-center gap-2 text-cream/70">
            <Loader2 className="w-4 h-4 animate-spin text-gold" />
            <span className="text-xs uppercase tracking-luxury">Uploading…</span>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 text-cream/60">
            <UploadCloud className="w-6 h-6 text-gold" />
            <span className="text-xs uppercase tracking-luxury">{label}</span>
            <span className="text-[10px] text-cream/40">PNG, JPG, WebP · Max 10 MB{multiple ? " · multiple allowed" : ""}</span>
          </div>
        )}
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          multiple={multiple}
          className="hidden"
          onChange={onFilesSelected}
          data-testid={`${testid}-input`}
        />
      </div>

      {urls.length > 0 && (
        <div className={multiple ? "grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2" : "flex flex-wrap gap-2"}>
          {urls.map((u, i) => (
            <div
              key={`${u}-${i}`}
              className={`group relative bg-ink-950 border border-white/10 overflow-hidden ${multiple ? "aspect-square" : "w-32 h-32"}`}
            >
              {/* eslint-disable-next-line */}
              <img src={u} alt="" className="w-full h-full object-cover" />
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); removeAt(i); }}
                className="absolute top-1 right-1 bg-black/70 hover:bg-red-500 text-white p-1"
                data-testid={`${testid}-remove-${i}`}
                aria-label="Remove image"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {!urls.length && (
        <div className="flex items-center gap-2 text-[10px] text-cream/40 italic">
          <ImageIcon className="w-3 h-3" /> No image yet
        </div>
      )}
    </div>
  );
}
