import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import AnvilIcon from './AnvilIcon';

describe('AnvilIcon', () => {
  it('renders with default props', () => {
    const { container } = render(<AnvilIcon />);
    const svg = container.querySelector('svg');

    expect(svg).toBeInTheDocument();
    expect(svg).toHaveAttribute('width', '24');
    expect(svg).toHaveAttribute('height', '24');
    expect(svg).toHaveAttribute('fill', 'currentColor');
  });

  it('renders with custom size', () => {
    const { container } = render(<AnvilIcon size={48} />);
    const svg = container.querySelector('svg');

    expect(svg).toHaveAttribute('width', '48');
    expect(svg).toHaveAttribute('height', '48');
  });

  it('renders with custom color', () => {
    const { container } = render(<AnvilIcon color="#ff0000" />);
    const svg = container.querySelector('svg');

    expect(svg).toHaveAttribute('fill', '#ff0000');
  });

  it('renders with white color for dark backgrounds', () => {
    const { container } = render(<AnvilIcon color="white" />);
    const svg = container.querySelector('svg');

    expect(svg).toHaveAttribute('fill', 'white');
  });

  it('renders with dark color for light backgrounds', () => {
    const { container } = render(<AnvilIcon color="#18181b" />);
    const svg = container.querySelector('svg');

    expect(svg).toHaveAttribute('fill', '#18181b');
  });

  it('has correct viewBox', () => {
    const { container } = render(<AnvilIcon />);
    const svg = container.querySelector('svg');

    expect(svg).toHaveAttribute('viewBox', '0 0 100 100');
  });

  it('contains path element', () => {
    const { container } = render(<AnvilIcon />);
    const path = container.querySelector('path');

    expect(path).toBeInTheDocument();
  });

  it('renders with both custom size and color', () => {
    const { container } = render(<AnvilIcon size={64} color="blue" />);
    const svg = container.querySelector('svg');

    expect(svg).toHaveAttribute('width', '64');
    expect(svg).toHaveAttribute('height', '64');
    expect(svg).toHaveAttribute('fill', 'blue');
  });
});
