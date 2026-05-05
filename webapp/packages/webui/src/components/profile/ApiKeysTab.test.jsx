import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ApiKeysTab from './ApiKeysTab';
import userService from '../../services/userService';
import { renderWithRouterAndTheme } from '../../test/testUtils';

// Mock userService
vi.mock('../../services/userService', () => ({
  default: {
    getApiKeys: vi.fn(),
    updateApiKey: vi.fn(),
    deleteApiKey: vi.fn(),
  },
}));

// ApiKeysTab uses useNavigate (back arrow → /). All tests render
// inside a router so the hook resolves.
const render = (ui) => renderWithRouterAndTheme(ui);

const noKeys = {
  openaiApiKey: null,
  anthropicApiKey: null,
  geminiApiKey: null,
  perplexityApiKey: null,
  openrouterApiKey: null,
};

describe('ApiKeysTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    userService.getApiKeys.mockResolvedValueOnce(noKeys);
    render(<ApiKeysTab />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('renders all provider sections after loading', async () => {
    userService.getApiKeys.mockResolvedValueOnce(noKeys);
    render(<ApiKeysTab />);

    await waitFor(() => {
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
      expect(screen.getByText('Anthropic')).toBeInTheDocument();
      expect(screen.getByText('Google Gemini')).toBeInTheDocument();
      expect(screen.getByText('Perplexity')).toBeInTheDocument();
      expect(screen.getByText('OpenRouter')).toBeInTheDocument();
    });
  });

  it('shows no Configured chip when no keys are set', async () => {
    // Only the "Configured" status chip is rendered now (absence = not
    // configured, indicated by the empty disabled text field with
    // placeholder "No API key configured"). Previously there was an
    // explicit "Not configured" chip too.
    userService.getApiKeys.mockResolvedValueOnce(noKeys);
    render(<ApiKeysTab />);

    await waitFor(() => {
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
    });
    expect(screen.queryByText('Configured')).not.toBeInTheDocument();
    expect(screen.getAllByPlaceholderText('No API key configured').length).toBe(5);
  });

  it('shows "Configured" chip for providers with keys', async () => {
    userService.getApiKeys.mockResolvedValueOnce({
      ...noKeys,
      openaiApiKey: 'sk-test-key',
    });
    render(<ApiKeysTab />);

    await waitFor(() => {
      expect(screen.getByText('Configured')).toBeInTheDocument();
    });
  });

  it('shows "Add key" button for providers without keys', async () => {
    userService.getApiKeys.mockResolvedValueOnce(noKeys);
    render(<ApiKeysTab />);

    await waitFor(() => {
      const addKeyButtons = screen.getAllByRole('button', { name: /add key/i });
      expect(addKeyButtons.length).toBe(5);
    });
  });

  it('shows Update button for providers with keys', async () => {
    userService.getApiKeys.mockResolvedValueOnce({
      ...noKeys,
      openaiApiKey: 'sk-test-key',
    });
    render(<ApiKeysTab />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /update/i })).toBeInTheDocument();
    });
  });

  it('shows input field when Add key is clicked', async () => {
    const user = userEvent.setup();
    userService.getApiKeys.mockResolvedValueOnce(noKeys);
    render(<ApiKeysTab />);

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
      .mockResolvedValueOnce(noKeys)
      .mockResolvedValueOnce({ ...noKeys, openaiApiKey: 'sk-new-key' });
    userService.updateApiKey.mockResolvedValueOnce({});

    render(<ApiKeysTab />);

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

  it('calls deleteApiKey when the remove icon is clicked', async () => {
    const user = userEvent.setup();
    userService.getApiKeys
      .mockResolvedValueOnce({ ...noKeys, openaiApiKey: 'sk-test-key' })
      .mockResolvedValueOnce(noKeys);
    userService.deleteApiKey.mockResolvedValueOnce({});

    render(<ApiKeysTab />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /remove openai api key/i })).toBeInTheDocument();
    });

    const removeButton = screen.getByRole('button', { name: /remove openai api key/i });
    await user.click(removeButton);

    await waitFor(() => {
      expect(userService.deleteApiKey).toHaveBeenCalledWith('openai');
    });
  });

  it('shows error message when API call fails', async () => {
    const user = userEvent.setup();
    userService.getApiKeys.mockResolvedValueOnce(noKeys);
    userService.updateApiKey.mockRejectedValueOnce(new Error('Failed to save'));

    render(<ApiKeysTab />);

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
    userService.getApiKeys.mockResolvedValueOnce(noKeys);
    render(<ApiKeysTab />);

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

  it('shows page header copy', async () => {
    userService.getApiKeys.mockResolvedValueOnce(noKeys);
    render(<ApiKeysTab />);

    await waitFor(() => {
      // The h5 title and the helper text below it. The old Alert
      // ("About API Keys") was dropped in favor of inline page chrome.
      expect(screen.getByRole('heading', { name: 'API Keys' })).toBeInTheDocument();
      expect(screen.getByText(/configure your own api keys for llm providers/i)).toBeInTheDocument();
    });
  });

  it('disables save button when input is empty', async () => {
    const user = userEvent.setup();
    userService.getApiKeys.mockResolvedValueOnce(noKeys);
    render(<ApiKeysTab />);

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
    userService.getApiKeys.mockResolvedValueOnce(noKeys);
    render(<ApiKeysTab />);

    await waitFor(() => {
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
    });

    const addKeyButton = screen.getAllByRole('button', { name: /add key/i })[0];
    await user.click(addKeyButton);

    const input = screen.getByPlaceholderText(/enter your openai api key/i);
    expect(input).toHaveAttribute('type', 'password');

    const visibilityButton = screen.getAllByRole('button').find(
      (btn) =>
        btn.querySelector('[data-testid="VisibilityIcon"]') ||
        btn.querySelector('[data-testid="VisibilityOffIcon"]'),
    );
    expect(visibilityButton).toBeDefined();
    await user.click(visibilityButton);

    expect(input).toHaveAttribute('type', 'text');
  });

  it('shows success message after saving key', async () => {
    const user = userEvent.setup();
    userService.getApiKeys
      .mockResolvedValueOnce(noKeys)
      .mockResolvedValueOnce({ ...noKeys, openaiApiKey: 'sk-new-key' });
    userService.updateApiKey.mockResolvedValueOnce({});

    render(<ApiKeysTab />);

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
