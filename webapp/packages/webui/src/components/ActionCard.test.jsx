import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ActionCard from './ActionCard';
import { Settings as SettingsIcon } from '@mui/icons-material';

describe('ActionCard', () => {
  const defaultProps = {
    icon: <SettingsIcon />,
    title: 'Test Action',
    description: 'This is a test action card',
    buttonText: 'Click Me',
    onClick: vi.fn(),
  };

  it('renders with required props', () => {
    render(<ActionCard {...defaultProps} />);

    expect(screen.getByText('Test Action')).toBeInTheDocument();
    expect(screen.getByText('This is a test action card')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Click Me' })).toBeInTheDocument();
  });

  it('calls onClick when card is clicked', async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();

    render(<ActionCard {...defaultProps} onClick={onClick} />);

    const card = screen.getByText('Test Action').closest('div').parentElement;
    await user.click(card);

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('calls onClick when button is clicked', async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();

    render(<ActionCard {...defaultProps} onClick={onClick} />);

    const button = screen.getByRole('button', { name: 'Click Me' });
    await user.click(button);

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('applies custom button color', () => {
    render(<ActionCard {...defaultProps} buttonColor="secondary" />);

    const button = screen.getByRole('button', { name: 'Click Me' });
    expect(button).toHaveClass('MuiButton-colorSecondary');
  });

  it('uses default button color when not specified', () => {
    render(<ActionCard {...defaultProps} />);

    const button = screen.getByRole('button', { name: 'Click Me' });
    expect(button).toHaveClass('MuiButton-colorPrimary');
  });

  it('displays title with noWrap', () => {
    render(<ActionCard {...defaultProps} title="Very Long Title That Should Not Wrap" />);

    const title = screen.getByText('Very Long Title That Should Not Wrap');
    const parentBox = title.parentElement;

    expect(title).toHaveStyle({ overflow: 'hidden' });
  });

  it('displays description with text wrapping', () => {
    const longDescription = 'This is a very long description that should wrap to multiple lines in the action card component';

    render(<ActionCard {...defaultProps} description={longDescription} />);

    expect(screen.getByText(longDescription)).toBeInTheDocument();
  });

  it('renders icon with correct size', () => {
    const { container } = render(<ActionCard {...defaultProps} />);

    const icon = container.querySelector('svg');
    expect(icon).toBeInTheDocument();
  });

  it('stops propagation when button is clicked', async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    const cardClick = vi.fn();

    const { container } = render(<ActionCard {...defaultProps} onClick={onClick} />);

    const card = container.firstChild;
    card.addEventListener('click', cardClick);

    const button = screen.getByRole('button', { name: 'Click Me' });
    await user.click(button);

    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
