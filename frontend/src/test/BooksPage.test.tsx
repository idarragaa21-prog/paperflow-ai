import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import BooksPage from '../pages/BooksPage';

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
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }),
}));

vi.mock('../hooks/useJobPolling', () => ({
  useJobPolling: () => ({ status: null, isRunning: false, isDone: false, isFailed: false, reset: vi.fn() }),
}));

vi.mock('../ui/Skeleton/Skeleton', () => ({
  Skeleton: () => <div data-testid="skeleton" />,
  SkeletonLines: () => <div data-testid="skeleton-lines" />,
}));

import { api } from '../services/api';

const BOOK = {
  id: 'book-1',
  title: 'Sports Medicine Manual',
  filename: 'sports.pdf',
  chapters_count: 12,
  total_pages: 220,
  indexed_at: '2026-03-29T12:00:00Z',
};

describe('BooksPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.get).mockResolvedValue({ data: [BOOK] });
    vi.mocked(api.post).mockResolvedValue({ data: { job_id: 'job-1' } });
    vi.mocked(api.delete).mockResolvedValue({ data: { ok: true } });
  });

  it('shows empty state when no books are indexed', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ data: [] });
    render(<BooksPage />);

    await waitFor(() => {
      expect(screen.getByText(/No private knowledge sources indexed yet/i)).toBeInTheDocument();
    });
  });

  it('starts a BOOKS folder scan job', async () => {
    render(<BooksPage />);

    await userEvent.click(await screen.findByRole('button', { name: /Scan BOOKS folder \+ index/i }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/books/scan-folder', {});
      expect(screen.getByText(/Scan job enqueued: job-1/i)).toBeInTheDocument();
    });
  });

  it('uploads and indexes a private PDF source', async () => {
    const { container } = render(<BooksPage />);

    await screen.findByText('Sports Medicine Manual');

    const file = new File(['pdf'], 'chapter.pdf', { type: 'application/pdf' });
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input).toBeTruthy();
    await userEvent.upload(input, file);
    fireEvent.click(screen.getByRole('button', { name: /Upload \+ index/i }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        '/books/index',
        expect.any(FormData),
        { headers: { 'Content-Type': 'multipart/form-data' } },
      );
    });
  });

  it('reindexes and deletes an existing book', async () => {
    render(<BooksPage />);

    await screen.findByText('Sports Medicine Manual');
    fireEvent.click(screen.getByRole('button', { name: 'Re-index' }));
    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/books/book-1/reindex');
    });

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
    await waitFor(() => {
      expect(api.delete).toHaveBeenCalledWith('/books/book-1');
    });
  });
});
