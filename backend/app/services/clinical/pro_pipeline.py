from __future__ import annotations

import json
from typing import Any

from app.config import settings
from app.core.logger import logger
from app.schemas.clinical_pro import ClinicalProOutput
from app.services.llm.openclaw import OpenClawProvider


def _safe_json_loads(text: str) -> Any:
    text = (text or "").strip()
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        if start == -1:
            raise ValueError("No JSON object found")
        depth = 0
        end = None
        for i in range(start, len(text)):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end is None:
            raise ValueError("Unterminated JSON object")
        return json.loads(text[start:end])


async def _json_repair(openclaw: OpenClawProvider, *, model: str, previous_output: str, error: str) -> dict[str, Any]:
    system = (
        "Tu salida anterior NO fue JSON válido. Devuelve SOLO JSON válido, sin markdown, sin comentarios. "
        "Corrige solo sintaxis (llaves, comas, comillas) y preserva el contenido clínico."
    )
    user = json.dumps({"error": error, "previous_output": previous_output[:24000]}, ensure_ascii=False)
    r = await openclaw.chat(model=model, system=system, user=user, temperature=0.0, max_tokens=4096, timeout=360, retry=2)
    return _safe_json_loads(r.get("content") or "")


async def generate_clinical_pro_output(
    *,
    topic: str,
    context: str | None,
    region: str | None,
    evidence_bundle: dict[str, Any],
    objective: str,
    focus: str,
    level: str,
    max_length: str,
    progress_cb: Any | None = None,
) -> tuple[ClinicalProOutput, dict[str, Any], list[str]]:
    """4-pass PRO generation: Claude writer -> OpenAI critic -> Claude revise -> Gemini validate.

    Returns: (validated_output, usage, warnings)
    """

    oc = OpenClawProvider()

    warnings: list[str] = []
    usage: dict[str, Any] = {"passes": []}

    import inspect

    async def prog(p: int, label: str) -> None:
        if not progress_cb:
            return
        try:
            r = progress_cb(int(p), label)
            if inspect.isawaitable(r):
                await r
        except Exception:
            return

    # PASS 1: Writer (Claude)
    await prog(45, "writer")
    logger.info(f"[clinical_pro] pass=writer model={settings.OPENCLAW_CLAUDE_MODEL}")
    system_writer = (
        "Eres un ortopedista experto y metodólogo clínico. Genera una ficha tipo UpToDate basada PRINCIPALMENTE en ARTÍCULOS científicos. "
        "Libros locales solo complementan definiciones/fisiopatología/contexto histórico (nunca dominan recomendaciones si hay artículos).\n\n"
        "DEVUELVE SOLO JSON válido (sin markdown, sin texto extra).\n"
        "Schema (obligatorio): {title, sections:[{id,title,content_markdown}], tables:[{title,columns,rows}], charts:[{title,type,data,note}], mermaid:[{title,code}], evidence_map:[{question,conclusion,strength,key_papers,limitations}], references_vancouver:[...], quality:{evidence_strength,gaps}}\n\n"
        "Secciones obligatorias (en este orden):\n"
        "A) Resumen Ejecutivo (5-8 bullets ultraclínicos)\n"
        "B) Definición + fisiopatología (breve)\n"
        "C) Diagnóstico (algoritmo)\n"
        "D) Tratamiento (tabla por escenarios)\n"
        "E) Perlas clínicas + errores frecuentes\n"
        "F) Controversias / zonas grises (con evidencia)\n"
        "G) Checklist para guardia / consultorio\n"
        "H) Referencias (Vancouver)\n\n"
        "Obligatorio: 3-6 tablas mínimo (ideal 5) y 2 charts (si no hay datos, conceptual).\n"
        "Obligatorio: 1 mermaid mindmap o flowchart (mapa conceptual) y 1 mermaid flowchart (algoritmo clínico).\n"
        "CITAS: En cada sección, termina con 'Fuentes: ...' con PMIDs/DOIs visibles. Si no hay evidencia, 'Fuentes: (No encontrado / evidencia insuficiente)'.\n"
        "Para afirmaciones importantes, añade al final: (PMID/DOI + tipo de estudio + año). No inventes."
    )

    user_writer = json.dumps(
        {
            "topic": topic,
            "context": context,
            "region": region,
            "objective": objective,
            "focus": focus,
            "level": level,
            "max_length": max_length,
            "evidence_bundle": evidence_bundle,
        },
        ensure_ascii=False,
    )

    r1 = await oc.chat(
        model=settings.OPENCLAW_CLAUDE_MODEL,
        system=system_writer,
        user=user_writer,
        temperature=0.3,
        max_tokens=4096,
        timeout=420,
        retry=2,
    )
    usage["passes"].append({"name": "writer", "model": r1.get("model"), "usage": r1.get("usage"), "latency_ms": r1.get("latency_ms")})

    draft_text = r1.get("content") or ""
    try:
        draft_json = _safe_json_loads(draft_text)
    except Exception as e:
        warnings.append("Writer output was not valid JSON; attempted repair.")
        draft_json = await _json_repair(oc, model=settings.OPENCLAW_CLAUDE_MODEL, previous_output=draft_text, error=str(e))

    # PASS 2: Critic (OpenAI)
    await prog(55, "critic")
    logger.info(f"[clinical_pro] pass=critic model={settings.OPENCLAW_OPENAI_MODEL}")
    system_crit = (
        "Eres un crítico clínico-metodológico. Devuelve SOLO JSON válido.\n"
        "Evalúa el JSON draft contra los requisitos: secciones A-H, min tablas (>=5), charts (>=2), mermaid (>=2: mindmap+flowchart), evidence_map presente, citas PMIDs/DOIs, libros secundarios.\n"
        "Devuelve: {issues:[{severity,path,problem,fix}], summary:string}."
    )
    user_crit = json.dumps({"draft": draft_json}, ensure_ascii=False)

    r2 = await oc.chat(
        model=settings.OPENCLAW_OPENAI_MODEL,
        system=system_crit,
        user=user_crit,
        temperature=0.0,
        max_tokens=2048,
        timeout=300,
        retry=2,
    )
    usage["passes"].append({"name": "critic", "model": r2.get("model"), "usage": r2.get("usage"), "latency_ms": r2.get("latency_ms")})

    crit_text = r2.get("content") or ""
    try:
        critique_json = _safe_json_loads(crit_text)
    except Exception as e:
        warnings.append("Critic output was not valid JSON; ignoring critique.")
        critique_json = {"issues": [], "summary": f"critic_invalid_json: {e}"}

    # PASS 3: Revise (Claude)
    await prog(65, "revise")
    logger.info(f"[clinical_pro] pass=revise model={settings.OPENCLAW_CLAUDE_MODEL}")
    system_rev = (
        "Eres el escritor senior. Devuelve SOLO JSON válido FINAL, cumpliendo todos los requisitos.\n"
        "Aplica las correcciones del crítico. No inventes PMIDs/DOIs/años/tipos.\n"
        "Recuerda: ARTÍCULOS dominan; libros solo conceptual."
    )
    user_rev = json.dumps({"draft": draft_json, "critique": critique_json}, ensure_ascii=False)

    r3 = await oc.chat(
        model=settings.OPENCLAW_CLAUDE_MODEL,
        system=system_rev,
        user=user_rev,
        temperature=0.3,
        max_tokens=4096,
        timeout=420,
        retry=2,
    )
    usage["passes"].append({"name": "revise", "model": r3.get("model"), "usage": r3.get("usage"), "latency_ms": r3.get("latency_ms")})

    rev_text = r3.get("content") or ""
    try:
        rev_json = _safe_json_loads(rev_text)
    except Exception as e:
        warnings.append("Revise output was not valid JSON; attempted repair.")
        rev_json = await _json_repair(oc, model=settings.OPENCLAW_CLAUDE_MODEL, previous_output=rev_text, error=str(e))

    # PASS 4: Validate (Gemini)
    await prog(72, "validate")
    logger.info(f"[clinical_pro] pass=validate model={settings.OPENCLAW_GEMINI_MODEL}")
    system_val = (
        "Eres un validador estricto. Devuelve SOLO JSON válido.\n"
        "Valida que el objeto cumpla schema y requisitos mínimos (secciones A-H, tablas>=5, charts>=2, mermaid>=2, evidence_map>=1).\n"
        "No inventes nada. Devuelve: {ok:bool, issues:[{severity,path,problem}], missing:[...]}"
    )
    user_val = json.dumps({"candidate": rev_json}, ensure_ascii=False)

    r4 = await oc.chat(
        model=settings.OPENCLAW_GEMINI_MODEL,
        system=system_val,
        user=user_val,
        temperature=0.0,
        max_tokens=2048,
        timeout=300,
        retry=2,
    )
    usage["passes"].append({"name": "validate", "model": r4.get("model"), "usage": r4.get("usage"), "latency_ms": r4.get("latency_ms")})

    val_text = r4.get("content") or ""
    try:
        val_json = _safe_json_loads(val_text)
    except Exception as e:
        warnings.append("Validator output invalid JSON; skipping validator.")
        val_json = {"ok": True, "issues": [], "missing": [], "error": str(e)}

    if isinstance(val_json, dict) and val_json.get("ok") is False:
        warnings.append("Validator reported issues; proceeding with local gates.")

    await prog(74, "schema_validate")

    def _norm_strength(v: Any) -> str:
        s = str(v or "").strip().lower()
        if not s:
            return "low"
        if "high" in s or "alta" in s:
            return "high"
        if "medium" in s or "moder" in s:
            # conservative: if also says 'baja', keep low
            if "baja" in s or "low" in s:
                return "low"
            return "medium"
        if "low" in s or "baja" in s:
            return "low"
        return "low"

    def _norm_chart_type(v: Any) -> str:
        s = str(v or "").strip().lower()
        if s in {"bar", "line", "forest_like", "conceptual"}:
            return s
        if s in {"timeline", "trend", "time", "time_series"}:
            return "line"
        if s in {"forest", "forestplot", "forest_plot"}:
            return "forest_like"
        if s in {"hist", "histogram"}:
            return "bar"
        return "conceptual"

    def _ensure_list(v: Any) -> list[Any]:
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return [v]

    def _normalize_candidate(obj: Any) -> dict[str, Any]:
        if not isinstance(obj, dict):
            return {"title": str(topic), "sections": [], "quality": {"evidence_strength": "low", "gaps": ["invalid_json"]}}

        out = dict(obj)

        # charts
        charts = _ensure_list(out.get("charts"))
        fixed_charts = []
        for ch in charts:
            if not isinstance(ch, dict):
                continue
            ch2 = dict(ch)
            ch2["type"] = _norm_chart_type(ch2.get("type"))
            if not isinstance(ch2.get("data"), dict):
                ch2["data"] = {}
            fixed_charts.append(ch2)
        out["charts"] = fixed_charts

        # evidence_map
        em = _ensure_list(out.get("evidence_map"))
        fixed_em = []
        for row in em:
            if not isinstance(row, dict):
                continue
            r2 = dict(row)
            r2["strength"] = _norm_strength(r2.get("strength"))
            kp = r2.get("key_papers")
            r2["key_papers"] = [str(x) for x in (_ensure_list(kp)) if str(x).strip()]
            fixed_em.append(r2)
        out["evidence_map"] = fixed_em

        # quality
        q = out.get("quality")
        if not isinstance(q, dict):
            q = {}
        q2 = dict(q)
        q2["evidence_strength"] = _norm_strength(q2.get("evidence_strength"))
        gaps = q2.get("gaps")
        if isinstance(gaps, str):
            parts = [p.strip() for p in gaps.replace("\n", ";").split(";")]
            q2["gaps"] = [p for p in parts if p]
        elif isinstance(gaps, list):
            q2["gaps"] = [str(x) for x in gaps if str(x).strip()]
        else:
            q2["gaps"] = []
        out["quality"] = q2

        # references_vancouver
        rv = out.get("references_vancouver")
        if isinstance(rv, str):
            out["references_vancouver"] = [x.strip() for x in rv.split("\n") if x.strip()]

        return out

    await prog(74, "schema_validate")

    # Local schema validation (normalize first; keep schema strict)
    candidate = _normalize_candidate(rev_json)
    try:
        out = ClinicalProOutput.model_validate(candidate)
    except Exception as e:
        # last resort: try a schema repair with Claude
        warnings.append(f"Schema validation failed; attempted schema repair: {e}")
        system_schema = (
            "Tu JSON no cumple el schema requerido. Devuelve SOLO JSON válido que cumpla EXACTAMENTE el schema. "
            "Campos enum: quality.evidence_strength y evidence_map[*].strength deben ser EXACTAMENTE: 'high'|'medium'|'low'. "
            "charts[*].type debe ser EXACTAMENTE: 'bar'|'line'|'forest_like'|'conceptual'. "
            "quality.gaps debe ser lista de strings. "
            "No inventes referencias. Si faltan datos, usa placeholders '(No encontrado / evidencia insuficiente)'."
        )
        user_schema = json.dumps({"error": str(e), "candidate": candidate}, ensure_ascii=False)
        rr = await oc.chat(
            model=settings.OPENCLAW_CLAUDE_MODEL,
            system=system_schema,
            user=user_schema,
            temperature=0.0,
            max_tokens=4096,
            timeout=360,
            retry=2,
        )
        usage["passes"].append({"name": "schema_repair", "model": rr.get("model"), "usage": rr.get("usage"), "latency_ms": rr.get("latency_ms")})
        repaired = _safe_json_loads(rr.get("content") or "")
        repaired2 = _normalize_candidate(repaired)
        out = ClinicalProOutput.model_validate(repaired2)

    return out, usage, warnings
