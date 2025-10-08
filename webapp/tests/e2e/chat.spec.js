webapp/tests/e2e/chat.spec.js
import { test, expect } from '@playwright/test';

test.describe('Chat Page E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app and handle mock login
    await page.goto('/');
    await page.getByRole('button', { name: 'Enter App' }).click();
    await expect(page).toHaveURL('/');
  });

  test('should navigate to chat page and get a response from the AI', async ({ page }) => {
    // Navigate to the chat page
    await page.getByRole('button', { name: 'Chat' }).click();
    await expect(page).toHaveURL('/chat');
    await expect(page.getByRole('heading', { name: 'AI Chat' })).toBeVisible();

    // The page loads providers, wait for the input to be enabled
    const messageInput = page.getByPlaceholder('Type your message...');
    await expect(messageInput).toBeEnabled({ timeout: 15000 }); // Wait for providers to load

    // Send a message
    await messageInput.fill('Hello, world!');
    await page.getByRole('button', { name: 'Send' }).click();

    // Wait for the response
    // The user's message appears immediately
    await expect(page.getByText('Hello, world!')).toBeVisible();

    // The bot's response will come after a network request, so we need to wait for it.
    // The test will be against a running API which might use a real model, so timeout should be generous.
    const botResponse = page.locator('.MuiListItem-root').filter({ hasText: 'toLocaleTimeString' }).last();
    
    // We expect the bot to respond with something. The exact content is not deterministic.
    // We will check that a response from the 'assistant' is present.
    await expect(botResponse.locator('svg[data-testid="BotIcon"]')).toBeVisible({ timeout: 30000 });
    await expect(botResponse.locator('.MuiListItemText-primary')).not.toBeEmpty();
  });
});