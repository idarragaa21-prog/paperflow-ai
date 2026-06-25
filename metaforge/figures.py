"""SVG → PNG rasterisation for embedding plots into Word/PDF.

Primary path is PyMuPDF (fitz): it ships wheels for every platform/Python (incl.
Apple Silicon + Python 3.14), needs NO system libraries, and renders crisply.
cairosvg is tried first only if the user happens to have it (system cairo);
svglib is kept as a last-ditch legacy fallback. Returns None if nothing works,
so callers degrade to a text-only document rather than crash.
"""
from __future__ import annotations

import io


def svg_to_png(svg: str, *, width: int = 1100) -> bytes | None:
    if not svg:
        return None
    data = svg.encode("utf-8")

    # 1) cairosvg — highest fidelity, but needs system cairo (optional extra)
    try:
        import cairosvg
        return cairosvg.svg2png(bytestring=data, output_width=width)
    except Exception:  # noqa: BLE001
        pass

    # 2) PyMuPDF — wheels everywhere, no system libs (the default path)
    try:
        import fitz
        doc = fitz.open(stream=data, filetype="svg")
        pdf = fitz.open("pdf", doc.convert_to_pdf())
        page = pdf[0]
        zoom = max(1.0, width / max(1.0, page.rect.width))
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        return pix.tobytes("png")
    except Exception:  # noqa: BLE001
        pass

    # 3) svglib + reportlab — legacy fallback (only if the C renderPM backend exists)
    try:
        from reportlab.graphics import renderPM
        from svglib.svglib import svg2rlg
        drawing = svg2rlg(io.StringIO(svg))
        if drawing is None:
            return None
        scale = width / max(1.0, drawing.width)
        drawing.scale(scale, scale)
        drawing.width *= scale
        drawing.height *= scale
        buf = io.BytesIO()
        renderPM.drawToFile(drawing, buf, fmt="PNG")
        return buf.getvalue()
    except Exception:  # noqa: BLE001
        return None


def png_available() -> bool:
    """Whether any rasteriser is importable (PyMuPDF is a core dependency)."""
    for mod in ("fitz", "cairosvg", "svglib"):
        try:
            __import__(mod)
            return True
        except Exception:  # noqa: BLE001
            continue
    return False
