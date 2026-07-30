"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { apiFetch, clearToken, getToken, setToken } from "@/lib/api-client";
import type { UserProfile } from "@/lib/types";
import * as authApi from "./api";

export function useAuthToken() {
  const [token, updateToken] = useState<string | null>(null);
  useEffect(() => {
    const sync = () => updateToken(getToken());
    sync();
    window.addEventListener("bullymarket-auth", sync);
    return () => window.removeEventListener("bullymarket-auth", sync);
  }, []);
  return token;
}

export function useMe() {
  const token = useAuthToken();
  return useQuery({
    queryKey: ["me", token],
    queryFn: () => apiFetch<UserProfile>("/users/me"),
    enabled: Boolean(token),
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: authApi.login,
    onSuccess: ({ access_token }) => {
      setToken(access_token);
      void queryClient.invalidateQueries();
    },
  });
}

export function useSignup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: authApi.signup,
    onSuccess: ({ access_token }) => {
      setToken(access_token);
      void queryClient.invalidateQueries();
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return () => {
    clearToken();
    queryClient.clear();
  };
}

