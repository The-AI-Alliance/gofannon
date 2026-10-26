// AuthExpiryModal listens for the auth:session-expired event
// and renders the modal with a sign-in button.
import { render, screen, act } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import AuthExpiryModal from './AuthExpiryModal';

describe('AuthExpiryModal', () => {
  beforeEach(() => {
    window.history.replaceState({}, '', '/');
  });

  it('is hidden until the auth:session-expired event fires', () => {
    render(<AuthExpiryModal />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('opens on auth:session-expired with returnTo from event detail', () => {
    render(<AuthExpiryModal />);
    act(() => {
      window.dispatchEvent(new CustomEvent('auth:session-expired', {
        detail: { returnTo: '/agents/abc123' },
      }));
    });
    expect(screen.getByText(/Your session has expired/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('navigates to login with returnTo encoded', () => {
    const hrefSetter = vi.fn();
    const original = window.location;
    delete window.location;
    window.location = { href: '/', search: '' };
    Object.defineProperty(window.location, 'href', { set: hrefSetter, configurable: true });

    render(<AuthExpiryModal />);
    act(() => {
      window.dispatchEvent(new CustomEvent('auth:session-expired', {
        detail: { returnTo: '/agents/abc' },
      }));
    });
    screen.getByRole('button', { name: /sign in/i }).click();
    expect(hrefSetter).toHaveBeenCalledWith('/login?returnTo=%2Fagents%2Fabc');
    window.location = original;
  });
});
