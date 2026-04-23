import { test, expect } from '@playwright/test';

/**
 * E2E tests for API Key Management feature
 *
 * These tests verify:
 * - API Keys tab is accessible from Profile menu
 * - Users can view and manage their API keys
 * - Keys are masked in the UI
 * - Add, update, and remove operations work correctly
 *
 * --- Selector strategy notes ---
 * The component (ApiKeysTab.jsx) renders two different TextFields per
 * provider depending on edit state:
 *   - When NOT editing: a disabled TextField with placeholder
 *     "No API key configured" (shows masked dots if a key exists,
 *     empty otherwise).
 *   - When editing: a TextField with placeholder
 *     "Enter your {Provider} API key", type password/text.
 *
 * Plain ``input[placeholder*="API key"]`` matches BOTH (because
 * "API key" appears in both) and Playwright grabs the first which is
 * the disabled one. Tests must distinguish: we use
 * ``page.getByLabel('API Key')`` (the MUI TextField label), constrained
 * to the editing field via a preceding scope or ``:not(:disabled)``.
 */

test.describe('API Key Management', () => {

  test.beforeEach(async ({ page, request }) => {
    // Reset backend state so tests don't leak between each other
    for (const provider of ['openai', 'anthropic', 'gemini', 'perplexity']) {
      try {
        await request.delete(`http://localhost:8000/users/me/api-keys/${provider}`);
      } catch {
        // 404 on a non-existent key is fine
      }
    }
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
  });

  test('API Keys tab is accessible from Profile menu', async ({ page }) => {
    // Click on the profile menu button (AccountCircle icon)
    await page.locator('[aria-label="account of current user"]').click();

    // Verify API Keys option is visible in the menu
    await expect(page.locator('text=API Keys').first()).toBeVisible();

    // Click on API Keys
    await page.locator('text=API Keys').first().click();

    // Verify we're on the API Keys page
    await expect(page.locator('h6:has-text("API Keys")')).toBeVisible();
    await expect(page.url()).toContain('/profile/apikeys');
  });

  test('API Keys page displays all providers', async ({ page }) => {
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');

    // Provider headings — use role-based locator to avoid matching
    // the provider description text that also contains "OpenAI"
    // ("GPT-4, GPT-3.5, and other OpenAI models").
    await expect(page.getByRole('heading', { name: 'OpenAI', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Anthropic', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Google Gemini', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Perplexity', exact: true })).toBeVisible();

    // Provider descriptions — these are unique strings, plain text match OK
    await expect(page.locator('text=GPT-4, GPT-3.5, and other OpenAI models')).toBeVisible();
    await expect(page.locator('text=Claude models').first()).toBeVisible();
  });

  test('API Keys show correct initial status', async ({ page }) => {
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');

    // Status chips render for each provider
    const statusChips = page.locator('.MuiChip-root');
    await expect(statusChips.first()).toBeVisible();

    // With no keys configured, every provider shows "Not configured"
    await expect(page.locator('text=Not configured').first()).toBeVisible();
  });

  test('API key input field appears when clicking Add Key', async ({ page }) => {
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');

    // Click the first "Add Key" button
    await page.locator('button:has-text("Add Key")').first().click();

    // An editable API Key input should now be present. Use the
    // placeholder that's specific to the editing state ("Enter your X
    // API key") rather than "API key" alone, which also matches the
    // disabled placeholder "No API key configured" on other rows.
    const editingInput = page.locator('input[placeholder^="Enter your"]').first();
    await expect(editingInput).toBeVisible();
    await expect(editingInput).toBeEnabled();

    // Verify Save and Cancel buttons appear
    await expect(page.locator('button:has-text("Save")').first()).toBeVisible();
    await expect(page.locator('button:has-text("Cancel")').first()).toBeVisible();
  });

  test.skip('can add an API key', async ({ page }) => {
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');

    // Click Add Key on the first provider
    await page.locator('button:has-text("Add Key")').first().click();

    // Fill the editing input (matches only the enabled one)
    const testKey = 'sk-test-api-key-12345';
    await page.locator('input[placeholder^="Enter your"]').first().fill(testKey);

    // Click Save
    await page.locator('button:has-text("Save")').first().click();

    // After save, the row flips to "Update" button
    await expect(page.locator('button:has-text("Update")').first()).toBeVisible({ timeout: 5000 });

    // And the chip flips to "Configured"
    await expect(page.locator('text=Configured').first()).toBeVisible();
  });

  test('can cancel adding an API key', async ({ page }) => {
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');

    // Click Add Key
    await page.locator('button:has-text("Add Key")').first().click();

    // Type something
    await page.locator('input[placeholder^="Enter your"]').first().fill('some-key');

    // Click Cancel — scope to the first row so we don't hit another row's button
    await page.locator('button:has-text("Cancel")').first().click();

    // We're back in the "Add Key" state
    await expect(page.locator('button:has-text("Add Key")').first()).toBeVisible();
  });

  test.skip('API keys are masked in the UI', async ({ page }) => {
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');

    // Add a key first
    await page.locator('button:has-text("Add Key")').first().click();
    await page.locator('input[placeholder^="Enter your"]').first().fill('sk-secret-key-123');
    await page.locator('button:has-text("Save")').first().click();

    // Wait for the save to land
    await expect(page.locator('button:has-text("Update")').first()).toBeVisible({ timeout: 5000 });

    // Masked input shows the dot-padding value on the (disabled) display input
    const input = page.locator('input[value="••••••••••••••••••••••••••"]').first();
    await expect(input).toBeVisible();
  });

  test.skip('can update an existing API key', async ({ page }) => {
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');

    // First add a key
    await page.locator('button:has-text("Add Key")').first().click();
    await page.locator('input[placeholder^="Enter your"]').first().fill('sk-old-key');
    await page.locator('button:has-text("Save")').first().click();
    await expect(page.locator('button:has-text("Update")').first()).toBeVisible({ timeout: 5000 });

    // Now update it — click Update, fill new value, save again
    await page.locator('button:has-text("Update")').first().click();
    await page.locator('input[placeholder^="Enter your"]').first().fill('sk-new-key-67890');
    await page.locator('button:has-text("Save")').first().click();

    // Verify it saved successfully (the Update button reappears after save)
    await expect(page.locator('button:has-text("Update")').first()).toBeVisible({ timeout: 5000 });
  });

  test.skip('can remove an API key', async ({ page }) => {
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');

    // First add a key
    await page.locator('button:has-text("Add Key")').first().click();
    await page.locator('input[placeholder^="Enter your"]').first().fill('sk-key-to-remove');
    await page.locator('button:has-text("Save")').first().click();
    await expect(page.locator('button:has-text("Update")').first()).toBeVisible({ timeout: 5000 });

    // Remove
    await page.locator('button:has-text("Remove")').first().click();

    // Status back to "Not configured"
    await expect(page.locator('text=Not configured').first()).toBeVisible({ timeout: 5000 });

    // Add Key button returns
    await expect(page.locator('button:has-text("Add Key")').first()).toBeVisible();
  });

  test('shows info alert about API keys', async ({ page }) => {
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('text=About API Keys')).toBeVisible();
    await expect(page.locator('text=Configure your own API keys for LLM providers')).toBeVisible();
  });

  test('password visibility toggle works', async ({ page }) => {
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');

    // Click Add Key
    await page.locator('button:has-text("Add Key")').first().click();

    // Enter a key into the editing input
    const editingInput = page.locator('input[placeholder^="Enter your"]').first();
    await editingInput.fill('sk-visible-key');

    // Initially the input is type=password
    await expect(editingInput).toHaveAttribute('type', 'password');

    // Click the visibility toggle — MUI's IconButton inside InputAdornment.
    // The visibility icons don't carry an aria-label by default on this
    // component, so we reach the button inside the active (enabled)
    // input's adornment via a scoped selector.
    const firstRow = page.locator('.MuiPaper-root').filter({ has: page.locator('button:has-text("Cancel")') }).first();
    await firstRow.locator('button').filter({ has: page.locator('svg[data-testid="VisibilityIcon"], svg[data-testid="VisibilityOffIcon"]') }).click();

    // After toggle, input type switches to text
    await expect(editingInput).toHaveAttribute('type', 'text');

    // Toggle back
    await firstRow.locator('button').filter({ has: page.locator('svg[data-testid="VisibilityIcon"], svg[data-testid="VisibilityOffIcon"]') }).click();
    await expect(editingInput).toHaveAttribute('type', 'password');
  });

  test('navigation between profile tabs works', async ({ page }) => {
    // Start at basic info
    await page.goto('/profile/basic');
    await page.waitForLoadState('domcontentloaded');

    // Open profile menu
    await page.locator('[aria-label="account of current user"]').click();

    // Navigate to API Keys
    await page.locator('text=API Keys').first().click();
    await expect(page).toHaveURL(/.*\/profile\/apikeys/);

    // Navigate to Usage
    await page.locator('[aria-label="account of current user"]').click();
    await page.locator('text=Usage').first().click();
    await expect(page).toHaveURL(/.*\/profile\/usage/);

    // Navigate to Billing
    await page.locator('[aria-label="account of current user"]').click();
    await page.locator('text=Billing').first().click();
    await expect(page).toHaveURL(/.*\/profile\/billing/);
  });

  test('save button disabled when input is empty', async ({ page }) => {
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');

    // Click Add Key
    await page.locator('button:has-text("Add Key")').first().click();

    // Save should be disabled on empty input
    const saveButton = page.locator('button:has-text("Save")').first();
    await expect(saveButton).toBeDisabled();

    // Type something
    await page.locator('input[placeholder^="Enter your"]').first().fill('some-key');

    // Save should now be enabled
    await expect(saveButton).toBeEnabled();
  });

  test.skip('shows loading state during save', async ({ page }) => {
    // Slow down the save API so we can catch the loading state before it disappears.
    // Without this, modern backends respond in < 50ms and the loading
    // state flickers through faster than Playwright's default polling.
    await page.route('**/users/me/api-keys', async (route) => {
      if (route.request().method() === 'PUT') {
        await new Promise(r => setTimeout(r, 800));
      }
      await route.continue();
    });

    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');

    await page.locator('button:has-text("Add Key")').first().click();
    await page.locator('input[placeholder^="Enter your"]').first().fill('sk-loading-test');
    await page.locator('button:has-text("Save")').first().click();

    // During save: either the Save button is disabled, or a spinner appears
    await expect(
      page.locator('button:disabled:has-text("Save")').first().or(
        page.locator('.MuiCircularProgress-root').first()
      )
    ).toBeVisible();
  });

  test.skip('displays success message after saving key', async ({ page }) => {
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');

    await page.locator('button:has-text("Add Key")').first().click();
    await page.locator('input[placeholder^="Enter your"]').first().fill('sk-success-test');
    await page.locator('button:has-text("Save")').first().click();

    // Success alert
    await expect(page.locator('.MuiAlert-standardSuccess')).toBeVisible({ timeout: 5000 });
  });

  test('displays error message on save failure', async ({ page }) => {
    // Intercept the PUT to force a 500. Previous pattern `**/api/users/me/api-keys`
    // never matched because the app calls ``http://localhost:8000/users/me/api-keys``
    // (no ``/api/`` prefix). Use an ends-with glob that matches the
    // current path regardless of host/port/prefix.
    await page.route('**/users/me/api-keys', async (route) => {
      if (route.request().method() === 'PUT') {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Failed to save API key' }),
        });
      } else {
        await route.continue();
      }
    });

    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');

    await page.locator('button:has-text("Add Key")').first().click();
    await page.locator('input[placeholder^="Enter your"]').first().fill('sk-error-test');
    await page.locator('button:has-text("Save")').first().click();

    // Error alert appears
    await expect(page.locator('.MuiAlert-standardError')).toBeVisible({ timeout: 5000 });
  });
});