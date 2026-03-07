from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_clinical_sheet_generates_markdown(monkeypatch):
    from app.services.clinical import generator as gen

    class FakeSheet:
        topic = "Dolor de rodilla"
        user_id = None
        project_id = None
        input_params = {
            "objective": "quick_review",
            "focus": "diagnostic",
            "level": "specialist",
            "search_online": False,
            "use_project_papers": False,
            "pro_output": False,
        }

    async def fake_chat(self, *, model, system, user, temperature=0.0, max_tokens=0, timeout=None, retry=0):
        # pass1: return JSON with markdown
        if "content_markdown" in system:
            import json

            md = (
                "## Resumen ejecutivo\n"
                "Fuentes: (Conocimiento clínico estándar)\n\n"
                "## Evaluación diagnóstica\n"
                "Fuentes: (Conocimiento clínico estándar)\n\n"
                "## Checklist práctico\n"
                "Fuentes: (Conocimiento clínico estándar)"
            )

            return {
                "content": json.dumps(
                    {
                        "content_markdown": md,
                        "references_json": [],
                        "sources_used": {},
                        "vancouver": ["1. (Referencia no disponible)"],
                    },
                    ensure_ascii=False,
                ),
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }
        # audit: ok
        return {"content": '{"ok": true, "issues": []}', "usage": {"prompt_tokens": 1, "completion_tokens": 1}}

    monkeypatch.setattr(gen.OpenClawProvider, "chat", fake_chat, raising=True)
    async def _empty_async(*a, **k):
        return []

    monkeypatch.setattr(gen, "_collect_book_fragments", _empty_async)
    monkeypatch.setattr(gen, "_collect_project_papers", _empty_async)
    monkeypatch.setattr(gen, "_collect_pubmed", _empty_async)

    out = await gen.generate_clinical_sheet(db=None, sheet=FakeSheet(), progress_cb=None)
    assert "## Referencias" in out["content_markdown"]
