import { defineConfig, devices } from "@playwright/test";
import path from "path";

const STORAGE_STATE = path.resolve("./tests/e2e/.auth/storageState.json");

/**
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  webServer: {
    command: "pnpm run dev -- --port 3000",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
  testDir: "./tests/e2e",
  // Runs once before any project. Writes a storageState file with a
  // logged-in mock user; every project picks it up via ``use.storageState``.
  globalSetup: "./tests/e2e/global-setup.js",
  /* Run tests in files in parallel */
  fullyParallel: false,
  workers: 1,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI. */
  /* Reporter to use. See https://playwright.dev/docs/api/class-testoptions#testoptions-reporter */
  reporter: "html",
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: "http://localhost:3000",

    // Every test starts with this storage state loaded. globalSetup
    // writes it once at the start of the run; individual tests can
    // override by passing a different storageState to ``test.use``.
    storageState: STORAGE_STATE,

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: "on-first-retry",
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
