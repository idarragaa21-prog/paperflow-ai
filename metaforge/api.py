"""FastAPI app: a stateless meta-analysis service that also serves the web UI."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel

from .ai import ai_available, ai_status_dict, save_ai_config, test_connection
from .citations import parse_references, to_bibtex, to_ris
from .demo import demo_state
from .docx_export import manuscript_docx
from .grade import auto_grade, grade_from_judgements, sof_svg
from .manuscript import generate_manuscript, generate_section
from .prisma import prisma_svg
from .projects import delete_project, list_projects, load_project, save_project
from .protocol import generate_protocol
from .questions import generate_questions
from .rob import TOOLS, domains_for, rob_summary_svg
from .samples import EXAMPLES, TEMPLATES
from .excel_export import extractions_to_xlsx
from .extract import extract_data, extract_full, extract_pdf, extract_to_csv_row
from .screen import dual_screen, screen_fulltext, screen_records
from .search import search_literature
from .service import analyze, analyze_csv, meta_regression_csv, meta_regression_rows
from .zotero import local_available, push_local, push_to_zotero

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(
    title="MetaForge",
    version="2.15.0",
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


class SofRequest(BaseModel):
    result: dict
    grade: dict
    outcome: str = "Desenlace principal"


class ProjectRequest(BaseModel):
    name: str
    state: dict
    id: str | None = None


class SearchRequest(BaseModel):
    query: str
    source: str = "europepmc"  # "europepmc" | "pubmed" | "both"
    page_size: int = 25
    only_oa: bool = False
    pubmed_query: str | None = None


class ScreenRequest(BaseModel):
    records: list[dict]
    inclusion: list[str] = []
    exclusion: list[str] = []
    mode: str = "auto"
    dual: bool = False


class ExtractRequest(BaseModel):
    record: dict
    measure: str = "OR"
    outcome: str = ""
    mode: str = "auto"


class FulltextScreenRequest(BaseModel):
    record: dict
    inclusion: list[str] = []
    exclusion: list[str] = []
    mode: str = "auto"


class FullExtractRequest(BaseModel):
    record: dict
    mode: str = "auto"


class ExcelRequest(BaseModel):
    extractions: list[dict]


class MetaRegRequest(BaseModel):
    csv: str | None = None
    rows: list[dict] | None = None
    moderator: str
    knapp_hartung: bool = True


class CitationsExportRequest(BaseModel):
    records: list[dict]
    format: str = "ris"  # "ris" | "bibtex"


class CitationsImportRequest(BaseModel):
    text: str


class ZoteroPushRequest(BaseModel):
    records: list[dict]
    api_key: str
    user_id: str
    library_type: str = "user"
    collection: str | None = None


class ZoteroLocalRequest(BaseModel):
    records: list[dict]


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": app.version}


class AiConfigRequest(BaseModel):
    provider: str  # "anthropic" | "openai" | "claude_cli"
    api_key: str = ""
    model: str = ""


@app.get("/ai-status")
def ai_status() -> dict:
    """AI connection status: provider, whether a key/CLI is available, etc."""
    return ai_status_dict()


@app.get("/ai/config")
def ai_config_get() -> dict:
    return ai_status_dict()


@app.post("/ai/config")
def ai_config_set(req: AiConfigRequest) -> dict:
    return save_ai_config(req.provider, req.api_key, req.model)


@app.post("/ai/test")
def ai_test() -> dict:
    return test_connection()


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
        return search_literature(req.query, source=req.source, page_size=req.page_size,
                                 only_oa=req.only_oa, pubmed_query=req.pubmed_query)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/screen")
def screen_endpoint(req: ScreenRequest) -> dict:
    if req.dual:
        return dual_screen(req.records, req.inclusion, req.exclusion)
    return screen_records(req.records, req.inclusion, req.exclusion, mode=req.mode)


@app.post("/extract")
def extract_endpoint(req: ExtractRequest) -> dict:
    out = extract_data(req.record, measure=req.measure, outcome=req.outcome, mode=req.mode)
    out["csv_row"] = extract_to_csv_row(out)
    return out


@app.post("/screen/fulltext")
def screen_fulltext_endpoint(req: FulltextScreenRequest) -> dict:
    return screen_fulltext(req.record, req.inclusion, req.exclusion, mode=req.mode)


@app.post("/extract/full")
def extract_full_endpoint(req: FullExtractRequest) -> dict:
    return extract_full(req.record, mode=req.mode)


@app.post("/extract/pdf")
async def extract_pdf_endpoint(file: UploadFile = File(...), mode: str = "auto") -> dict:
    """Rigorously extract data from an uploaded PDF (text + tables + figure images)."""
    name = file.filename or "documento.pdf"
    if not name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Sube un archivo .pdf")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")
    if len(data) > 40 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="El PDF supera 40 MB.")
    return extract_pdf(data, filename=name, mode=mode)


@app.post("/extract/excel")
def extract_excel_endpoint(req: ExcelRequest) -> Response:
    data = extractions_to_xlsx(req.extractions)
    return Response(
        data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="extraccion_metaforge.xlsx"'},
    )


@app.post("/meta-regression")
def meta_regression_endpoint(req: MetaRegRequest) -> dict:
    try:
        if req.rows:
            return meta_regression_rows(req.rows, req.moderator, knapp_hartung=req.knapp_hartung)
        if req.csv:
            return meta_regression_csv(req.csv, req.moderator, knapp_hartung=req.knapp_hartung)
        raise ValueError("Provide 'csv' or 'rows'.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/citations/export")
def citations_export(req: CitationsExportRequest) -> Response:
    if req.format == "bibtex":
        body, ext, ctype = to_bibtex(req.records), "bib", "application/x-bibtex"
    else:
        body, ext, ctype = to_ris(req.records), "ris", "application/x-research-info-systems"
    return Response(body, media_type=ctype,
                    headers={"Content-Disposition": f'attachment; filename="metaforge_referencias.{ext}"'})


@app.post("/citations/import")
def citations_import(req: CitationsImportRequest) -> dict:
    records = parse_references(req.text)
    return {"records": records, "count": len(records)}


@app.post("/zotero/push")
def zotero_push(req: ZoteroPushRequest) -> dict:
    try:
        return push_to_zotero(req.records, req.api_key, req.user_id,
                              library_type=req.library_type, collection=req.collection)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/zotero/local-status")
def zotero_local_status() -> dict:
    return {"available": local_available()}


@app.post("/zotero/local-push")
def zotero_local_push(req: ZoteroLocalRequest) -> dict:
    try:
        return push_local(req.records)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/grade")
def grade_endpoint(req: GradeRequest) -> dict:
    try:
        if req.downgrades is not None:
            return grade_from_judgements(req.result, req.design, req.downgrades, req.upgrades)
        return auto_grade(req.result, design=req.design, rob=req.rob)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/grade/sof")
def grade_sof(req: SofRequest) -> dict:
    try:
        return {"svg": sof_svg(req.result, req.grade, outcome=req.outcome)}
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


@app.get("/demo")
def demo() -> dict:
    return demo_state()


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
