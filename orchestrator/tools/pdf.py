from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from .web import find_pdf_links_in_html, safe_fetch_bytes


PDF_SIGNATURE = b'%PDF'


def _safe_name(url: str) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name or 'downloaded.pdf'
    name = re.sub(r'[^a-zA-Z0-9._-]+', '-', name)
    if not name.lower().endswith('.pdf'):
        name += '.pdf'
    return name


def _rough_page_count(data: bytes) -> int | None:
    matches = len(re.findall(rb'/Type\s*/Page\b', data))
    return matches or None


def _run_text_tool(command: list[str]) -> str:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode == 0:
        return completed.stdout.strip()
    return ''


def _extract_text_with_pdftotext(pdf_path: Path) -> str:
    if not shutil.which('pdftotext'):
        return ''
    return _run_text_tool(['pdftotext', '-layout', str(pdf_path), '-'])


def _extract_text_with_pypdf(pdf_path: Path, *, max_pages: int = 20) -> tuple[str, int]:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    page_count = len(reader.pages)
    chunks: list[str] = []
    for page in reader.pages[:max_pages]:
        try:
            chunks.append(page.extract_text() or '')
        except Exception:
            continue
    text = '\n'.join(chunk.strip() for chunk in chunks if chunk.strip())
    return text, page_count


def _ocr_pdf(pdf_path: Path) -> Path | None:
    if not shutil.which('ocrmypdf'):
        return None
    with tempfile.TemporaryDirectory(prefix='orch-ocr-') as tmp_dir:
        output_path = Path(tmp_dir) / 'ocr.pdf'
        completed = subprocess.run(
            ['ocrmypdf', '--skip-text', '--quiet', str(pdf_path), str(output_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0 or not output_path.exists():
            return None
        persisted = pdf_path.with_name(f'{pdf_path.stem}.ocr{pdf_path.suffix}')
        persisted.write_bytes(output_path.read_bytes())
        return persisted


def extract_pdf_text(path: str | Path, *, max_pages: int = 20) -> dict:
    pdf_path = Path(path)
    method = 'pypdf'
    text = _extract_text_with_pdftotext(pdf_path)
    page_count = None
    if text:
        method = 'pdftotext'
        try:
            _, page_count = _extract_text_with_pypdf(pdf_path, max_pages=max_pages)
        except Exception:
            page_count = None
    else:
        text, page_count = _extract_text_with_pypdf(pdf_path, max_pages=max_pages)

    ocr_used = False
    if len(text.strip()) < 500:
        ocr_path = _ocr_pdf(pdf_path)
        if ocr_path is not None:
            ocr_text = _extract_text_with_pdftotext(ocr_path)
            if ocr_text and len(ocr_text) > len(text):
                text = ocr_text
                method = 'ocrmypdf+pdftotext'
                ocr_used = True
                try:
                    _, page_count = _extract_text_with_pypdf(ocr_path, max_pages=max_pages)
                except Exception:
                    pass

    return {
        'path': str(pdf_path),
        'page_count': page_count,
        'text': text,
        'text_preview': text[:3000],
        'method': method,
        'ocr_used': ocr_used,
    }


def _normalize_label(value: str | None) -> str:
    if value is None:
        return ''
    lowered = str(value).strip().lower()
    lowered = lowered.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
    return re.sub(r'[^a-z0-9]+', ' ', lowered).strip()


def _search(patterns: list[str], text: str, *, flags: int = re.IGNORECASE) -> tuple[str | None, str | None]:
    for pattern in patterns:
        found = re.search(pattern, text, flags=flags)
        if found:
            return found.group(1).strip(), found.group(0).strip()
    return None, None


FIELD_SPECS = {
    'primer autor': {
        'key': 'first_author',
        'patterns': [],
        'source': 'metadata',
    },
    'ano de publicacion': {
        'key': 'year',
        'patterns': [r'\b(19\d{2}|20\d{2})\b'],
        'source': 'metadata',
    },
    'pais': {
        'key': 'country',
        'patterns': [r'(?:conducted in|from|in)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)'],
    },
    'revista': {
        'key': 'journal',
        'patterns': [],
        'source': 'metadata',
    },
    'diseno del estudio': {
        'key': 'design',
        'patterns': [],
    },
    'numero total de pacientes': {
        'key': 'n_total',
        'patterns': [r'\bn\s*=\s*(\d{1,4})\b', r'(\d{1,4})\s+patients', r'included\s+(\d{1,4})'],
    },
    'edad media de o mediana riq': {
        'key': 'age_mean',
        'patterns': [r'mean age(?: was| of|:)?\s*(\d+(?:\.\d+)?)', r'age(?: was| of|:)?\s*(\d+(?:\.\d+)?)\s*(?:years|y)'],
    },
    'sexo masculino': {
        'key': 'male_sex',
        'patterns': [r'(?:male|men)\s*(\d+\s*\(?\d*%?\)?)'],
    },
    'mecanismo de trauma': {
        'key': 'trauma_mechanism',
        'patterns': [r'(?:mechanism of injury|mechanism)\s*[:\-]?\s*([^\.;]{1,80})'],
    },
    'clasificacion gustilo anderson': {
        'key': 'gustilo',
        'patterns': [r'(Gustilo[^\.:\n]{1,100})'],
    },
    'tamano medio del defecto de': {
        'key': 'defect_size_cm',
        'patterns': [r'(?:defect size|bone defect)(?: was| of|:)?\s*(\d+(?:\.\d+)?)\s*cm'],
    },
    'localizacion': {
        'key': 'location',
        'patterns': [r'(?:location|located at)\s*[:\-]?\s*([^\.;]{1,80})'],
    },
    'estado de partes blandas': {
        'key': 'soft_tissue_status',
        'patterns': [r'(?:soft tissue|soft-tissue)[^\.:\n]{0,40}[:\-]?\s*([^\.;]{1,80})'],
    },
    'tipo de colgajo si aplica': {
        'key': 'flap_type',
        'patterns': [r'(?:flap|free flap|local flap)[^\.:\n]{0,40}[:\-]?\s*([^\.;]{1,80})'],
    },
    'infeccion al momento de reconstruccion': {
        'key': 'infection_at_reconstruction',
        'patterns': [r'(?:infection at reconstruction|infected at baseline)[^\.:\n]{0,20}[:\-]?\s*([^\.;]{1,80})'],
    },
    'tipo de infeccion': {
        'key': 'infection_type',
        'patterns': [r'(?:osteomyelitis|chronic infection|acute infection|deep infection)[^\.:\n]{0,40}'],
    },
    'microorganismo': {
        'key': 'microorganism',
        'patterns': [r'(?:staphylococcus|pseudomonas|enterococcus|e\.?\s*coli)[^\.;]{0,50}'],
    },
    'tipo de fijador': {
        'key': 'fixator_type',
        'patterns': [r'(Ilizarov|TSF|Taylor Spatial Frame|monolateral|intramedullary nail|plate)'],
    },
    'tasa de distraccion': {
        'key': 'distraction_rate',
        'patterns': [r'(\d+(?:\.\d+)?)\s*mm\s*/\s*day'],
    },
    'indice de curacion healing index': {
        'key': 'healing_index',
        'patterns': [r'(?:healing index)[^0-9]{0,20}(\d+(?:\.\d+)?)\s*(?:months|mo)?\s*/\s*cm'],
    },
    'duracion total con fijador externo': {
        'key': 'external_fixator_months',
        'patterns': [r'(?:external fixator time|duration with external fixator)[^0-9]{0,20}(\d+(?:\.\d+)?)\s*(?:months|mo)'],
    },
    'consolidacion osea': {
        'key': 'consolidation',
        'patterns': [r'(?:bone union|union rate|consolidation)[^\.:\n]{0,40}[:\-]?\s*([^\.;]{1,100})'],
    },
    'tiempo hasta consolidacion': {
        'key': 'time_to_union',
        'patterns': [r'(?:time to union|time to consolidation)[^0-9]{0,20}(\d+(?:\.\d+)?)\s*(?:months|mo)'],
    },
    'definicion de consolidacion': {
        'key': 'union_definition',
        'patterns': [r'(?:defined as|union was defined as)\s*([^\.;]{1,140})'],
    },
    'infeccion profunda postoperatoria': {
        'key': 'postop_infection',
        'patterns': [r'(?:deep infection|postoperative infection)[^\.:\n]{0,40}[:\-]?\s*([^\.;]{1,80})'],
    },
    'reintervencion no planificada': {
        'key': 'reintervention',
        'patterns': [r'(?:reoperation|reintervention)[^\.:\n]{0,40}[:\-]?\s*([^\.;]{1,80})'],
    },
    'discrepancia de longitud residual': {
        'key': 'residual_length_discrepancy',
        'patterns': [r'(?:limb length discrepancy|residual discrepancy)[^0-9]{0,20}(\d+(?:\.\d+)?)\s*cm'],
    },
    'deformidad angular residual': {
        'key': 'residual_angular_deformity',
        'patterns': [r'(?:angular deformity|residual angulation)[^0-9]{0,20}(\d+(?:\.\d+)?)\s*(?:degrees|deg|°)'],
    },
    'score funcional escala': {
        'key': 'functional_score',
        'patterns': [r'(?:functional score|AOFAS|DASH|MEPS|Constant)[^\.:\n]{0,40}[:\-]?\s*([^\.;]{1,80})'],
    },
    'asami oseo': {
        'key': 'asami_bone',
        'patterns': [r'(?:ASAMI bone)[^\.:\n]{0,40}[:\-]?\s*([^\.;]{1,80})'],
    },
    'asami funcional': {
        'key': 'asami_functional',
        'patterns': [r'(?:ASAMI functional)[^\.:\n]{0,40}[:\-]?\s*([^\.;]{1,80})'],
    },
    'amputacion secundaria': {
        'key': 'secondary_amputation',
        'patterns': [r'(?:amputation)[^\.:\n]{0,40}[:\-]?\s*([^\.;]{1,80})'],
    },
    'tiempo total de tratamiento': {
        'key': 'total_treatment_months',
        'patterns': [r'(?:total treatment time)[^0-9]{0,20}(\d+(?:\.\d+)?)\s*(?:months|mo)'],
    },
    'infeccion de tracto de pin': {
        'key': 'pin_tract_infection',
        'patterns': [r'(?:pin tract infection)[^\.:\n]{0,40}[:\-]?\s*([^\.;]{1,80})'],
    },
    'fractura del regenerado': {
        'key': 'regenerate_fracture',
        'patterns': [r'(?:regenerate fracture)[^\.:\n]{0,40}[:\-]?\s*([^\.;]{1,80})'],
    },
    'no union del docking': {
        'key': 'docking_nonunion',
        'patterns': [r'(?:docking site nonunion|docking nonunion)[^\.:\n]{0,40}[:\-]?\s*([^\.;]{1,80})'],
    },
    'fallo del implante': {
        'key': 'implant_failure',
        'patterns': [r'(?:implant failure)[^\.:\n]{0,40}[:\-]?\s*([^\.;]{1,80})'],
    },
    'equino del pie': {
        'key': 'equinus',
        'patterns': [r'(?:equinus)[^\.:\n]{0,40}[:\-]?\s*([^\.;]{1,80})'],
    },
    'rigidez articular': {
        'key': 'joint_stiffness',
        'patterns': [r'(?:joint stiffness|stiffness)[^\.:\n]{0,40}[:\-]?\s*([^\.;]{1,80})'],
    },
    'edema persistente': {
        'key': 'persistent_edema',
        'patterns': [r'(?:persistent edema|edema)[^\.:\n]{0,40}[:\-]?\s*([^\.;]{1,80})'],
    },
    'tromboembolismo': {
        'key': 'thromboembolism',
        'patterns': [r'(?:thromboembolism|DVT|pulmonary embolism)[^\.:\n]{0,40}[:\-]?\s*([^\.;]{1,80})'],
    },
    'lesion neurovascular': {
        'key': 'neurovascular_injury',
        'patterns': [r'(?:neurovascular injury)[^\.:\n]{0,40}[:\-]?\s*([^\.;]{1,80})'],
    },
    'fracaso del injerto': {
        'key': 'graft_failure',
        'patterns': [r'(?:graft failure)[^\.:\n]{0,40}[:\-]?\s*([^\.;]{1,80})'],
    },
    'otras complicaciones': {
        'key': 'notes',
        'patterns': [r'(?:complications?)[^\.:\n]{0,40}[:\-]?\s*([^\.;]{1,140})'],
    },
    'seguimiento medio de o mediana riq': {
        'key': 'follow_up_months',
        'patterns': [r'(?:follow[- ]?up)[^0-9]{0,20}(\d+(?:\.\d+)?)\s*(?:months|mo)'],
    },
}


def _metadata_value(key: str, metadata: dict) -> str | None:
    if key == 'first_author':
        authors = metadata.get('authors') or []
        if authors:
            return authors[0].split()[-1]
        return None
    if key == 'year':
        year = metadata.get('year')
        return str(year) if year else None
    if key == 'journal':
        return metadata.get('journal')
    if key == 'study_id':
        return metadata.get('study_id') or metadata.get('doi') or metadata.get('title')
    return metadata.get(key)


def infer_study_fields(text: str, metadata: dict | None = None) -> dict:
    metadata = metadata or {}
    normalized_text = ' '.join(text.split())
    lowered = normalized_text.lower()

    design = None
    design_evidence = None
    if 'randomized' in lowered or 'randomised' in lowered:
        design = 'ECA'
        design_evidence = 'randomized/randomised'
    elif 'retrospective' in lowered:
        design = 'Cohorte retrospectiva'
        design_evidence = 'retrospective'
    elif 'prospective' in lowered:
        design = 'Cohorte prospectiva'
        design_evidence = 'prospective'
    elif 'case series' in lowered or 'series of' in lowered:
        design = 'Serie de casos'
        design_evidence = 'case series'
    elif 'comparative' in lowered or 'compared with' in lowered:
        design = 'Comparativo'
        design_evidence = 'comparative'

    field_trace: dict[str, dict] = {}
    form_values: dict[str, str] = {}
    values: dict[str, object] = {
        'study_id': _metadata_value('study_id', metadata),
        'title': metadata.get('title'),
        'journal': metadata.get('journal'),
        'year': metadata.get('year'),
        'design': design,
        'notes': metadata.get('landing_url') or metadata.get('pdf_url'),
    }

    for label, spec in FIELD_SPECS.items():
        key = spec['key']
        value = None
        evidence = None
        confidence = 0.15
        if spec.get('source') == 'metadata':
            value = _metadata_value(key, metadata)
            evidence = 'metadata'
            confidence = 0.9 if value else 0.15
        elif key == 'design' and design:
            value = design
            evidence = design_evidence
            confidence = 0.7
        else:
            value, evidence = _search(spec.get('patterns', []), normalized_text)
            if value:
                confidence = 0.72

        if value in (None, ''):
            value = 'No reportado'
            confidence = 0.05

        values[key] = values.get(key) if values.get(key) not in (None, '') and value == 'No reportado' else value
        form_values[label] = str(value)
        field_trace[label] = {
            'key': key,
            'value': value,
            'confidence': confidence,
            'evidence': evidence,
        }

    if values.get('design') in (None, '', 'No reportado') and design:
        values['design'] = design

    return {
        **values,
        'first_author': _metadata_value('first_author', metadata) or 'No reportado',
        'country': values.get('country', 'No reportado'),
        'n_total': values.get('n_total', 'No reportado'),
        'age_mean': values.get('age_mean', 'No reportado'),
        'follow_up_months': values.get('follow_up_months', values.get('time_to_union', 'No reportado')),
        'consolidation': values.get('consolidation', 'No reportado'),
        'postop_infection': values.get('postop_infection', 'No reportado'),
        'primary_outcome': values.get('consolidation') if values.get('consolidation') not in (None, 'No reportado') else values.get('postop_infection', 'No reportado'),
        'form_values': form_values,
        'field_trace': field_trace,
    }


def validate_pdf_target(target: str, *, download_dir: Path | None = None) -> dict:
    local = Path(target).expanduser()
    if local.exists() and local.is_file():
        data = local.read_bytes()
        is_pdf = data.startswith(PDF_SIGNATURE)
        return {
            'source': str(local),
            'final_url': None,
            'saved_path': str(local),
            'status': 'validated' if is_pdf else 'not_pdf',
            'mime_valid': is_pdf,
            'fake_pdf': not is_pdf,
            'size_bytes': len(data),
            'page_count_estimate': _rough_page_count(data) if is_pdf else None,
        }

    fetched, error = safe_fetch_bytes(target)
    if error:
        return {
            'source': target,
            'final_url': None,
            'saved_path': None,
            'status': 'fetch_error',
            'mime_valid': False,
            'fake_pdf': True,
            'error': error,
        }

    data, headers, final_url = fetched
    content_type = (headers.get('content-type') or '').lower()
    is_pdf = data.startswith(PDF_SIGNATURE) or 'application/pdf' in content_type
    if not is_pdf and 'html' in content_type:
        html = data.decode(errors='ignore')
        for candidate in find_pdf_links_in_html(html, final_url):
            nested, nested_error = safe_fetch_bytes(candidate)
            if nested_error or not nested:
                continue
            nested_data, nested_headers, nested_final = nested
            nested_type = (nested_headers.get('content-type') or '').lower()
            nested_is_pdf = nested_data.startswith(PDF_SIGNATURE) or 'application/pdf' in nested_type
            if nested_is_pdf:
                data, headers, final_url = nested_data, nested_headers, nested_final
                content_type = nested_type
                is_pdf = True
                break
    saved_path = None
    if is_pdf and download_dir is not None:
        download_dir.mkdir(parents=True, exist_ok=True)
        destination = download_dir / _safe_name(final_url)
        destination.write_bytes(data)
        saved_path = str(destination)

    return {
        'source': target,
        'final_url': final_url,
        'saved_path': saved_path,
        'status': 'validated' if is_pdf else 'not_pdf',
        'mime_valid': is_pdf,
        'fake_pdf': not is_pdf,
        'content_type': content_type,
        'size_bytes': len(data),
        'page_count_estimate': _rough_page_count(data) if is_pdf else None,
    }
