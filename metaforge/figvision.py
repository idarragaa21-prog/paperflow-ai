"""Read data out of figure IMAGES (not just captions).

For an open-access article we already parse tables, captions and narrative as
text. But a lot of evidence lives only inside figure images — Kaplan-Meier /
cumulative-incidence curves, bar charts, or tables rendered as pictures. This
module downloads those images and asks the (vision-capable) Claude CLI to read
the quantitative data off them.

Honesty: numbers read off a plotted curve are APPROXIMATE (estimated from the
geometry). Every outcome produced here is flagged `from_figure=True` with a note
saying it was read from the figure, so the Excel layer can keep it in the
comprehensive sheet while keeping it OUT of the synthesis-ready sheet until a
human verifies it against the source.
"""
from __future__ import annotations

import os
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

from .ai import run_claude_json

_UA = {"User-Agent": "Mozilla/5.0 (compatible; MetaForge/1.0; systematic-review)"}
ARTICLE_HTML = "https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
_MAX_FIGURES = int(os.environ.get("METAFORGE_MAX_FIGURES", "8"))

_FIG_OUTCOME_SCHEMA = (
    '{"name":"","type":"binary|continuous|time-to-event|count|other","timepoint":"",'
    '"intervention":{"events":null,"n":null,"mean":null,"sd":null,"person_time":null},'
    '"control":{"events":null,"n":null,"mean":null,"sd":null,"person_time":null},'
    '"effect":{"measure":"","value":null,"ci_lower":null,"ci_upper":null,"p":null},'
    '"notes":""}'
)


def _figs_from_xml(xml: str) -> list[dict]:
    """[{label, caption, file}] for each <fig> that references a graphic file."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []
    for el in root.iter():
        el.tag = el.tag.rpartition("}")[2]
    out = []
    def _txt(el) -> str:
        return " ".join("".join(el.itertext()).split())

    for fig in root.iter("fig"):
        label = " ".join(_txt(e) for e in fig.findall("label"))
        caption = " ".join(_txt(e) for e in fig.findall("caption"))
        href, thumb = None, None
        for g in fig.iter("graphic"):
            h = g.get("href") or g.get("{http://www.w3.org/1999/xlink}href")
            if not h or not h.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff")):
                continue
            if (g.get("content-type") or "") == "thumb":
                thumb = thumb or h
            else:
                href = h
                break
        href = href or thumb
        if href:
            out.append({"label": label.strip(), "caption": caption.strip(),
                        "file": os.path.basename(href)})
    return out


def _cdn_map(pmcid: str, *, timeout: int = 25) -> dict[str, str]:
    """Map figure filename -> full CDN image URL by reading the article HTML."""
    try:
        req = urllib.request.Request(ARTICLE_HTML.format(pmcid=pmcid), headers=_UA)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001
        return {}
    mapping: dict[str, str] = {}
    for url in re.findall(r"https?://[^\"'\s)]+\.(?:jpg|jpeg|png|gif)", html):
        base = os.path.basename(url.split("?")[0])
        if base not in mapping or "_HTML." in base:  # prefer the full-size image
            mapping[base] = url
    return mapping


def _download(url: str, path: str, *, timeout: int = 30, retries: int = 2) -> bool:
    import time
    req = urllib.request.Request(url, headers=_UA)
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                ctype = resp.headers.get("Content-Type", "")
                data = resp.read()
            if not data or not ctype.startswith("image"):
                return False
            with open(path, "wb") as fh:
                fh.write(data)
            return True
        except urllib.error.HTTPError:
            return False
        except Exception:  # noqa: BLE001
            if attempt < retries:
                time.sleep(1.0 * (attempt + 1))
                continue
            return False
    return False


def fetch_figure_images(record: dict, xml: str, dest_dir: str) -> list[dict]:
    """Download up to _MAX_FIGURES figure images. Returns [{label, caption, path}]."""
    pmcid = record.get("pmcid")
    if not pmcid or not xml:
        return []
    figs = _figs_from_xml(xml)
    if not figs:
        return []
    cdn = _cdn_map(pmcid)
    if not cdn:
        return []
    got = []
    for i, fig in enumerate(figs[:_MAX_FIGURES]):
        url = cdn.get(fig["file"])
        if not url:  # try a stem (extension-insensitive) match
            stem = fig["file"].rsplit(".", 1)[0].lower()
            url = next((u for b, u in cdn.items() if b.rsplit(".", 1)[0].lower() == stem), None)
        if not url:
            continue
        ext = os.path.splitext(url.split("?")[0])[1] or ".jpg"
        path = os.path.join(dest_dir, f"fig{i}{ext}")
        if _download(url, path):
            got.append({"label": fig["label"], "caption": fig["caption"], "path": path})
    return got


def _fig_prompt(fig: dict) -> str:
    label = fig["label"] or "Figura"
    name = os.path.basename(fig["path"])  # referenced relative to the CLI's cwd
    return (
        "Eres un revisor experto extrayendo datos para un meta-análisis. Lee la IMAGEN del "
        f"archivo «{name}» (está en tu directorio de trabajo) y extrae CADA dato cuantitativo que "
        "puedas leer de la gráfica: valores en cada punto/tiempo, alturas de barras, números "
        "impresos sobre el gráfico, y cualquier efecto (HR/OR/RR/IRR), IC95% o p que aparezca "
        "dibujado. Si la figura es un diagrama de flujo o un esquema SIN datos cuantitativos de "
        "desenlaces, devuelve la lista vacía. Los valores leídos de una curva o barra son "
        "APROXIMADOS: indícalo en 'notes'. NO inventes lo que no se vea con claridad.\n\n"
        f"Pie de figura (contexto): {fig['caption'][:600] or '(sin pie)'}\n\n"
        'Devuelve SOLO un objeto JSON: {"outcomes":[' + _FIG_OUTCOME_SCHEMA + ", ...]}\n"
        f'Pon source="{label}" en cada desenlace. Responde en español; números como números.'
    )


def extract_from_figures(figs: list[dict], *, model: str | None = None,
                         timeout: int = 150, max_workers: int = 4,
                         cwd: str | None = None) -> list[dict]:
    """Run one vision call per figure image; return raw outcome dicts (flagged).

    `cwd` is the directory holding the images; the CLI runs there so it can read
    them without an interactive permission prompt.
    """
    if not figs:
        return []
    from concurrent.futures import ThreadPoolExecutor, as_completed

    outcomes: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as ex:
        futs = {ex.submit(run_claude_json, _fig_prompt(f), timeout=timeout, model=model, cwd=cwd): f
                for f in figs}
        for fut in as_completed(futs):
            fig = futs[fut]
            try:
                obj = fut.result()
            except Exception:  # noqa: BLE001 — a figure that can't be read is skipped
                continue
            if not isinstance(obj, dict):
                continue
            for o in (obj.get("outcomes") or []):
                if not isinstance(o, dict) or not str(o.get("name", "")).strip():
                    continue
                o["from_figure"] = True
                o["source"] = o.get("source") or fig["label"] or "figura"
                note = str(o.get("notes", "")).strip()
                tag = "leído de la imagen de la figura (aproximado)"
                o["notes"] = f"{note}; {tag}" if note and tag not in note else (note or tag)
                outcomes.append(o)
    return outcomes
