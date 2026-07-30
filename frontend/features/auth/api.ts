import { apiFetch } from "@/lib/api-client";

interface TokenResponse {
  access_token: string;
  token_type: string;
}

export function login(input: { email: string; password: string }) {
  return apiFetch<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function signup(input: {
  email: string;
  display_name: string;
  password: string;
}) {
  return apiFetch<TokenResponse>("/auth/signup", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

