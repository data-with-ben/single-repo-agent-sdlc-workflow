import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import App from './App';

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      json: () => Promise.resolve([]),
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
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
