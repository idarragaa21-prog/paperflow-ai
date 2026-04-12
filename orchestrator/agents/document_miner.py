from __future__ import annotations

from pathlib import Path
import json

from orchestrator.agents.base import AgentContext, BaseAgent
from orchestrator.models import AgentResult
from orchestrator.tools import extract_pdf_text, fill_extraction_workbook, infer_study_fields, validate_pdf_target


class DocumentMinerAgent(BaseAgent):
    agent_id = 'document-miner'

    def _load_candidates(self, ctx: AgentContext) -> list[dict]:
        task_inputs = ctx.task.get('inputs', {}) or {}
        source_list = ctx.runtime_dir / 'artifacts' / 'source_list.json'
        candidates: list[dict] = []
        seen: set[str] = set()
        if source_list.exists():
            for item in json.loads(source_list.read_text()).get('candidates', []):
                key = str(item.get('pdf_url') or item.get('landing_url') or item.get('doi') or item.get('title'))
                if key and key not in seen:
                    candidates.append(item)
                    seen.add(key)

        direct_items: list[str] = []
        direct_items.extend(str(item) for item in task_inputs.get('articles') or [])
        for file_path in task_inputs.get('files') or []:
            path = Path(file_path).expanduser()
            if path.suffix.lower() == '.pdf':
                direct_items.append(str(path))

        for raw in direct_items:
            key = raw.strip()
            if not key or key in seen:
                continue
            path = Path(raw).expanduser()
            title = path.stem if path.exists() else raw
            candidates.append(
                {
                    'study_id': f"direct_{len(candidates) + 1}",
                    'title': title,
                    'doi': None,
                    'year': None,
                    'authors': [],
                    'pdf_url': str(path) if path.exists() else raw,
                    'landing_url': None if path.exists() else raw,
                }
            )
            seen.add(key)

        return candidates

    def _excel_template_path(self, ctx: AgentContext) -> Path | None:
        task_inputs = ctx.task.get('inputs', {}) or {}
        template = task_inputs.get('excel_template')
        if template:
            path = Path(template).expanduser()
            if path.exists():
                return path
        for file_path in task_inputs.get('files') or []:
            path = Path(file_path).expanduser()
            if path.suffix.lower() == '.xlsx' and path.exists():
                return path
        return None

    def run(self, ctx: AgentContext) -> AgentResult:
        task_inputs = ctx.task.get('inputs', {}) or {}
        query = task_inputs.get('query', '')
        download_dir = ctx.runtime_dir / 'inputs' / 'downloads'
        validated_assets = {'query': query, 'assets': []}
        extractions: list[dict] = []
        field_traces: list[dict] = []
        warnings: list[str] = []
        fallbacks: list[str] = []
        study_rows: list[dict] = []

        candidates = self._load_candidates(ctx)
        if not candidates:
            warnings.append('No source_list.json was present; document-miner validated only direct task inputs.')

        for candidate in candidates[:20]:
            target = candidate.get('pdf_url') or candidate.get('landing_url')
            if target:
                validation = validate_pdf_target(str(target), download_dir=download_dir)
            else:
                validation = {
                    'source': None,
                    'final_url': None,
                    'saved_path': None,
                    'status': 'missing_source',
                    'mime_valid': False,
                    'fake_pdf': True,
                }

            if validation.get('status') != 'validated':
                fallbacks.append('landing_page_or_abstract')

            extracted_text = None
            inferred_fields = infer_study_fields('', metadata=candidate)
            if validation.get('saved_path'):
                try:
                    extracted_text = extract_pdf_text(validation['saved_path'])
                    inferred_fields = infer_study_fields(extracted_text.get('text', ''), metadata=candidate)
                except Exception as exc:
                    warnings.append(f"pdf_extract_error:{candidate.get('study_id') or candidate.get('title')}: {exc}")

            asset = {
                'study_id': candidate.get('study_id'),
                'title': candidate.get('title'),
                'doi': candidate.get('doi'),
                **validation,
            }
            validated_assets['assets'].append(asset)

            extraction_row = {
                'study_id': candidate.get('study_id'),
                'pdf_status': validation.get('status'),
                'ocr_used': False,
                'extraction_confidence': 0.82 if validation.get('status') == 'validated' else 0.35,
                'fields': {
                    **inferred_fields,
                    'notes': inferred_fields.get('notes') or (
                        f"Validated via {'pdf' if validation.get('mime_valid') else 'fallback'} path."
                    ),
                },
            }
            if extracted_text:
                extraction_row['text_preview'] = extracted_text.get('text_preview')
                extraction_row['page_count'] = extracted_text.get('page_count')
            extractions.append(extraction_row)
            study_rows.append(extraction_row['fields'])
            field_traces.append(
                {
                    'study_id': candidate.get('study_id'),
                    'title': candidate.get('title'),
                    'field_trace': extraction_row['fields'].get('field_trace', {}),
                }
            )

        if not validated_assets['assets']:
            validated_assets['assets'].append(
                {
                    'study_id': 'no-assets',
                    'status': 'needs_live_fetch',
                    'mime_valid': False,
                    'fake_pdf': True,
                }
            )
            extractions.append(
                {
                    'study_id': 'no-assets',
                    'pdf_status': 'needs_live_fetch',
                    'ocr_used': False,
                    'extraction_confidence': 0.1,
                    'fields': {'notes': 'No candidate URLs available yet.'},
                }
            )

        artifacts = [
            {'path': 'artifacts/validated_assets.json', 'payload': validated_assets},
            {'path': 'artifacts/extractions.json', 'payload': {'items': extractions}},
            {'path': 'artifacts/field_trace.json', 'payload': {'items': field_traces}},
        ]

        excel_template = self._excel_template_path(ctx)
        workbook_report = None
        if excel_template and study_rows:
            output_path = ctx.runtime_dir / 'outputs' / f"filled_{excel_template.name}"
            workbook_report = fill_extraction_workbook(excel_template, study_rows, output_path)
            artifacts.append({'path': 'artifacts/workbook_fill_report.json', 'payload': workbook_report})

        report_lines = ['# Document mining', '', f"Candidates checked: {len(validated_assets['assets'])}"]
        report_lines.append(f"Validated PDFs: {sum(1 for item in validated_assets['assets'] if item.get('status') == 'validated')}")
        if workbook_report:
            report_lines.append(f"Workbook filled: {workbook_report['output_path']}")
            report_lines.append(f"Studies written: {workbook_report['studies_written']}")
        report = '\n'.join(report_lines) + '\n'
        artifacts.append({'path': 'outputs/document_mining.md', 'payload': report})

        return AgentResult(
            agent_id=self.agent_id,
            summary='Document miner downloaded/validated articles, extracted study fields, and filled the workbook when a template was provided.',
            artifacts=artifacts,
            warnings=warnings,
            fallbacks_used=sorted(set(fallbacks)),
            next_action='Route structured outputs back to research-scout or review the filled workbook.',
        )
