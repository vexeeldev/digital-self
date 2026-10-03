import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ExperienceInput from '../components/experience/ExperienceInput';
import * as api from '../lib/api';
import { Experience } from '../lib/types';

// Mock the API module
jest.mock('../lib/api', () => ({
  createExperience: jest.fn(),
}));

describe('ExperienceInput', () => {
  const mockOnExperienceAdded = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('submits experience, passes result to callback, and clears input on success', async () => {
    const mockExp: Experience = {
      id: 'exp-123',
      raw_text: 'Test experience',
      occurred_at: null,
      created_at: new Date().toISOString(),
    };
    
    (api.createExperience as jest.Mock).mockResolvedValue(mockExp);

    render(<ExperienceInput onExperienceAdded={mockOnExperienceAdded} />);

    const textarea = screen.getByPlaceholderText(/tadi di kantor/i);
    const button = screen.getByRole('button', { name: /remember/i });

    // Initial state
    expect(button).toBeDisabled();

    // Type something
    fireEvent.change(textarea, { target: { value: 'Test experience' } });
    expect(button).not.toBeDisabled();

    // Submit
    fireEvent.click(button);

    // During submission
    expect(button).toHaveTextContent(/remembering/i);
    expect(button).toBeDisabled();
    expect(textarea).toBeDisabled();

    // Wait for resolution
    await waitFor(() => {
      expect(mockOnExperienceAdded).toHaveBeenCalledWith(mockExp);
    });

    // Post-submission state
    expect(textarea).toHaveValue('');
    expect(button).toHaveTextContent(/remember/i);
  });

  it('keeps input text and shows error if submission fails, without calling callback', async () => {
    (api.createExperience as jest.Mock).mockRejectedValue(new Error('Network error'));

    render(<ExperienceInput onExperienceAdded={mockOnExperienceAdded} />);

    const textarea = screen.getByPlaceholderText(/tadi di kantor/i);
    const button = screen.getByRole('button', { name: /remember/i });

    fireEvent.change(textarea, { target: { value: 'Failing experience' } });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText(/could not remember this experience/i)).toBeInTheDocument();
    });

    // Callback should not be called
    expect(mockOnExperienceAdded).not.toHaveBeenCalled();

    // Text should remain
    expect(textarea).toHaveValue('Failing experience');
    expect(textarea).not.toBeDisabled();
  });
});
