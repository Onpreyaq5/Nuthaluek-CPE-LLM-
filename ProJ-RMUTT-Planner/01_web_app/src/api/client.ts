import { copy as uiCopy } from "@/i18n/th";
export const isMock = import.meta.env.VITE_USE_MOCKS !== "false";
export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public details: Record<string, unknown> = {},
    public requestId = "",
  ) {
    super(message);
    this.name = "ApiError";
  }
}
export function errorText(error: unknown) {
  return error instanceof ApiError
    ? "" +
        error.message +
        "" +
        (error.requestId ? ` (อ้างอิง ${error.requestId})` : "") +
        ""
    : error instanceof Error
      ? error.message
      : uiCopy.client001;
}
export async function apiFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers,
    credentials: "include",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    if (response.status === 401)
      window.dispatchEvent(new Event("campusmate:unauthorized"));
    throw new ApiError(
      body.error?.code || `HTTP_${response.status}`,
      body.error?.message || uiCopy.client002,
      body.error?.details || {},
      body.meta?.request_id || response.headers.get("x-request-id") || "",
    );
  }
  return response;
}
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const timeout = AbortSignal.timeout(25000);
  const response = await apiFetch(path, {
    ...init,
    signal: init?.signal ? AbortSignal.any([init.signal, timeout]) : timeout,
  });
  const body = await response.json();
  if (body.ok !== true)
    throw new ApiError(
      body.error?.code || "INVALID_RESPONSE",
      body.error?.message || uiCopy.client003,
      body.error?.details,
      body.meta?.request_id,
    );
  return body.data as T;
}
export const api = {
  get: <T>(path: string, signal?: AbortSignal) => request<T>(path, { signal }),
  post: <T>(path: string, body: unknown, signal?: AbortSignal) =>
    request<T>(path, {
      method: "POST",
      body: body instanceof FormData ? body : JSON.stringify(body),
      signal,
    }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

/** 02 ห่อทุก list endpoint เป็น {items, next_cursor} (cursor pagination) — จุดเดียวที่ unwrap ให้ทุกที่เรียกผ่าน */
export async function requestPage<T>(
  path: string,
  signal?: AbortSignal,
): Promise<{ items: T[]; nextCursor: string | null }> {
  const data = await request<{ items: T[]; next_cursor?: string | null }>(path, { signal });
  return { items: data.items, nextCursor: data.next_cursor ?? null };
}
