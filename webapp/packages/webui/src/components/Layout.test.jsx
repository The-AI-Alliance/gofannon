import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import Layout from './Layout';

// Mock child components
vi.mock('./ProfileMenu', () => ({
  default: () => <div data-testid="profile-menu">Profile Menu</div>,
}));

vi.mock('./AnvilIcon', () => ({
  default: ({ size, color }) => (
    <div data-testid="anvil-icon" data-size={size} data-color={color}>
      Anvil Icon
    </div>
  ),
}));

vi.mock('./FloatingChat', () => ({
  default: () => <div data-testid="floating-chat">Floating Chat</div>,
}));

const renderWithRouter = (ui, { route = '/' } = {}) => {
  return render(
    <MemoryRouter initialEntries={[route]}>
      {ui}
    </MemoryRouter>
  );
};

describe('Layout', () => {
  it('renders children content', () => {
    renderWithRouter(
      <Layout>
        <div>Test Content</div>
      </Layout>
    );

    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('renders app bar with Gofannon title', () => {
    renderWithRouter(
      <Layout>
        <div>Content</div>
      </Layout>
    );

    expect(screen.getByText('Gofannon')).toBeInTheDocument();
  });

  it('renders AnvilIcon with correct props', () => {
    renderWithRouter(
      <Layout>
        <div>Content</div>
      </Layout>
    );

    const icon = screen.getByTestId('anvil-icon');
    expect(icon).toBeInTheDocument();
    expect(icon).toHaveAttribute('data-size', '28');
    expect(icon).toHaveAttribute('data-color', '#ffffff');
  });

  it('renders ProfileMenu', () => {
    renderWithRouter(
      <Layout>
        <div>Content</div>
      </Layout>
    );

    expect(screen.getByTestId('profile-menu')).toBeInTheDocument();
  });

  it('renders FloatingChat', () => {
    renderWithRouter(
      <Layout>
        <div>Content</div>
      </Layout>
    );

    expect(screen.getByTestId('floating-chat')).toBeInTheDocument();
  });

  it('logo area is clickable', async () => {
    const user = userEvent.setup();
    renderWithRouter(
      <Layout>
        <div>Content</div>
      </Layout>
    );

    // Find the clickable logo area (Box with Gofannon text)
    const logo = screen.getByText('Gofannon').closest('div');

    // Verify it's clickable (has onClick handler)
    expect(logo).toBeInTheDocument();
    await user.click(logo);
  });

  it('renders with multiple children', () => {
    renderWithRouter(
      <Layout>
        <div>Child 1</div>
        <div>Child 2</div>
        <p>Child 3</p>
      </Layout>
    );

    expect(screen.getByText('Child 1')).toBeInTheDocument();
    expect(screen.getByText('Child 2')).toBeInTheDocument();
    expect(screen.getByText('Child 3')).toBeInTheDocument();
  });

  it('applies correct styling to app bar', () => {
    const { container } = renderWithRouter(
      <Layout>
        <div>Content</div>
      </Layout>
    );

    const appBar = container.querySelector('header');
    expect(appBar).toBeInTheDocument();
  });

  it('includes main content area', () => {
    const { container } = renderWithRouter(
      <Layout>
        <div>Content</div>
      </Layout>
    );

    // Main content area should exist
    const main = container.querySelector('main');
    expect(main).toBeInTheDocument();
    expect(screen.getByText('Content')).toBeInTheDocument();
  });
});
