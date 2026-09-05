/* eslint-disable @next/next/no-img-element */

import type { ImgHTMLAttributes } from "react";

import { mediaUrl } from "@/lib/api-client";

type MediaImageProps = Omit<ImgHTMLAttributes<HTMLImageElement>, "alt" | "src"> & {
  alt: string;
  src?: string;
};

export function MediaImage({ alt, src, ...props }: MediaImageProps) {
  const resolved = typeof src === "string" ? mediaUrl(src) : undefined;
  if (!resolved) return null;
  return <img {...props} alt={alt} src={resolved} />;
}
