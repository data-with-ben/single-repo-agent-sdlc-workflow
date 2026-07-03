import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import App from './App';

afterEach(() => {
  cleanup();
});

describe('App', () => {
  it('renders without crashing', () => {
    const { container } = render(<App />);
    expect(container.querySelector('main')).not.toBeNull();
  });

  it('renders the hello-world heading', () => {
    render(<App />);
    expect(screen.getByText('Hello, Fantasy Timesheets')).not.toBeNull();
  });
});
