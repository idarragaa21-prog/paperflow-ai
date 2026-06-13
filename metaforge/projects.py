"""Local project persistence: save and resume a whole review.

Projects are plain JSON files under a local data directory (``METAFORGE_DATA``,
default ``~/.metaforge/projects``). Nothing leaves the machine. Each project
stores the full workspace state (topic, questions, protocol, data, results,
PRISMA, risk-of-bias, GRADE and manuscript) so a review can be picked up later.
"""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from pathlib import Path

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{0,63}$")
_MAX_BYTES = 8 * 1024 * 1024


def data_dir() -> Path:
    base = os.environ.get("METAFORGE_DATA")
    root = Path(base) if base else Path.home() / ".metaforge"
    d = root / "projects"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return (s or "proyecto")[:40]


def _path(project_id: str) -> Path:
    if not _ID_RE.match(project_id or ""):
        raise ValueError("Identificador de proyecto inválido.")
    p = (data_dir() / f"{project_id}.json").resolve()
    if p.parent != data_dir().resolve():
        raise ValueError("Ruta de proyecto inválida.")
    return p


def save_project(state: dict, name: str, project_id: str | None = None) -> dict:
    name = (name or "").strip() or "Proyecto sin título"
    if project_id and not _ID_RE.match(project_id):
        project_id = None
    now = time.time()
    if project_id and _path(project_id).exists():
        existing = json.loads(_path(project_id).read_text())
        created = existing.get("created", now)
    else:
        project_id = f"{_slug(name)}-{uuid.uuid4().hex[:6]}"
        created = now
    record = {"id": project_id, "name": name, "created": created, "updated": now, "state": state}
    payload = json.dumps(record, ensure_ascii=False)
    if len(payload.encode("utf-8")) > _MAX_BYTES:
        raise ValueError("El proyecto es demasiado grande para guardarse.")
    _path(project_id).write_text(payload)
    return {"id": project_id, "name": name, "created": created, "updated": now}


def list_projects() -> list[dict]:
    out = []
    for f in data_dir().glob("*.json"):
        try:
            r = json.loads(f.read_text())
            out.append({"id": r["id"], "name": r.get("name", r["id"]),
                        "created": r.get("created"), "updated": r.get("updated")})
        except Exception:  # noqa: BLE001 — skip corrupt files
            continue
    return sorted(out, key=lambda r: r.get("updated") or 0, reverse=True)


def load_project(project_id: str) -> dict:
    p = _path(project_id)
    if not p.exists():
        raise ValueError("Proyecto no encontrado.")
    return json.loads(p.read_text())


def delete_project(project_id: str) -> bool:
    p = _path(project_id)
    if p.exists():
        p.unlink()
        return True
    return False
