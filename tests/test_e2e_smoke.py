"""End-to-end smoke test: an epidemiologist runs a full meta-analysis through the
API. Exercises every deterministic endpoint of the 8-step pipeline and asserts
nothing returns a 5xx — the "funciona todo sin errores" guarantee. AI/network
endpoints (search, screening, extraction) run in local mode here; they are
validated live elsewhere.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from metaforge.api import app

client = TestClient(app)

# A realistic binary-outcome dataset (statins vs colorectal cancer, 5 cohorts).
ROWS = [
    {"study_label": "Huang 2026", "effect_measure": "OR", "a_events": 42, "b_non_events": 610,
     "c_events": 88, "d_non_events": 598},
    {"study_label": "García 2024", "effect_measure": "OR", "a_events": 30, "b_non_events": 470,
     "c_events": 55, "d_non_events": 445},
    {"study_label": "Singh 2023", "effect_measure": "OR", "a_events": 12, "b_non_events": 300,
     "c_events": 25, "d_non_events": 290},
    {"study_label": "Müller 2022", "effect_measure": "OR", "a_events": 60, "b_non_events": 900,
     "c_events": 95, "d_non_events": 880},
    {"study_label": "Tan 2021", "effect_measure": "OR", "a_events": 8, "b_non_events": 210,
     "c_events": 18, "d_non_events": 205},
]


def _ok(resp, *codes):
    assert resp.status_code in (codes or (200,)), f"{resp.request.url} -> {resp.status_code}: {resp.text[:200]}"
    return resp


def test_health_and_status():
    _ok(client.get("/health"))
    _ok(client.get("/ai-status"))
    assert client.get("/health").json()["status"] == "ok"


def test_step1_questions_local():
    r = _ok(client.post("/questions", json={"topic": "estatinas y cáncer colorrectal", "mode": "local"}))
    assert r.json().get("questions")


def test_step2_protocol_local():
    r = _ok(client.post("/protocol", json={"question": "¿Reducen las estatinas el cáncer colorrectal?",
                                           "measure": "OR", "mode": "local"}))
    assert "pico" in r.json() or "inclusion" in r.json() or r.json()


def test_step45_analysis_full_result():
    r = _ok(client.post("/analyze", json={"rows": ROWS, "model": "random", "tau2_method": "REML",
                                          "knapp_hartung": True}))
    d = r.json()
    assert d["k"] == 5
    for key in ("pooled", "heterogeneity", "forest_svg", "funnel_svg", "leave_one_out",
                "egger", "trim_fill", "baujat_svg"):
        assert key in d, f"missing {key}"
    assert "<svg" in d["forest_svg"]
    assert d["pooled"]["estimate"] > 0


def test_step5_meta_regression():
    rows = [dict(r, year=2021 + i) for i, r in enumerate(ROWS)]
    r = _ok(client.post("/meta-regression", json={"rows": rows, "moderator": "year"}))
    assert r.json()


def test_step6_prisma_both_layouts():
    counts = {"identified_db": 1200, "duplicates": 200, "screened": 1000, "excluded_screen": 900,
              "sought": 100, "not_retrieved": 5, "fulltext_assessed": 95, "fulltext_excluded": 90,
              "included": 5}
    _ok(client.post("/prisma", json={"counts": counts, "included_meta": 5}))


def test_step7_rob_and_grade_and_sof():
    studies = [r["study_label"] for r in ROWS]
    ratings = {s: {"D1": "low", "D2": "some", "D3": "low", "D4": "low", "D5": "low"} for s in studies}
    _ok(client.post("/rob", json={"studies": studies, "ratings": ratings, "tool": "rob2"}))
    result = client.post("/analyze", json={"rows": ROWS}).json()
    grade = _ok(client.post("/grade", json={"result": result, "design": "observational"})).json()
    _ok(client.post("/grade/sof", json={"result": result, "grade": grade, "outcome": "Cáncer colorrectal"}))


def test_step8_manuscript_and_docx_export():
    import io
    import zipfile
    result = client.post("/analyze", json={"rows": ROWS}).json()
    ms = _ok(client.post("/manuscript", json={"question": "¿Estatinas y CCR?", "result": result,
                                              "mode": "local"})).json()
    sections = ms.get("sections") or {"Resumen": "x", "Métodos": "y"}
    # export with embedded figures, using the SAME keys the UI sends (forest/funnel)
    figures = {"forest": result["forest_svg"], "funnel": result["funnel_svg"]}
    grade = client.post("/grade", json={"result": result, "design": "observational"}).json()
    r = _ok(client.post("/manuscript/docx", json={"sections": sections, "facts": "I² = 30%",
                                                  "figures": figures, "grade": grade}))
    assert r.content[:2] == b"PK"  # a real .docx (zip)
    imgs = [n for n in zipfile.ZipFile(io.BytesIO(r.content)).namelist() if n.startswith("word/media/")]
    assert len(imgs) >= 2, "forest + funnel figures must be embedded in the Word export"


def test_excel_export_endpoint_full_shape():
    ext = {"study_label": "Huang 2026", "doi": "10.x", "data": {
        "label": "Huang 2026", "study": {"year": "2026", "country": "Taiwán"}, "population": {"total_n": 1200},
        "arms": [], "followup": "10 años", "data_in_figures_only": "", "notes": "",
        "outcomes": [{"name": "CCR", "type": "binary", "timepoint": "10a",
                      "intervention": {"events": 42, "n": 652}, "control": {"events": 88, "n": 686},
                      "effect": {"measure": "OR", "value": 0.5, "ci_lower": 0.3, "ci_upper": 0.8},
                      "source": "tabla 2", "from_figure": False, "approx": False}]}}
    r = _ok(client.post("/extract/excel", json={"extractions": [ext]}))
    assert r.content[:2] == b"PK"


def test_citations_roundtrip():
    recs = [{"authors": "Huang", "year": 2026, "title": "Statins and CRC", "journal": "BMC Cancer",
             "doi": "10.1/x", "pmid": "1"}]
    ris = _ok(client.post("/citations/export", json={"records": recs, "format": "ris"})).text
    back = _ok(client.post("/citations/import", json={"text": ris})).json()
    assert back["count"] >= 1


def test_templates_examples_demo():
    _ok(client.get("/templates"))
    for kind in client.get("/templates").json()["templates"]:
        _ok(client.get(f"/templates/{kind}"))
    _ok(client.get("/examples"))
    for key in client.get("/examples").json():
        _ok(client.get(f"/examples/{key}"))
    _ok(client.get("/demo"))


def test_projects_crud():
    state = {"question": "q", "result": None}
    saved = _ok(client.post("/projects", json={"name": "Mi revisión", "state": state})).json()
    pid = saved["id"]
    _ok(client.get(f"/projects/{pid}"))
    assert any(p["id"] == pid for p in client.get("/projects").json()["projects"])
    _ok(client.delete(f"/projects/{pid}"))


def test_static_assets_served():
    _ok(client.get("/"))
    assert "<svg" in client.get("/").text or "<!doctype" in client.get("/").text.lower()
    _ok(client.get("/app.js"))
    _ok(client.get("/styles.css"))
