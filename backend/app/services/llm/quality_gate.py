from __future__ import annotations

import re
from collections import Counter
from typing import Any

from app.services.llm.schemas import (
    ContentSlide,
    ImagePlaceholderSlide,
    OutlineMeta,
    PresentationOutline,
    ReferencesSlide,
    SectionSlide,
    SlideType,
    TitleSlide,
)


_STOPWORDS = {
    "de",
    "la",
    "el",
    "y",
    "en",
    "a",
    "un",
    "una",
    "para",
    "con",
    "por",
    "del",
    "los",
    "las",
    "se",
    "que",
    "es",
    "al",
    "o",
    "u",
}


def _tokenize(text: str) -> set[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9áéíóúñü\s]", " ", text)
    tokens = {t for t in text.split() if t and t not in _STOPWORDS and len(t) > 2}
    return tokens


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def enforce_citations_in_notes(slide: Any) -> None:
    """Append citations tokens to notes, without inventing."""
    if getattr(slide, "type", None) not in (SlideType.content, SlideType.image_placeholder):
        return
    citations: list[str] = getattr(slide, "citations", []) or []
    if not citations:
        # Explicit note when no IDs available
        if "Citas no disponibles" not in slide.notes:
            slide.notes = (slide.notes.rstrip() + "\n\nCitas no disponibles en metadata; revisar paper original.").strip()
        return

    suffix = " ".join(citations)
    if suffix not in slide.notes:
        slide.notes = (slide.notes.rstrip() + "\n\n" + suffix).strip()


def anti_redundancy(slides: list[Any], threshold: float = 0.65) -> None:
    """If consecutive slides are too similar, lightly rewrite the later slide title/bullets.

    We do NOT invent facts. Strategy: drop repeated bullets and keep the most distinct ones.
    """

    for i in range(1, len(slides)):
        a = slides[i - 1]
        b = slides[i]
        if getattr(a, "type", None) not in (SlideType.content, SlideType.section):
            continue
        if getattr(b, "type", None) != SlideType.content:
            continue

        a_text = " ".join(getattr(a, "content", []) or []) + " " + getattr(a, "title", "")
        b_text = " ".join(getattr(b, "content", []) or []) + " " + getattr(b, "title", "")
        sim = _jaccard(_tokenize(a_text), _tokenize(b_text))
        if sim <= threshold:
            continue

        # Remove bullets that also appear in previous slide (token overlap)
        prev_tokens = _tokenize(a_text)
        new_bullets: list[str] = []
        for bullet in list(getattr(b, "content", []) or []):
            if _jaccard(_tokenize(bullet), prev_tokens) < 0.6:
                new_bullets.append(bullet)

        # Ensure at least 3 bullets remain; if not, keep first 3 unique-ish
        if len(new_bullets) < 3:
            seen = set()
            for bullet in list(getattr(b, "content", []) or []):
                key = " ".join(sorted(_tokenize(bullet)))
                if key in seen:
                    continue
                seen.add(key)
                new_bullets.append(bullet)
                if len(new_bullets) >= 3:
                    break

        b.content = new_bullets[:8]
        if b.title:
            b.title = b.title + " (enfoque complementario)"


def _ensure_required_structure(outline: PresentationOutline) -> None:
    """Hard requirements: title slide, objectives, agenda, >=5 sections, pitfalls, checklist,
    1-2 image placeholders, 2 take-home slides, references last.

    This function inserts missing slides in a non-filler way (generic but useful), without references.
    """

    slides = outline.slides

    # Slide 1 title already enforced at validation time; ensure it has subtitle in content
    if isinstance(slides[0], TitleSlide) and not slides[0].content:
        slides[0].content = f"{outline.meta.audience} · {outline.meta.duration_minutes} min"

    def has_content_title(substr: str) -> bool:
        return any(s.type == SlideType.content and substr.lower() in (s.title or "").lower() for s in slides)

    def insert_after(index: int, slide: Any) -> None:
        slides.insert(index + 1, slide)

    # Slide 2 objectives
    if len(slides) < 2 or slides[1].type != SlideType.content or "objet" not in (slides[1].title or "").lower():
        obj = ContentSlide(
            type=SlideType.content,
            title="Objetivos",
            content=[
                "Definir conceptos clave y alcance clínico",
                "Reconocer presentación y evaluación diagnóstica",
                "Revisar opciones terapéuticas y criterios de selección",
                "Identificar complicaciones y medidas preventivas",
            ],
            notes="Objetivos docentes (estructura estándar).",
            citations=[],
        )
        insert_after(0, obj)

    # Slide 3 agenda
    if len(slides) < 3 or slides[2].type != SlideType.content or "agenda" not in (slides[2].title or "").lower():
        agenda = ContentSlide(
            type=SlideType.content,
            title="Agenda",
            content=[
                "Contexto y definiciones",
                "Diagnóstico y evaluación",
                "Tratamiento: conservador y quirúrgico (si aplica)",
                "Complicaciones y seguimiento",
                "Perlas clínicas + take-home",
            ],
            notes="Agenda sugerida; ajustar según evidencia disponible.",
            citations=[],
        )
        insert_after(1, agenda)

    # Ensure at least 5 section dividers with required titles
    required_sections = [
        "Contexto y definiciones",
        "Diagnóstico y evaluación",
        "Métodos y evidencia",
        "Resultados",
        "Aplicación clínica",
        "Limitaciones",
        "Tratamiento",
        "Complicaciones + perlas clínicas",
    ]

    existing = [s.title for s in slides if s.type == SlideType.section]
    for title in required_sections:
        if not any(title.lower() in (t or "").lower() for t in existing):
            # insert sections roughly after agenda
            idx = 2
            slides.insert(
                idx + 1,
                SectionSlide(type=SlideType.section, title=title, notes=f"Inicio de sección: {title}."),
            )

    # Pitfalls slide
    if not has_content_title("pitfalls") and not has_content_title("errores"):
        slides.insert(
            max(3, len(slides) - 3),
            ContentSlide(
                type=SlideType.content,
                title="Pitfalls / errores frecuentes",
                content=[
                    "Anclaje diagnóstico prematuro (no re-evaluar si no mejora)",
                    "Interpretación parcial de imágenes (omitir proyecciones/planos)",
                    "Subestimar comorbilidades/factores de riesgo",
                    "Plan terapéutico sin objetivos medibles (dolor/función/tiempo)",
                ],
                notes="Errores frecuentes en práctica clínica; adaptar al tema específico.",
                citations=[],
            ),
        )

    # Checklist slide
    if not has_content_title("checklist"):
        slides.insert(
            max(3, len(slides) - 3),
            ContentSlide(
                type=SlideType.content,
                title="Checklist práctico / pasos",
                content=[
                    "Confirmar diagnóstico y diferenciales",
                    "Definir severidad/estadio y factores de riesgo",
                    "Seleccionar tratamiento según criterios (clínica + imagen + paciente)",
                    "Plan de seguimiento y red flags",
                    "Documentar outcome (dolor/función/complicaciones)",
                ],
                notes="Checklist práctico para aplicar en consulta/guardia.",
                citations=[],
            ),
        )

    # Take-home messages (2)
    th_count = sum(1 for s in slides if s.type == SlideType.content and "take-home" in (s.title or "").lower())
    while th_count < 2:
        slides.insert(
            max(3, len(slides) - 2),
            ContentSlide(
                type=SlideType.content,
                title=f"Take-home messages ({th_count+1}/2)",
                content=[
                    "Define 3 decisiones clínicas clave del tema",
                    "Prioriza criterios de selección del tratamiento",
                    "Anticipa complicaciones y cómo prevenirlas",
                    "Usa un plan de seguimiento con métricas claras",
                ],
                notes="Mensajes clave finales. Ajustar con evidencia específica cuando haya papers.",
                citations=[],
            ),
        )
        th_count += 1

    # Image placeholders 1-2
    img_count = sum(1 for s in slides if s.type == SlideType.image_placeholder)
    if img_count == 0:
        slides.insert(
            max(3, len(slides) - 4),
            ImagePlaceholderSlide(
                type=SlideType.image_placeholder,
                title="Algoritmo / figura clave",
                notes="Insertar figura: algoritmo diagnóstico/terapéutico relevante para el tema.",
                citations=[],
                image_suggestion="Algoritmo de decisión (diagnóstico → clasificación → tratamiento).",
            ),
        )

    # References slide last (ensure last type)
    if slides[-1].type != SlideType.references:
        # remove any references slides not at end
        slides[:] = [s for s in slides if s.type != SlideType.references]
        slides.append(ReferencesSlide(type=SlideType.references, title="Referencias", notes=""))


def _clip_bullets(outline: PresentationOutline) -> None:
    for s in outline.slides:
        if s.type == SlideType.content:
            if len(s.content) > 6 and "WARNING" not in (s.notes or ""):
                s.notes = (s.notes or "").rstrip() + "\n\nWARNING: demasiados bullets (>6). Considera simplificar." 
            # hard cap
            if len(s.content) > 10:
                s.content = s.content[:10]


def _ensure_slide_count(outline: PresentationOutline) -> None:
    slides = outline.slides

    # If too many: drop lowest-value content slides with generic titles.
    def score(slide: Any) -> int:
        if slide.type == SlideType.title:
            return 999
        if slide.type == SlideType.references:
            return 998
        if slide.type == SlideType.section:
            return 900
        t = (slide.title or "").lower()
        if "objet" in t or "agenda" in t:
            return 800
        if "take-home" in t:
            return 850
        if "checklist" in t or "pitfalls" in t or "errores" in t:
            return 840
        if slide.type == SlideType.image_placeholder:
            return 830
        return 500

    while len(slides) > 40:
        # remove a content slide with lowest score, preferring duplicates by title
        content_idxs = [i for i, s in enumerate(slides) if s.type == SlideType.content]
        if not content_idxs:
            slides.pop(-2)
            continue
        titles = [slides[i].title for i in content_idxs]
        counts = Counter([t.lower() for t in titles if t])
        # prefer removing repeated titles
        remove_idx = None
        for i in content_idxs:
            t = (slides[i].title or "").lower()
            if t and counts.get(t, 0) > 1:
                remove_idx = i
                break
        if remove_idx is None:
            remove_idx = min(content_idxs, key=lambda i: score(slides[i]))
        slides.pop(remove_idx)

    # If too few: insert useful slides inside sections
    def insert_before_references(slide: Any) -> None:
        if slides and slides[-1].type == SlideType.references:
            slides.insert(len(slides) - 1, slide)
        else:
            slides.append(slide)

    while len(slides) < 30:
        insert_before_references(
            ContentSlide(
                type=SlideType.content,
                title="Punto clave adicional",
                content=[
                    "Define cuándo escalar evaluación (red flags)",
                    "Selecciona estudios complementarios de forma costo-efectiva",
                    "Integra preferencias del paciente y riesgos",
                    "Documenta decisión clínica y plan de seguimiento",
                ],
                notes="Slide añadido por auto-fix para cumplir rango 30–40 sin inventar evidencia.",
                citations=[],
            )
        )


def quality_gate_and_fix(outline_dict: dict[str, Any]) -> PresentationOutline:
    """Local quality gate.

    - Parses into Pydantic schema (strict)
    - Applies auto-fix to meet hard constraints (30–40 slides, required structure)
    - Anti-redundancy on consecutive content slides
    - Enforces citations tokens in notes
    - Validates again; raises if still invalid
    """

    meta = outline_dict.get("meta") or {}
    meta.setdefault("target_slides", 36)
    outline_dict["meta"] = meta

    # Best effort normalize slide fields (so we can auto-fix instead of failing early)
    slides = outline_dict.get("slides") or []
    for s in slides:
        if not isinstance(s, dict):
            continue
        t = (s.get("type") or "").lower()

        # normalize content/bullets
        if t == "content":
            if "bullets" in s and "content" not in s:
                s["content"] = s.pop("bullets")
            if "content" not in s or s["content"] is None:
                s["content"] = []
            if not isinstance(s["content"], list):
                s["content"] = [str(s["content"])]

            s.setdefault("notes", "(auto-fix) notas pendientes")
            s.setdefault("citations", [])

        elif t == "image_placeholder":
            s.setdefault("notes", "(auto-fix) insertar imagen/figura")
            s.setdefault("citations", [])
            s.setdefault("image_suggestion", s.get("image_suggestion"))

        elif t == "section":
            s.setdefault("notes", "(auto-fix) inicio de sección")

        elif t == "title":
            # subtitle lives in content
            s.setdefault("content", s.get("content") or "")
            s.setdefault("notes", s.get("notes") or "")

        elif t == "references":
            s.setdefault("notes", s.get("notes") or "")

    outline_dict["slides"] = slides

    # Pre-flight: ensure title + references exist to allow later fixes
    if not slides:
        slides = [
            {"type": "title", "title": outline_dict.get("title") or meta.get("topic") or "Presentation", "content": ""},
            {"type": "references", "title": "Referencias", "notes": ""},
        ]
        outline_dict["slides"] = slides

    # Ensure first is title
    if slides and isinstance(slides[0], dict) and (slides[0].get("type") or "").lower() != "title":
        slides.insert(0, {"type": "title", "title": outline_dict.get("title") or meta.get("topic") or "Presentation", "content": ""})

    # Ensure last is references
    if slides and isinstance(slides[-1], dict) and (slides[-1].get("type") or "").lower() != "references":
        # remove any mid references
        slides[:] = [s for s in slides if not (isinstance(s, dict) and (s.get("type") or "").lower() == "references")]
        slides.append({"type": "references", "title": "Referencias", "notes": ""})

    # Pre-adjust slide count into 30-40 range (rough) to satisfy schema
    while len(slides) < 30:
        slides.insert(
            max(1, len(slides) - 1),
            {
                "type": "content",
                "title": "Punto clave adicional",
                "content": [
                    "Identificar red flags que cambian la conducta",
                    "Elegir estudios complementarios con criterio",
                    "Definir criterios de tratamiento y seguimiento",
                    "Documentar outcomes y complicaciones",
                ],
                "notes": "Auto-fix: slide añadido para cumplir 30–40 sin inventar evidencia.",
                "citations": [],
            },
        )

    while len(slides) > 40:
        # drop a mid content slide (avoid first 3 and last)
        drop_idx = None
        for i in range(3, len(slides) - 1):
            s = slides[i]
            if isinstance(s, dict) and (s.get("type") or "").lower() == "content":
                drop_idx = i
                break
        if drop_idx is None:
            break
        slides.pop(drop_idx)

    outline_dict["slides"] = slides

    outline = PresentationOutline.model_validate(outline_dict)

    # Auto-fix passes (Pydantic object-level)
    _ensure_required_structure(outline)
    _clip_bullets(outline)
    anti_redundancy(outline.slides)
    for s in outline.slides:
        if s.type in (SlideType.content, SlideType.image_placeholder):
            enforce_citations_in_notes(s)

    _ensure_slide_count(outline)

    # Validate again
    outline = PresentationOutline.model_validate(outline.model_dump())
    return outline
