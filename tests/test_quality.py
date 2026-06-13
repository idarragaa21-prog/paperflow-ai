from fastapi.testclient import TestClient

from metaforge.api import app
from metaforge.docx_export import manuscript_docx
from metaforge.prisma import prisma_svg
from metaforge.rob import domains_for, rob_summary_svg

client = TestClient(app)


# ---- PRISMA ----
def test_prisma_svg_basic():
    svg = prisma_svg({"identified_db": 400, "identified_other": 10, "duplicates": 60,
                      "screened": 350, "excluded_screen": 300, "fulltext_assessed": 50,
                      "fulltext_excluded": 44, "included": 6}, included_meta=5)
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert "n = 410" in svg          # identified = 400 + 10
    assert "meta-análisis (n = 5)" in svg


def test_prisma_tolerates_missing():
    svg = prisma_svg({"identified_db": 100})
    assert svg.startswith("<svg")


def test_prisma_two_column_when_other_sources():
    svg = prisma_svg({"identified_db": 600, "other_citation": 20, "other_assessed": 18,
                      "included": 5}, included_meta=4)
    assert "otras fuentes" in svg.lower()
    assert "bases de datos" in svg.lower()
    assert svg.startswith("<svg") and svg.endswith("</svg>")


def test_prisma_stays_single_without_other():
    svg = prisma_svg({"identified_db": 400, "duplicates": 50, "included": 4})
    assert "otras fuentes" not in svg.lower()


def test_api_prisma():
    r = client.post("/prisma", json={"counts": {"identified_db": 200, "duplicates": 20}, "included_meta": 4})
    assert r.status_code == 200
    assert r.json()["svg"].startswith("<svg")


# ---- RoB ----
def test_domains_counts():
    assert len(domains_for("rob2")) == 5
    assert len(domains_for("robins-i")) == 7


def test_rob_overall_is_worst():
    studies = ["A"]
    ratings = {"A": {"D1": "low", "D2": "high", "D3": "low", "D4": "low", "D5": "some"}}
    svg = rob_summary_svg(studies, ratings, tool="rob2")
    assert svg.startswith("<svg")
    # red (#c62828) appears because D2 is high -> also drives Global
    assert "#c62828" in svg


def test_api_rob_and_tools():
    tools = client.get("/rob/tools").json()
    assert "rob2" in tools and "robins-i" in tools
    r = client.post("/rob", json={"studies": ["A", "B"],
                                  "ratings": {"A": {"D1": "low"}, "B": {"D1": "high"}}, "tool": "rob2"})
    assert r.status_code == 200
    assert r.json()["svg"].startswith("<svg")


# ---- DOCX ----
def test_manuscript_docx_bytes():
    data = manuscript_docx({"title": "T", "abstract": "**Bold** text.\n\n- item", "results": "OR 0.8."})
    assert data[:2] == b"PK"          # valid .docx (zip)
    assert len(data) > 1000


def test_api_docx():
    r = client.post("/manuscript/docx", json={"sections": {"title": "T", "results": "OR 0.8 [0.6, 0.9]."}})
    assert r.status_code == 200
    assert "wordprocessingml" in r.headers["content-type"]
    assert r.content[:2] == b"PK"


def test_svg_to_png():
    from metaforge.figures import svg_to_png
    png = svg_to_png('<svg xmlns="http://www.w3.org/2000/svg" width="80" height="40"><rect width="80" height="40" fill="#333"/></svg>')
    assert png is not None and png[:4] == b"\x89PNG"


def test_docx_with_figures_is_larger():
    from metaforge.docx_export import manuscript_docx
    forest = '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200"><rect width="400" height="200" fill="#eee"/><circle cx="200" cy="100" r="40" fill="#1c2d8c"/></svg>'
    plain = manuscript_docx({"title": "T", "results": "R."})
    withfig = manuscript_docx({"title": "T", "results": "R."}, figures={"forest": forest})
    assert len(withfig) > len(plain) + 1000   # an image was embedded
