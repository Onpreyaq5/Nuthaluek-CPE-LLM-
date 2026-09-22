import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { consumeSSE, type ChatEvent } from "./chat-stream";
const encoder = new TextEncoder();
function splitStream(text: string) {
  const bytes = encoder.encode(text);
  return new ReadableStream<Uint8Array>({
    start(c) {
      for (const b of bytes) c.enqueue(new Uint8Array([b]));
      c.close();
    },
  });
}
describe("POST chat SSE reader", () => {
  it("keeps Thai UTF-8 intact when every byte arrives separately, supports CRLF and heartbeat", async () => {
    const events: ChatEvent[] = [];
    const text =
      ': heartbeat\r\n\r\ndata: {"type":"token","text":"สวัสดีครับ 🦉"}\r\n\r\ndata: {"type":"done","message_id":12}\r\n\r\n';
    assert.equal(
      await consumeSSE(splitStream(text), (e) => events.push(e)),
      "complete",
    );
    assert.deepEqual(events, [
      { type: "token", text: "สวัสดีครับ 🦉" },
      { type: "done", message_id: 12 },
    ]);
  });
  it("never treats EOF without done as a complete answer", async () => {
    assert.equal(
      await consumeSSE(
        splitStream('data: {"type":"token","text":"บางส่วน"}\n\n'),
        () => {},
      ),
      "interrupted",
    );
  });
  it("returns an explicit stream error", async () => {
    assert.equal(
      await consumeSSE(
        splitStream(
          'data: {"type":"error","code":"UPSTREAM_502","message":"ล่ม"}\n\n',
        ),
        () => {},
      ),
      "error",
    );
  });
  it("rejects malformed JSON instead of accepting a corrupt answer", async () => {
    await assert.rejects(
      consumeSSE(splitStream("data: {broken}\n\n"), () => {}),
    );
  });
  it("aborts a pending read without waiting for the next token", async () => {
    let cancelled = false;
    const controller = new AbortController();
    const promise = consumeSSE(
      new ReadableStream({
        cancel() {
          cancelled = true;
        },
      }),
      () => {},
      controller.signal,
    );
    controller.abort();
    await assert.rejects(promise, { name: "AbortError" });
    assert.equal(cancelled, true);
  });
  it("accepts named SSE events and replaces the sources event payload", async () => {
    const events: ChatEvent[] = [];
    const text =
      'event: sources\ndata: {"items":[]}\n\nevent: done\ndata: {"message_id":15}\n\n';
    assert.equal(
      await consumeSSE(splitStream(text), (e) => events.push(e)),
      "complete",
    );
    assert.deepEqual(events, [
      { type: "sources", items: [] },
      { type: "done", message_id: 15 },
    ]);
  });
  it("rejects done without a valid message id", async () => {
    await assert.rejects(
      consumeSSE(splitStream('data: {"type":"done"}\n\n'), () => {}),
    );
  });
});
