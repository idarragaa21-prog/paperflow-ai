"""AI account linking: config storage, status shape, provider switching."""
from __future__ import annotations

from fastapi.testclient import TestClient

from metaforge.api import app


def test_ai_config_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("METAFORGE_DATA", str(tmp_path))
    c = TestClient(app)
    # save an OpenAI key
    r = c.post("/ai/config", json={"provider": "openai", "api_key": "sk-test-abcd1234", "model": ""})
    s = r.json()
    assert r.status_code == 200 and s["provider"] == "openai" and s["has_key"] is True
    assert s["masked_key"].endswith("1234") and "sk-test" not in s["masked_key"]  # never echo the key
    assert s["ai_available"] is True
    # GET reflects it
    assert c.get("/ai/config").json()["provider"] == "openai"
    # switching to CLI mode clears the stored key
    s2 = c.post("/ai/config", json={"provider": "claude_cli", "api_key": "", "model": ""}).json()
    assert s2["has_key"] is False and s2["provider"] in ("claude_cli", "")


def test_ai_status_includes_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("METAFORGE_DATA", str(tmp_path))
    d = TestClient(app).get("/ai-status").json()
    for k in ("ai_available", "provider", "has_key", "cli_available"):
        assert k in d


def test_anthropic_dispatch_uses_api(tmp_path, monkeypatch):
    """With an Anthropic key configured, run_claude must call the Anthropic API
    (not the CLI). We stub the HTTP layer to assert routing without a network call."""
    monkeypatch.setenv("METAFORGE_DATA", str(tmp_path))
    import metaforge.ai as ai
    ai.save_ai_config("anthropic", "sk-ant-xyz", "")
    seen = {}

    def fake_post(url, headers, body, timeout):
        seen["url"] = url; seen["model"] = body["model"]
        return {"content": [{"type": "text", "text": '{"ok": true}'}]}

    monkeypatch.setattr(ai, "_http_post_json", fake_post)
    out = ai.run_claude_json("hola", model="haiku")
    assert out == {"ok": True}
    assert "anthropic.com" in seen["url"] and "haiku" in seen["model"]
