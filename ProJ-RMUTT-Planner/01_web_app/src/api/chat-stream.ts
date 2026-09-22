import { copy as uiCopy } from "@/i18n/th";
import { apiFetch } from "./client";
import type { ChatRequest, SourceItem } from "./types";
export type ChatEvent =
  | { type: "session"; session_id: number }
  | { type: "tool_start" | "tool_end"; tool: string }
  | { type: "token"; text: string }
  | { type: "sources"; items: SourceItem[] }
  | { type: "done"; message_id: number }
  | { type: "error"; code: string; message: string };
/** schema.d.ts type `Record<string, never>` สำหรับ plan_draft เป็นผลจาก 02 ประกาศเป็น `dict` เปล่าไม่มี sub-schema
 * (openapi-typescript จึงตีเป็น object ว่างเป๊ะ) — คลายเป็น object ทั่วไปแค่ตอนส่งจริงจากฝั่งนี้ */
export type ChatStreamBody = Omit<ChatRequest, "plan_draft"> & {
  plan_draft?: Record<string, unknown> | null;
};

export async function consumeSSE(
  stream: ReadableStream<Uint8Array>,
  onEvent: (event: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<"complete" | "interrupted" | "error"> {
  const reader = stream.getReader(),
    decoder = new TextDecoder();
  let buffer = "";
  let outcome: "complete" | "interrupted" | "error" = "interrupted";
  const abort = () => {
    void reader.cancel();
  };
  signal?.addEventListener("abort", abort, { once: true });
  const parse = () => {
    let match: RegExpExecArray | null;
    while ((match = /\r?\n\r?\n/.exec(buffer))) {
      const block = buffer.slice(0, match.index);
      buffer = buffer.slice(match.index + match[0].length);
      const data = block
        .split(/\r?\n/)
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trimStart())
        .join("\n");
      if (!data) continue;
      const parsed = JSON.parse(data);
      const namedType = block
        .split(/\r?\n/)
        .find((line) => line.startsWith("event:"))
        ?.slice(6)
        .trim();
      if (!parsed || typeof parsed !== "object")
        throw new Error(uiCopy.chatstream001);
      const event = { ...parsed, type: parsed.type || namedType } as ChatEvent;
      if (
        ![
          "session",
          "tool_start",
          "tool_end",
          "token",
          "sources",
          "done",
          "error",
        ].includes(event.type)
      )
        continue;
      if (event.type === "token" && typeof event.text !== "string")
        throw new Error(uiCopy.chatstream002);
      if (event.type === "sources" && !Array.isArray(event.items))
        throw new Error(uiCopy.chatstream003);
      if (event.type === "session" && !Number.isInteger(event.session_id))
        throw new Error(uiCopy.chatstream004);
      if (event.type === "done" && !Number.isInteger(event.message_id))
        throw new Error(uiCopy.chatstream005);
      onEvent(event);
      if (event.type === "done") {
        outcome = "complete";
        return;
      }
      if (event.type === "error") {
        outcome = "error";
        return;
      }
    }
  };
  try {
    while (true) {
      if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
      const { value, done } = await reader.read();
      if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
      if (done) {
        buffer += decoder.decode();
        parse();
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      parse();
      if (outcome !== "interrupted") break;
    }
    return outcome;
  } finally {
    signal?.removeEventListener("abort", abort);
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
export async function streamChat(
  body: ChatStreamBody,
  onEvent: (event: ChatEvent) => void,
  signal: AbortSignal,
) {
  const response = await apiFetch("/chat", {
    method: "POST",
    body: JSON.stringify(body),
    signal,
  });
  if (
    !response.headers.get("content-type")?.includes("text/event-stream") ||
    !response.body
  )
    throw new Error(uiCopy.chatstream006);
  return consumeSSE(response.body, onEvent, signal);
}
