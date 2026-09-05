const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const TOKEN_KEY = "bullymarket_access_token";
export const AUTH_FAILURE_EVENT = "bullymarket-auth-failed";

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number,
    public readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
  window.dispatchEvent(new Event("bullymarket-auth"));
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
  window.dispatchEvent(new Event("bullymarket-auth"));
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  const isFormData =
    typeof FormData !== "undefined" && init.body instanceof FormData;
  if (init.body && !isFormData && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }
  if (token) headers.set("authorization", `Bearer ${token}`);

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
  });
  if (!response.ok) {
    if (response.status === 401 && typeof window !== "undefined") {
      clearToken();
      window.dispatchEvent(new Event(AUTH_FAILURE_EVENT));
    }
    const payload = (await response.json().catch(() => null)) as
      | {
          error?: { code?: string; message?: string };
          detail?: string;
          request_id?: string;
        }
      | null;
    throw new ApiError(
      payload?.error?.code ?? "request_failed",
      payload?.error?.message ?? payload?.detail ?? "The request failed",
      response.status,
      payload?.request_id ?? response.headers.get("x-request-id") ?? undefined,
    );
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function mediaUrl(path: string | null | undefined): string | undefined {
  if (!path) return undefined;
  if (/^(?:https?:\/\/|blob:|data:)/i.test(path)) return path;
  return `${API_URL.replace(/\/api\/v1\/?$/, "")}${path}`;
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.requestId
      ? `${error.message} · Reference ${error.requestId}`
      : error.message;
  }
  return error instanceof Error ? error.message : "Something went wrong";
}
