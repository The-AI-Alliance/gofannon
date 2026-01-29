import { describe, it, expect, vi, beforeEach } from 'vitest';
import userService from './userService';
import apiClient from './apiClient';

// Mock apiClient
vi.mock('./apiClient', () => ({
  default: {
    get: vi.fn(),
    put: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('userService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getApiKeys', () => {
    it('calls GET /users/me/api-keys', async () => {
      const mockResponse = {
        openaiApiKey: 'sk-test',
        anthropicApiKey: null,
        geminiApiKey: null,
        perplexityApiKey: null,
      };
      apiClient.get.mockResolvedValueOnce(mockResponse);

      const result = await userService.getApiKeys();

      expect(apiClient.get).toHaveBeenCalledWith('/users/me/api-keys');
      expect(result).toEqual(mockResponse);
    });

    it('returns null values for unset keys', async () => {
      const mockResponse = {
        openaiApiKey: null,
        anthropicApiKey: null,
        geminiApiKey: null,
        perplexityApiKey: null,
      };
      apiClient.get.mockResolvedValueOnce(mockResponse);

      const result = await userService.getApiKeys();

      expect(result.openaiApiKey).toBeNull();
      expect(result.anthropicApiKey).toBeNull();
    });
  });

  describe('updateApiKey', () => {
    it('calls PUT /users/me/api-keys with correct payload', async () => {
      const mockResponse = {
        id: 'user-123',
        apiKeys: {
          openaiApiKey: 'sk-new-key',
        },
      };
      apiClient.put.mockResolvedValueOnce(mockResponse);

      const result = await userService.updateApiKey('openai', 'sk-new-key');

      expect(apiClient.put).toHaveBeenCalledWith('/users/me/api-keys', {
        provider: 'openai',
        api_key: 'sk-new-key',
      });
      expect(result).toEqual(mockResponse);
    });

    it('sends api_key in snake_case for backend compatibility', async () => {
      apiClient.put.mockResolvedValueOnce({});

      await userService.updateApiKey('anthropic', 'sk-ant-key');

      const callArg = apiClient.put.mock.calls[0][1];
      expect(callArg).toHaveProperty('api_key');
      expect(callArg).not.toHaveProperty('apiKey');
    });

    it('throws error when API call fails', async () => {
      const error = new Error('Network error');
      apiClient.put.mockRejectedValueOnce(error);

      await expect(userService.updateApiKey('openai', 'sk-key')).rejects.toThrow('Network error');
    });
  });

  describe('updateApiKey for all providers', () => {
    it.each([
      ['openai', 'sk-openai-key'],
      ['anthropic', 'sk-ant-key'],
      ['gemini', 'gemini-key'],
      ['perplexity', 'pplx-key'],
    ])('handles %s provider', async (provider, key) => {
      vi.clearAllMocks();
      apiClient.put.mockResolvedValueOnce({});

      await userService.updateApiKey(provider, key);

      expect(apiClient.put).toHaveBeenCalledWith('/users/me/api-keys', {
        provider,
        api_key: key,
      });
    });
  });

  describe('deleteApiKey', () => {
    it('calls DELETE /users/me/api-keys/{provider}', async () => {
      const mockResponse = {
        id: 'user-123',
        apiKeys: {
          openaiApiKey: null,
        },
      };
      apiClient.delete.mockResolvedValueOnce(mockResponse);

      const result = await userService.deleteApiKey('openai');

      expect(apiClient.delete).toHaveBeenCalledWith('/users/me/api-keys/openai');
      expect(result).toEqual(mockResponse);
    });

    it('throws error when API call fails', async () => {
      const error = new Error('Network error');
      apiClient.delete.mockRejectedValueOnce(error);

      await expect(userService.deleteApiKey('openai')).rejects.toThrow('Network error');
    });
  });

  describe('deleteApiKey for all providers', () => {
    it.each(['openai', 'anthropic', 'gemini', 'perplexity'])('handles %s provider', async (provider) => {
      vi.clearAllMocks();
      apiClient.delete.mockResolvedValueOnce({});

      await userService.deleteApiKey(provider);

      expect(apiClient.delete).toHaveBeenCalledWith(`/users/me/api-keys/${provider}`);
    });
  });

  describe('getEffectiveApiKey', () => {
    it('calls GET /users/me/api-keys/{provider}/effective', async () => {
      const mockResponse = {
        provider: 'openai',
        hasKey: true,
        source: 'user',
      };
      apiClient.get.mockResolvedValueOnce(mockResponse);

      const result = await userService.getEffectiveApiKey('openai');

      expect(apiClient.get).toHaveBeenCalledWith('/users/me/api-keys/openai/effective');
      expect(result).toEqual(mockResponse);
    });

    it('returns has_key=false when no key available', async () => {
      const mockResponse = {
        provider: 'openai',
        hasKey: false,
        source: null,
      };
      apiClient.get.mockResolvedValueOnce(mockResponse);

      const result = await userService.getEffectiveApiKey('openai');

      expect(result.hasKey).toBe(false);
      expect(result.source).toBeNull();
    });

    it('returns source=user when user key is set', async () => {
      const mockResponse = {
        provider: 'openai',
        hasKey: true,
        source: 'user',
      };
      apiClient.get.mockResolvedValueOnce(mockResponse);

      const result = await userService.getEffectiveApiKey('openai');

      expect(result.source).toBe('user');
    });

    it('returns source=env when using environment variable', async () => {
      const mockResponse = {
        provider: 'openai',
        hasKey: true,
        source: 'env',
      };
      apiClient.get.mockResolvedValueOnce(mockResponse);

      const result = await userService.getEffectiveApiKey('openai');

      expect(result.source).toBe('env');
    });

    it('throws error when API call fails', async () => {
      const error = new Error('Network error');
      apiClient.get.mockRejectedValueOnce(error);

      await expect(userService.getEffectiveApiKey('openai')).rejects.toThrow('Network error');
    });
  });

  describe('getEffectiveApiKey for all providers', () => {
    it.each(['openai', 'anthropic', 'gemini', 'perplexity'])('handles %s provider', async (provider) => {
      vi.clearAllMocks();
      apiClient.get.mockResolvedValueOnce({ provider, hasKey: true, source: 'user' });

      await userService.getEffectiveApiKey(provider);

      expect(apiClient.get).toHaveBeenCalledWith(`/users/me/api-keys/${provider}/effective`);
    });
  });

  describe('existing methods still work', () => {
    it('getProfile calls correct endpoint', async () => {
      apiClient.get.mockResolvedValueOnce({ id: 'user-123' });

      await userService.getProfile();

      expect(apiClient.get).toHaveBeenCalledWith('/users/me');
    });

    it('updateMonthlyAllowance calls correct endpoint', async () => {
      apiClient.put.mockResolvedValueOnce({});

      await userService.updateMonthlyAllowance(100);

      expect(apiClient.put).toHaveBeenCalledWith('/users/me/monthly-allowance', { monthlyAllowance: 100 });
    });
  });
});
