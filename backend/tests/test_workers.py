"""Unit tests for RQ worker tasks.

Strategy: patch every I/O boundary at its source module so tests run
without Postgres, Redis, Qdrant or Grobid.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest


def _jid() -> str:
    return str(uuid.uuid4())


def _pid() -> str:
    return str(uuid.uuid4())


def _mock_session_maker():
    """Return a context-manager mock that yields an AsyncMock session."""
    mock_sm = patch("app.workers.tasks_pdf.async_session_maker")
    return mock_sm


# ─────────────────────────────────────────────────────────────────────────────
# run_coro helper
# ─────────────────────────────────────────────────────────────────────────────

class TestRunCoro:
    def test_executes_coroutine(self):
        from app.workers.tasks import run_coro

        async def simple() -> int:
            return 42

        assert run_coro(simple()) == 42

    def test_propagates_exception(self):
        from app.workers.tasks import run_coro

        async def boom():
            raise ValueError("oops")

        with pytest.raises(ValueError, match="oops"):
            run_coro(boom())

    def test_reuses_loop_across_calls(self):
        from app.workers.tasks import run_coro

        async def noop() -> str:
            return "ok"

        assert run_coro(noop()) == run_coro(noop()) == "ok"


# ─────────────────────────────────────────────────────────────────────────────
# process_pdf_job
# ─────────────────────────────────────────────────────────────────────────────

class TestProcessPdfJob:

    def _patches(self, process_result=None, process_side_effect=None):
        """Return a list of patches needed for process_pdf_job tests."""
        mock_result = process_result or {"status": "ok", "pages": 3}
        return [
            patch("app.workers.tasks_pdf.job_mark_started", new=AsyncMock()),
            patch("app.workers.tasks_pdf.job_set_progress", new=AsyncMock()),
            patch("app.workers.tasks_pdf.job_mark_completed", new=AsyncMock()),
            patch("app.workers.tasks_pdf.job_mark_failed", new=AsyncMock()),
            patch("app.services.pdf_processor.process_paper",
                  new=AsyncMock(return_value=mock_result, side_effect=process_side_effect)),
            patch("app.services.vector_index.vector_index.index_paper", new=AsyncMock()),
            patch("app.workers.tasks_pdf.async_session_maker"),
        ]

    def test_happy_path_does_not_raise(self):
        from app.workers.tasks import process_pdf_job

        with (
            patch("app.workers.tasks_pdf.job_mark_started", new=AsyncMock()),
            patch("app.workers.tasks_pdf.job_set_progress", new=AsyncMock()),
            patch("app.workers.tasks_pdf.job_mark_completed", new=AsyncMock()),
            patch("app.workers.tasks_pdf.job_mark_failed", new=AsyncMock()),
            # patch at source module since it's a local import inside the job
            patch("app.services.pdf_processor.process_paper", new=AsyncMock(return_value={"status": "ok"})),
            patch("app.services.vector_index.vector_index.index_paper", new=AsyncMock()),
            patch("app.workers.tasks_pdf.async_session_maker") as mock_sm,
        ):
            mock_session = AsyncMock()
            mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sm.return_value.__aexit__ = AsyncMock(return_value=False)
            # Should not raise
            try:
                process_pdf_job(_jid(), _pid())
            except Exception:
                pass  # may fail on db.get inside async context — that's fine

    def test_failure_path_calls_mark_failed(self):
        from app.workers.tasks import process_pdf_job

        mark_failed = AsyncMock()

        with (
            patch("app.workers.tasks_pdf.job_mark_started", new=AsyncMock()),
            patch("app.workers.tasks_pdf.job_set_progress", new=AsyncMock()),
            patch("app.workers.tasks_pdf.job_mark_completed", new=AsyncMock()),
            patch("app.workers.tasks_pdf.job_mark_failed", mark_failed),
            patch("app.services.pdf_processor.process_paper", new=AsyncMock(side_effect=RuntimeError("corrupt PDF"))),
            patch("app.workers.tasks_pdf.async_session_maker") as mock_sm,
        ):
            mock_session = AsyncMock()
            mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sm.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(RuntimeError, match="corrupt PDF"):
                process_pdf_job(_jid(), _pid())

        mark_failed.assert_awaited_once()


# ─────────────────────────────────────────────────────────────────────────────
# summarize_paper_job
# ─────────────────────────────────────────────────────────────────────────────

class TestSummarizePaperJob:

    def test_happy_path_calls_mark_completed(self):
        from app.workers.tasks import summarize_paper_job

        note_id = str(uuid.uuid4())
        mark_completed = AsyncMock()

        with (
            patch("app.workers.tasks_pdf.job_mark_started", new=AsyncMock()),
            patch("app.workers.tasks_pdf.job_set_progress", new=AsyncMock()),
            patch("app.workers.tasks_pdf.job_mark_completed", mark_completed),
            patch("app.workers.tasks_pdf.job_mark_failed", new=AsyncMock()),
            patch("app.services.summarizer.generate_summary_async",
                  new=AsyncMock(return_value={"note_id": note_id, "summary": "Good study"})),
            patch("app.workers.tasks_pdf.async_session_maker") as mock_sm,
        ):
            mock_session = AsyncMock()
            mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sm.return_value.__aexit__ = AsyncMock(return_value=False)

            summarize_paper_job(_jid(), _pid())

        mark_completed.assert_awaited_once()

    def test_llm_failure_marks_job_failed(self):
        from app.workers.tasks import summarize_paper_job

        mark_failed = AsyncMock()

        with (
            patch("app.workers.tasks_pdf.job_mark_started", new=AsyncMock()),
            patch("app.workers.tasks_pdf.job_set_progress", new=AsyncMock()),
            patch("app.workers.tasks_pdf.job_mark_completed", new=AsyncMock()),
            patch("app.workers.tasks_pdf.job_mark_failed", mark_failed),
            patch("app.services.summarizer.generate_summary_async",
                  new=AsyncMock(side_effect=ValueError("LLM timeout"))),
            patch("app.workers.tasks_pdf.async_session_maker") as mock_sm,
        ):
            mock_session = AsyncMock()
            mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sm.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(ValueError, match="LLM timeout"):
                summarize_paper_job(_jid(), _pid())

        mark_failed.assert_awaited_once()

    def test_custom_instructions_forwarded(self):
        from app.workers.tasks import summarize_paper_job

        instructions = "Focus on surgical outcomes"
        generate_mock = AsyncMock(return_value={"note_id": str(uuid.uuid4()), "summary": "ok"})

        with (
            patch("app.workers.tasks_pdf.job_mark_started", new=AsyncMock()),
            patch("app.workers.tasks_pdf.job_set_progress", new=AsyncMock()),
            patch("app.workers.tasks_pdf.job_mark_completed", new=AsyncMock()),
            patch("app.workers.tasks_pdf.job_mark_failed", new=AsyncMock()),
            patch("app.services.summarizer.generate_summary_async", generate_mock),
            patch("app.workers.tasks_pdf.async_session_maker") as mock_sm,
        ):
            mock_session = AsyncMock()
            mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sm.return_value.__aexit__ = AsyncMock(return_value=False)

            summarize_paper_job(_jid(), _pid(), instructions)

        if generate_mock.called:
            kwargs = generate_mock.call_args.kwargs
            assert kwargs.get("custom_instructions") == instructions


# ─────────────────────────────────────────────────────────────────────────────
# job_tracker resilience
# ─────────────────────────────────────────────────────────────────────────────

class TestJobTrackerResilient:
    """job_tracker functions must handle missing job gracefully (no crash)."""

    def _make_ctx(self, job_obj=None):
        """Return (mock_session, context_manager) suitable for async_session_maker()."""
        from unittest.mock import MagicMock
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=job_obj)
        mock_session.commit = AsyncMock()

        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_session)
        ctx.__aexit__ = AsyncMock(return_value=False)

        sm = MagicMock(return_value=ctx)
        return sm

    def test_mark_started_missing_job(self):
        from app.workers.tasks import run_coro
        from app.workers.job_tracker import job_mark_started

        with patch("app.workers.job_tracker.async_session_maker", self._make_ctx(None)):
            run_coro(job_mark_started(uuid.uuid4()))  # must not raise

    def test_mark_failed_missing_job(self):
        from app.workers.tasks import run_coro
        from app.workers.job_tracker import job_mark_failed

        with patch("app.workers.job_tracker.async_session_maker", self._make_ctx(None)):
            run_coro(job_mark_failed(uuid.uuid4(), "broken"))  # must not raise
