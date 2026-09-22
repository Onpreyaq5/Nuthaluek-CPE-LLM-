import { describe, it, afterEach } from "node:test";
import assert from "node:assert/strict";
import { api, ApiError } from "./client";
const originalFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = originalFetch;
});
describe("API gateway adapter", () => {
  it("unwraps the envelope and sends cookies only to the relative gateway", async () => {
    globalThis.fetch = async (url, options) => {
      assert.equal(url, "/api/v1/plans");
      assert.equal(options?.credentials, "include");
      return Response.json({
        ok: true,
        data: [{ id: 7 }],
        meta: { request_id: "req-test" },
      });
    };
    assert.deepEqual(await api.get("/plans"), [{ id: 7 }]);
  });
  it("preserves multipart boundaries by not setting the Content-Type header", async () => {
    const form = new FormData();
    form.append("file", new Blob(["sample"]), "sample.html");
    globalThis.fetch = async (_, options) => {
      assert.equal(new Headers(options?.headers).has("Content-Type"), false);
      assert.equal(options?.body, form);
      return Response.json({ ok: true, data: { imported_count: 5 } });
    };
    assert.deepEqual(await api.post("/students/me/import", form), {
      imported_count: 5,
    });
  });
  it("retains the backend error code and request id", async () => {
    globalThis.fetch = async () =>
      Response.json(
        {
          ok: false,
          error: { code: "CONFLICT_409", message: "duplicate", details: {} },
          meta: { request_id: "req-409" },
        },
        { status: 409 },
      );
    await assert.rejects(
      api.post("/plans", {}),
      (error: unknown) =>
        error instanceof ApiError &&
        error.code === "CONFLICT_409" &&
        error.requestId === "req-409",
    );
  });
});
