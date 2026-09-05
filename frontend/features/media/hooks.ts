"use client";

import { useMutation } from "@tanstack/react-query";

import { uploadImage } from "./api";

export function useUploadImage() {
  return useMutation({ mutationFn: uploadImage });
}
