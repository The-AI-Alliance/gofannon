import { describe, it, expect, vi, beforeEach } from 'vitest';
import apiClient from './apiClient';
import authService from './authService';
import config from '../config';

vi.mock('./authService', () => ({
  default: {
    getCurrentUser: vi.fn(),
  },
}));

vi.mock('../config', () => ({
  default: {
    api: {
      baseUrl: 'http://localhost:8000',
    },
  },
}));

global.fetch = vi.fn();

describe('apiClient', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  describe('request', () => {
    it('makes a successful GET request', async () => {
      const mockData = { id: 1, name: 'Test' };
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });
      authService.getCurrentUser.mockReturnValue(null);

      const result = await apiClient.request('/test', { method: 'GET' });

      expect(result).toEqual(mockData);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/test',
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          }),
        })
      );
    });

    it('includes auth token when user is authenticated', async () => {
      const mockUser = {
        getIdToken: vi.fn().mockResolvedValue('mock-token'),
      };
      authService.getCurrentUser.mockReturnValue(mockUser);
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      await apiClient.request('/test');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/test',
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer mock-token',
          }),
        })
      );
    });

    it('works without auth token when user is not authenticated', async () => {
      authService.getCurrentUser.mockReturnValue(null);
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      await apiClient.request('/test');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/test',
        expect.objectContaining({
          headers: expect.not.objectContaining({
            Authorization: expect.anything(),
          }),
        })
      );
    });

    it('throws error on failed request', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Not found' }),
      });
      authService.getCurrentUser.mockReturnValue(null);

      await expect(apiClient.request('/test')).rejects.toThrow('Not found');
    });

    it('handles response without detail field', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({}),
      });
      authService.getCurrentUser.mockReturnValue(null);

      await expect(apiClient.request('/test')).rejects.toThrow(
        'Request failed with status 500'
      );
    });

    it('gracefully handles empty response body', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => {
          throw new Error('No JSON');
        },
      });
      authService.getCurrentUser.mockReturnValue(null);

      const result = await apiClient.request('/test');

      expect(result).toEqual({});
    });

    it('includes custom headers', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });
      authService.getCurrentUser.mockReturnValue(null);

      await apiClient.request('/test', {
        headers: { 'X-Custom': 'value' },
      });

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/test',
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-Custom': 'value',
          }),
        })
      );
    });
  });

  describe('get', () => {
    it('makes GET request', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: 'test' }),
      });
      authService.getCurrentUser.mockReturnValue(null);

      const result = await apiClient.get('/users');

      expect(result).toEqual({ data: 'test' });
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/users',
        expect.objectContaining({ method: 'GET' })
      );
    });
  });

  describe('post', () => {
    it('makes POST request with body', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: 1 }),
      });
      authService.getCurrentUser.mockReturnValue(null);

      const body = { name: 'Test' };
      const result = await apiClient.post('/users', body);

      expect(result).toEqual({ id: 1 });
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/users',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(body),
        })
      );
    });
  });

  describe('put', () => {
    it('makes PUT request with body', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ updated: true }),
      });
      authService.getCurrentUser.mockReturnValue(null);

      const body = { name: 'Updated' };
      const result = await apiClient.put('/users/1', body);

      expect(result).toEqual({ updated: true });
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/users/1',
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify(body),
        })
      );
    });
  });

  describe('delete', () => {
    it('makes DELETE request', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ deleted: true }),
      });
      authService.getCurrentUser.mockReturnValue(null);

      const result = await apiClient.delete('/users/1');

      expect(result).toEqual({ deleted: true });
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/users/1',
        expect.objectContaining({ method: 'DELETE' })
      );
    });
  });

  describe('error handling', () => {
    it('handles token retrieval error', async () => {
      const mockUser = {
        getIdToken: vi.fn().mockRejectedValue(new Error('Token error')),
      };
      authService.getCurrentUser.mockReturnValue(mockUser);
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      await apiClient.request('/test');

      expect(console.error).toHaveBeenCalledWith(
        'Error getting auth token:',
        expect.any(Error)
      );
      // Should still make request without token
      expect(global.fetch).toHaveBeenCalled();
    });

    it('logs API errors to console', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Bad request' }),
      });
      authService.getCurrentUser.mockReturnValue(null);

      await expect(apiClient.request('/test')).rejects.toThrow();

      expect(console.error).toHaveBeenCalledWith(
        'API Error on /test:',
        'Bad request'
      );
    });
  });
});
