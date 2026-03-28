import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ReaderPage from '../pages/ReaderPage';

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import { api } from '../services/api';

const PROJECT_ID = 'reader-project-1';

function renderPage() {
  return render(
    <MemoryRouter initialEntries={[`/projects/${PROJECT_ID}/reader`]}>
      <Routes>
        <Route path="/projects/:projectId/reader" element={<ReaderPage />} />
        <Route path="/projects/:projectId/library" element={<div>Library</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ReaderPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders an answer after asking at project scope', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: [{ id: 'paper-1', title: 'ACL augmentation trial', processing_status: 'ready' }],
    });
    vi.mocked(api.post).mockResolvedValue({
      data: {
        session_id: 'session-1',
        answer: 'Respuesta con evidencia suficiente.',
        claim_type: 'supported',
        confidence: 0.91,
        grounded: true,
        citations: [],
      },
    });

    renderPage();

    fireEvent.change(await screen.findByTestId('reader-question-input'), { target: { value: 'What is the main result?' } });
    fireEvent.click(screen.getByTestId('reader-ask-button'));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(`/projects/${PROJECT_ID}/chat`, {
        question: 'What is the main result?',
        task_type: 'chat',
        max_citations: 4,
      });
    });

    expect(await screen.findByTestId('reader-answer-panel')).toHaveTextContent('Respuesta con evidencia suficiente.');
  });

  it('disables asking for an unprocessed paper until processing is triggered', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: [{ id: 'paper-1', title: 'ACL augmentation trial', processing_status: 'uploaded' }],
    });

    renderPage();

    fireEvent.change(await screen.findByTestId('reader-scope-select'), { target: { value: 'paper-1' } });
    fireEvent.change(screen.getByTestId('reader-question-input'), { target: { value: 'Can I ask now?' } });

    await waitFor(() => {
      expect(screen.getByTestId('reader-ask-button')).toBeDisabled();
      expect(screen.getByTestId('reader-process-now')).toBeInTheDocument();
    });
  });
});
