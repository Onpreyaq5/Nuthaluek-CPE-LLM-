import { useQuery } from "@tanstack/react-query";
import { api, requestPage } from "./client";
export function useApiQuery<T>(
  key: readonly unknown[],
  path: string,
  enabled = true,
) {
  return useQuery({
    queryKey: key,
    queryFn: ({ signal }) => api.get<T>(path, signal),
    enabled,
    retry: false,
  });
}
/** สำหรับ endpoint ที่ 02 คืน {items, next_cursor} (cursor pagination) — ใช้แทน useApiQuery ทุกจุดที่ดึง list */
export function useApiPage<T>(
  key: readonly unknown[],
  path: string,
  enabled = true,
) {
  return useQuery({
    queryKey: key,
    queryFn: ({ signal }) => requestPage<T>(path, signal),
    enabled,
    retry: false,
  });
}
