"""FastAPI app: a stateless meta-analysis service that also serves the web UI."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel

from .ai import ai_available
from .docx_export import manuscript_docx
from .grade import auto_grade, grade_from_judgements
from .manuscript import generate_manuscript, generate_section
from .prisma import prisma_svg
from .projects import delete_project, list_projects, load_project, save_project
from .protocol import generate_protocol
from .questions import generate_questions
from .rob import TOOLS, domains_for, rob_summary_svg
from .samples import EXAMPLES, TEMPLATES
from .screen import screen_records
from .search import search_literature
from .service import analyze, analyze_csv

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(
    title="MetaForge",
    version="2.3.0",
    description="Local-first research workspace: question → protocol → meta-analysis → manuscript.",
)


class AnalyzeRequest(BaseModel):
    csv: str | None = None
    rows: list[dict] | None = None
    model: str = "random"
    tau2_method: str = "REML"
    knapp_hartung: bool = True
    favours_low: str = "intervention"
    favours_high: str = "control"


class QuestionRequest(BaseModel):
    topic: str
    n: int = 5
    mode: str = "auto"  # "auto" | "ai" | "local"


class ProtocolRequest(BaseModel):
    question: str
    measure: str = "GEN"
    mode: str = "auto"


class ManuscriptRequest(BaseModel):
    question: str
    result: dict
    protocol: dict | None = None
    mode: str = "auto"


class SectionRequest(BaseModel):
    question: str
    result: dict
    section: str
    protocol: dict | None = None
    mode: str = "auto"


class PrismaRequest(BaseModel):
    counts: dict
    included_meta: int | None = None


class RobRequest(BaseModel):
    studies: list[str]
    ratings: dict
    tool: str = "rob2"


class DocxRequest(BaseModel):
    sections: dict
    facts: str | None = None
    figures: dict | None = None
    grade: dict | None = None


class GradeRequest(BaseModel):
    result: dict
    design: str = "rct"
    rob: dict | None = None
    downgrades: dict | None = None
    upgrades: dict | None = None


class ProjectRequest(BaseModel):
    name: str
    state: dict
    id: str | None = None


class SearchRequest(BaseModel):
    query: str
    page_size: int = 25
    only_oa: bool = False
    pubmed_query: str | None = None


class ScreenRequest(BaseModel):
    records: list[dict]
    inclusion: list[str] = []
    exclusion: list[str] = []
    mode: str = "auto"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": app.version}


@app.get("/ai-status")
def ai_status() -> dict:
    """Whether the local Claude CLI is available to power AI question generation."""
    return {"ai_available": ai_available()}


@app.post("/questions")
def questions_endpoint(req: QuestionRequest) -> dict:
    try:
        return generate_questions(req.topic, n=req.n, mode=req.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/protocol")
def protocol_endpoint(req: ProtocolRequest) -> dict:
    try:
        return generate_protocol(req.question, measure=req.measure, mode=req.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/manuscript")
def manuscript_endpoint(req: ManuscriptRequest) -> dict:
    try:
        return generate_manuscript(req.question, req.result, protocol=req.protocol, mode=req.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/manuscript/section")
def section_endpoint(req: SectionRequest) -> dict:
    try:
        return generate_section(req.question, req.result, req.section, protocol=req.protocol, mode=req.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/prisma")
def prisma_endpoint(req: PrismaRequest) -> dict:
    return {"svg": prisma_svg(req.counts, included_meta=req.included_meta)}


@app.get("/rob/tools")
def rob_tools() -> dict:
    return {k: {"name": v["name"], "domains": v["domains"]} for k, v in TOOLS.items()}


@app.post("/rob")
def rob_endpoint(req: RobRequest) -> dict:
    return {"svg": rob_summary_svg(req.studies, req.ratings, tool=req.tool),
            "domains": domains_for(req.tool)}


@app.post("/search")
def search_endpoint(req: SearchRequest) -> dict:
    try:
        return search_literature(req.query, page_size=req.page_size, only_oa=req.only_oa,
                                 pubmed_query=req.pubmed_query)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/screen")
def screen_endpoint(req: ScreenRequest) -> dict:
    return screen_records(req.records, req.inclusion, req.exclusion, mode=req.mode)


@app.post("/grade")
def grade_endpoint(req: GradeRequest) -> dict:
    try:
        if req.downgrades is not None:
            return grade_from_judgements(req.result, req.design, req.downgrades, req.upgrades)
        return auto_grade(req.result, design=req.design, rob=req.rob)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/projects")
def projects_list() -> dict:
    return {"projects": list_projects()}


@app.post("/projects")
def projects_save(req: ProjectRequest) -> dict:
    try:
        return save_project(req.state, req.name, req.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/projects/{project_id}")
def projects_load(project_id: str) -> dict:
    try:
        return load_project(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/projects/{project_id}")
def projects_delete(project_id: str) -> dict:
    try:
        return {"deleted": delete_project(project_id)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/manuscript/docx")
def manuscript_docx_endpoint(req: DocxRequest) -> Response:
    data = manuscript_docx(req.sections, facts=req.facts, figures=req.figures, grade=req.grade)
    return Response(
        data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="manuscrito_metaforge.docx"'},
    )


@app.post("/analyze")
def analyze_endpoint(req: AnalyzeRequest) -> dict:
    if req.model not in ("random", "fixed"):
        raise HTTPException(status_code=400, detail="model must be 'random' or 'fixed'")
    if req.tau2_method.upper() not in ("REML", "DL", "PM"):
        raise HTTPException(status_code=400, detail="tau2_method must be REML, DL or PM")
    try:
        kwargs = dict(
            model=req.model,
            tau2_method=req.tau2_method,
            knapp_hartung=req.knapp_hartung,
            favours_low=req.favours_low,
            favours_high=req.favours_high,
        )
        if req.rows:
            return analyze(req.rows, **kwargs)
        if req.csv:
            return analyze_csv(req.csv, **kwargs)
        raise ValueError("Provide either 'csv' or 'rows'.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/examples")
def examples() -> dict:
    return {k: {"title": v["title"], "favours_low": v["favours_low"], "favours_high": v["favours_high"]}
            for k, v in EXAMPLES.items()}


@app.get("/examples/{key}")
def example(key: str) -> JSONResponse:
    if key not in EXAMPLES:
        raise HTTPException(status_code=404, detail="Unknown example")
    return JSONResponse(EXAMPLES[key])


@app.get("/templates")
def templates() -> dict:
    return {"templates": sorted(TEMPLATES.keys())}


@app.get("/templates/{kind}")
def template(kind: str) -> Response:
    if kind not in TEMPLATES:
        raise HTTPException(status_code=404, detail="Unknown template")
    return Response(
        TEMPLATES[kind],
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="metaforge_{kind}_template.csv"'},
    )


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/app.js")
def appjs() -> Response:
    return Response((WEB_DIR / "app.js").read_text(), media_type="application/javascript")


@app.get("/styles.css")
def styles() -> Response:
    return Response((WEB_DIR / "styles.css").read_text(), media_type="text/css")
