from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

from app.core.logger import logger


@dataclass
class OCRAvailability:
    ocr_enabled: bool
    tesseract_available: bool
    ocrmypdf_available: bool


def detect_ocr_availability(*, ocr_enabled: bool) -> OCRAvailability:
    t_ok = False
    ocrmypdf_ok = False

    try:
        import pytesseract

        _ = pytesseract.get_tesseract_version()
        t_ok = True
    except Exception:
        logger.warning("Tesseract not installed. OCR disabled. Install with: brew install tesseract")

    try:
        import ocrmypdf  # noqa: F401

        ocrmypdf_ok = True
    except Exception:
        logger.warning("ocrmypdf not installed. Scanned PDF preprocessing disabled.")

    return OCRAvailability(ocr_enabled=bool(ocr_enabled), tesseract_available=t_ok, ocrmypdf_available=ocrmypdf_ok)


def ocrmypdf_preprocess(input_pdf: Path, output_pdf: Path) -> bool:
    """Run OCRmyPDF best-effort. Returns True on success."""

    try:
        import ocrmypdf

        ocrmypdf.ocr(
            str(input_pdf),
            str(output_pdf),
            skip_text=True,
            deskew=True,
            optimize=1,
            rotate_pages=True,
            progress_bar=False,
        )
        return True
    except Exception as e:
        logger.warning(f"ocrmypdf preprocess failed: {e}")
        return False


def ocr_pages_best_effort(pdf_path: Path, *, max_pages: int = 3) -> tuple[str, bool]:
    """OCR first N pages (full page images). Returns (ocr_text, used)."""

    try:
        import fitz
        import pytesseract
        from PIL import Image

        doc = fitz.open(pdf_path)
        try:
            chunks: list[str] = []
            for pno in range(min(max_pages, doc.page_count)):
                page = doc.load_page(pno)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                txt = pytesseract.image_to_string(img)
                if txt and txt.strip():
                    chunks.append(f"[page {pno+1}]\n{txt.strip()}")
            out = "\n\n".join(chunks).strip()
            return out, bool(out)
        finally:
            doc.close()
    except Exception as e:
        logger.warning(f"OCR pages failed: {e}")
        return "", False
