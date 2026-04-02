import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { InsightCard } from '../components/WorkflowPrimitives';

describe('InsightCard', () => {
  it('renders required props (title, body) correctly', () => {
    render(<InsightCard title="Test Title" body="Test Body" />);
    expect(screen.getByText('Test Title')).toBeInTheDocument();
    expect(screen.getByText('Test Body')).toBeInTheDocument();
  });

  it('applies the default tone class based on neutral default prop', () => {
    const { container } = render(<InsightCard title="Test Title" body="Test Body" />);
    const cardDiv = container.firstChild as HTMLElement;
    expect(cardDiv.className).toContain('neutral');
  });

  it('correctly applies custom tone classes', () => {
    const { container } = render(
      <InsightCard title="Test Title" body="Test Body" tone="success" />
    );
    const cardDiv = container.firstChild as HTMLElement;
    expect(cardDiv.className).toContain('success');
  });

  it('conditionally renders the eyebrow text if provided', () => {
    render(<InsightCard title="Test Title" body="Test Body" eyebrow="Eyebrow Text" />);
    expect(screen.getByText('Eyebrow Text')).toBeInTheDocument();
  });

  it('conditionally renders an action element if provided', () => {
    render(
      <InsightCard
        title="Test Title"
        body="Test Body"
        action={<button>Click Me</button>}
      />
    );
    expect(screen.getByRole('button', { name: 'Click Me' })).toBeInTheDocument();
  });
});
