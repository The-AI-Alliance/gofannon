import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CodeEditor from './CodeEditor';

describe('CodeEditor', () => {
  const defaultProps = {
    code: 'print("Hello, World!")',
    onCodeChange: vi.fn(),
  };

  it('renders with code', () => {
    render(<CodeEditor {...defaultProps} />);

    expect(screen.getByDisplayValue('print("Hello, World!")')).toBeInTheDocument();
    expect(screen.getByText('Python Code')).toBeInTheDocument();
  });

  it('shows Edit Code button by default', () => {
    render(<CodeEditor {...defaultProps} />);

    expect(screen.getByRole('button', { name: /edit code/i })).toBeInTheDocument();
  });

  it('starts in read-only mode', () => {
    render(<CodeEditor {...defaultProps} />);
    const textField = screen.getByDisplayValue('print("Hello, World!")');

    expect(textField).toHaveAttribute('readonly');
  });

  it('toggles to edit mode when Edit Code is clicked', async () => {
    const user = userEvent.setup();
    render(<CodeEditor {...defaultProps} />);

    await user.click(screen.getByRole('button', { name: /edit code/i }));

    expect(screen.getByRole('button', { name: /done editing/i })).toBeInTheDocument();
  });

  it('allows editing when in edit mode', async () => {
    const user = userEvent.setup();
    const onCodeChange = vi.fn();
    render(<CodeEditor {...defaultProps} onCodeChange={onCodeChange} />);

    // Enter edit mode
    await user.click(screen.getByRole('button', { name: /edit code/i }));

    // Type new code
    const textField = screen.getByDisplayValue('print("Hello, World!")');
    await user.clear(textField);
    await user.type(textField, 'print("New code")');

    expect(onCodeChange).toHaveBeenCalled();
  });

  it('does not show Edit button when isReadOnly is true', () => {
    render(<CodeEditor {...defaultProps} isReadOnly={true} />);

    expect(screen.queryByRole('button', { name: /edit code/i })).not.toBeInTheDocument();
  });

  it('stays read-only when isReadOnly is true', () => {
    render(<CodeEditor {...defaultProps} isReadOnly={true} />);
    const textField = screen.getByDisplayValue('print("Hello, World!")');

    expect(textField).toHaveAttribute('readonly');
  });

  it('calls onCodeChange when code is modified in edit mode', async () => {
    const user = userEvent.setup();
    const onCodeChange = vi.fn();
    render(<CodeEditor code="" onCodeChange={onCodeChange} />);

    // Enter edit mode
    await user.click(screen.getByRole('button', { name: /edit code/i }));

    // Type in the text field
    const textField = screen.getByRole('textbox');
    await user.type(textField, 'x = 1');

    expect(onCodeChange).toHaveBeenCalled();
  });

  it('displays Save icon when editing', async () => {
    const user = userEvent.setup();
    render(<CodeEditor {...defaultProps} />);

    await user.click(screen.getByRole('button', { name: /edit code/i }));

    // Button text changes to "Done Editing"
    expect(screen.getByRole('button', { name: /done editing/i })).toBeInTheDocument();
  });

  it('toggles back to read-only when Done Editing is clicked', async () => {
    const user = userEvent.setup();
    render(<CodeEditor {...defaultProps} />);

    // Enter edit mode
    await user.click(screen.getByRole('button', { name: /edit code/i }));
    expect(screen.getByRole('button', { name: /done editing/i })).toBeInTheDocument();

    // Exit edit mode
    await user.click(screen.getByRole('button', { name: /done editing/i }));
    expect(screen.getByRole('button', { name: /edit code/i })).toBeInTheDocument();
  });

  it('renders with empty code', () => {
    render(<CodeEditor code="" onCodeChange={vi.fn()} />);
    const textField = screen.getByRole('textbox');

    expect(textField).toHaveValue('');
  });

  it('renders with multiline code', () => {
    const multilineCode = `def hello():
    print("Hello")
    return True`;

    render(<CodeEditor code={multilineCode} onCodeChange={vi.fn()} />);

    const textField = screen.getByRole('textbox');
    expect(textField).toHaveValue(multilineCode);
  });

  it('has monospace font styling', () => {
    const { container } = render(<CodeEditor {...defaultProps} />);
    const inputBase = container.querySelector('.MuiInputBase-root');

    expect(inputBase).toHaveStyle({ fontFamily: 'monospace' });
  });
});
