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


def cohen_kappa(labels_a: list[str], labels_b: list[str]) -> float | None:
    """Cohen's kappa for inter-reviewer agreement over categorical decisions."""
    n = len(labels_a)
    if n == 0 or n != len(labels_b):
        return None
    cats = set(labels_a) | set(labels_b)
    po = sum(1 for a, b in zip(labels_a, labels_b) if a == b) / n
    pe = sum((labels_a.count(c) / n) * (labels_b.count(c) / n) for c in cats)
    if pe >= 1.0:
        return 1.0
    return round((po - pe) / (1 - pe), 3)


def _screen_once(records, inclusion, exclusion) -> dict:
    out = {}
    for d in _screen_batch_ai(records, inclusion, exclusion)["decisions"]:
        out[str(d["id"])] = d
    return out


def dual_screen(records: list[dict], inclusion: list[str], exclusion: list[str]) -> dict:
    """Two independent AI screening passes + Cohen's kappa, flagging conflicts.

    Mirrors dual independent screening (Cochrane): disagreements are surfaced for
    human resolution rather than silently resolved.
    """
    if not records or not ai_available():
        base = screen_records(records, inclusion, exclusion, mode="local")
        for d in base["decisions"]:
            d.update({"decision2": d["decision"], "reason2": "", "agree": True})
        base["dual"] = True
        base["kappa"] = None
        return base
    try:
        a = _screen_once(records, inclusion, exclusion)
        b = _screen_once(records, inclusion, exclusion)
    except Exception:  # noqa: BLE001
        return {**screen_records(records, inclusion, exclusion, mode="local"), "dual": True, "kappa": None}
    decisions, la, lb = [], [], []
    for r in records:
        rid = str(r["id"])
        da, db = a.get(rid, {}), b.get(rid, {})
        d1, d2 = da.get("decision", "maybe"), db.get("decision", "maybe")
        la.append(d1)
        lb.append(d2)
        decisions.append({"id": r["id"], "decision": d1, "reason": da.get("reason", ""),
                          "decision2": d2, "reason2": db.get("reason", ""), "agree": d1 == d2})
    return {"source": "ai", "dual": True, "decisions": decisions, "kappa": cohen_kappa(la, lb),
            "note": "Doble cribado independiente por IA — resuelve los conflictos (κ mide la concordancia)."}


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
