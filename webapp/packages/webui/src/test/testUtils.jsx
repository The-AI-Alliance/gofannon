import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { createTheme } from '@mui/material/styles';

// Default MUI theme for testing
const defaultTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

/**
 * Renders a component with Router context
 */
export const renderWithRouter = (ui, { route = '/', ...renderOptions } = {}) => {
  return render(
    <MemoryRouter initialEntries={[route]}>
      {ui}
    </MemoryRouter>,
    renderOptions
  );
};

/**
 * Renders a component with MUI Theme context
 */
export const renderWithTheme = (ui, { theme = defaultTheme, ...renderOptions } = {}) => {
  return render(
    <ThemeProvider theme={theme}>
      {ui}
    </ThemeProvider>,
    renderOptions
  );
};

/**
 * Renders a component with both Router and Theme context
 */
export const renderWithRouterAndTheme = (
  ui,
  { route = '/', theme = defaultTheme, ...renderOptions } = {}
) => {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <ThemeProvider theme={theme}>
        {ui}
      </ThemeProvider>
    </MemoryRouter>,
    renderOptions
  );
};

/**
 * Creates a mock user object for testing
 */
export const createMockUser = (overrides = {}) => ({
  uid: 'test-user-123',
  email: 'test@example.com',
  displayName: 'Test User',
  photoURL: 'https://example.com/photo.jpg',
  emailVerified: true,
  getIdToken: vi.fn().mockResolvedValue('mock-token'),
  ...overrides,
});

/**
 * Creates a mock API response
 */
export const createMockResponse = (data, ok = true, status = 200) => ({
  ok,
  status,
  json: async () => data,
  text: async () => JSON.stringify(data),
  headers: new Headers({
    'Content-Type': 'application/json',
  }),
});

/**
 * Waits for all pending promises to resolve
 */
export const waitForPromises = () => new Promise((resolve) => setTimeout(resolve, 0));

/**
 * Creates a mock error for testing
 */
export const createMockError = (message = 'Test error', name = 'Error') => {
  const error = new Error(message);
  error.name = name;
  error.stack = `${name}: ${message}\n    at test.js:1:1`;
  return error;
};

/**
 * Mock localStorage for testing
 */
export const mockLocalStorage = () => {
  const store = {};
  return {
    getItem: vi.fn((key) => store[key] || null),
    setItem: vi.fn((key, value) => {
      store[key] = value.toString();
    }),
    removeItem: vi.fn((key) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      Object.keys(store).forEach((key) => delete store[key]);
    }),
  };
};

/**
 * Mock sessionStorage for testing
 */
export const mockSessionStorage = mockLocalStorage;

/**
 * Creates mock agent data for testing
 */
export const createMockAgent = (overrides = {}) => ({
  id: 'agent-123',
  name: 'Test Agent',
  description: 'A test agent for unit testing',
  code: 'print("Hello, World!")',
  apiSpecs: ['https://api.example.com/openapi.json'],
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
  ...overrides,
});

/**
 * Creates mock chat message for testing
 */
export const createMockChatMessage = (overrides = {}) => ({
  id: 'msg-123',
  role: 'user',
  content: 'Hello, how are you?',
  timestamp: '2024-01-01T00:00:00Z',
  ...overrides,
});

export default {
  renderWithRouter,
  renderWithTheme,
  renderWithRouterAndTheme,
  createMockUser,
  createMockResponse,
  waitForPromises,
  createMockError,
  mockLocalStorage,
  mockSessionStorage,
  createMockAgent,
  createMockChatMessage,
};
