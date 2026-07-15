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
 * Props:
 *   value       string | string[]   — current URL(s)
 *   onChange    (urlOrUrls) => void — called with the new value (matches the shape of `value`)
 *   multiple    boolean             — allow multiple files (returns string[])
 *   folder      string              — Cloudinary folder (must start with "artyfex")
 *   label       string              — label for the drop zone
 *   testid      string              — data-testid prefix
 */
export default function CloudinaryUpload({
  value,
  onChange,
  multiple = false,
  folder = "artyfex",
  label = "Drop image or click to upload",
  testid = "cldn",
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
        // 1) Get signature from our backend (admin auth required — axios instance already has token)
        const { data: sig } = await api.get(`/cloudinary/signature`, { params: { folder, resource_type: "image" } });
        // 2) POST directly to Cloudinary
        const form = new FormData();
        form.append("file", file);
        form.append("api_key", sig.api_key);
        form.append("timestamp", sig.timestamp);
        form.append("signature", sig.signature);
        form.append("folder", sig.folder);
        const res = await fetch(
          `https://api.cloudinary.com/v1_1/${sig.cloud_name}/image/upload`,
          { method: "POST", body: form }
        );
        const data = await res.json();
        if (!res.ok || !data.secure_url) {
          throw new Error(data.error?.message || "Cloudinary upload failed");
        }
        uploaded.push(data.secure_url);
      }
      if (multiple) {
        onChange([...(Array.isArray(value) ? value : (value ? [value] : [])), ...uploaded]);
      } else {
        onChange(uploaded[uploaded.length - 1] || "");
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

  const removeAt = (idx) => {
    if (multiple) {
      const next = [...urls]; next.splice(idx, 1);
      onChange(next);
    } else {
      onChange("");
    }
  };

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
        <div className={`grid ${multiple ? "grid-cols-3 sm:grid-cols-4 md:grid-cols-6" : "grid-cols-1"} gap-2`}>
          {urls.map((u, i) => (
            <div key={`${u}-${i}`} className="group relative aspect-square bg-ink-950 border border-white/10 overflow-hidden">
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
