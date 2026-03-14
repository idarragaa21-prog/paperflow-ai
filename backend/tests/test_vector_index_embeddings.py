from __future__ import annotations

import httpx

from app.services.vector_index import VectorIndex


class DummyResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://test.invalid")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("error", request=request, response=response)

    def json(self) -> dict:
        return self._payload


def test_vector_index_falls_back_to_legacy_ollama_embeddings_endpoint(monkeypatch):
    calls: list[tuple[str, dict]] = []

    def fake_post(url: str, json: dict, timeout: float):
        calls.append((url, json))
        if url.endswith("/api/embed"):
            raise httpx.HTTPStatusError(
                "missing",
                request=httpx.Request("POST", url),
                response=httpx.Response(404, request=httpx.Request("POST", url)),
            )
        return DummyResponse({"embedding": [0.1, 0.2, 0.3]})

    monkeypatch.setattr(httpx, "post", fake_post)

    index = VectorIndex()
    vector = index._embed_text("paperflow embeddings test")

    assert vector == [0.1, 0.2, 0.3]
    assert any(url.endswith("/api/embed") for url, _payload in calls)
    assert any(url.endswith("/api/embeddings") for url, _payload in calls)


def test_vector_index_falls_back_to_chat_model_when_embedding_model_unavailable(monkeypatch):
    calls: list[tuple[str, dict]] = []
    monkeypatch.setattr("app.services.vector_index.settings.PAPERFLOW_EMBEDDING_MODEL", "bge-m3")
    monkeypatch.setattr("app.services.vector_index.settings.PAPERFLOW_CHAT_MODEL", "qwen2.5:3b")

    def fake_post(url: str, json: dict, timeout: float):
        calls.append((url, json))
        if json["model"] == "bge-m3":
            raise httpx.HTTPStatusError(
                "not found",
                request=httpx.Request("POST", url),
                response=httpx.Response(404, request=httpx.Request("POST", url)),
            )
        return DummyResponse({"embedding": [0.4, 0.5]})

    monkeypatch.setattr(httpx, "post", fake_post)

    index = VectorIndex()
    vector = index._embed_text("paperflow embeddings test")

    assert vector == [0.4, 0.5]
    attempted_models = [payload["model"] for _url, payload in calls]
    assert "bge-m3" in attempted_models
    assert "qwen2.5:3b" in attempted_models
