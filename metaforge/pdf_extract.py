"""Turn an uploaded PDF into the same `parts` shape the extractor expects.

Uses PyMuPDF (fitz) to pull out the narrative text, tables (as pipe-delimited
grids) and embedded figure images. The images are written to a temp directory so
the vision step can read them, exactly like the open-access figure pipeline. The
caller is responsible for cleaning up `image_dir` when done.
"""
from __future__ import annotations

import os
import re
import tempfile


def _looks_like_caption(line: str) -> bool:
    return bool(re.match(r"\s*(fig(?:ure|ura)?\.?|tabla|table)\s*\d+", line, re.I))


def pdf_to_parts(pdf_bytes: bytes, *, max_pages: int = 40, max_images: int = 12) -> dict:
    """Parse a PDF into {narrative, tables, captions, image_paths, image_dir, ...}.

    image_dir is a TemporaryDirectory path the caller must remove when finished
    (the images live there for the vision step).
    """
    import fitz  # PyMuPDF

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    narrative_parts: list[str] = []
    tables: list[str] = []
    captions: list[str] = []
    image_dir = tempfile.mkdtemp(prefix="mf_pdf_")
    image_paths: list[str] = []
    seen_xrefs: set[int] = set()

    for pno, page in enumerate(doc):
        if pno >= max_pages:
            break
        text = page.get_text("text") or ""
        narrative_parts.append(text)
        for line in text.splitlines():
            if _looks_like_caption(line) and len(line.strip()) > 8:
                captions.append(line.strip()[:200])
        # tables
        try:
            finder = page.find_tables()
            for tbl in (finder.tables if finder else []):
                grid = tbl.extract()
                rows = [" | ".join((str(c).strip() if c is not None else "") for c in row)
                        for row in grid if any(c not in (None, "") for c in row)]
                if len(rows) >= 2:
                    tables.append("\n".join(rows))
        except Exception:  # noqa: BLE001 — table detection is best-effort
            pass
        # embedded images (skip tiny logos/rules)
        for img in page.get_images(full=True):
            if len(image_paths) >= max_images:
                break
            xref = img[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.width < 130 or pix.height < 130:
                    pix = None
                    continue
                if pix.n - pix.alpha >= 4:  # CMYK / other → RGB
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                path = os.path.join(image_dir, f"fig_{pno}_{xref}.png")
                pix.save(path)
                image_paths.append(path)
                pix = None
            except Exception:  # noqa: BLE001
                continue

    narrative = re.sub(r"\s+\n", "\n", "\n".join(narrative_parts)).strip()
    doc.close()
    return {
        "narrative": narrative,
        "tables": tables,
        "captions": captions[:30],
        "image_paths": image_paths,
        "image_dir": image_dir,
        "has_fulltext": bool(narrative or tables),
        "n_pages": min(len(narrative_parts), max_pages),
    }
