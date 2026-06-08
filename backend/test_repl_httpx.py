import pytest

@pytest.fixture(autouse=True)
def setup_mock_httpx(monkeypatch):
    class DummyResponse:
        def __init__(self, json_payload=None, text=""):
            self._json_payload = json_payload or {}
            self.text = text
            self.status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return self._json_payload

    class DummyContextManager:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def post(self, url, **kwargs):
            if "run-analysis" in url:
                return DummyResponse(
                    json_payload={
                        "summary": {"rows_total": 2},
                        "figure_artifacts": {"forest": {"svg": "PHN2Zz48L3N2Zz4="}}
                    }
                )
            return DummyResponse()

        async def get(self, url, **kwargs):
            return DummyResponse()

    import app.services.meta_runs_service as m_service
    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", DummyContextManager)
    monkeypatch.setattr(m_service.httpx, "AsyncClient", DummyContextManager)
