# Frontend Testing Guide

This guide covers testing React components using Vitest and React Testing Library.

## Overview

- **Framework:** [Vitest](https://vitest.dev/)
- **DOM Testing:** [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- **Location:** Co-located with components (`*.test.jsx`)
- **Configuration:** `webapp/packages/webui/vitest.config.ts`

## Running Tests

```bash
cd webapp/packages/webui

# Run all tests
pnpm test

# Run tests in watch mode
pnpm test -- --watch

# Run with coverage
pnpm test:coverage

# Run with UI
pnpm test:ui

# Run specific file
pnpm test ActionCard.test.jsx

# Run tests matching pattern
pnpm test -- --grep "renders"
```

### Via pnpm (from webapp/)

```bash
cd webapp
pnpm test:unit:frontend
pnpm test:coverage:frontend
```

## Test Location

Tests are co-located with their components:

```
src/
├── components/
│   ├── ActionCard.jsx
│   ├── ActionCard.test.jsx    # Component test
│   ├── AgentEditor/
│   │   ├── AgentEditor.jsx
│   │   └── AgentEditor.test.jsx
├── hooks/
│   ├── useAuth.js
│   └── useAuth.test.js        # Hook test
└── utils/
    ├── formatters.js
    └── formatters.test.js     # Utility test
```

## Writing Component Tests

### Basic Component Test

```jsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ActionCard from './ActionCard';
import { Settings as SettingsIcon } from '@mui/icons-material';

describe('ActionCard', () => {
  const defaultProps = {
    icon: <SettingsIcon />,
    title: 'Test Action',
    description: 'Test description',
    buttonText: 'Click Me',
    onClick: vi.fn(),
  };

  it('renders with required props', () => {
    render(<ActionCard {...defaultProps} />);

    expect(screen.getByText('Test Action')).toBeInTheDocument();
    expect(screen.getByText('Test description')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Click Me' })).toBeInTheDocument();
  });

  it('calls onClick when button is clicked', async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();

    render(<ActionCard {...defaultProps} onClick={onClick} />);

    await user.click(screen.getByRole('button', { name: 'Click Me' }));

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('disables button when disabled prop is true', () => {
    render(<ActionCard {...defaultProps} disabled />);

    expect(screen.getByRole('button')).toBeDisabled();
  });
});
```

### Testing with Context Providers

```jsx
import { render, screen } from '@testing-library/react';
import { AuthContext } from '../contexts/AuthContext';
import { BrowserRouter } from 'react-router-dom';
import UserProfile from './UserProfile';

// Helper to render with providers
const renderWithProviders = (component, { authValue = {}, ...options } = {}) => {
  return render(
    <BrowserRouter>
      <AuthContext.Provider value={authValue}>
        {component}
      </AuthContext.Provider>
    </BrowserRouter>,
    options
  );
};

describe('UserProfile', () => {
  it('shows user name when authenticated', () => {
    renderWithProviders(<UserProfile />, {
      authValue: { user: { id: '123', displayName: 'John Doe' } }
    });

    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });

  it('shows login prompt when not authenticated', () => {
    renderWithProviders(<UserProfile />, {
      authValue: { user: null }
    });

    expect(screen.getByText('Please log in')).toBeInTheDocument();
  });
});
```

### Testing Hooks

```jsx
import { renderHook, act } from '@testing-library/react';
import { useCounter } from './useCounter';

describe('useCounter', () => {
  it('initializes with default value', () => {
    const { result } = renderHook(() => useCounter());

    expect(result.current.count).toBe(0);
  });

  it('initializes with provided value', () => {
    const { result } = renderHook(() => useCounter(10));

    expect(result.current.count).toBe(10);
  });

  it('increments counter', () => {
    const { result } = renderHook(() => useCounter());

    act(() => {
      result.current.increment();
    });

    expect(result.current.count).toBe(1);
  });

  it('decrements counter', () => {
    const { result } = renderHook(() => useCounter(5));

    act(() => {
      result.current.decrement();
    });

    expect(result.current.count).toBe(4);
  });
});
```

### Testing Async Components

```jsx
import { render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import AgentList from './AgentList';
import * as api from '../services/api';

// Mock the API module
vi.mock('../services/api');

describe('AgentList', () => {
  it('shows loading state initially', () => {
    api.fetchAgents.mockReturnValue(new Promise(() => {})); // Never resolves

    render(<AgentList />);

    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('displays agents after loading', async () => {
    api.fetchAgents.mockResolvedValue([
      { id: '1', name: 'Agent One' },
      { id: '2', name: 'Agent Two' },
    ]);

    render(<AgentList />);

    await waitFor(() => {
      expect(screen.getByText('Agent One')).toBeInTheDocument();
      expect(screen.getByText('Agent Two')).toBeInTheDocument();
    });
  });

  it('shows error message on fetch failure', async () => {
    api.fetchAgents.mockRejectedValue(new Error('Network error'));

    render(<AgentList />);

    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });
});
```

### Mocking API Calls with Axios

```jsx
import { vi } from 'vitest';
import axios from 'axios';
import { render, screen, waitFor } from '@testing-library/react';
import UserProfile from './UserProfile';

vi.mock('axios');

describe('UserProfile', () => {
  it('fetches and displays user data', async () => {
    axios.get.mockResolvedValue({
      data: { id: '123', name: 'Test User', email: 'test@example.com' }
    });

    render(<UserProfile userId="123" />);

    await waitFor(() => {
      expect(screen.getByText('Test User')).toBeInTheDocument();
      expect(screen.getByText('test@example.com')).toBeInTheDocument();
    });

    expect(axios.get).toHaveBeenCalledWith('/api/users/123');
  });
});
```

### Testing Form Interactions

```jsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import LoginForm from './LoginForm';

describe('LoginForm', () => {
  it('submits form with entered values', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();

    render(<LoginForm onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText('Email'), 'test@example.com');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.click(screen.getByRole('button', { name: 'Login' }));

    expect(onSubmit).toHaveBeenCalledWith({
      email: 'test@example.com',
      password: 'password123',
    });
  });

  it('shows validation error for invalid email', async () => {
    const user = userEvent.setup();

    render(<LoginForm onSubmit={vi.fn()} />);

    await user.type(screen.getByLabelText('Email'), 'invalid-email');
    await user.click(screen.getByRole('button', { name: 'Login' }));

    expect(screen.getByText(/invalid email/i)).toBeInTheDocument();
  });
});
```

## Configuration

### vitest.config.ts

```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
      ],
      thresholds: {
        lines: 95,
        functions: 95,
        branches: 95,
        statements: 95,
      },
    },
  },
});
```

### Test Setup (src/test/setup.ts)

```typescript
import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});
```

## Best Practices

1. **Query by accessibility:** Prefer `getByRole`, `getByLabelText` over `getByTestId`
2. **Use `userEvent` over `fireEvent`** for realistic user interactions
3. **Test behavior, not implementation:** Don't test internal state
4. **Keep tests focused:** One behavior per test
5. **Use meaningful assertions:** `toBeInTheDocument()`, `toHaveTextContent()`

## Common Queries

| Query | Use Case |
|-------|----------|
| `getByRole` | Interactive elements (buttons, inputs, links) |
| `getByLabelText` | Form inputs with labels |
| `getByText` | Text content |
| `getByPlaceholderText` | Inputs with placeholders |
| `getByTestId` | Last resort when no semantic query works |

## Related Documentation

- [Unit Testing Guide](unit-testing.md) - General patterns
- [Contributing Tests](contributing.md) - PR requirements
- [React Testing Library Docs](https://testing-library.com/docs/react-testing-library/intro/)