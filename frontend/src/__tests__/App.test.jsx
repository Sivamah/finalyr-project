import { render, screen } from '@testing-library/react';
import App from '../App';
import { vi } from 'vitest';

vi.mock('../services/api', () => ({
  default: { get: vi.fn(), post: vi.fn() }
}));

describe('App Component', () => {
  test('renders without crashing and defaults to Login if unauthenticated', () => {
    // Clear localStorage to simulate unauthenticated user
    localStorage.clear();
    
    render(<App />);
    
    // Should render the Login component by default when hitting '/'
    expect(screen.getByRole('button', { name: /Sign in/i })).toBeInTheDocument();
  });
});
