import { describe, it, expect } from 'vitest';
import {
  createMockUser,
  createMockResponse,
  createMockError,
  mockLocalStorage,
  createMockAgent,
  createMockChatMessage,
  waitForPromises,
} from './testUtils';

describe('Test Utilities', () => {
  describe('createMockUser', () => {
    it('creates a mock user with default values', () => {
      const user = createMockUser();

      expect(user).toHaveProperty('uid');
      expect(user).toHaveProperty('email');
      expect(user).toHaveProperty('displayName');
      expect(user).toHaveProperty('photoURL');
      expect(user.emailVerified).toBe(true);
      expect(typeof user.getIdToken).toBe('function');
    });

    it('allows overriding default values', () => {
      const user = createMockUser({
        uid: 'custom-id',
        email: 'custom@example.com',
      });

      expect(user.uid).toBe('custom-id');
      expect(user.email).toBe('custom@example.com');
    });

    it('getIdToken returns a promise', async () => {
      const user = createMockUser();
      const token = await user.getIdToken();

      expect(token).toBe('mock-token');
    });
  });

  describe('createMockResponse', () => {
    it('creates a successful response', async () => {
      const data = { id: 1, name: 'Test' };
      const response = createMockResponse(data);

      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);
      expect(await response.json()).toEqual(data);
    });

    it('creates a failed response', async () => {
      const data = { error: 'Not found' };
      const response = createMockResponse(data, false, 404);

      expect(response.ok).toBe(false);
      expect(response.status).toBe(404);
      expect(await response.json()).toEqual(data);
    });

    it('has proper headers', () => {
      const response = createMockResponse({});

      expect(response.headers.get('Content-Type')).toBe('application/json');
    });
  });

  describe('createMockError', () => {
    it('creates an error with message', () => {
      const error = createMockError('Test error');

      expect(error.message).toBe('Test error');
      expect(error.name).toBe('Error');
      expect(error.stack).toBeTruthy();
    });

    it('creates an error with custom name', () => {
      const error = createMockError('Type error', 'TypeError');

      expect(error.name).toBe('TypeError');
      expect(error.message).toBe('Type error');
    });
  });

  describe('mockLocalStorage', () => {
    it('implements getItem and setItem', () => {
      const storage = mockLocalStorage();

      storage.setItem('key', 'value');
      expect(storage.getItem('key')).toBe('value');
    });

    it('implements removeItem', () => {
      const storage = mockLocalStorage();

      storage.setItem('key', 'value');
      storage.removeItem('key');
      expect(storage.getItem('key')).toBeNull();
    });

    it('implements clear', () => {
      const storage = mockLocalStorage();

      storage.setItem('key1', 'value1');
      storage.setItem('key2', 'value2');
      storage.clear();

      expect(storage.getItem('key1')).toBeNull();
      expect(storage.getItem('key2')).toBeNull();
    });

    it('returns null for non-existent keys', () => {
      const storage = mockLocalStorage();

      expect(storage.getItem('nonexistent')).toBeNull();
    });
  });

  describe('createMockAgent', () => {
    it('creates a mock agent with default values', () => {
      const agent = createMockAgent();

      expect(agent).toHaveProperty('id');
      expect(agent).toHaveProperty('name');
      expect(agent).toHaveProperty('description');
      expect(agent).toHaveProperty('code');
      expect(agent).toHaveProperty('apiSpecs');
      expect(Array.isArray(agent.apiSpecs)).toBe(true);
    });

    it('allows overriding default values', () => {
      const agent = createMockAgent({
        id: 'custom-id',
        name: 'Custom Agent',
      });

      expect(agent.id).toBe('custom-id');
      expect(agent.name).toBe('Custom Agent');
    });
  });

  describe('createMockChatMessage', () => {
    it('creates a mock chat message with default values', () => {
      const message = createMockChatMessage();

      expect(message).toHaveProperty('id');
      expect(message).toHaveProperty('role');
      expect(message).toHaveProperty('content');
      expect(message).toHaveProperty('timestamp');
    });

    it('allows overriding default values', () => {
      const message = createMockChatMessage({
        role: 'assistant',
        content: 'Custom response',
      });

      expect(message.role).toBe('assistant');
      expect(message.content).toBe('Custom response');
    });
  });

  describe('waitForPromises', () => {
    it('waits for pending promises to resolve', async () => {
      let resolved = false;
      Promise.resolve().then(() => {
        resolved = true;
      });

      expect(resolved).toBe(false);
      await waitForPromises();
      expect(resolved).toBe(true);
    });
  });
});
