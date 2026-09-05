import { apiFetch } from "@/lib/api-client";

export function uploadImage(image: File) {
  const body = new FormData();
  body.append("image", image);
  return apiFetch<{ image_url: string }>("/uploads/images", {
    method: "POST",
    body,
  });
}
