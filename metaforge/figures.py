"""SVG → PNG rasterisation for embedding plots into Word/PDF.

Tries cairosvg first (best fidelity), then svglib (pure Python, no system
libraries). Returns None if neither is available, so callers can degrade to a
text-only document rather than crash.
"""
from __future__ import annotations

import io


def svg_to_png(svg: str, *, width: int = 1100) -> bytes | None:
    if not svg:
        return None
    try:  # high-fidelity path (needs libcairo)
        import cairosvg
        return cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=width)
    except Exception:  # noqa: BLE001
        pass
    try:  # pure-Python fallback
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
    """Whether any rasteriser is importable."""
    try:
        import cairosvg  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        pass
    try:
        import svglib  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False
