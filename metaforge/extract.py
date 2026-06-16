"""AI-assisted data extraction from open-access full text.

For an included open-access record, fetches the JATS full text from Europe PMC
and asks the AI to pull out exactly the numbers needed to compute the chosen
effect measure for a given outcome (2x2 cells, arm means/SDs, or effect+CI),
together with the supporting quote. Falls back to the abstract when no full text
is available. Every extraction must be checked against the source by a human.
"""
from __future__ import annotations

import os
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

from .ai import ai_available, run_claude_json

_UA = {"User-Agent": "MetaForge/1.0 (systematic-review tool)"}
FULLTEXT = "https://www.ebi.ac.uk/europepmc/webservices/rest/{id}/fullTextXML"

FIELDS_BY_MEASURE = {
    "OR": ["a_events", "b_non_events", "c_events", "d_non_events"],
    "RR": ["a_events", "b_non_events", "c_events", "d_non_events"],
    "RD": ["a_events", "b_non_events", "c_events", "d_non_events"],
    "HR": ["effect_value", "ci_lower_95", "ci_upper_95"],
    "IRR": ["events_intervention", "time_intervention", "events_control", "time_control"],
    "MD": ["n_intervention", "mean_intervention", "sd_intervention", "n_control", "mean_control", "sd_control"],
    "SMD": ["n_intervention", "mean_intervention", "sd_intervention", "n_control", "mean_control", "sd_control"],
    "PLOGIT": ["events", "n_total"],
    "ZCOR": ["r", "n_total"],
    "GEN": ["yi", "se"],
}


def fields_for(measure: str) -> list[str]:
    return FIELDS_BY_MEASURE.get((measure or "GEN").upper(), FIELDS_BY_MEASURE["GEN"])


def _fetch_xml(record: dict, *, timeout: int = 30, retries: int = 2) -> str | None:
    pmcid = record.get("pmcid")
    if not pmcid:
        return None
    import time
    req = urllib.request.Request(FULLTEXT.format(id=pmcid), headers=_UA)
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as exc:
            # 404/410/403 = genuinely not retrievable (not OA). 429/5xx = transient.
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            return None
        except Exception:  # noqa: BLE001 — transient network/timeout: retry with backoff
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            return None


def _narrative(xml: str) -> str:
    text = re.sub(r"<[^>]+>", " ", xml)
    return re.sub(r"\s+", " ", text).strip()


def _txt(el) -> str:
    return " ".join("".join(el.itertext()).split())


def extract_tables(xml: str) -> list[str]:
    """Parse JATS/HTML tables into readable pipe-delimited grids with captions."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []
    for el in root.iter():
        el.tag = el.tag.rpartition("}")[2]  # drop namespaces

    out, seen = [], set()
    for wrap in root.iter():
        if wrap.tag not in ("table-wrap", "table"):
            continue
        if id(wrap) in seen:
            continue
        if wrap.tag == "table-wrap":
            caption = " ".join(_txt(e) for e in list(wrap.findall("label")) + list(wrap.findall("caption")))
            tables = list(wrap.iter("table"))
            for t in tables:
                seen.add(id(t))
        else:
            caption, tables = "", [wrap]
        grids = []
        for table in tables:
            rows = []
            for tr in table.iter("tr"):
                cells = [_txt(c) for c in tr if c.tag in ("td", "th")]
                if any(cells):
                    rows.append(" | ".join(cells))
            if rows:
                grids.append("\n".join(rows))
        if grids:
            out.append((caption.strip() + "\n" if caption.strip() else "") + "\n".join(grids))
    return out


def fetch_fulltext(record: dict, *, timeout: int = 30) -> str | None:
    """Narrative full text (tables stripped) — used by full-text screening."""
    xml = _fetch_xml(record, timeout=timeout)
    return _narrative(xml) or None if xml else None


def fetch_fulltext_parts(record: dict, *, timeout: int = 30) -> tuple[str, list[str]]:
    """(narrative text, list of table grids) from the open-access full text."""
    xml = _fetch_xml(record, timeout=timeout)
    if not xml:
        return "", []
    return _narrative(xml), extract_tables(xml)


def extract_captions(xml: str) -> list[str]:
    """Figure captions/legends from JATS — they often carry key numbers."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []
    for el in root.iter():
        el.tag = el.tag.rpartition("}")[2]
    out = []
    for fig in root.iter("fig"):
        label = " ".join(_txt(e) for e in fig.findall("label"))
        caption = " ".join(_txt(e) for e in fig.findall("caption"))
        text = (label + " " + caption).strip()
        if text:
            out.append(text)
    return out


_FULLTEXT_CACHE: dict[str, dict] = {}


def fetch_fulltext_full(record: dict, *, timeout: int = 30) -> dict:
    """Everything extractable: narrative, tables and figure captions.

    Cached per-PMCID in-process so screening + extraction (or a re-run) don't
    re-download the same article.
    """
    pmcid = record.get("pmcid")
    if pmcid and pmcid in _FULLTEXT_CACHE:
        return _FULLTEXT_CACHE[pmcid]
    xml = _fetch_xml(record, timeout=timeout)
    if not xml:
        result = {"narrative": record.get("abstract", ""), "tables": [], "captions": [],
                  "xml": "", "has_fulltext": False}
    else:
        result = {"narrative": _narrative(xml), "tables": extract_tables(xml),
                  "captions": extract_captions(xml), "xml": xml, "has_fulltext": True}
    if pmcid and result["has_fulltext"]:
        _FULLTEXT_CACHE[pmcid] = result
    return result


def _label(record: dict) -> str:
    first = (record.get("authors") or "").split(",")[0].strip() or "Estudio"
    return f"{first} {record.get('year', '')}".strip()


def _build_prompt(tables: list[str], narrative: str, measure: str, outcome: str, fields: list[str]) -> str:
    tables_block = "\n\n".join(f"[TABLA {i + 1}]\n{t}" for i, t in enumerate(tables))[:9000]
    return (
        "Eres un revisor experto extrayendo datos para un meta-análisis. Extrae "
        "ÚNICAMENTE los números necesarios para calcular el efecto "
        f"«{measure}» para el desenlace «{outcome or 'el desenlace principal'}». "
        "Los datos suelen estar en las TABLAS: revísalas primero. No inventes "
        "valores: si un dato no aparece con claridad, ponlo en null.\n\n"
        f"Campos a extraer (numéricos): {', '.join(fields)}.\n"
        "Para tablas 2x2: a=eventos en el grupo de intervención/expuesto, b=no eventos en "
        "ese grupo, c=eventos en control/no expuesto, d=no eventos en control.\n\n"
        f"=== TABLAS DEL ARTÍCULO ===\n{tables_block or '(sin tablas extraíbles)'}\n\n"
        f"=== TEXTO (puede estar truncado) ===\n{narrative[:8000]}\n\n"
        "Devuelve SOLO un objeto JSON (sin markdown) con esta forma:\n"
        '{"found": true|false, "fields": {' + ", ".join(f'"{f}": <número|null>' for f in fields) +
        '}, "quote": "celda o frase exacta de donde sale el dato (indica la tabla)", "note": "aclaración breve"}'
    )


def extract_data(record: dict, *, measure: str = "OR", outcome: str = "", mode: str = "auto") -> dict:
    measure = (measure or "OR").upper()
    fields = fields_for(measure)
    narrative, tables = fetch_fulltext_parts(record)
    has_full = bool(narrative or tables)
    if not narrative and not tables:
        narrative = record.get("abstract", "")
    base = {"study_label": _label(record), "effect_measure": measure,
            "source": "fulltext" if has_full else "abstract", "n_tables": len(tables),
            "doi": record.get("doi"), "fields": {f: None for f in fields},
            "found": False, "quote": "", "note": ""}

    if not narrative and not tables:
        base["note"] = "Sin texto disponible (no es de acceso abierto)."
        return base
    if not (mode != "local" and (mode == "ai" or ai_available())):
        base["note"] = "Extracción manual: la IA no está disponible."
        return base
    try:
        obj = run_claude_json(_build_prompt(tables, narrative, measure, outcome, fields), timeout=120)
    except Exception as exc:  # noqa: BLE001
        base["note"] = f"No se pudo extraer con IA: {exc}"
        return base

    raw = obj.get("fields", {}) if isinstance(obj.get("fields"), dict) else {}
    cleaned = {}
    for f in fields:
        v = raw.get(f)
        try:
            cleaned[f] = float(v) if v not in (None, "", "null") else None
        except (TypeError, ValueError):
            cleaned[f] = None
    base.update({
        "fields": cleaned,
        "found": bool(obj.get("found")) and any(v is not None for v in cleaned.values()),
        "quote": str(obj.get("quote") or "")[:400],
        "note": str(obj.get("note") or ""),
    })
    return base


def extract_to_csv_row(extraction: dict) -> str:
    """One CSV line: study_label,effect_measure,<fields…> (blank where missing)."""
    fields = list(extraction["fields"].keys())
    vals = ["" if extraction["fields"][f] is None else _fmt(extraction["fields"][f]) for f in fields]
    label = extraction["study_label"].replace('"', "'")
    return f'"{label}",{extraction["effect_measure"]},' + ",".join(vals)


def _fmt(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else str(v)


# --- Comprehensive extraction (everything, for an Excel data sheet) ----------
def _num(v):
    if v in (None, "", "null", "NA", "NR"):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# The single-shot prompt over a whole article (all tables + text + captions) is
# too large/slow and times out. Instead we fan out into several small, focused
# calls — one for study characteristics, one per table, one for the narrative —
# run them in parallel, and merge. Each call has tiny input and output, so it
# finishes well within the timeout, and nothing is dropped.

_OUTCOME_SCHEMA = (
    '{"name":"","type":"binary|continuous|time-to-event|count|other","timepoint":"",'
    '"intervention":{"events":null,"n":null,"mean":null,"sd":null,"person_time":null},'
    '"control":{"events":null,"n":null,"mean":null,"sd":null,"person_time":null},'
    '"effect":{"measure":"","value":null,"ci_lower":null,"ci_upper":null,"p":null},'
    '"source":"","notes":""}'
)


def _build_main_prompt(parts: dict, record: dict) -> str:
    """Study characteristics + outcomes reported in text/figures, in one call.

    Merging these avoids reading the (long) narrative twice — one read, one set
    of tokens — while the per-table calls handle the bulk of the numbers."""
    caps = "\n".join(f"- {c}" for c in parts["captions"])[:2000]
    narr = parts["narrative"][:7000]
    return (
        "Eres un revisor experto haciendo la extracción de datos de un artículo para una revisión "
        "sistemática. Haz DOS cosas a la vez: (1) resume las CARACTERÍSTICAS del estudio, su "
        "población, brazos/grupos y seguimiento; (2) extrae los DESENLACES cuantitativos que se "
        "informen en el TEXTO o en los PIES DE FIGURA (no en tablas): números por brazo "
        "(eventos/N, media/DE, persona-tiempo) y/o efecto con IC95%. Si un valor SOLO aparece "
        "dibujado dentro de una figura, NO lo inventes: descríbelo en 'data_in_figures_only'. "
        "NO inventes nada: dato ausente = null/\"\".\n\n"
        f"=== TEXTO ===\n{narr}\n\n"
        f"=== PIES DE FIGURA ===\n{caps or '(ninguno)'}\n\n"
        "Devuelve SOLO un objeto JSON (sin markdown) con esta forma EXACTA:\n"
        '{"study":{"authors":"","year":"","country":"","design":"","setting":"","funding":"","registration":""},'
        '"population":{"description":"","total_n":null,"age":"","sex":"","key_inclusion":"","key_exclusion":""},'
        '"arms":[{"name":"","description":"","n":null,"details":""}],'
        '"followup":"","data_in_figures_only":"","notes":"",'
        '"outcomes":[' + _OUTCOME_SCHEMA + "]}\n"
        "Pon source=\"texto\" o \"figura\" en cada desenlace. Responde en español; números como números."
    )


def _build_table_prompt(table: str, idx: int) -> str:
    return (
        "Eres un revisor experto extrayendo datos para un meta-análisis desde UNA tabla de un "
        "artículo. Extrae CADA desenlace/resultado cuantitativo de la tabla, con los números por "
        "brazo (eventos/N, o media/DE, o eventos/persona-tiempo) y/o el efecto con su IC95%. "
        "Crea una entrada por cada fila/comparación con datos. Si la tabla es de características "
        "basales o no contiene resultados, devuelve la lista vacía. NO inventes: dato ausente = null.\n\n"
        f"=== TABLA {idx + 1} ===\n{table[:4500]}\n\n"
        'Devuelve SOLO un objeto JSON: {"outcomes":[' + _OUTCOME_SCHEMA + ", ...]}\n"
        "Pon en cada desenlace source=\"tabla " + str(idx + 1) + "\". Números como números."
    )


def _clean_arm(a: dict) -> dict:
    a = a or {}
    return {"events": _num(a.get("events")), "n": _num(a.get("n")),
            "mean": _num(a.get("mean")), "sd": _num(a.get("sd")),
            "person_time": _num(a.get("person_time"))}


def _clean_outcome(o: dict) -> dict | None:
    if not isinstance(o, dict) or not str(o.get("name", "")).strip():
        return None
    eff = o.get("effect", {}) if isinstance(o.get("effect"), dict) else {}
    return {
        "name": str(o.get("name", "")).strip(),
        "type": str(o.get("type", "")).strip(),
        "timepoint": str(o.get("timepoint", "")).strip(),
        "intervention": _clean_arm(o.get("intervention")),
        "control": _clean_arm(o.get("control")),
        "effect": {"measure": str(eff.get("measure", "")).strip(),
                   "value": _num(eff.get("value")), "ci_lower": _num(eff.get("ci_lower")),
                   "ci_upper": _num(eff.get("ci_upper")), "p": _num(eff.get("p"))},
        "source": str(o.get("source", "")).strip(), "notes": str(o.get("notes", "")).strip(),
        "from_figure": bool(o.get("from_figure")),
        # only meaningful for figure reads: True = estimated off a curve/bar,
        # False = a number printed on the figure (exact). Default exact otherwise.
        "approx": bool(o.get("approx")) if o.get("from_figure") else False,
    }


def _outcome_data_count(o: dict) -> int:
    """How many numeric data points an outcome carries (for dedup / richness)."""
    n = 0
    for arm in ("intervention", "control"):
        n += sum(1 for v in o.get(arm, {}).values() if v is not None)
    n += sum(1 for k in ("value", "ci_lower", "ci_upper", "p") if o.get("effect", {}).get(k) is not None)
    return n


def _dedup_outcomes(outcomes: list[dict]) -> list[dict]:
    """Drop empty outcomes and collapse duplicates of the same outcome.

    Outcomes are grouped by (name, timepoint). The richest copy is always kept.
    A second copy in the same group is kept only when it carries substantial data
    on its own (≥4 values) AND a distinct effect estimate — this preserves e.g.
    both an adjusted and an unadjusted HR while discarding partial text mentions
    that merely echo a number already captured in full from a table.
    """
    groups: dict[tuple, list[dict]] = {}
    order: list[tuple] = []
    for o in outcomes:
        if _outcome_data_count(o) == 0:
            continue  # no numbers — nothing to meta-analyse
        key = (o["name"].lower(), o["timepoint"].lower())
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(o)

    def _rank(o: dict) -> tuple:
        # exact text/table first, then printed-on-figure, then estimated-from-curve,
        # then richer over poorer.
        return (not o.get("from_figure"), not o.get("approx"), _outcome_data_count(o))

    kept: list[dict] = []
    for key in order:
        # Figure reads survive only when nothing more reliable covers the same
        # outcome+timepoint (i.e. they fill a real gap).
        members = sorted(groups[key], key=_rank, reverse=True)
        richest = members[0]
        kept.append(richest)
        seen_effects = {richest["effect"]["value"]}
        for o in members[1:]:
            val = o["effect"]["value"]
            # keep a second reliable analysis (e.g. adjusted vs unadjusted); never add
            # an approximate figure duplicate of something already captured.
            if (not (o.get("from_figure") and o.get("approx")) and _outcome_data_count(o) >= 4
                    and val is not None and val not in seen_effects):
                kept.append(o)
                seen_effects.add(val)
    return kept


def _assemble_full(study_obj: dict, outcomes: list[dict], record: dict) -> dict:
    study = study_obj.get("study", {}) if isinstance(study_obj.get("study"), dict) else {}
    study.setdefault("authors", record.get("authors", ""))
    study.setdefault("year", str(record.get("year", "")))
    pop = study_obj.get("population", {}) if isinstance(study_obj.get("population"), dict) else {}
    pop["total_n"] = _num(pop.get("total_n"))
    arms = []
    for a in (study_obj.get("arms") or []):
        if isinstance(a, dict):
            arms.append({"name": str(a.get("name", "")), "description": str(a.get("description", "")),
                         "n": _num(a.get("n")), "details": str(a.get("details", ""))})
    cleaned = [c for c in (_clean_outcome(o) for o in outcomes) if c]
    return {
        "label": _label(record), "doi": record.get("doi"), "pmid": record.get("pmid"),
        "study": {k: str(study.get(k, "")) for k in ("authors", "year", "country", "design", "setting", "funding", "registration")},
        "population": {**{k: str(pop.get(k, "")) for k in ("description", "age", "sex", "key_inclusion", "key_exclusion")},
                       "total_n": pop["total_n"]},
        "arms": arms, "followup": str(study_obj.get("followup", "")),
        "outcomes": _dedup_outcomes(cleaned),
        "data_in_figures_only": str(study_obj.get("data_in_figures_only", "")),
        "notes": str(study_obj.get("notes", "")),
    }


# Backwards-compatible single-object cleaner (used by tests / direct callers).
def _clean_full(obj: dict, record: dict) -> dict:
    return _assemble_full(obj, obj.get("outcomes") or [], record)


_MAX_TABLES = 12  # cap fan-out so very long supplements don't explode call count
# Bulk structured extraction is a great fit for a fast model: the numbers are
# right there in the supplied text, so it's reading, not reasoning. Default to a
# fast model for speed/economy on the user's account; override with the env var,
# set it empty to use the account default. Failed calls retry on the default model.
_EXTRACT_MODEL = os.environ.get("METAFORGE_EXTRACT_MODEL", "haiku")


def _run_jobs(jobs: list[tuple[str, str]], *, timeout: int, max_workers: int,
              model: str | None = None) -> tuple[dict, list[str]]:
    """Run prompt jobs in parallel; return ({key: result}, [failed_keys])."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results: dict[str, dict] = {}
    failed: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as ex:
        futs = {ex.submit(run_claude_json, prompt, timeout=timeout, model=model): key
                for key, prompt in jobs}
        for fut in as_completed(futs):
            key = futs[fut]
            try:
                results[key] = fut.result()
            except Exception:  # noqa: BLE001 — record the key so we can retry it once
                failed.append(key)
    return results, failed


_READ_FIGURES = os.environ.get("METAFORGE_READ_FIGURES", "on").lower() != "off"


def _figure_outcomes(record: dict, parts: dict, *, timeout: int, max_workers: int) -> tuple[list[dict], int]:
    """Download the article's figure images and read quantitative data off them.

    Returns (outcomes, n_figures_read). Uses the fast vision model — it reads the
    numbers printed on figures (forest plots, n-at-risk) accurately and quickly,
    and curve estimates are approximate (and kept out of synthesis) regardless.
    Any failure degrades silently to no figure data; text extraction is unaffected.
    """
    import tempfile
    from . import figvision

    try:
        with tempfile.TemporaryDirectory(prefix="mf_figs_") as tmp:
            figs = figvision.fetch_figure_images(record, parts.get("xml", ""), tmp)
            if not figs:
                return [], 0
            outs = figvision.extract_from_figures(figs, model=_EXTRACT_MODEL or None,
                                                  timeout=timeout, max_workers=max_workers, cwd=tmp)
            return outs, len(figs)
    except Exception:  # noqa: BLE001 — figures are a bonus, never block the run
        return [], 0


def extract_full(record: dict, *, mode: str = "auto", timeout: int = 150,
                 max_workers: int = 8, read_figures: bool | None = None) -> dict:
    """Comprehensive structured extraction of everything in an article.

    Fans out into small parallel AI calls — one merged study+narrative call plus
    one per table — so each finishes fast, then merges and de-duplicates. The
    first pass uses a fast model for speed; any section that fails is retried
    once on the account's default model, so nothing is lost. If the article has
    figure images, their quantitative data is also read with a vision call and
    added (flagged as approximate, read from the figure).
    """
    parts = fetch_fulltext_full(record)
    base = {"study_label": _label(record), "doi": record.get("doi"), "pmid": record.get("pmid"),
            "source": "fulltext" if parts["has_fulltext"] else "abstract",
            "has_fulltext": parts["has_fulltext"], "n_tables": len(parts["tables"]),
            "n_captions": len(parts["captions"]), "n_figures": 0,
            "data": None, "found": False, "note": ""}
    if not (parts["narrative"] or parts["tables"]):
        base["note"] = "Sin texto disponible (no es de acceso abierto)."
        return base
    if not (mode != "local" and (mode == "ai" or ai_available())):
        base["note"] = "La extracción comprehensiva requiere IA (ejecuta `claude login`)."
        return base

    job_prompts: dict[str, str] = {"main": _build_main_prompt(parts, record)}
    for i, t in enumerate(parts["tables"][:_MAX_TABLES]):
        job_prompts[f"table{i}"] = _build_table_prompt(t, i)

    # Kick off figure reading (download + vision) in the background so it overlaps
    # with the text extraction instead of running after it.
    from concurrent.futures import ThreadPoolExecutor
    want_figs = _READ_FIGURES if read_figures is None else read_figures
    fig_pool = fig_future = None
    if want_figs and parts.get("xml"):
        fig_pool = ThreadPoolExecutor(max_workers=1)
        fig_future = fig_pool.submit(_figure_outcomes, record, parts, timeout=timeout, max_workers=4)

    results, failed = _run_jobs(list(job_prompts.items()), timeout=timeout,
                                max_workers=max_workers, model=_EXTRACT_MODEL or None)
    if failed:  # retry the stragglers on the default model so nothing is silently dropped
        retry_jobs = [(k, job_prompts[k]) for k in failed]
        retried, failed = _run_jobs(retry_jobs, timeout=timeout, max_workers=max_workers, model=None)
        results.update(retried)
    errors = list(failed)

    study_obj = results.get("main", {}) if isinstance(results.get("main"), dict) else {}
    outcomes: list[dict] = []
    for obj in results.values():
        if isinstance(obj, dict):
            outcomes.extend(obj.get("outcomes") or [])

    if fig_future is not None:
        try:
            fig_outs, n_figs = fig_future.result()
            base["n_figures"] = n_figs
            outcomes.extend(fig_outs)
        except Exception:  # noqa: BLE001 — figures are a bonus, never block the run
            pass
        finally:
            fig_pool.shutdown(wait=False)

    data = _assemble_full(study_obj, outcomes, record)
    base["data"] = data
    base["found"] = bool(data["outcomes"])
    if errors and not data["outcomes"]:
        base["note"] = "No se pudo extraer con IA (revisa la conexión o reintenta)."
    elif errors:
        base["note"] = (f"Extracción parcial: {len(errors)} de {len(job_prompts)} secciones "
                        "no se pudieron leer tras un reintento; revisa esas tablas a mano.")
    return base
