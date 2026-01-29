import { test, expect } from '@playwright/test';

/**
 * E2E tests for API Key Management feature
 * 
 * These tests verify:
 * - API Keys tab is accessible from Profile menu
 * - Users can view and manage their API keys
 * - Keys are masked in the UI
 * - Add, update, and remove operations work correctly
 */

test.describe('API Key Management', () => {
  
  test.beforeEach(async ({ page }) => {
    // Navigate to the app and login (assuming local dev mode)
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
  });

  test('API Keys tab is accessible from Profile menu', async ({ page }) => {
    // Click on the profile menu button (AccountCircle icon)
    await page.locator('[aria-label="account of current user"]').click();
    
    // Verify API Keys option is visible in the menu
    await expect(page.locator('text=API Keys')).toBeVisible();
    
    // Click on API Keys
    await page.locator('text=API Keys').click();
    
    // Verify we're on the API Keys page
    await expect(page.locator('h6:has-text("API Keys")')).toBeVisible();
    await expect(page.url()).toContain('/profile/apikeys');
  });

  test('API Keys page displays all providers', async ({ page }) => {
    // Navigate directly to API Keys page
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');
    
    // Verify all provider sections are displayed
    await expect(page.locator('text=OpenAI')).toBeVisible();
    await expect(page.locator('text=Anthropic')).toBeVisible();
    await expect(page.locator('text=Google Gemini')).toBeVisible();
    await expect(page.locator('text=Perplexity')).toBeVisible();
    
    // Verify provider descriptions are shown
    await expect(page.locator('text=GPT-4, GPT-3.5, and other OpenAI models')).toBeVisible();
    await expect(page.locator('text=Claude models')).toBeVisible();
  });

  test('API Keys show correct initial status', async ({ page }) => {
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');
    
    // Check that status chips are visible for each provider
    const statusChips = page.locator('.MuiChip-root');
    await expect(statusChips.first()).toBeVisible();
    
    // At least one provider should show "Not configured" initially
    await expect(page.locator('text=Not configured').first()).toBeVisible();
  });

  test('API key input field appears when clicking Add Key', async ({ page }) => {
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');
    
    // Find the first "Add Key" button and click it
    const addKeyButton = page.locator('button:has-text("Add Key")').first();
    await addKeyButton.click();
    
    // Verify the API key input field appears
    const apiKeyInput = page.locator('input[placeholder*="API key"]').first();
    await expect(apiKeyInput).toBeVisible();
    
    // Verify Save and Cancel buttons appear
    await expect(page.locator('button:has-text("Save")').first()).toBeVisible();
    await expect(page.locator('button:has-text("Cancel")').first()).toBeVisible();
  });

  test('can add an API key', async ({ page }) => {
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');
    
    // Click Add Key on the first provider
    await page.locator('button:has-text("Add Key")').first().click();
    
    // Enter a test API key
    const testKey = 'sk-test-api-key-12345';
    await page.locator('input[placeholder*="API key"]').first().fill(testKey);
    
    // Click Save
    await page.locator('button:has-text("Save")').first().click();
    
    // Wait for the save to complete (button should change back to "Update")
    await expect(page.locator('button:has-text("Update")').first()).toBeVisible({ timeout: 5000 });
    
    // Verify status changed to "Configured"
    await expect(page.locator('text=Configured').first()).toBeVisible();
  });

  test('can cancel adding an API key', async ({ page }) => {
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');
    
    // Click Add Key
    await page.locator('button:has-text("Add Key")').first().click();
    
    // Enter some text
    await page.locator('input[placeholder*="API key"]').first().fill('some-key');
    
    // Click Cancel
    await page.locator('button:has-text("Cancel")').first().click();
    
    // Verify we're back to the Add Key state
    await expect(page.locator('button:has-text("Add Key")').first()).toBeVisible();
  });

  test('API keys are masked in the UI', async ({ page }) => {
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');
    
    // Add a key first
    await page.locator('button:has-text("Add Key")').first().click();
    await page.locator('input[placeholder*="API key"]').first().fill('sk-secret-key-123');
    await page.locator('button:has-text("Save")').first().click();
    
    // Wait for save
    await expect(page.locator('button:has-text("Update")').first()).toBeVisible({ timeout: 5000 });
    
    // The input should show masked value (dots)
    const input = page.locator('input[value="••••••••••••••••••••••••••"]').first();
    await expect(input).toBeVisible();
  });

  test('can update an existing API key', async ({ page }) => {
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');
    
    // First add a key
    await page.locator('button:has-text("Add Key")').first().click();
    await page.locator('input[placeholder*="API key"]').first().fill('sk-old-key');
    await page.locator('button:has-text("Save")').first().click();
    await expect(page.locator('button:has-text("Update")').first()).toBeVisible({ timeout: 5000 });
    
    // Now update it
    await page.locator('button:has-text("Update")').first().click();
    await page.locator('input[placeholder*="API key"]').first().fill('sk-new-key-67890');
    await page.locator('button:has-text("Save")').first().click();
    
    // Verify it saved successfully
    await expect(page.locator('button:has-text("Update")').first()).toBeVisible({ timeout: 5000 });
  });

  test('can remove an API key', async ({ page }) => {
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');
    
    // First add a key
    await page.locator('button:has-text("Add Key")').first().click();
    await page.locator('input[placeholder*="API key"]').first().fill('sk-key-to-remove');
    await page.locator('button:has-text("Save")').first().click();
    await expect(page.locator('button:has-text("Update")').first()).toBeVisible({ timeout: 5000 });
    
    // Remove the key
    await page.locator('button:has-text("Remove")').first().click();
    
    // Verify status changed back to "Not configured"
    await expect(page.locator('text=Not configured').first()).toBeVisible({ timeout: 5000 });
    
    // Verify Add Key button is back
    await expect(page.locator('button:has-text("Add Key")').first()).toBeVisible();
  });

  test('shows info alert about API keys', async ({ page }) => {
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');
    
    // Verify the info alert is visible
    await expect(page.locator('text=About API Keys')).toBeVisible();
    await expect(page.locator('text=Configure your own API keys for LLM providers')).toBeVisible();
  });

  test('password visibility toggle works', async ({ page }) => {
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');
    
    // Click Add Key
    await page.locator('button:has-text("Add Key")').first().click();
    
    // Enter a key
    await page.locator('input[placeholder*="API key"]').first().fill('sk-visible-key');
    
    // Find and click the visibility toggle button
    const visibilityButton = page.locator('button[aria-label*="visibility"]').first();
    await visibilityButton.click();
    
    // The input type should change from password to text
    const input = page.locator('input[type="text"][placeholder*="API key"]').first();
    await expect(input).toBeVisible();
    
    // Toggle back
    await visibilityButton.click();
    const passwordInput = page.locator('input[type="password"]').first();
    await expect(passwordInput).toBeVisible();
  });

  test('navigation between profile tabs works', async ({ page }) => {
    // Start at basic info
    await page.goto('/profile/basic');
    await page.waitForLoadState('domcontentloaded');
    
    // Click on profile menu
    await page.locator('[aria-label="account of current user"]').click();
    
    // Navigate to API Keys
    await page.locator('text=API Keys').click();
    
    // Verify URL changed
    await expect(page).toHaveURL(/.*\/profile\/apikeys/);
    
    // Navigate to Usage
    await page.locator('[aria-label="account of current user"]').click();
    await page.locator('text=Usage').click();
    
    await expect(page).toHaveURL(/.*\/profile\/usage/);
    
    // Navigate to Billing
    await page.locator('[aria-label="account of current user"]').click();
    await page.locator('text=Billing').click();
    
    await expect(page).toHaveURL(/.*\/profile\/billing/);
  });

  test('save button disabled when input is empty', async ({ page }) => {
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');
    
    // Click Add Key
    await page.locator('button:has-text("Add Key")').first().click();
    
    // Save button should be disabled when input is empty
    const saveButton = page.locator('button:has-text("Save")').first();
    await expect(saveButton).toBeDisabled();
    
    // Type something
    await page.locator('input[placeholder*="API key"]').first().fill('some-key');
    
    // Save button should now be enabled
    await expect(saveButton).toBeEnabled();
  });

  test('shows loading state during save', async ({ page }) => {
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');
    
    // Click Add Key
    await page.locator('button:has-text("Add Key")').first().click();
    
    // Enter a key
    await page.locator('input[placeholder*="API key"]').first().fill('sk-loading-test');
    
    // Click Save
    await page.locator('button:has-text("Save")').first().click();
    
    // During save, either a loading spinner appears or the button is disabled
    // We'll check for the disabled state or circular progress
    await expect(
      page.locator('button:disabled:has-text("Save")').first().or(
        page.locator('.MuiCircularProgress-root').first()
      )
    ).toBeVisible();
  });

  test('displays success message after saving key', async ({ page }) => {
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');
    
    // Click Add Key on first provider
    await page.locator('button:has-text("Add Key")').first().click();
    
    // Enter a key
    await page.locator('input[placeholder*="API key"]').first().fill('sk-success-test');
    
    // Click Save
    await page.locator('button:has-text("Save")').first().click();
    
    // Wait for and verify success message
    await expect(page.locator('.MuiAlert-standardSuccess')).toBeVisible({ timeout: 5000 });
  });

  test('displays error message on save failure', async ({ page }) => {
    // Intercept and fail the API call
    await page.route('**/api/users/me/api-keys', async (route) => {
      await route.fulfill({
        status: 500,
        body: JSON.stringify({ detail: 'Failed to save API key' }),
      });
    });
    
    await page.goto('/profile/apikeys');
    await page.waitForLoadState('domcontentloaded');
    
    // Click Add Key
    await page.locator('button:has-text("Add Key")').first().click();
    
    // Enter a key
    await page.locator('input[placeholder*="API key"]').first().fill('sk-error-test');
    
    // Click Save
    await page.locator('button:has-text("Save")').first().click();
    
    // Wait for and verify error message
    await expect(page.locator('.MuiAlert-standardError')).toBeVisible({ timeout: 5000 });
  });
});
