import assert from "node:assert/strict";
import test from "node:test";
import { decisionSections, evidenceAnchor, readerInformationState, relationshipsForDecision, selectedDecision } from "./decisionReaderModel.ts";

const MULTI_DECISION = `## 2026-07-30 10:00 - Example

#### D1 - Preserve Markdown authority
- D: Read entries without a second record.
- R: Source text stays inspectable.

#### D2 - Keep evidence exact
- D: Link file and line anchors.
- R: A generated summary is not evidence.

### Validation
- T: Reader fixture passes.`;

test("models each numbered decision without swallowing following entry sections", () => {
  const sections = decisionSections(MULTI_DECISION);
  assert.deepEqual(sections.map((section) => [section.ordinal, section.title]), [["d1", "Preserve Markdown authority"], ["d2", "Keep evidence exact"]]);
  assert.match(sections[1].text, /generated summary/);
  assert.doesNotMatch(sections[1].text, /Reader fixture/);
});

test("selects the exact Trail decision heading and falls back to the first recorded decision", () => {
  const sections = decisionSections(MULTI_DECISION);
  assert.equal(selectedDecision(sections, "D2 - Keep evidence exact")?.ordinal, "d2");
  assert.equal(selectedDecision(sections, "missing heading")?.ordinal, "d1");
});

test("models a regular one-decision entry and retains its authored D statement", () => {
  const sections = decisionSections("### Decision\n\n- D: Keep the entry as context.\n\n### Validation\n- T: Pass.");
  assert.equal(sections.length, 1);
  assert.equal(sections[0].title, "Keep the entry as context.");
  assert.equal(sections[0].text, "- D: Keep the entry as context.");
});

test("never manufactures evidence when a source anchor is absent", () => {
  assert.deepEqual(evidenceAnchor(null, []), { available: false, label: "Missing canonical source anchor", source: null });
  assert.deepEqual(evidenceAnchor(".memory-seed/sessions/2026-07/2026-07-30.md", [18, 30]), {
    available: true,
    label: "Recorded source · .memory-seed/sessions/2026-07/2026-07-30.md:18-30",
    source: ".memory-seed/sessions/2026-07/2026-07-30.md",
  });
});

test("names derived and suggested records instead of styling them as recorded", () => {
  assert.equal(readerInformationState("authored", "source_control"), "Derived");
  assert.equal(readerInformationState("generated", "generated_artefact"), "Suggested");
  assert.equal(readerInformationState("authored", "authored_memory"), "Recorded");
});

test("a superseding decision exposes only its own typed lifecycle edge", () => {
  const active = "mse_new#decisions/d2-keep-evidence-exact";
  assert.deepEqual(relationshipsForDecision([
    { source: active, target: "mse_old#decisions/d1-use-summary", type: "replaces" },
    { source: "mse_new#decisions/d1-keep-context", target: "mse_other", type: "related" },
  ], active, "mse_new"), [{
    kind: "replaces",
    entryId: "mse_old",
    otherId: "mse_old#decisions/d1-use-summary",
    outgoing: true,
  }]);
});
