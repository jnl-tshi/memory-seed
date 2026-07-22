import assert from "node:assert/strict";
import test from "node:test";

// Pure config mapping, so these run without a DOM: the palette reader is
// injected. That is the reason readPaletteToken is a separate export rather
// than being called inside mermaidConfig.
import { mermaidConfig, mermaidThemeVariables } from "./mermaidConfig.ts";

/** Stands in for getComputedStyle over :root. */
const reader = (values: Record<string, string>) => (token: string) => values[token] ?? "";

test("the Drawn/Slick setting selects Mermaid's look", () => {
  assert.equal(mermaidConfig("hand", reader({})).look, "handDrawn");
  assert.equal(mermaidConfig("slick", reader({})).look, "classic");
});

test("the theme is always base, the only one that honours themeVariables", () => {
  // Guards the binding itself: a named theme would silently ignore every
  // palette value below and diagrams would render in stock Mermaid colours.
  assert.equal(mermaidConfig("hand", reader({})).theme, "base");
  assert.equal(mermaidConfig("slick", reader({})).theme, "base");
});

test("palette tokens are read from CSS rather than duplicated in TypeScript", () => {
  const vars = mermaidThemeVariables(
    reader({ "--chip": "#e7dec9", "--text": "#383023", "--muted": "#70624d" }),
  );
  assert.equal(vars.primaryColor, "#e7dec9");
  assert.equal(vars.mainBkg, "#e7dec9");
  assert.equal(vars.textColor, "#383023");
  assert.equal(vars.lineColor, "#70624d");
});

test("a dark palette flows through unchanged, so polarity is the tokens' job", () => {
  const vars = mermaidThemeVariables(reader({ "--chip": "#18211d", "--text": "#d8e0dc" }));
  assert.equal(vars.primaryColor, "#18211d");
  assert.equal(vars.textColor, "#d8e0dc");
});

test("subgraph containers are styled, not left to Mermaid's defaults", () => {
  // Restoring subgraph grouping is why this renderer swap exists; an unstyled
  // cluster would land a stock grey box in the middle of the warm palette.
  const vars = mermaidThemeVariables(reader({ "--bar": "#eae2d0", "--border-2": "#ccbd9f" }));
  assert.equal(vars.clusterBkg, "#eae2d0");
  assert.equal(vars.clusterBorder, "#ccbd9f");
});

test("missing tokens fall back to a literal rather than emitting empty strings", () => {
  // Mermaid rejects "" and would fail the whole render, so an unreadable
  // palette must degrade to a usable diagram, not to no diagram.
  const vars = mermaidThemeVariables(reader({}));
  for (const [name, value] of Object.entries(vars)) {
    assert.notEqual(value, "", `${name} must never be empty`);
  }
});

test("strict sanitising is pinned, since innerHTML gave up JSX's escaping", () => {
  // Deliberately asserts ONLY securityLevel. An earlier version of this test
  // also pinned `flowchart.htmlLabels === false`, which passed while being
  // false in practice: it asserted this module's own output rather than
  // Mermaid's behaviour, and Mermaid 11 ignores that flag (verified live -
  // one foreignObject per node). A test that can only confirm what the code
  // already says is not a test of the property it appears to guard.
  const config = mermaidConfig("hand", reader({}));
  assert.equal(config.securityLevel, "strict");
});
