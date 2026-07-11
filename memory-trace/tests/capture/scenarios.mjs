// Named interaction scenarios for the Memory Trace recording harness.
// Each scenario is (page, baseUrl) -> Promise<void>: drive real UI actions,
// no test assertions - the recording IS the artifact. Keep scenarios short
// (roughly 5-10s of action) so exported GIFs stay embeddable in docs.
//
// Add a scenario by exporting a new entry in SCENARIOS; capture.mjs looks
// nothing up beyond this file, so no other wiring is needed.

const settle = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function waitForTrailRows(page) {
  await page.waitForSelector(".trail-row", { timeout: 20000 });
  await settle(300); // let the SVG rail finish drawing alongside the rows
}

export const SCENARIOS = {
  // Trail's two-stage selection: resting -> selected (saturated routes,
  // reader opens) -> second click (muted/pinned) -> third click (restored).
  async "trail-selection-lifecycle"(page, baseUrl) {
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await waitForTrailRows(page);
    await settle(600);

    const row = page.locator(".trail-row").nth(3);
    await row.click();
    await page.waitForSelector(".detail-header h2", { timeout: 10000 });
    await settle(900);

    await page.locator(".trail-row.selected").click(); // second click: mute
    await settle(900);

    await page.locator(".trail-row.pinned").click(); // third click: restore
    await settle(700);
  },

  // Search as a function over the current view: type a query, watch the
  // ranked dropdown and in-place match markers appear, cycle with Enter,
  // then clear back to resting state.
  async "search-as-function"(page, baseUrl) {
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await waitForTrailRows(page);
    await settle(500);

    await page.click("#query");
    await page.type("#query", "trail lane", { delay: 45 });
    await page.waitForSelector(".search-dropdown", { timeout: 10000 });
    await settle(900);

    await page.keyboard.press("Enter"); // jump to the first match
    await settle(700);
    await page.click("#query");
    await page.keyboard.press("Enter"); // cycle to the next match
    await settle(700);

    await page.click("[data-search-clear]");
    await settle(600);
  },

  // Graph exploration: switch tabs, hover a node (neighbourhood highlight),
  // then select it.
  async "graph-explore"(page, baseUrl) {
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await waitForTrailRows(page);
    await page.click('.tab[data-view="graph"]');
    await page.waitForSelector(".graph-node", { timeout: 20000 });
    await settle(700);

    // The force layout scatters nodes across the whole canvas, so a fixed
    // index can land under the sidebar's left edge (a real overlap, not a
    // bug - just wrong for a click target). Pick the first node whose
    // bounding box sits clearly clear of the sidebar.
    const nodes = page.locator(".graph-node");
    const count = await nodes.count();
    let target = null;
    for (let i = 0; i < count; i += 1) {
      const candidate = nodes.nth(i);
      const box = await candidate.boundingBox();
      if (box && box.x > 320) {
        target = { locator: candidate, box };
        break;
      }
    }
    if (target) {
      await page.mouse.move(target.box.x + target.box.width / 2, target.box.y + target.box.height / 2);
      await settle(900);
      await target.locator.click();
      await page.waitForSelector(".detail-header h2", { timeout: 10000 });
      await settle(700);
    }
  },
};
