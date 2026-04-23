// webapp/tests/e2e/global-setup.js
//
// Playwright global setup: writes a single storageState file that every
// test inherits, containing a logged-in mock user in localStorage.
//
// Why this approach vs. per-test login:
//   - The mock authService in webui reads from localStorage on mount
//     (``getCurrentUser`` → ``localStorage.getItem('user')``). Seeding
//     the key makes ``AuthContext`` see a user on the very first render,
//     so routes stay mounted and tests can start interacting immediately.
//   - Per-test login steps couple every test file to the login UI.
//     Changing how login works would break all tests at once; this
//     decouples them.
//
// NB: this only works against the dev-mode ``mock`` auth provider. When
// running E2E against a real Firebase or session-auth backend, replace
// this file with one that performs a real sign-in and saves the resulting
// cookie/token via ``context.storageState({path: ...})``.

const { chromium } = require('@playwright/test');
const path = require('path');
const fs = require('fs');

const STORAGE_STATE_PATH = path.join(__dirname, '.auth', 'storageState.json');

async function globalSetup(config) {
  // The config passes ``use.baseURL`` through to us. Fall back to 3001
  // since that's what the webServer config spawns.
  const baseURL = config.projects?.[0]?.use?.baseURL
    || config.use?.baseURL
    || 'http://localhost:3001';

  fs.mkdirSync(path.dirname(STORAGE_STATE_PATH), { recursive: true });

  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  // Visit the app once so the origin exists in storage state (localStorage
  // is partitioned by origin; Playwright won't save localStorage for an
  // origin it hasn't visited).
  await page.goto(baseURL);
  // Seed the mock user. Matches the shape ``mockAuth.getCurrentUser``
  // expects: ``{uid, email}`` at minimum.
  await page.evaluate(() => {
    window.localStorage.setItem('user', JSON.stringify({
      uid: 'e2e-test-user',
      email: 'e2e@gofannon.local',
    }));
  });

  await context.storageState({ path: STORAGE_STATE_PATH });
  await browser.close();
}

module.exports = globalSetup;
module.exports.STORAGE_STATE_PATH = STORAGE_STATE_PATH;
