# Contributing Tests

This guide explains the testing requirements for contributing code to Gofannon.

## Pull Request Requirements

Every PR must include:

1. ✅ **Tests for all new code**
2. ✅ **Tests for modified code** (if changing behavior)
3. ✅ **95% minimum coverage** on changed files
4. ✅ **All tests passing** (unit + integration)
5. ✅ **No lint errors**

## PR Testing Checklist

Before submitting your PR, verify:

- [ ] I've written unit tests for new functions/components
- [ ] I've written integration tests for new endpoints/features
- [ ] All tests pass locally
- [ ] Coverage is ≥95% on files I modified
- [ ] Tests follow the project's testing patterns
- [ ] Test names clearly describe what they test
- [ ] No tests are skipped or commented out
- [ ] CI/CD checks are passing

## Writing Tests for Your Changes

### For New Features

1. **Write tests first** (TDD approach recommended)
2. **Cover happy path** - normal successful execution
3. **Cover edge cases** - empty input, null values, boundaries
4. **Cover error cases** - validation failures, exceptions
5. **Test interactions** - how your feature works with others

### For Bug Fixes

1. **Write a failing test** that reproduces the bug
2. **Fix the bug**
3. **Verify the test passes**
4. **Add additional tests** for related edge cases

### For Refactoring

1. **Ensure existing tests pass** before starting
2. **Don't modify test expectations** (behavior shouldn't change)
3. **Add tests if coverage decreased**
4. **Verify all tests still pass** after refactoring

## Test Coverage Rules

### You Are Responsible For

- **Files you create**: 95% minimum coverage
- **Files you modify**: Maintain or improve existing coverage
- **New functions/methods**: 100% coverage (no exceptions)

### Coverage Exceptions

Only exclude from coverage:
- Type checking blocks (`if TYPE_CHECKING:`)
- Abstract methods (`@abstractmethod`)
- Main blocks (`if __name__ == "__main__":`)
- Explicitly unreachable code (`pragma: no cover`)

Never exclude:
- Business logic
- Error handling
- Validation code
- Utility functions

## Test Organization

### File Naming

```
# Backend (Python)
tests/unit/test_<module_name>.py
tests/integration/test_<feature_name>.py

# Frontend (JavaScript)
src/components/ComponentName.test.jsx
src/utils/utilityName.test.js
```

### Test Structure

```python
# Backend
class TestFeatureName:
    """Test suite for FeatureName."""

    def test_feature_does_something_when_condition(self):
        """Test that feature does X when Y happens."""
        # Arrange
        # Act
        # Assert
```

```jsx
// Frontend
describe('ComponentName', () => {
  describe('when prop X is true', () => {
    it('renders element Y', () => {
      // Arrange, Act, Assert
    });
  });
});
```

## Common Scenarios

### Adding a New API Endpoint

**Required Tests:**
1. Unit test for the route handler function
2. Unit tests for any new service methods
3. Integration test for the full HTTP request/response
4. Test authentication/authorization
5. Test validation errors
6. Test success case with valid data

**Example:**
```python
# tests/unit/test_routes.py
def test_create_agent_validates_input(mock_db):
    with pytest.raises(ValidationError):
        create_agent(CreateAgentRequest(name=""))  # Empty name

def test_create_agent_saves_to_database(mock_db):
    agent = create_agent(CreateAgentRequest(name="Test"))
    mock_db.save.assert_called_once()

# tests/integration/test_agent_endpoints.py
def test_create_agent_endpoint(client):
    response = client.post("/agents", json={"name": "Test"})
    assert response.status_code == 201
    assert response.json()["name"] == "Test"
```

### Adding a New React Component

**Required Tests:**
1. Test component renders with required props
2. Test user interactions (clicks, typing, etc.)
3. Test conditional rendering
4. Test prop validation/defaults
5. Test error states
6. Test accessibility

**Example:**
```jsx
// ActionCard.test.jsx
describe('ActionCard', () => {
  it('renders with required props', () => {
    render(<ActionCard {...requiredProps} />);
    expect(screen.getByText('Title')).toBeInTheDocument();
  });

  it('calls onClick when clicked', async () => {
    const onClick = vi.fn();
    render(<ActionCard {...requiredProps} onClick={onClick} />);

    await userEvent.click(screen.getByRole('button'));

    expect(onClick).toHaveBeenCalled();
  });

  it('shows error message when prop is invalid', () => {
    render(<ActionCard {...requiredProps} title="" />);
    expect(screen.getByText('Title is required')).toBeInTheDocument();
  });
});
```

### Modifying Existing Code

1. **Run existing tests** to verify they still pass
2. **Update tests** if behavior changed (document why in PR)
3. **Add new tests** for new behavior/edge cases
4. **Ensure coverage** doesn't decrease

## Running Tests Locally

### Before Creating PR

```bash
# 1. Run all unit tests
cd webapp
pnpm test:unit

# 2. Check coverage
pnpm test:coverage

# 3. Run integration tests if you changed API/services
pnpm test:integration

# 4. Run lint
cd packages/webui
pnpm lint

# 5. Verify everything passes
cd ../..
pnpm test
```

### During PR Review

If CI fails:
1. Check GitHub Actions logs
2. Reproduce failure locally
3. Fix the issue
4. Re-run tests locally
5. Push fix

## Code Review Focus

Reviewers will check:
- [ ] Tests cover new/modified code
- [ ] Test names are descriptive
- [ ] Tests are independent (no shared state)
- [ ] Appropriate test type (unit vs integration)
- [ ] Mocks used correctly in unit tests
- [ ] Edge cases covered
- [ ] No flaky tests (random failures)
- [ ] Coverage meets 95% threshold

## Examples of Good PRs

### Example 1: New Feature

```
Title: Add user allowance reset endpoint

Tests Added:
- test_reset_allowance_sets_to_monthly_limit (unit)
- test_reset_allowance_clears_usage_history (unit)
- test_reset_allowance_endpoint_returns_updated_user (integration)
- test_reset_allowance_requires_authentication (integration)

Coverage: 98% on modified files
```

### Example 2: Bug Fix

```
Title: Fix user creation with missing email

Tests Added:
- test_create_user_without_email_uses_default (unit)
- test_create_user_with_null_email_raises_error (unit)

Before: Bug allowed null emails
After: Bug fixed, tests verify correct behavior
Coverage: 100% on user_service.py
```

## Getting Help

### Test Writing Help
- Review existing tests in similar files
- Check the [Unit Testing Guide](./unit-testing.md)
- Ask in team chat or PR comments

### Coverage Issues
- Run `pnpm test:coverage` to see uncovered lines
- Focus on testing the red lines in coverage report
- Review [Coverage Requirements](./coverage.md)

### CI Failures
- Check GitHub Actions logs for error details
- Reproduce locally with same command from CI
- Check if it's a timing issue (flaky test)

## Common Mistakes to Avoid

### 1. Not Testing Error Cases

```python
# Bad - only tests success
def test_create_user():
    user = create_user("test@example.com")
    assert user.email == "test@example.com"

# Good - tests error cases too
def test_create_user_with_invalid_email():
    with pytest.raises(ValidationError):
        create_user("invalid-email")

def test_create_user_with_duplicate_email():
    create_user("test@example.com")
    with pytest.raises(DuplicateEmailError):
        create_user("test@example.com")
```

### 2. Testing Implementation Instead of Behavior

```jsx
// Bad - tests implementation detail
it('calls setState with correct value', () => {
  const setState = vi.spyOn(component, 'setState');
  component.handleClick();
  expect(setState).toHaveBeenCalledWith({ clicked: true });
});

// Good - tests visible behavior
it('shows success message after clicking', async () => {
  render(<Component />);
  await userEvent.click(screen.getByRole('button'));
  expect(screen.getByText('Success!')).toBeInTheDocument();
});
```

### 3. Shared State Between Tests

```python
# Bad - shared state
user = User(_id="test-123")

def test_update_email():
    user.email = "new@example.com"  # Modifies shared object!

def test_update_name():
    user.name = "New Name"  # Depends on previous test!

# Good - isolated tests
def test_update_email():
    user = User(_id="test-123")
    user.email = "new@example.com"

def test_update_name():
    user = User(_id="test-123")
    user.name = "New Name"
```

### 4. Skipping Integration Tests

```python
# Bad - only unit tests for new endpoint
def test_create_agent_saves_to_db(mock_db):
    create_agent(data, mock_db)
    mock_db.save.assert_called()

# Good - also has integration test
def test_create_agent_endpoint_e2e(client):
    response = client.post("/agents", json=valid_data)
    assert response.status_code == 201

    # Verify it's actually in the database
    agent = client.get(f"/agents/{response.json()['id']}")
    assert agent.json()["name"] == valid_data["name"]
```

## PR Approval Criteria

Your PR will be approved when:
1. ✅ All CI checks pass
2. ✅ Coverage is ≥95%
3. ✅ Tests are well-written and maintainable
4. ✅ Code review feedback addressed
5. ✅ Documentation updated (if needed)

## Resources

- [Unit Testing Guide](./unit-testing.md)
- [Integration Testing Guide](./integration-testing.md)
- [Frontend Testing Guide](./frontend-testing.md)
- [Backend Testing Guide](./backend-testing.md)
- [CI/CD Testing](./ci-cd.md)
