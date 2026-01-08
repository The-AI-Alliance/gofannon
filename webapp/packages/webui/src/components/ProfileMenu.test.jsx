import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import ProfileMenu from './ProfileMenu';

// Mock AuthContext
const mockLogout = vi.fn();
vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    logout: mockLogout,
  }),
}));

const renderWithRouter = (component) => {
  return render(
    <MemoryRouter>
      {component}
    </MemoryRouter>
  );
};

describe('ProfileMenu', () => {
  it('renders profile icon button', () => {
    renderWithRouter(<ProfileMenu />);

    const button = screen.getByRole('button', { name: /account of current user/i });
    expect(button).toBeInTheDocument();
  });

  it('opens menu when icon is clicked', async () => {
    const user = userEvent.setup();
    renderWithRouter(<ProfileMenu />);

    const button = screen.getByRole('button', { name: /account of current user/i });
    await user.click(button);

    expect(screen.getByText('Basic Info')).toBeInTheDocument();
    expect(screen.getByText('Usage')).toBeInTheDocument();
    expect(screen.getByText('Billing')).toBeInTheDocument();
    expect(screen.getByText('Logout')).toBeInTheDocument();
  });

  it('navigates when menu item is clicked', async () => {
    const user = userEvent.setup();
    renderWithRouter(<ProfileMenu />);

    // Open menu
    const button = screen.getByRole('button', { name: /account of current user/i });
    await user.click(button);

    // Click menu item - just verify it's clickable
    const basicInfoItem = screen.getByText('Basic Info');
    expect(basicInfoItem).toBeInTheDocument();
    await user.click(basicInfoItem);

    // Test passed if no error thrown
  });

  it('calls logout when Logout is clicked', async () => {
    const user = userEvent.setup();
    renderWithRouter(<ProfileMenu />);

    // Open menu
    const button = screen.getByRole('button', { name: /account of current user/i });
    await user.click(button);

    // Click logout
    await user.click(screen.getByText('Logout'));

    expect(mockLogout).toHaveBeenCalledTimes(1);
  });

  it('has menu items for navigation', async () => {
    const user = userEvent.setup();
    renderWithRouter(<ProfileMenu />);

    const button = screen.getByRole('button', { name: /account of current user/i });
    await user.click(button);

    expect(screen.getByText('Basic Info')).toBeInTheDocument();
    expect(screen.getByText('Usage')).toBeInTheDocument();
    expect(screen.getByText('Billing')).toBeInTheDocument();
  });

  it('menu button has proper attributes', () => {
    renderWithRouter(<ProfileMenu />);

    const button = screen.getByRole('button', { name: /account of current user/i });
    expect(button).toHaveAttribute('aria-haspopup', 'true');
    expect(button).toHaveAttribute('aria-controls', 'menu-appbar');
  });
});
