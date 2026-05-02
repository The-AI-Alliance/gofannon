// webapp/tests/e2e/global-setup.js
//
// Playwright global setup: walks the dev_stub login flow once at the
// start of the run, captures the resulting session cookie via
// storageState, and saves it for every test to inherit.
//
// Why this approach vs. per-test login:
//   - Login is multiple redirects + a server-rendered picker page.
//     Doing it once amortizes the cost across the whole suite.
//   - Per-test login steps couple every test file to the login UI.
//     Changing how login works would break all tests at once; this
//     decouples them.
//
// NB: this requires the dev_stub provider to be enabled in the
// running backend (default in dev). For E2E against a deployment
// using real OAuth providers, replace this file with one that
// performs the appropriate sign-in.

const { chromium } = require('@playwright/test');
const path = require('path');
const fs = require('fs');

const STORAGE_STATE_PATH = path.join(__dirname, '.auth', 'storageState.json');
const API_BASE = process.env.E2E_API_BASE || 'http://localhost:8000';
const STUB_USER = process.env.E2E_STUB_USER || 'alice';

async function globalSetup(config) {
  const baseURL = config.projects?.[0]?.use?.baseURL
    || config.use?.baseURL
    || 'http://localhost:3000';

  fs.mkdirSync(path.dirname(STORAGE_STATE_PATH), { recursive: true });

  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  // Walk the dev_stub login flow:
  //   1. GET /auth/login/dev_stub  → 302 → /auth/dev-stub-picker
  //      Sets gofannon_auth_state cookie for CSRF.
  //   2. Picker page renders one <a> per configured user. The link's
  //      href encodes the uid as ?code=<uid>&state=<token>.
  //   3. Clicking the alice link hits /auth/callback/dev_stub which
  //      validates state, creates a session, sets gofannon_sid cookie,
  //      and 302s to return_to.
  await page.goto(
    `${API_BASE}/auth/login/dev_stub?return_to=${encodeURIComponent(baseURL + '/')}`
  );
  // Picker uses <a> elements, not <button>s. Match the link by its
  // href containing code=<uid> — most robust against text/styling
  // changes.
  await page.locator(`a[href*="code=${STUB_USER}"]`).click();
  await page.waitForURL(`${baseURL}/`, { timeout: 10000 });

  // Sanity-check we actually got authenticated. If /auth/me returns
  // 401 the storageState would be useless and the failure mode
  // downstream is confusing ("AccountCircle not found, timeout").
  const meResp = await page.request.get(`${API_BASE}/auth/me`);
  if (!meResp.ok()) {
    throw new Error(
      `globalSetup: /auth/me returned ${meResp.status()} after dev_stub login. ` +
      `Verify dev_stub is enabled in the backend's auth config and ${API_BASE} ` +
      `is reachable from the test runner.`
    );
  }

  await context.storageState({ path: STORAGE_STATE_PATH });
  await browser.close();
}

module.exports = globalSetup;
module.exports.STORAGE_STATE_PATH = STORAGE_STATE_PATH;