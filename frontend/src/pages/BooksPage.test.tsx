import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import BooksPage from './BooksPage';

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('../ui/Dialog/useConfirm', () => ({
  useConfirm: () => vi.fn().mockResolvedValue(true),
}));

vi.mock('../ui/Toast/ToastProvider', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

vi.mock('../ui/Skeleton/Skeleton', () => ({
  Skeleton: ({ width, height }: any) => <div style={{ width, height }} data-testid="skeleton" />,
  SkeletonLines: ({ lines }: any) => <div data-testid="skeleton-lines">{lines}</div>,
}));

import { api } from '../services/api';

const mockBooks = [
  { id: 'b1', filename: 'harrison.pdf', file_path: 'books/harrison.pdf', title: "Harrison's Principles", total_pages: 4012, chapters_count: 52, indexed_at: '2025-01-01T00:00:00', created_at: '2025-01-01T00:00:00' },
  { id: 'b2', filename: 'schwartz.pdf', file_path: 'books/schwartz.pdf', title: null, total_pages: null, chapters_count: 0, indexed_at: null, created_at: '2025-01-02T00:00:00' },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <BooksPage />
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  (api.get as any).mockResolvedValue({ data: mockBooks });
});

describe('BooksPage', () => {
  it('renders indexed books list', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Harrison's Principles")).toBeInTheDocument();
    });
  });

  it('shows error state when API fails', async () => {
    (api.get as any).mockRejectedValue({ response: { data: { detail: 'Failed to load books' } } });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/failed to load books/i)).toBeInTheDocument();
    });
  });

  it('shows empty state when no books', async () => {
    (api.get as any).mockResolvedValue({ data: [] });
    renderPage();
    await waitFor(() => {
      expect(screen.queryByText("Harrison's Principles")).not.toBeInTheDocument();
    });
  });

  it('calls delete endpoint after confirm', async () => {
    (api.delete as any).mockResolvedValue({});
    renderPage();
    await waitFor(() => screen.getByText("Harrison's Principles"));

    const deleteBtn = screen.getAllByRole('button', { name: /delete/i })[0];
    fireEvent.click(deleteBtn);
    await waitFor(() => {
      expect(api.delete).toHaveBeenCalledWith('/books/b1');
    });
  });

  it('calls reindex endpoint when reindex button clicked', async () => {
    (api.post as any).mockResolvedValue({ data: { job_id: 'j1' } });
    renderPage();
    await waitFor(() => screen.getByText("Harrison's Principles"));

    const reindexBtn = screen.getAllByRole('button', { name: /reindex/i })[0];
    fireEvent.click(reindexBtn);
    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/books/b1/reindex');
    });
  });
});
