import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ApiKeysTab from './ApiKeysTab';
import userService from '../../services/userService';
import { renderWithTheme } from '../../test/testUtils';

// Mock userService
vi.mock('../../services/userService', () => ({
  default: {
    getApiKeys: vi.fn(),
    updateApiKey: vi.fn(),
    deleteApiKey: vi.fn(),
  },
}));

describe('ApiKeysTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    userService.getApiKeys.mockResolvedValueOnce({
      openaiApiKey: null,
      anthropicApiKey: null,
      geminiApiKey: null,
      perplexityApiKey: null,
    });

    renderWithTheme(<ApiKeysTab />);

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('renders all provider sections after loading', async () => {
    userService.getApiKeys.mockResolvedValueOnce({
      openaiApiKey: null,
      anthropicApiKey: null,
      geminiApiKey: null,
      perplexityApiKey: null,
    });

    renderWithTheme(<ApiKeysTab />);

    await waitFor(() => {
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
      expect(screen.getByText('Anthropic')).toBeInTheDocument();
      expect(screen.getByText('Google Gemini')).toBeInTheDocument();
      expect(screen.getByText('Perplexity')).toBeInTheDocument();
    });
  });

  it('shows "Not configured" status for providers without keys', async () => {
    userService.getApiKeys.mockResolvedValueOnce({
      openaiApiKey: null,
      anthropicApiKey: null,
      geminiApiKey: null,
      perplexityApiKey: null,
    });

    renderWithTheme(<ApiKeysTab />);

    await waitFor(() => {
      const notConfiguredChips = screen.getAllByText('Not configured');
      expect(notConfiguredChips.length).toBe(4);
    });
  });

  it('shows "Configured" status for providers with keys', async () => {
    userService.getApiKeys.mockResolvedValueOnce({
      openaiApiKey: 'sk-test-key',
      anthropicApiKey: null,
      geminiApiKey: null,
      perplexityApiKey: null,
    });

    renderWithTheme(<ApiKeysTab />);

    await waitFor(() => {
      expect(screen.getByText('Configured')).toBeInTheDocument();
      expect(screen.getAllByText('Not configured').length).toBe(3);
    });
  });

  it('shows Add Key button for providers without keys', async () => {
    userService.getApiKeys.mockResolvedValueOnce({
      openaiApiKey: null,
      anthropicApiKey: null,
      geminiApiKey: null,
      perplexityApiKey: null,
    });

    renderWithTheme(<ApiKeysTab />);

    await waitFor(() => {
      const addKeyButtons = screen.getAllByRole('button', { name: /add key/i });
      expect(addKeyButtons.length).toBe(4);
    });
  });

  it('shows Update button for providers with keys', async () => {
    userService.getApiKeys.mockResolvedValueOnce({
      openaiApiKey: 'sk-test-key',
      anthropicApiKey: null,
      geminiApiKey: null,
      perplexityApiKey: null,
    });

    renderWithTheme(<ApiKeysTab />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /update/i })).toBeInTheDocument();
    });
  });

  it('shows input field when Add Key is clicked', async () => {
    const user = userEvent.setup();
    userService.getApiKeys.mockResolvedValueOnce({
      openaiApiKey: null,
      anthropicApiKey: null,
      geminiApiKey: null,
      perplexityApiKey: null,
    });

    renderWithTheme(<ApiKeysTab />);

    await waitFor(() => {
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
    });

    const addKeyButton = screen.getAllByRole('button', { name: /add key/i })[0];
    await user.click(addKeyButton);

    expect(screen.getByPlaceholderText(/enter your openai api key/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });

  it('calls updateApiKey when saving a new key', async () => {
    const user = userEvent.setup();
    userService.getApiKeys
      .mockResolvedValueOnce({
        openaiApiKey: null,
        anthropicApiKey: null,
        geminiApiKey: null,
        perplexityApiKey: null,
      })
      .mockResolvedValueOnce({
        openaiApiKey: 'sk-new-key',
        anthropicApiKey: null,
        geminiApiKey: null,
        perplexityApiKey: null,
      });

    userService.updateApiKey.mockResolvedValueOnce({});

    renderWithTheme(<ApiKeysTab />);

    await waitFor(() => {
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
    });

    const addKeyButton = screen.getAllByRole('button', { name: /add key/i })[0];
    await user.click(addKeyButton);

    const input = screen.getByPlaceholderText(/enter your openai api key/i);
    await user.type(input, 'sk-new-key');

    const saveButton = screen.getByRole('button', { name: /^save$/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(userService.updateApiKey).toHaveBeenCalledWith('openai', 'sk-new-key');
    });
  });

  it('calls deleteApiKey when Remove is clicked', async () => {
    const user = userEvent.setup();
    userService.getApiKeys
      .mockResolvedValueOnce({
        openaiApiKey: 'sk-test-key',
        anthropicApiKey: null,
        geminiApiKey: null,
        perplexityApiKey: null,
      })
      .mockResolvedValueOnce({
        openaiApiKey: null,
        anthropicApiKey: null,
        geminiApiKey: null,
        perplexityApiKey: null,
      });

    userService.deleteApiKey.mockResolvedValueOnce({});

    renderWithTheme(<ApiKeysTab />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /remove/i })).toBeInTheDocument();
    });

    const removeButton = screen.getByRole('button', { name: /remove/i });
    await user.click(removeButton);

    await waitFor(() => {
      expect(userService.deleteApiKey).toHaveBeenCalledWith('openai');
    });
  });

  it('shows error message when API call fails', async () => {
    const user = userEvent.setup();
    userService.getApiKeys.mockResolvedValueOnce({
      openaiApiKey: null,
      anthropicApiKey: null,
      geminiApiKey: null,
      perplexityApiKey: null,
    });

    userService.updateApiKey.mockRejectedValueOnce(new Error('Failed to save'));

    renderWithTheme(<ApiKeysTab />);

    await waitFor(() => {
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
    });

    const addKeyButton = screen.getAllByRole('button', { name: /add key/i })[0];
    await user.click(addKeyButton);

    const input = screen.getByPlaceholderText(/enter your openai api key/i);
    await user.type(input, 'sk-test-key');

    const saveButton = screen.getByRole('button', { name: /^save$/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText(/failed to save/i)).toBeInTheDocument();
    });
  });

  it('cancels editing when Cancel is clicked', async () => {
    const user = userEvent.setup();
    userService.getApiKeys.mockResolvedValueOnce({
      openaiApiKey: null,
      anthropicApiKey: null,
      geminiApiKey: null,
      perplexityApiKey: null,
    });

    renderWithTheme(<ApiKeysTab />);

    await waitFor(() => {
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
    });

    const addKeyButton = screen.getAllByRole('button', { name: /add key/i })[0];
    await user.click(addKeyButton);

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    await waitFor(() => {
      expect(screen.queryByPlaceholderText(/enter your openai api key/i)).not.toBeInTheDocument();
    });
  });

  it('shows info alert about API keys', async () => {
    userService.getApiKeys.mockResolvedValueOnce({
      openaiApiKey: null,
      anthropicApiKey: null,
      geminiApiKey: null,
      perplexityApiKey: null,
    });

    renderWithTheme(<ApiKeysTab />);

    await waitFor(() => {
      expect(screen.getByText('About API Keys')).toBeInTheDocument();
      expect(screen.getByText(/configure your own api keys for llm providers/i)).toBeInTheDocument();
    });
  });

  it('disables save button when input is empty', async () => {
    const user = userEvent.setup();
    userService.getApiKeys.mockResolvedValueOnce({
      openaiApiKey: null,
      anthropicApiKey: null,
      geminiApiKey: null,
      perplexityApiKey: null,
    });

    renderWithTheme(<ApiKeysTab />);

    await waitFor(() => {
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
    });

    const addKeyButton = screen.getAllByRole('button', { name: /add key/i })[0];
    await user.click(addKeyButton);

    const saveButton = screen.getByRole('button', { name: /^save$/i });
    expect(saveButton).toBeDisabled();
  });

  it('toggles password visibility when visibility icon is clicked', async () => {
    const user = userEvent.setup();
    userService.getApiKeys.mockResolvedValueOnce({
      openaiApiKey: null,
      anthropicApiKey: null,
      geminiApiKey: null,
      perplexityApiKey: null,
    });

    renderWithTheme(<ApiKeysTab />);

    await waitFor(() => {
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
    });

    const addKeyButton = screen.getAllByRole('button', { name: /add key/i })[0];
    await user.click(addKeyButton);

    const input = screen.getByPlaceholderText(/enter your openai api key/i);
    expect(input).toHaveAttribute('type', 'password');

    // Find visibility toggle by test ID or aria-label pattern
    const visibilityButton = screen.getAllByRole('button').find(
      btn => btn.querySelector('[data-testid="VisibilityIcon"]') || 
             btn.querySelector('[data-testid="VisibilityOffIcon"]')
    );
    expect(visibilityButton).toBeDefined();
    await user.click(visibilityButton);

    expect(input).toHaveAttribute('type', 'text');
  });

  it('shows success message after saving key', async () => {
    const user = userEvent.setup();
    userService.getApiKeys
      .mockResolvedValueOnce({
        openaiApiKey: null,
        anthropicApiKey: null,
        geminiApiKey: null,
        perplexityApiKey: null,
      })
      .mockResolvedValueOnce({
        openaiApiKey: 'sk-new-key',
        anthropicApiKey: null,
        geminiApiKey: null,
        perplexityApiKey: null,
      });

    userService.updateApiKey.mockResolvedValueOnce({});

    renderWithTheme(<ApiKeysTab />);

    await waitFor(() => {
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
    });

    const addKeyButton = screen.getAllByRole('button', { name: /add key/i })[0];
    await user.click(addKeyButton);

    const input = screen.getByPlaceholderText(/enter your openai api key/i);
    await user.type(input, 'sk-new-key');

    const saveButton = screen.getByRole('button', { name: /^save$/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText(/saved successfully/i)).toBeInTheDocument();
    });
  });
});
