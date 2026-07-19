import assert from "node:assert/strict";
import test from "node:test";
import { READER_SCROLL_MARGIN, readerScrollTarget } from "./inspectorScroll.ts";

// (elementTop, scrollTop, viewportHeight, maxScroll)
test("a section below the fold scrolls down to just under the top edge", () => {
  assert.equal(readerScrollTarget(900, 0, 400, 2000), 900 - READER_SCROLL_MARGIN);
});

test("a section above the current position scrolls back up", () => {
  assert.equal(readerScrollTarget(200, 800, 400, 2000), 200 - READER_SCROLL_MARGIN);
});

test("a section already anchored does not move", () => {
  const anchored = 600 - READER_SCROLL_MARGIN;
  assert.equal(readerScrollTarget(600, anchored, 400, 2000), null);
});

test("the target clamps to the top of the document", () => {
  // A section within the margin of the top would otherwise ask for a negative
  // scrollTop; from a scrolled position that still means "go to the top".
  assert.equal(readerScrollTarget(10, 300, 400, 2000), 0);
  // ...and from the top itself there is nothing to do.
  assert.equal(readerScrollTarget(10, 0, 400, 2000), null);
});

test("the target clamps to the bottom of the document", () => {
  assert.equal(readerScrollTarget(1900, 0, 400, 1000), 1000);
});

test("a zero-height viewport yields no target", () => {
  // The pane can be measured before layout settles; scrolling on those numbers
  // would jump to a position computed from a viewport that does not exist yet.
  assert.equal(readerScrollTarget(900, 0, 0, 2000), null);
});

test("a negative maxScroll is treated as an unscrollable pane", () => {
  // scrollHeight - clientHeight goes negative when the content is shorter than
  // the container, which is common for a one-decision entry.
  assert.equal(readerScrollTarget(900, 0, 400, -50), null);
});
