"use client";

import { useEffect, useMemo, useState } from "react";

import { MediaImage } from "@/components/media-image";

export function ImagePicker({
  file,
  label,
  onChange,
}: {
  file: File | null;
  label: string;
  onChange: (file: File | null) => void;
}) {
  const [validationError, setValidationError] = useState<string>();
  const preview = useMemo(
    () => (file ? URL.createObjectURL(file) : undefined),
    [file],
  );

  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview);
    };
  }, [preview]);

  return (
    <div className="image-picker">
      {preview ? (
        <MediaImage
          alt={`${label} preview`}
          className="image-preview"
          src={preview}
        />
      ) : (
        <div className="image-placeholder" aria-hidden="true">
          <span>+</span>
          <small>Optional cover</small>
        </div>
      )}
      <div>
        <label className="button secondary compact image-picker-button">
          {file ? "Change image" : `Add ${label.toLowerCase()}`}
          <input
            accept="image/jpeg,image/png,image/webp,image/gif"
            className="visually-hidden"
            onChange={(event) => {
              const selected = event.target.files?.[0] ?? null;
              if (selected && selected.size > 5 * 1024 * 1024) {
                setValidationError("Choose an image that is 5 MB or smaller.");
                event.target.value = "";
                return;
              }
              if (
                selected &&
                !["image/jpeg", "image/png", "image/webp", "image/gif"].includes(
                  selected.type,
                )
              ) {
                setValidationError("Choose a JPEG, PNG, WebP, or GIF image.");
                event.target.value = "";
                return;
              }
              setValidationError(undefined);
              onChange(selected);
            }}
            type="file"
          />
        </label>
        <p className="muted image-help">JPEG, PNG, WebP, or GIF · up to 5 MB</p>
        {file ? (
          <button
            className="text-button"
            onClick={() => onChange(null)}
            type="button"
          >
            Remove image
          </button>
        ) : null}
        {validationError ? (
          <p className="image-error" role="alert">
            {validationError}
          </p>
        ) : null}
      </div>
    </div>
  );
}
