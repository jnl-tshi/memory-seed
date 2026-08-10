import { test, expect, type Page } from "@playwright/test";

async function waitForProjectLoaded(page: Page) {
  await expect(page.getByText("Loading entries")).toHaveCount(0, { timeout: 30_000 });
  await expect(page.getByText("Loading trail")).toHaveCount(0, { timeout: 30_000 });
}

test.describe("accessible next-generation workflows", () => {
  test("folder modal restores focus to its opener", async ({ page }) => {
    await page.goto("/");
    await waitForProjectLoaded(page);

    const opener = page.getByRole("button", { name: "Open folder" });
    await opener.focus();
    await page.keyboard.press("Enter");

    const dialog = page.getByRole("dialog", { name: "Open folder" });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("button", { name: "Close open folder" })).toBeFocused();

    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(opener).toBeFocused();
  });

  test("graph list alternative is keyboard selectable and updates the inspector", async ({ page }) => {
    await page.goto("/");
    await waitForProjectLoaded(page);
    await page.locator(".view-switch").getByRole("button", { name: "Graph" }).click();
    await expect(page.locator(".graph-canvas")).toBeVisible({ timeout: 30_000 });

    await page.getByRole("button", { name: "Show graph list" }).click();
    const list = page.getByRole("region", { name: "Graph entries list" });
    await expect(list).toBeVisible();

    const entry = list.getByRole("button").first();
    await entry.focus();
    await expect(entry).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.locator(".inspector h2")).not.toHaveText("No entry selected", { timeout: 15_000 });
  });
});
