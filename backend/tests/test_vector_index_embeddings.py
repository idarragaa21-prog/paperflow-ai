from __future__ import annotations

from types import SimpleNamespace

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


def test_vector_index_batches_embeddings_when_api_embed_supports_multiple_inputs(monkeypatch):
    calls: list[tuple[str, dict]] = []
    expected_model = "qwen-batch-test"
    monkeypatch.setattr("app.services.vector_index.settings.PAPERFLOW_CHAT_MODEL", expected_model)

    def fake_post(url: str, json: dict, timeout: float):
        calls.append((url, json))
        assert url.endswith("/api/embed")
        assert json["input"] == ["first text", "second text"]
        return DummyResponse({"embeddings": [[0.1, 0.2], [0.3, 0.4]]})

    monkeypatch.setattr(httpx, "post", fake_post)

    index = VectorIndex()
    vectors = index._embed_texts(["first text", "second text"])

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
    assert calls == [("http://127.0.0.1:11434/api/embed", {"model": expected_model, "input": ["first text", "second text"]})]


def test_vector_index_recreates_collection_when_dimensions_drift(monkeypatch):
    recreated: list[tuple[str, object]] = []

    class DummyClient:
        def get_collections(self):
            return SimpleNamespace(collections=[SimpleNamespace(name="paperflow_paper_chunks")])

        def get_collection(self, collection_name: str):
            assert collection_name == "paperflow_paper_chunks"
            return SimpleNamespace(
                config=SimpleNamespace(
                    params=SimpleNamespace(
                        vectors=SimpleNamespace(size=64),
                    )
                )
            )

        def delete_collection(self, collection_name: str):
            recreated.append(("delete", collection_name))

        def create_collection(self, collection_name: str, vectors_config):
            recreated.append(("create", collection_name, vectors_config.size))

    class DummyVectorParams:
        def __init__(self, size: int, distance):
            self.size = size
            self.distance = distance

    dummy_qm = SimpleNamespace(
        VectorParams=DummyVectorParams,
        Distance=SimpleNamespace(COSINE="cosine"),
    )

    index = VectorIndex()
    index._client = DummyClient()
    index._embed_dim = 2048
    monkeypatch.setattr(index, "_qdrant_modules", lambda: (object, dummy_qm))

    index._ensure_collection()

    assert recreated == [
        ("delete", "paperflow_paper_chunks"),
        ("create", "paperflow_paper_chunks", 2048),
    ]
