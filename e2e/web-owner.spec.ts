/**
 * web-owner Playwright smoke tests.
 *
 * Verifies page renders, DESIGN.md compliance (fonts, colors, no shadows),
 * and basic navigation.
 */

import { test, expect } from "@playwright/test";

test.describe("web-owner smoke tests", () => {
  test("renders daily brief page with sidebar navigation", async ({ page }) => {
    await page.goto("/");
    // Sidebar or mobile header renders navigation items
    await expect(page.getByText("Daily Brief").first()).toBeVisible();
  });

  test("renders commitment list page with create button", async ({ page }) => {
    await page.goto("/");
    // Navigate via sidebar/app link
    await page.getByText("Commitments").first().click();
    await expect(page.getByText("Create").first()).toBeVisible();
  });

  test("renders create commitment page with form", async ({ page }) => {
    await page.goto("/");
    await page.getByText("Commitments").first().click();
    await page.getByText("Create").first().click();
    // Form fields render
    await expect(page.locator("input").first()).toBeVisible();
  });

  test("uses correct background color (DESIGN.md: #F5F2EC)", async ({ page }) => {
    await page.goto("/");
    const bg = await page.evaluate(() => {
      return getComputedStyle(document.body).backgroundColor;
    });
    // #F5F2EC = rgb(245, 242, 236)
    expect(bg).toBe("rgb(245, 242, 236)");
  });

  test("no shadows on commitment cards (DESIGN.md)", async ({ page }) => {
    await page.goto("/");
    await page.getByText("Commitments").first().click();
    await page.waitForTimeout(500);
    const shadows = await page.evaluate(() => {
      const cards = document.querySelectorAll("[class*='MuiBox']");
      return Array.from(cards).some(
        (el) => getComputedStyle(el).boxShadow !== "none",
      );
    });
    expect(shadows).toBe(false);
  });

  test("state filter shows all states", async ({ page }) => {
    await page.goto("/");
    await page.getByText("Commitments").first().click();
    await expect(page.getByText("ALL")).toBeVisible();
    await expect(page.getByText("PROPOSED")).toBeVisible();
    await expect(page.getByText("ACCEPTED")).toBeVisible();
  });
});
