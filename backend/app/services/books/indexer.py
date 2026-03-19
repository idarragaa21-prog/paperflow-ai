from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.core.logger import logger


STOPWORDS = set(
    [
        # Spanish
        "de",
        "la",
        "el",
        "y",
        "en",
        "del",
        "los",
        "las",
        "un",
        "una",
        "para",
        "por",
        "con",
        "sin",
        "a",
        "o",
        "u",
        "al",
        "se",
        "que",
        "como",
        "es",
        "son",
        "más",
        "menos",
        "muy",
        "sobre",
        "entre",
        # English
        "the",
        "and",
        "or",
        "of",
        "to",
        "in",
        "for",
        "with",
        "without",
        "on",
        "by",
        "from",
        "is",
        "are",
        "be",
        "as",
        "an",
        "a",
    ]
)


@dataclass
class ChapterCandidate:
    title: str
    page_start: int


def _tokenize(text: str) -> list[str]:
    toks = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ\-]{2,}", text)
    out: list[str] = []
    for t in toks:
        s = t.lower()
        if s in STOPWORDS:
            continue
        if len(s) < 3:
            continue
        out.append(s)
    return out


def _top_keywords(text: str, k: int = 20) -> list[str]:
    toks = _tokenize(text)
    if not toks:
        return []
    c = Counter(toks)
    return [w for (w, _) in c.most_common(k)]


def _detect_chapter_title(lines: list[str]) -> str | None:
    for ln in lines[:8]:
        s = (ln or "").strip()
        if not s:
            continue
        if re.match(r"^(chapter|cap[ií]tulo)\s+\d+\b", s, flags=re.I):
            return s
        # common ToC-like heading: short line in title case
        if 4 <= len(s) <= 80 and sum(ch.isalpha() for ch in s) >= 4:
            # avoid lines that are just numbers
            if re.match(r"^\d+(\.\d+)*$", s):
                continue
            # heuristic: many uppercase words or title-case
            return s
    return None


def index_book_pdf(pdf_path: Path) -> dict:
    """Index a book PDF. Returns dict with: title, total_pages, chapters[].

    chapters = [{title, page_start, page_end, keywords[]}]
    """

    import fitz

    doc = fitz.open(pdf_path)
    try:
        total_pages = int(doc.page_count)
        meta_title = (doc.metadata or {}).get("title") if hasattr(doc, "metadata") else None
        meta_title = (meta_title or "").strip() or None

        candidates: list[ChapterCandidate] = []
        # sample first line(s) per page for headings
        for i in range(total_pages):
            page = doc.load_page(i)
            txt = page.get_text("text") or ""
            lines = [ln.strip() for ln in (txt.splitlines() if txt else []) if ln.strip()]
            title = _detect_chapter_title(lines)
            if title:
                # avoid duplicates: same title repeated on every page header
                if candidates and candidates[-1].title.lower() == title.lower():
                    continue
                candidates.append(ChapterCandidate(title=title, page_start=i + 1))

        # build chapter ranges
        chapters: list[dict] = []
        if not candidates:
            # fallback: single chapter whole book
            all_text = "\n".join((doc.load_page(i).get_text("text") or "") for i in range(min(total_pages, 20)))
            chapters.append(
                {
                    "title": meta_title or pdf_path.stem,
                    "page_start": 1,
                    "page_end": total_pages,
                    "keywords": _top_keywords(all_text, k=30),
                }
            )
        else:
            for idx, cand in enumerate(candidates):
                start = cand.page_start
                end = (candidates[idx + 1].page_start - 1) if idx + 1 < len(candidates) else total_pages
                # extract first 2 pages of chapter for keywords
                sample_pages = list(range(start, min(end, start + 1) + 1))
                sample_text_parts: list[str] = []
                for pno in sample_pages:
                    try:
                        sample_text_parts.append(doc.load_page(pno - 1).get_text("text") or "")
                    except Exception:
                        pass
                sample_text = "\n".join(sample_text_parts)
                chapters.append(
                    {
                        "title": cand.title,
                        "page_start": start,
                        "page_end": end,
                        "keywords": _top_keywords(sample_text, k=25),
                    }
                )

        title = meta_title or (chapters[0].get("title") if chapters else None) or pdf_path.stem

        return {
            "title": title,
            "total_pages": total_pages,
            "chapters": chapters,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        doc.close()


def extract_pages_text(pdf_path: Path, page_start: int, page_end: int, *, max_chars: int = 12000) -> str:
    import fitz

    doc = fitz.open(pdf_path)
    try:
        parts: list[str] = []
        for pno in range(max(1, int(page_start)), int(page_end) + 1):
            if sum(len(p) for p in parts) >= max_chars:
                break
            try:
                parts.append(doc.load_page(pno - 1).get_text("text") or "")
            except Exception:
                continue
        out = "\n".join(parts).strip()
        if len(out) > max_chars:
            out = out[:max_chars]
        return out
    finally:
        doc.close()
