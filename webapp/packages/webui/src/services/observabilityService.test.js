import { describe, it, expect, vi, beforeEach } from 'vitest';
import observabilityService from './observabilityService';
import apiClient from './apiClient';

vi.mock('./apiClient', () => ({
  default: {
    post: vi.fn(() => Promise.resolve({})),
  },
}));

describe('ObservabilityService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  describe('log', () => {
    it('sends log data to backend', () => {
      const logData = {
        eventType: 'user-action',
        message: 'User clicked button',
        level: 'INFO',
        metadata: { buttonId: 'submit' },
      };

      observabilityService.log(logData);

      expect(apiClient.post).toHaveBeenCalledWith('/log/client', logData);
    });

    it('uses default level INFO when not specified', () => {
      const logData = {
        eventType: 'navigation',
        message: 'User navigated to /home',
      };

      observabilityService.log(logData);

      expect(apiClient.post).toHaveBeenCalledWith('/log/client', {
        ...logData,
        level: 'INFO',
        metadata: {},
      });
    });

    it('uses empty metadata object when not specified', () => {
      const logData = {
        eventType: 'page-view',
        message: 'Page viewed',
        level: 'INFO',
      };

      observabilityService.log(logData);

      expect(apiClient.post).toHaveBeenCalledWith('/log/client', {
        ...logData,
        metadata: {},
      });
    });

    it('handles API errors gracefully', async () => {
      const error = new Error('Network error');
      apiClient.post.mockRejectedValueOnce(error);

      observabilityService.log({
        eventType: 'test',
        message: 'test message',
      });

      // Wait for the promise to reject
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(console.error).toHaveBeenCalledWith(
        'Failed to send client log to backend:',
        error
      );
    });

    it('includes custom metadata', () => {
      const logData = {
        eventType: 'api-call',
        message: 'API request made',
        level: 'INFO',
        metadata: {
          endpoint: '/users',
          method: 'GET',
          duration: 250,
        },
      };

      observabilityService.log(logData);

      expect(apiClient.post).toHaveBeenCalledWith('/log/client', logData);
    });

    it('supports WARN level', () => {
      const logData = {
        eventType: 'warning',
        message: 'Slow network detected',
        level: 'WARN',
      };

      observabilityService.log(logData);

      expect(apiClient.post).toHaveBeenCalledWith('/log/client', {
        ...logData,
        metadata: {},
      });
    });

    it('supports ERROR level', () => {
      const logData = {
        eventType: 'error',
        message: 'Operation failed',
        level: 'ERROR',
        metadata: { errorCode: 500 },
      };

      observabilityService.log(logData);

      expect(apiClient.post).toHaveBeenCalledWith('/log/client', logData);
    });
  });

  describe('logError', () => {
    it('logs error with message and stack', () => {
      const error = new Error('Test error');
      error.stack = 'Error: Test error\n    at test.js:1:1';

      observabilityService.logError(error);

      expect(apiClient.post).toHaveBeenCalledWith('/log/client', {
        eventType: 'error',
        message: 'Test error',
        level: 'ERROR',
        metadata: {
          stack: error.stack,
          name: 'Error',
        },
      });
    });

    it('includes additional context', () => {
      const error = new Error('Component error');
      const context = {
        component: 'UserProfile',
        userId: '123',
      };

      observabilityService.logError(error, context);

      expect(apiClient.post).toHaveBeenCalledWith('/log/client', {
        eventType: 'error',
        message: 'Component error',
        level: 'ERROR',
        metadata: {
          ...context,
          stack: error.stack,
          name: 'Error',
        },
      });
    });

    it('works without additional context', () => {
      const error = new Error('Simple error');

      observabilityService.logError(error);

      expect(apiClient.post).toHaveBeenCalledWith('/log/client', {
        eventType: 'error',
        message: 'Simple error',
        level: 'ERROR',
        metadata: {
          stack: error.stack,
          name: 'Error',
        },
      });
    });

    it('includes error name', () => {
      const error = new TypeError('Invalid type');

      observabilityService.logError(error);

      expect(apiClient.post).toHaveBeenCalledWith('/log/client',
        expect.objectContaining({
          metadata: expect.objectContaining({
            name: 'TypeError',
          }),
        })
      );
    });

    it('handles errors from componentDidCatch', () => {
      const error = new Error('React error');
      const context = {
        componentStack: 'at Component (Component.jsx:10)',
        location: 'https://example.com/page',
      };

      observabilityService.logError(error, context);

      expect(apiClient.post).toHaveBeenCalledWith('/log/client', {
        eventType: 'error',
        message: 'React error',
        level: 'ERROR',
        metadata: {
          ...context,
          stack: error.stack,
          name: 'Error',
        },
      });
    });
  });
});
