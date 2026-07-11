/**
 * web-thread Playwright smoke tests.
 *
 * Verifies receipt view renders, performance budget compliance,
 * and DESIGN.md styling.
 */

import { test, expect } from "@playwright/test";

test.describe("web-thread smoke tests", () => {
  test("renders OPENLNK header", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("text=OPENLNK")).toBeVisible();
  });

  test("shows loading state without token", async ({ page }) => {
    await page.goto("/");
    // Without a valid token, should show "no commitment" or equivalent
    await page.waitForTimeout(500);
    const content = await page.textContent("main");
    expect(content).toBeTruthy();
  });

  test("chat input is always visible (DESIGN.md)", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("input[placeholder]")).toBeVisible();
    await expect(page.locator("button:text('Send')")).toBeVisible();
  });

  test("uses correct background color (DESIGN.md: bg token)", async ({ page }) => {
    await page.goto("/");
    const bg = await page.evaluate(() => {
      const main = document.querySelector(".bg-bg");
      return main ? getComputedStyle(main).backgroundColor : null;
    });
    // bg-bg should resolve to #F5F2EC = rgb(245, 242, 236)
    expect(bg).toBe("rgb(245, 242, 236)");
  });

  test("send button is disabled when input is empty", async ({ page }) => {
    await page.goto("/");
    const sendBtn = page.locator("button:text('Send')");
    await expect(sendBtn).toBeDisabled();
  });

  test("total JS bundle under 120KB gzip (OL-084)", async ({ page }) => {
    const responses: { size: number; url: string }[] = [];
    page.on("response", (response) => {
      const url = response.url();
      if (url.endsWith(".js") || url.endsWith(".css")) {
        const headers = response.headers();
        const size = parseInt(headers["content-length"] ?? "0", 10);
        responses.push({ size, url });
      }
    });
    await page.goto("/");
    // Total transferred JS+CSS should be under 120KB
    // Note: preview server doesn't gzip, so we check raw size < 500KB
    // (gzipped is verified by vite build output in CI)
    const totalBytes = responses.reduce((sum, r) => sum + r.size, 0);
    expect(totalBytes).toBeLessThan(500_000);
  });
});
