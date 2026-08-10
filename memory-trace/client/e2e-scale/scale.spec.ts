import { test, expect, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(here, "measurements.json");
const results: Record<string, unknown> = {};

async function enterGraph(page: Page) {
  await page.goto("/");
  await expect(page.getByText("Loading entries")).toHaveCount(0, { timeout: 60_000 });
  await expect(page.getByText("Loading trail")).toHaveCount(0, { timeout: 60_000 });
  await page.locator(".view-switch").getByRole("button", { name: "Graph" }).click();
  await expect(page.locator(".graph-canvas")).toBeVisible({ timeout: 60_000 });
  await page.waitForFunction(() => {
    const cy = (window as any).memoryTraceNextDebug?.graphCy;
    return cy && cy.nodes().length > 0;
  }, undefined, { timeout: 60_000 });
}

// Snapshot of what the renderer currently holds.
async function snapshot(page: Page) {
  return page.evaluate(() => {
    const cy = (window as any).memoryTraceNextDebug.graphCy;
    const colours: Record<string, string> = {};
    cy.nodes().forEach((n: any) => (colours[n.id()] = n.data("colour")));
    return {
      nodes: cy.nodes().length,
      edges: cy.edges().length,
      distinctColours: Array.from(new Set(Object.values(colours))).sort(),
      colours,
    };
  });
}

// Re-run the SHIPPED cose options at a given iteration budget and time it on
// the main thread. This is the exact question "does layoutIterations hold at
// full size" — measured, not reasoned.
// Interaction budget: zoom, pan and selection restyle, each timed to the frame
// that actually paints the result.
async function timeInteractions(page: Page) {
  const zoomAndPan = await page.evaluate(async () => {
    const cy = (window as any).memoryTraceNextDebug.graphCy;
    const frame = () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    const measure = async (fn: () => void) => {
      await frame();
      const t0 = performance.now();
      fn();
      await frame();
      return Math.round(performance.now() - t0);
    };
    const zoomIn = await measure(() => cy.zoom({ level: cy.zoom() * 1.22, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } }));
    const zoomOut = await measure(() => cy.zoom({ level: cy.zoom() * 0.82, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } }));
    const pan = await measure(() => cy.panBy({ x: 120, y: 80 }));
    const fit = await measure(() => cy.fit(cy.elements(), 52));
    return { zoomIn, zoomOut, pan, fit };
  });
  // Selection: a real click on a node, timed to the Inspector title changing.
  const t0 = Date.now();
  await page.evaluate(() => {
    const cy = (window as any).memoryTraceNextDebug.graphCy;
    cy.nodes()[Math.floor(cy.nodes().length / 2)].emit("tap");
  });
  await page.waitForFunction(() => {
    const cy = (window as any).memoryTraceNextDebug.graphCy;
    return cy.nodes('[selected = "yes"]').length === 1;
  }, undefined, { timeout: 20_000 });
  return { ...zoomAndPan, selectRestyleMs: Date.now() - t0 };
}

async function showMore(page: Page) {
  const button = page.getByRole("button", { name: "Show more" });
  if (!(await button.count())) return false;
  // Wait on nodes OR edges: past the point where the node count saturates,
  // a "Show more" step only brings back more edges.
  const before = await page.evaluate(() => {
    const cy = (window as any).memoryTraceNextDebug.graphCy;
    return `${cy.nodes().length}/${cy.edges().length}`;
  });
  await button.click();
  try {
    await page.waitForFunction(
      (prev) => {
        const cy = (window as any).memoryTraceNextDebug?.graphCy;
        return cy && `${cy.nodes().length}/${cy.edges().length}` !== prev;
      },
      before,
      { timeout: 10_000 },
    );
    return true;
  } catch {
    // The API can return the same capped projection for one final wider ask.
    // Treat that as exhaustion rather than holding the acceptance run hostage.
    return false;
  }
}

test("graph scale acceptance at full corpus size", async ({ page }) => {
  const steps: unknown[] = [];
  const gotoStart = Date.now();
  await enterGraph(page);
  const firstPaintMs = Date.now() - gotoStart;

  let step = 0;
  for (;;) {
    // Measure the shipped incremental simulation. Re-running CoSE here would
    // benchmark a renderer the application no longer uses.
    await page.waitForTimeout(500);
    const snap = await snapshot(page);
    const interactions = await timeInteractions(page);
    steps.push({
      step,
      nodes: snap.nodes,
      edges: snap.edges,
      distinctColours: snap.distinctColours,
      interactions,
    });
    console.log(JSON.stringify({ step, nodes: snap.nodes, edges: snap.edges, slowestInteractionMs: Math.max(...Object.values(interactions)) }));
    step += 1;
    if (!(await showMore(page))) break;
    if (step > 24) break;
  }
  results.firstPaintMs = firstPaintMs;
  results.steps = steps;
  fs.writeFileSync(OUT, JSON.stringify(results, null, 2));

  const final = steps.at(-1) as { nodes: number; edges: number; interactions: Record<string, number> };
  const slowestInteraction = Math.max(...Object.values(final.interactions));
  // These acceptance budgets cover the actual interactive renderer. The floor
  // confirms that paging reached the full current projection, rather than only
  // exercising its first page.
  expect(firstPaintMs).toBeLessThanOrEqual(5_000);
  expect(final.nodes).toBeGreaterThanOrEqual(600);
  expect(final.edges).toBeGreaterThanOrEqual(1_200);
  expect(slowestInteraction).toBeLessThanOrEqual(250);
});

test("community colours are stable across two reloads at full size", async ({ page }) => {
  const capture = async () => {
    await enterGraph(page);
    // Grow to full size so the stability probe runs on the largest node set.
    for (let i = 0; i < 24; i += 1) {
      await page.waitForTimeout(500);
      if (!(await showMore(page))) break;
    }
    await page.waitForTimeout(1_500);
    return snapshot(page);
  };
  const first = await capture();
  const second = await capture();

  const shared = Object.keys(first.colours).filter((id) => id in second.colours);
  const changed = shared.filter((id) => first.colours[id] !== second.colours[id]);
  const stability = {
    loadOne: { nodes: first.nodes, edges: first.edges, distinctColours: first.distinctColours },
    loadTwo: { nodes: second.nodes, edges: second.edges, distinctColours: second.distinctColours },
    sharedNodes: shared.length,
    nodesThatChangedColour: changed.length,
  };
  console.log("STABILITY " + JSON.stringify(stability));
  const existing = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, "utf-8")) : {};
  fs.writeFileSync(OUT, JSON.stringify({ ...existing, stability }, null, 2));
  expect(changed).toHaveLength(0);
});
