from __future__ import annotations

from pathlib import Path
import csv
import io
import json
import re

from orchestrator.agents.base import AgentContext, BaseAgent
from orchestrator.models import AgentResult
from orchestrator.tools import browser_navigate, lookup_crossref_doi, looks_like_url, search_crossref


class ResearchScoutAgent(BaseAgent):
    agent_id = 'research-scout'

    def _looks_like_doi(self, value: str) -> bool:
        return bool(re.match(r'^(?:https?://doi\.org/)?10\.\d{4,9}/\S+$', value.strip(), flags=re.IGNORECASE))

    def _build_candidates_from_articles(self, articles: list[str]) -> tuple[list[dict], list[str]]:
        candidates: list[dict] = []
        warnings: list[str] = []
        for index, article in enumerate(articles, start=1):
            raw = article.strip()
            if not raw:
                continue
            local_path = Path(raw).expanduser()
            if local_path.exists() and local_path.is_file():
                candidates.append(
                    {
                        'rank': index,
                        'study_id': f'file-{index}',
                        'title': local_path.stem,
                        'doi': None,
                        'pmid': None,
                        'year': None,
                        'authors': [],
                        'journal': None,
                        'type': 'local_file',
                        'oa_status': 'local',
                        'landing_url': str(local_path),
                        'pdf_url': str(local_path) if local_path.suffix.lower() == '.pdf' else None,
                        'confidence': 0.9,
                    }
                )
                continue
            if self._looks_like_doi(raw):
                candidate, item_warnings = lookup_crossref_doi(raw)
                warnings.extend(item_warnings)
                if candidate:
                    candidate['rank'] = index
                    candidates.append(candidate)
                    continue
            if raw.lower().startswith(('http://', 'https://')):
                candidates.append(
                    {
                        'rank': index,
                        'study_id': f'url-{index}',
                        'title': raw,
                        'doi': None,
                        'pmid': None,
                        'year': None,
                        'authors': [],
                        'journal': None,
                        'type': None,
                        'oa_status': 'unknown',
                        'landing_url': raw,
                        'pdf_url': raw if raw.lower().endswith('.pdf') else None,
                        'confidence': 0.75,
                    }
                )
                continue
            search_results, item_warnings = search_crossref(raw, rows=1)
            warnings.extend(item_warnings)
            if search_results:
                search_results[0]['rank'] = index
                candidates.append(search_results[0])
            else:
                candidates.append(
                    {
                        'rank': index,
                        'study_id': f'text-{index}',
                        'title': raw,
                        'doi': None,
                        'pmid': None,
                        'year': None,
                        'authors': [],
                        'journal': None,
                        'type': None,
                        'oa_status': 'unknown',
                        'landing_url': None,
                        'pdf_url': None,
                        'confidence': 0.2,
                    }
                )
        return candidates, warnings

    def _source_list_path(self, ctx: AgentContext) -> Path:
        return ctx.runtime_dir / 'artifacts' / 'source_list.json'

    def _extractions_path(self, ctx: AgentContext) -> Path:
        return ctx.runtime_dir / 'artifacts' / 'extractions.json'

    def _assemble_review_outputs(self, ctx: AgentContext) -> AgentResult:
        source_list = json.loads(self._source_list_path(ctx).read_text()) if self._source_list_path(ctx).exists() else {'candidates': []}
        extractions = json.loads(self._extractions_path(ctx).read_text()) if self._extractions_path(ctx).exists() else {'items': []}
        extraction_by_id = {item.get('study_id'): item for item in extractions.get('items', [])}

        rows: list[dict[str, object]] = []
        for candidate in source_list.get('candidates', []):
            study_id = candidate.get('study_id') or candidate.get('doi') or candidate.get('title')
            extracted = extraction_by_id.get(study_id) or next(iter(extraction_by_id.values()), {})
            fields = extracted.get('fields', {}) if extracted else {}
            rows.append(
                {
                    'study_id': study_id,
                    'title': candidate.get('title'),
                    'doi': candidate.get('doi'),
                    'year': candidate.get('year'),
                    'pdf_status': extracted.get('pdf_status'),
                    'design': fields.get('design'),
                    'n_total': fields.get('n_total'),
                    'primary_outcome': fields.get('primary_outcome'),
                    'notes': fields.get('notes'),
                }
            )

        csv_buffer = io.StringIO()
        fieldnames = ['study_id', 'title', 'doi', 'year', 'pdf_status', 'design', 'n_total', 'primary_outcome', 'notes']
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        summary = (
            '# Review summary\n\n'
            f"Studies screened: {len(source_list.get('candidates', []))}\n\n"
            f"Structured rows assembled: {len(rows)}\n"
        )
        return AgentResult(
            agent_id=self.agent_id,
            summary='Research scout assembled screening outputs from discovered sources and document extractions.',
            artifacts=[
                {'path': 'artifacts/screening_table.json', 'payload': {'rows': rows}},
                {'path': 'outputs/evidence_table.csv', 'payload': csv_buffer.getvalue()},
                {'path': 'outputs/review_summary.md', 'payload': summary},
            ],
            next_action='Review the evidence table and enrich extraction schemas if needed.',
        )

    def run(self, ctx: AgentContext) -> AgentResult:
        if ctx.step.get('step_id') == 's3' and self._source_list_path(ctx).exists():
            return self._assemble_review_outputs(ctx)

        task_inputs = ctx.task.get('inputs', {}) or {}
        query = task_inputs.get('query', ctx.task.get('objective', ''))
        direct_articles = task_inputs.get('articles') or []
        urls = task_inputs.get('urls') or []
        max_sources = int(ctx.task.get('constraints', {}).get('max_sources', 5) or 5)
        if urls:
            navigations = [browser_navigate(url) for url in urls[:3]]
            summary_lines = ['# Web navigation summary', '']
            for nav in navigations:
                summary_lines.append(f"- {nav.get('title') or nav.get('final_url')}")
                summary_lines.append(f"  URL: {nav.get('final_url')}")
                snippet = (nav.get('text') or '').replace('\n', ' ')[:300]
                if snippet:
                    summary_lines.append(f"  Snippet: {snippet}")
            return AgentResult(
                agent_id=self.agent_id,
                summary='Research scout navigated the requested web pages and captured structured summaries.',
                artifacts=[
                    {'path': 'artifacts/web_navigation.json', 'payload': {'items': navigations}},
                    {'path': 'outputs/web_navigation.md', 'payload': '\n'.join(summary_lines) + '\n'},
                ],
                next_action='Use the captured page summaries to continue browsing or extract follow-up links.',
            )

        if looks_like_url(query):
            navigation = browser_navigate(query)
            summary_lines = [
                '# Web navigation summary',
                '',
                f"Title: {navigation.get('title') or 'Untitled'}",
                f"URL: {navigation.get('final_url')}",
                '',
                (navigation.get('text') or '')[:1200],
            ]
            return AgentResult(
                agent_id=self.agent_id,
                summary='Research scout navigated the requested URL and captured the readable content.',
                artifacts=[
                    {'path': 'artifacts/web_navigation.json', 'payload': {'items': [navigation]}},
                    {'path': 'outputs/web_navigation.md', 'payload': '\n'.join(summary_lines) + '\n'},
                ],
                next_action='Follow discovered links or summarize the page content.',
            )
        if direct_articles:
            candidates, warnings = self._build_candidates_from_articles(direct_articles)
        else:
            candidates, warnings = search_crossref(query, rows=min(max_sources, 5))
        if not candidates:
            candidates = [
                {
                    'rank': 1,
                    'study_id': 'fallback-query-only',
                    'title': 'No live source returned; keep query for manual follow-up',
                    'query': query,
                    'doi': None,
                    'pmid': None,
                    'year': None,
                    'authors': [],
                    'journal': None,
                    'type': None,
                    'oa_status': 'unknown',
                    'landing_url': None,
                    'pdf_url': None,
                    'confidence': 0.2,
                }
            ]
        else:
            for candidate in candidates:
                candidate['study_id'] = candidate.get('study_id') or candidate.get('doi') or f"rank-{candidate['rank']}"

        summary = (
            '# Research summary\n\n'
            f'Query: {query}\n\n'
            f'Candidates: {len(candidates)}\n'
        )
        return AgentResult(
            agent_id=self.agent_id,
            summary='Research candidates collected from Crossref and queued for document validation.',
            artifacts=[
                {'path': 'artifacts/source_list.json', 'payload': {'query': query, 'candidates': candidates}},
                {'path': 'outputs/research_summary.md', 'payload': summary},
            ],
            warnings=warnings,
            next_action='Pass source list to document-miner when full text is required.',
        )
