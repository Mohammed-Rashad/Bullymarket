import { apiFetch } from "@/lib/api-client";

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface VerificationChallengeResponse {
  verification_required: boolean;
  expires_in_seconds: number;
  message: string;
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
  return apiFetch<VerificationChallengeResponse>("/auth/signup", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function verifySignup(input: { email: string; code: string }) {
  return apiFetch<TokenResponse>("/auth/signup/verify", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function forgotPassword(input: { email: string }) {
  return apiFetch<{ message: string }>("/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function resetPassword(input: {
  email: string;
  code: string;
  new_password: string;
}) {
  return apiFetch<TokenResponse>("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify(input),
  });
}
