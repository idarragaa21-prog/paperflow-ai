import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { InsightCard } from '../components/WorkflowPrimitives';

describe('InsightCard', () => {
  it('renders with all props provided', () => {
    const { container } = render(
      <InsightCard
        eyebrow="My Eyebrow"
        title="My Title"
        body="My Body"
        action={<button>Click Me</button>}
        tone="success"
      />
    );

    expect(screen.getByText('My Eyebrow')).toBeInTheDocument();
    expect(screen.getByText('My Title')).toBeInTheDocument();
    expect(screen.getByText('My Body')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Click Me' })).toBeInTheDocument();

    const element = container.firstChild as HTMLElement;
    expect(element.className).toContain('success');
  });

  it('renders without optional props', () => {
    const { container } = render(<InsightCard title="My Title" body="My Body" />);

    expect(screen.getByText('My Title')).toBeInTheDocument();
    expect(screen.getByText('My Body')).toBeInTheDocument();

    // Eyebrow and Action should not be present
    expect(screen.queryByText('My Eyebrow')).not.toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();

    // Default tone should be 'neutral'
    const element = container.firstChild as HTMLElement;
    expect(element.className).toContain('neutral');
  });

  it('applies the primary tone correctly', () => {
    const { container } = render(<InsightCard title="Title" body="Body" tone="primary" />);
    const element = container.firstChild as HTMLElement;
    expect(element.className).toContain('primary');
  });

  it('applies the warning tone correctly', () => {
    const { container } = render(<InsightCard title="Title" body="Body" tone="warning" />);
    const element = container.firstChild as HTMLElement;
    expect(element.className).toContain('warning');
  });
});
