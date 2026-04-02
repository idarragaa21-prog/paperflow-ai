import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Breadcrumb } from '../components/Breadcrumb';

describe('Breadcrumb', () => {
  it('returns null when items array is empty', () => {
    const { container } = render(<Breadcrumb items={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders a single item without separators or links', () => {
    render(
      <MemoryRouter>
        <Breadcrumb items={[{ label: 'Home' }]} />
      </MemoryRouter>
    );
    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Home').tagName).toBe('SPAN');
    expect(screen.queryByText('/')).not.toBeInTheDocument();
  });

  it('renders multiple items with separators', () => {
    render(
      <MemoryRouter>
        <Breadcrumb items={[{ label: 'Home' }, { label: 'Projects' }]} />
      </MemoryRouter>
    );
    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Projects')).toBeInTheDocument();
    expect(screen.getByText('/')).toBeInTheDocument();
  });

  it('renders items with a `to` property as links except the last one', () => {
    render(
      <MemoryRouter>
        <Breadcrumb
          items={[
            { label: 'Home', to: '/home' },
            { label: 'Projects', to: '/projects' },
            { label: 'Details', to: '/projects/1' }
          ]}
        />
      </MemoryRouter>
    );

    const homeLink = screen.getByText('Home');
    expect(homeLink.tagName).toBe('A');
    expect(homeLink).toHaveAttribute('href', '/home');

    const projectsLink = screen.getByText('Projects');
    expect(projectsLink.tagName).toBe('A');
    expect(projectsLink).toHaveAttribute('href', '/projects');

    const detailsText = screen.getByText('Details');
    expect(detailsText.tagName).toBe('SPAN');
    expect(detailsText).not.toHaveAttribute('href');
  });

  it('renders the last item without link even if it has a `to` property', () => {
    render(
      <MemoryRouter>
        <Breadcrumb items={[{ label: 'Home', to: '/home' }]} />
      </MemoryRouter>
    );

    const homeText = screen.getByText('Home');
    expect(homeText.tagName).toBe('SPAN');
    expect(homeText).not.toHaveAttribute('href');
  });
});
