# Unit Testing Guide

Unit tests verify individual functions, classes, and components in isolation from external dependencies.

## Overview

- **Framework (Frontend)**: Vitest + React Testing Library
- **Framework (Backend)**: pytest + pytest-mock
- **Location**: `tests/unit/` directory
- **Mocking**: Mock all external dependencies (DB, APIs, file system)
- **Coverage**: Must maintain ≥95% coverage

## Writing Backend Unit Tests (Python)

### Basic Structure

```python
import pytest
from unittest.mock import Mock, AsyncMock
from services.user_service import UserService

pytestmark = pytest.mark.unit  # Mark as unit test


class TestUserService:
    """Test suite for UserService class."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database service."""
        db = Mock()
        db.get = Mock(return_value={"id": "test-123"})
        db.save = Mock(return_value={"rev": "test-rev"})
        return db

    @pytest.fixture
    def user_service(self, mock_db):
        """Create a UserService instance with mock database."""
        return UserService(mock_db)

    def test_get_user_existing(self, user_service, mock_db):
        """Test getting an existing user."""
        user = user_service.get_user("test-123")

        mock_db.get.assert_called_once_with("users", "test-123")
        assert user.id == "test-123"

    def test_get_user_not_found(self, user_service, mock_db):
        """Test handling of user not found."""
        from fastapi import HTTPException
        mock_db.get.side_effect = HTTPException(status_code=404)

        user = user_service.get_user("new-user")

        assert user.id == "new-user"
        mock_db.save.assert_called_once()  # Creates new user
```

### Using Test Factories

```python
from tests.factories.user_factory import UserFactory

def test_user_creation():
    """Test user creation with factory data."""
    user_data = UserFactory.build()

    assert "uid" in user_data
    assert "email" in user_data
    assert user_data["email_verified"] == True

def test_multiple_users():
    """Create multiple test users."""
    users = UserFactory.build_batch(5)

    assert len(users) == 5
    assert all(u["email"] for u in users)
```

### Testing Async Functions

```python
import pytest

pytestmark = pytest.mark.asyncio  # Enable async support


async def test_async_function():
    """Test an async function."""
    result = await my_async_function()
    assert result == expected_value


async def test_with_async_mock(mocker):
    """Test with async mocked dependency."""
    mock_service = mocker.AsyncMock()
    mock_service.fetch_data.return_value = {"data": "test"}

    result = await function_using_service(mock_service)

    mock_service.fetch_data.assert_called_once()
    assert result["data"] == "test"
```

### Testing Models (Pydantic)

```python
import pytest
from pydantic import ValidationError
from models.user import User, BasicInfo

def test_user_creation_minimal():
    """Test creating a User with minimal required fields."""
    user = User(_id="test-123")

    assert user.id == "test-123"
    assert user.rev is None

def test_user_validation_fails_without_id():
    """Test that User requires an ID."""
    with pytest.raises(ValidationError):
        User()

def test_user_from_dict():
    """Test creating User from dictionary."""
    data = {
        "_id": "test-123",
        "basicInfo": {"displayName": "Test User"}
    }
    user = User(**data)

    assert user.id == "test-123"
    assert user.basic_info.display_name == "Test User"
```

## Writing Frontend Unit Tests (JavaScript/React)

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
  });

  it('calls onClick when button is clicked', async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();

    render(<ActionCard {...defaultProps} onClick={onClick} />);

    await user.click(screen.getByRole('button', { name: 'Click Me' }));

    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
```

### Testing with Context

```jsx
import { render } from '@testing-library/react';
import { AuthContext } from '../contexts/AuthContext';

const renderWithAuth = (component, authValue) => {
  return render(
    <AuthContext.Provider value={authValue}>
      {component}
    </AuthContext.Provider>
  );
};

it('shows logout button when authenticated', () => {
  renderWithAuth(<MyComponent />, { user: { id: '123' } });

  expect(screen.getByText('Logout')).toBeInTheDocument();
});
```

### Testing Hooks

```jsx
import { renderHook, act } from '@testing-library/react';
import { useCounter } from './useCounter';

it('increments counter', () => {
  const { result } = renderHook(() => useCounter());

  act(() => {
    result.current.increment();
  });

  expect(result.current.count).toBe(1);
});
```

### Mocking API Calls

```jsx
import { vi } from 'vitest';
import axios from 'axios';

vi.mock('axios');

it('fetches user data', async () => {
  axios.get.mockResolvedValue({
    data: { id: '123', name: 'Test User' }
  });

  render(<UserProfile userId="123" />);

  await screen.findByText('Test User');

  expect(axios.get).toHaveBeenCalledWith('/api/users/123');
});
```

## Running Unit Tests

### Frontend Tests

```bash
cd webapp/packages/webui

# Run tests
pnpm test

# Run tests in watch mode
pnpm test -- --watch

# Run tests with coverage
pnpm test:coverage

# Run tests with UI
pnpm test:ui

# Run specific test file
pnpm test ActionCard.test.jsx
```

### Backend Tests

```bash
cd webapp/packages/api/user-service

# Run all unit tests
python -m pytest tests/unit -v

# Run specific test file
python -m pytest tests/unit/test_user_service.py -v

# Run specific test
python -m pytest tests/unit/test_user_service.py::TestUserService::test_get_user -v

# Run with coverage
python -m pytest tests/unit --cov=. --cov-report=html

# Run in watch mode (requires pytest-watch)
ptw tests/unit
```

## Best Practices

### 1. Test One Thing Per Test

```python
# Good
def test_user_creation_sets_email():
    user = create_user(email="test@example.com")
    assert user.email == "test@example.com"

def test_user_creation_sets_timestamp():
    user = create_user()
    assert user.created_at is not None

# Bad
def test_user_creation():
    user = create_user(email="test@example.com")
    assert user.email == "test@example.com"
    assert user.created_at is not None
    assert user.id is not None
```

### 2. Use Descriptive Names

```python
# Good
def test_get_user_raises_exception_when_database_unavailable():
    pass

# Bad
def test_get_user():
    pass
```

### 3. Follow AAA Pattern (Arrange, Act, Assert)

```python
def test_add_usage_deducts_from_remaining():
    # Arrange
    user = User(_id="test-123")
    user.usage_info.spend_remaining = 100.0
    mock_db.get.return_value = user.model_dump()

    # Act
    updated_user = user_service.add_usage("test-123", 25.0)

    # Assert
    assert updated_user.usage_info.spend_remaining == 75.0
```

### 4. Mock External Dependencies

```python
# Good - mocked database
def test_save_user(user_service, mock_db):
    user = User(_id="test-123")
    user_service.save_user(user)

    mock_db.save.assert_called_once()

# Bad - real database (integration test)
def test_save_user():
    user = User(_id="test-123")
    db = CouchDB(url="http://localhost:5984")  # Real connection!
    user_service = UserService(db)
    user_service.save_user(user)
```

### 5. Test Edge Cases

```python
def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)

def test_empty_list():
    result = process_items([])
    assert result == []

def test_null_input():
    result = process_user(None)
    assert result is None
```

### 6. Use Parametrize for Similar Tests

```python
@pytest.mark.parametrize("input,expected", [
    ("hello", "Hello"),
    ("WORLD", "World"),
    ("", ""),
    ("123", "123"),
])
def test_capitalize(input, expected):
    assert capitalize(input) == expected
```

## Common Patterns

### Testing Exceptions

```python
def test_invalid_input_raises_value_error():
    with pytest.raises(ValueError, match="Invalid input"):
        process_data("invalid")
```

### Testing HTTP Errors

```python
def test_not_found_returns_404():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        get_user("nonexistent")

    assert exc_info.value.status_code == 404
```

### Testing Private Methods

```python
def test_private_method():
    service = MyService()
    # Access private method for testing
    result = service._private_method("test")
    assert result == expected
```

## Troubleshooting

### Tests Hanging
- Check for missing `await` on async functions
- Verify mocks are properly configured
- Look for infinite loops or blocking calls

### Import Errors
- Verify `PYTHONPATH` includes project root
- Check for circular imports
- Ensure `__init__.py` files exist

### Flaky Tests
- Remove time-based assertions
- Ensure test isolation (no shared state)
- Check for race conditions in async code

### Coverage Not Increasing
- Verify test markers are correct
- Check `.coveragerc` exclusions
- Run coverage report to see uncovered lines

## Next Steps

- Read [Integration Testing Guide](./integration-testing.md)
- Review [Frontend Testing Guide](./frontend-testing.md)
- Check [Contributing Tests](./contributing.md)
