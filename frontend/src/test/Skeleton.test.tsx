import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Skeleton } from '../ui/Skeleton/Skeleton';

describe('Skeleton', () => {
  it('renders without crashing', () => {
    const { container } = render(<Skeleton />);
    expect(container.firstChild).toBeInstanceOf(HTMLElement);
  });

  it('merges custom className correctly', () => {
    const { container } = render(<Skeleton className="custom-test-class" />);
    const el = container.firstChild as HTMLElement;

    expect(el).toHaveClass('custom-test-class');
  });

  it('renders the correct inline styles based on props', () => {
    // We pass inline styles via the style prop as per standard HTML attributes
    const { container } = render(
      <Skeleton style={{ width: '200px', height: '50px', backgroundColor: 'red' }} />
    );
    const el = container.firstChild as HTMLElement;

    expect(el).toHaveStyle({
      width: '200px',
      height: '50px',
      backgroundColor: 'red',
    });
  });

  it('passes standard attributes to the element', () => {
    const { container } = render(<Skeleton data-testid="skeleton-element" />);
    const el = container.firstChild as HTMLElement;

    expect(el).toHaveAttribute('data-testid', 'skeleton-element');
  });
});
