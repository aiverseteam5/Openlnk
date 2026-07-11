/**
 * Playwright config — smoke tests for web-owner and web-thread.
 *
 * CLAUDE.md: Playwright (web-owner, web-thread) in CI testing pyramid.
 * Runs against Vite preview servers.
 */

import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 15_000,
  retries: 0,
  use: {
    headless: true,
  },
  projects: [
    {
      name: "web-owner",
      testMatch: "web-owner.spec.ts",
      use: { baseURL: "http://localhost:4173" },
    },
    {
      name: "web-thread",
      testMatch: "web-thread.spec.ts",
      use: { baseURL: "http://localhost:4174" },
    },
  ],
  webServer: [
    {
      command: "pnpm --filter web-owner preview --port 4173",
      port: 4173,
      reuseExistingServer: true,
    },
    {
      command: "pnpm --filter web-thread preview --port 4174",
      port: 4174,
      reuseExistingServer: true,
    },
  ],
});
