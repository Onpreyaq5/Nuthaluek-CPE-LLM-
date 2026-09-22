import { it } from "node:test";
import assert from "node:assert/strict";
import { placement } from "./Timetable";
it("places half-hour meetings and the 20:00 boundary without spilling outside the grid", () => {
  assert.deepEqual(placement("08:00", "08:30"), {
    top: 0,
    height: (30 / 720) * 100,
  });
  const last = placement("19:30", "20:00");
  assert.ok(Math.abs(last.top + last.height - 100) < 1e-10);
});
