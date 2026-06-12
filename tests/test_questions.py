import pytest
from fastapi.testclient import TestClient

from metaforge.ai import extract_json
from metaforge.api import app
from metaforge.effects import ALL_MEASURES
from metaforge.questions import _normalise_measure, generate_questions

client = TestClient(app)


def test_local_generation_structure():
    out = generate_questions("ejercicio y presión arterial", n=5, mode="local")
    assert out["source"] == "local"
    assert 1 <= len(out["questions"]) <= 6
    for q in out["questions"]:
        assert q["question"]
        assert q["measure"] in ALL_MEASURES
        assert q["framework"]


def test_local_embeds_topic():
    out = generate_questions("café", n=3, mode="local")
    assert any("café" in q["question"] for q in out["questions"])


def test_english_topic_detected():
    out = generate_questions("the effect of statins on cardiovascular risk", n=3, mode="local")
    # English templates use 'In [population]' phrasing.
    assert any("population" in q["question"].lower() for q in out["questions"])


def test_empty_topic_raises():
    with pytest.raises(ValueError):
        generate_questions("   ", mode="local")


def test_normalise_measure():
    assert _normalise_measure("or") == "OR"
    assert _normalise_measure("bogus") == "GEN"
    assert _normalise_measure(None) == "GEN"


def test_extract_json_with_fences():
    obj = extract_json('```json\n{"questions": [{"question": "x"}]}\n```')
    assert obj["questions"][0]["question"] == "x"


def test_extract_json_with_surrounding_prose():
    obj = extract_json('Sure! {"questions": []} hope that helps')
    assert obj == {"questions": []}


def test_ai_off_forces_local(monkeypatch):
    monkeypatch.setenv("METAFORGE_AI", "off")
    from metaforge.ai import ai_available
    assert ai_available() is False
    out = generate_questions("cualquier tema", n=2, mode="auto")
    assert out["source"] == "local"


def test_api_ai_status():
    r = client.get("/ai-status")
    assert r.status_code == 200
    assert "ai_available" in r.json()


def test_api_questions_local():
    r = client.post("/questions", json={"topic": "vacunación y gripe", "n": 4, "mode": "local"})
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "local"
    assert len(body["questions"]) >= 1


def test_api_questions_empty_topic():
    r = client.post("/questions", json={"topic": "", "mode": "local"})
    assert r.status_code == 400


def test_styles_served():
    r = client.get("/styles.css")
    assert r.status_code == 200
    assert "text/css" in r.headers["content-type"]
