import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  AUTH_FAILURE_EVENT,
  ApiError,
  TOKEN_KEY,
  apiFetch,
  mediaUrl,
} from "./api-client";

describe("apiFetch", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  it("sends the stored bearer token and parses JSON", async () => {
    window.localStorage.setItem(TOKEN_KEY, "test-token");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    await expect(apiFetch<{ status: string }>("/example")).resolves.toEqual({
      status: "ok",
    });
    const request = fetchMock.mock.calls[0];
    const headers = new Headers(request[1]?.headers);
    expect(headers.get("authorization")).toBe("Bearer test-token");
  });

  it("lets the browser set multipart boundaries for form data", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ image_url: "/media/images/photo.png" }), {
        status: 201,
      }),
    );
    const body = new FormData();
    body.append("image", new File(["image"], "photo.png", { type: "image/png" }));

    await apiFetch("/uploads/images", { method: "POST", body });

    const headers = new Headers(fetchMock.mock.calls[0][1]?.headers);
    expect(headers.has("content-type")).toBe(false);
  });

  it("resolves managed and local-preview image URLs", () => {
    expect(mediaUrl("/media/images/photo.png")).toBe(
      "http://localhost:8000/media/images/photo.png",
    );
    expect(mediaUrl("blob:http://localhost/preview")).toBe(
      "blob:http://localhost/preview",
    );
  });

  it("preserves domain error codes and request IDs", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          error: { code: "insufficient_balance", message: "Not enough points" },
          request_id: "request-123",
        }),
        { status: 409 },
      ),
    );

    const error = await apiFetch("/trade").catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      code: "insufficient_balance",
      message: "Not enough points",
      requestId: "request-123",
      status: 409,
    });
  });

  it("clears rejected authentication and requests a sign-in redirect", async () => {
    window.localStorage.setItem(TOKEN_KEY, "expired-token");
    const authenticationFailed = vi.fn();
    window.addEventListener(AUTH_FAILURE_EVENT, authenticationFailed);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          error: { code: "invalid_token", message: "Authentication failed" },
        }),
        { status: 401 },
      ),
    );

    const error = await apiFetch("/users/me").catch((caught: unknown) => caught);

    expect(error).toMatchObject({ status: 401 });
    expect(window.localStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(authenticationFailed).toHaveBeenCalledOnce();
    window.removeEventListener(AUTH_FAILURE_EVENT, authenticationFailed);
  });
});
