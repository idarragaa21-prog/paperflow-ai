import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import SectionErrorBoundary from '../components/SectionErrorBoundary';

// A child component that throws an error when told to
function Bomb({ shouldThrow = false }: { shouldThrow?: boolean }) {
  if (shouldThrow) {
    throw new Error('Boom!');
  }
  return <div>Safe Child</div>;
}

describe('SectionErrorBoundary', () => {
  // Suppress React's default console.error for expected errors in Error Boundaries
  // and spy on console.warn for SectionErrorBoundary's specific logging
  let consoleErrorSpy: ReturnType<typeof vi.spyOn>;
  let consoleWarnSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
    consoleWarnSpy.mockRestore();
  });

  it('renders children normally when no error is thrown', () => {
    render(
      <SectionErrorBoundary>
        <Bomb />
      </SectionErrorBoundary>
    );
    expect(screen.getByText('Safe Child')).toBeInTheDocument();
  });

  it('catches errors and renders default error UI with label', () => {
    render(
      <SectionErrorBoundary label="Test Section">
        <Bomb shouldThrow={true} />
      </SectionErrorBoundary>
    );

    // Verify error UI is displayed
    expect(screen.getByText('⚠ "Test Section" failed to render')).toBeInTheDocument();
    expect(screen.getByText('Boom!')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();

    // Verify it warned properly
    expect(consoleWarnSpy).toHaveBeenCalledWith(
      '[SectionErrorBoundary] Test Section crashed:',
      expect.any(Error),
      expect.any(String)
    );
  });

  it('catches errors and renders custom fallback when provided', () => {
    render(
      <SectionErrorBoundary fallback={<div data-testid="custom-fallback">Custom Error View</div>}>
        <Bomb shouldThrow={true} />
      </SectionErrorBoundary>
    );

    expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
    expect(screen.getByText('Custom Error View')).toBeInTheDocument();
    // Default error UI shouldn't be there
    expect(screen.queryByText('Retry')).not.toBeInTheDocument();
  });

  it('allows retrying after an error', () => {
    const { rerender } = render(
      <SectionErrorBoundary label="Retryable Section">
        <Bomb shouldThrow={true} />
      </SectionErrorBoundary>
    );

    // Ensure error UI is shown
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();

    // Rerender with safe child so retry can succeed
    rerender(
      <SectionErrorBoundary label="Retryable Section">
        <Bomb shouldThrow={false} />
      </SectionErrorBoundary>
    );

    // Click retry
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));

    // Verify the safe child is now shown
    expect(screen.getByText('Safe Child')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument();
  });
});
