"""FastAPI app: a stateless meta-analysis service that also serves the web UI."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel

from .samples import EXAMPLES, TEMPLATES
from .service import analyze, analyze_csv

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(
    title="MetaForge",
    version="1.0.0",
    description="Local-first pairwise meta-analysis for epidemiologists.",
)


class AnalyzeRequest(BaseModel):
    csv: str | None = None
    rows: list[dict] | None = None
    model: str = "random"
    tau2_method: str = "REML"
    knapp_hartung: bool = True
    favours_low: str = "intervention"
    favours_high: str = "control"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": app.version}


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
