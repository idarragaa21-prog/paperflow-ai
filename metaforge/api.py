"""FastAPI app: a stateless meta-analysis service that also serves the web UI."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from .service import analyze, analyze_csv

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="MetaForge", version="0.1.0")


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
    return {"status": "ok"}


@app.post("/analyze")
def analyze_endpoint(req: AnalyzeRequest) -> dict:
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


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/app.js")
def appjs() -> Response:
    return Response((WEB_DIR / "app.js").read_text(), media_type="application/javascript")
