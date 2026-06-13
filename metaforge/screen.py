"""AI-assisted title/abstract screening against the protocol's criteria.

This is a FIRST-PASS screen: it classifies each record as include / exclude /
maybe with a reason, judged strictly against the inclusion and exclusion
criteria. It does NOT replace human screening — Cochrane/PRISMA require that a
human verifies every decision. MetaForge surfaces the AI's reasons so the
reviewer can confirm or override each one.
"""
from __future__ import annotations

from .ai import ai_available, run_claude_json

_VALID = {"include", "exclude", "maybe"}


def _build_prompt(records: list[dict], inclusion: list[str], exclusion: list[str]) -> str:
    inc = "\n".join(f"- {c}" for c in inclusion) or "- (no especificados)"
    exc = "\n".join(f"- {c}" for c in exclusion) or "- (no especificados)"
    items = []
    for r in records:
        ab = (r.get("abstract") or "").strip().replace("\n", " ")[:1600]
        items.append(f'ID {r["id"]}\nTítulo: {r.get("title","")}\nResumen: {ab or "(sin resumen)"}')
    body = "\n\n".join(items)
    return (
        "Eres un revisor experto en revisiones sistemáticas haciendo el cribado por "
        "título y resumen. Decide, SOLO con la información del título y el resumen, si "
        "cada registro cumple los criterios. Sé estricto: si el resumen no aporta "
        "información suficiente para decidir, usa 'maybe' (no excluyas por falta de datos).\n\n"
        f"CRITERIOS DE INCLUSIÓN:\n{inc}\n\nCRITERIOS DE EXCLUSIÓN:\n{exc}\n\n"
        f"REGISTROS:\n{body}\n\n"
        "Devuelve SOLO un objeto JSON (sin texto extra, sin markdown) con la forma:\n"
        '{"decisions":[{"id":"<id>","decision":"include|exclude|maybe","reason":"<motivo breve citando el criterio>"}]}\n'
        "Responde en español."
    )


def _local(records: list[dict]) -> list[dict]:
    return [{"id": r["id"], "decision": "maybe",
             "reason": "Requiere cribado manual (IA no disponible)."} for r in records]


def _screen_batch_ai(records: list[dict], inclusion, exclusion) -> dict:
    obj = run_claude_json(_build_prompt(records, inclusion, exclusion), timeout=120)
    by_id = {}
    for d in obj.get("decisions", []):
        dec = str(d.get("decision", "")).lower().strip()
        if dec not in _VALID:
            dec = "maybe"
        by_id[str(d.get("id"))] = {"decision": dec, "reason": str(d.get("reason", "")).strip()}
    out = []
    for r in records:
        info = by_id.get(str(r["id"]), {"decision": "maybe", "reason": "Sin decisión de la IA."})
        out.append({"id": r["id"], **info})
    return {"decisions": out}


def screen_records(records: list[dict], inclusion: list[str], exclusion: list[str],
                   *, mode: str = "auto", batch_size: int = 6) -> dict:
    if not records:
        return {"source": "local", "decisions": []}
    want_ai = mode != "local" and (mode == "ai" or ai_available())
    if not want_ai:
        return {"source": "local", "decisions": _local(records),
                "note": "Cribado manual: la IA no está disponible (ejecuta `claude login`)."}

    decisions: list[dict] = []
    used_ai = False
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            decisions.extend(_screen_batch_ai(batch, inclusion, exclusion)["decisions"])
            used_ai = True
        except Exception:  # noqa: BLE001 — degrade this batch only
            decisions.extend(_local(batch))
    return {
        "source": "ai" if used_ai else "local",
        "decisions": decisions,
        "note": "Cribado de primera pasada por IA — verifica cada decisión (requisito PRISMA/Cochrane).",
    }
