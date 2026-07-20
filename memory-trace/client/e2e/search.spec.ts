import { test, expect, type Page } from "@playwright/test";

// Runs against the packaged React build served by the real `memory-trace` CLI over
// this repo's own real corpus (see playwright.config.ts) - not a mock server, not a
// synthetic fixture. "lense" is a durable search term: this session alone added the
// Track A.4 removal work referencing it dozens of times across session logs and docs,
// so the corpus will always have matches regardless of what else changes over time.

// The first request against a real corpus warms the retrieval cache from scratch
// (this repo has 600+ real session entries) before the Trail/sidebar can render
// anything to search over. Wait that out explicitly rather than racing it.
async function waitForProjectLoaded(page: Page) {
  await expect(page.getByText("Loading entries")).toHaveCount(0, { timeout: 30_000 });
  await expect(page.getByText("Loading trail")).toHaveCount(0, { timeout: 30_000 });
}

test.describe("search to strongest Trail match", () => {
  test("typing a query surfaces local title matches with a live match count", async ({ page }) => {
    await page.goto("/next");
    await waitForProjectLoaded(page);

    const search = page.getByRole("textbox", { name: "Search memory or entry ID" });
    await expect(search).toBeVisible();
    await search.fill("lense");

    const findBar = page.getByRole("status", { name: "Search matches" });
    await expect(findBar).toBeVisible();
    await expect(findBar.locator(".find-count")).toBeVisible();

    const countText = await findBar.locator(".find-count").innerText();
    const [, total] = countText.split("/");
    expect(Number(total.replace("+", ""))).toBeGreaterThan(0);
  });

  test("next/previous match navigation moves the position without changing the total", async ({ page }) => {
    await page.goto("/next");
    await waitForProjectLoaded(page);

    const search = page.getByRole("textbox", { name: "Search memory or entry ID" });
    await search.fill("lense");

    const findBar = page.getByRole("status", { name: "Search matches" });
    const countEl = findBar.locator(".find-count");
    await expect(countEl).toBeVisible();

    // Before any navigation no match is focused yet - the position shows "-", not a
    // number (matchPosition starts at -1, so `matchPosition + 1 || "-"` is falsy at 0).
    const [, startingTotal] = (await countEl.innerText()).split("/");
    const total = Number(startingTotal.replace("+", ""));
    expect(total).toBeGreaterThan(0);

    const nextButton = page.getByRole("button", { name: "Next match" });
    await expect(nextButton).toBeEnabled();
    await nextButton.click();

    const [firstPositionText, firstTotal] = (await countEl.innerText()).split("/");
    expect(firstTotal).toBe(startingTotal);
    expect(Number(firstPositionText)).toBe(1);

    await nextButton.click();
    const [secondPositionText, secondTotal] = (await countEl.innerText()).split("/");
    expect(secondTotal).toBe(startingTotal);
    // Wraps to 1 if there was only one match; otherwise advances to 2.
    expect(Number(secondPositionText)).toBe(total > 1 ? 2 : 1);

    const prevButton = page.getByRole("button", { name: "Previous match" });
    await prevButton.click();
    const [thirdPositionText] = (await countEl.innerText()).split("/");
    expect(Number(thirdPositionText)).toBe(1);
  });

  test("keyboard-only operation: Enter in the search box cycles to the next match", async ({ page }) => {
    await page.goto("/next");
    await waitForProjectLoaded(page);

    const search = page.getByRole("textbox", { name: "Search memory or entry ID" });
    await search.fill("lense");

    const findBar = page.getByRole("status", { name: "Search matches" });
    const countEl = findBar.locator(".find-count");
    await expect(countEl).toBeVisible();
    const [, total] = (await countEl.innerText()).split("/");
    expect(Number(total.replace("+", ""))).toBeGreaterThan(0);

    // No match is focused yet, so the first Enter selects match 1 (not "+1").
    await search.press("Enter");
    const [firstPositionText, firstTotal] = (await countEl.innerText()).split("/");
    expect(firstTotal).toBe(total);
    expect(Number(firstPositionText)).toBe(1);
  });
});
