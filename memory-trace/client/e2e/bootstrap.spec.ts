import { test, expect, type Page } from "@playwright/test";

// Startup network discipline for the lazy-bootstrap contract:
// - Trail is the default view, so the initial load must NOT request the graph
//   projection at all - Graph data is fetched on first entry to Graph view;
// - the full-corpus Trail/index payload is fetched exactly once (it serves
//   both the timeline and every cross-corpus lookup), not once per consumer;
// - switching to Graph view fetches the projection once, preserves the
//   current selection, and switching back and forth does not refetch.
// Runs against the packaged React build over this repo's real corpus.

function recordApiRequests(page: Page) {
  const requests: string[] = [];
  page.on("request", (request) => {
    const url = request.url();
    if (url.includes("/api/v1/")) requests.push(url);
  });
  return requests;
}

async function waitForProjectLoaded(page: Page) {
  await expect(page.getByText("Loading entries")).toHaveCount(0, { timeout: 30_000 });
  await expect(page.getByText("Loading trail")).toHaveCount(0, { timeout: 30_000 });
}

const isProjection = (url: string) => url.includes("/graph/projection");
// A Trail-row click resolves its Inspector data through a small entry-scoped
// projection request (entry_id=...); the Graph WORKSPACE fetch is the
// unscoped one. Only the latter is the lazy-bootstrap budget under test.
const isWorkspaceProjection = (url: string) => isProjection(url) && !url.includes("entry_id=");
const isFullTrail = (url: string) => url.includes("/trail") && !url.includes("topic=");

test.describe("lazy bootstrap", () => {
  test("initial Trail load requests no graph projection and one full trail index", async ({ page }) => {
    const requests = recordApiRequests(page);
    await page.goto("/next");
    await waitForProjectLoaded(page);
    // Let any stray post-paint fetches land before counting.
    await page.waitForTimeout(1_000);

    expect(requests.filter(isProjection)).toHaveLength(0);
    expect(requests.filter(isFullTrail)).toHaveLength(1);
  });

  test("entering Graph view fetches the projection once and preserves the selection", async ({ page }) => {
    const requests = recordApiRequests(page);
    await page.goto("/next");
    await waitForProjectLoaded(page);

    // Select a Trail row so there is a selection to preserve.
    const firstRow = page.locator(".trail-row").first();
    await firstRow.click();
    const inspectorTitle = page.locator(".inspector h2");
    await expect(inspectorTitle).not.toHaveText("No entry selected", { timeout: 15_000 });
    const selectedTitle = await inspectorTitle.innerText();

    const viewSwitch = page.locator(".view-switch");
    await viewSwitch.getByRole("button", { name: "Graph" }).click();
    await expect(page.locator(".graph-canvas")).toBeVisible({ timeout: 30_000 });
    await page.waitForTimeout(500);
    expect(requests.filter(isWorkspaceProjection)).toHaveLength(1);

    // The selection (and with it the Inspector) survives the view switch.
    await expect(inspectorTitle).toHaveText(selectedTitle);

    // Trail -> Graph again: data is already loaded, no refetch.
    await viewSwitch.getByRole("button", { name: "Trail" }).click();
    await viewSwitch.getByRole("button", { name: "Graph" }).click();
    await page.waitForTimeout(500);
    expect(requests.filter(isWorkspaceProjection)).toHaveLength(1);
    expect(requests.filter(isFullTrail)).toHaveLength(1);
  });
});
