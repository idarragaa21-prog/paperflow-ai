from __future__ import annotations

from typing import Any
from pathlib import Path

from .models import RouteDecision


class TaskRouter:
    KEYWORDS = {
        'voice-agent': ['audio', 'transcribe', 'transcription', 'tts', 'voice', 'speech', 'spoken'],
        'coder-builder': ['repo', 'code', 'bug', 'feature', 'script', 'test', 'automation', 'python', 'node'],
        'document-miner': ['pdf', 'excel', 'csv', 'doi', 'pmid', 'extract', 'table', 'ocr'],
        'ops-runner': ['install', 'shell', 'mac', 'system', 'process', 'folder', 'file', 'launch', 'command'],
        'research-scout': ['paper', 'article', 'review', 'search', 'web', 'evidence', 'study', 'systematic'],
    }

    def route(self, task: dict[str, Any]) -> RouteDecision:
        objective = f"{task.get('title', '')} {task.get('objective', '')}".lower()
        inputs = task.get('inputs', {}) or {}
        classification = task.get('classification', {}) or {}
        domain_hint = (classification.get('domain') or '').lower()
        risk = classification.get('risk', 'medium')
        estimated_inputs = sum(1 for value in inputs.values() if value)
        file_inputs = inputs.get('files') or []
        audio_suffixes = {'.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac', '.mp4', '.mov'}
        has_audio_files = any(Path(item).suffix.lower() in audio_suffixes for item in file_inputs if isinstance(item, str))

        if domain_hint in {'voice', 'audio'} or has_audio_files:
            return RouteDecision(
                domain='voice',
                assigned_agent='voice-agent',
                direct=False,
                reason='explicit voice/audio inputs detected',
                plan=[{'step_id': 's1', 'title': 'Process voice task', 'agent': 'voice-agent', 'status': 'queued'}],
            )

        if domain_hint in {'ops', 'system'} or any(inputs.get(key) for key in ['command', 'cmd', 'shell']):
            return RouteDecision(
                domain='ops',
                assigned_agent='ops-runner',
                direct=False,
                reason='explicit operational command detected',
                plan=[{'step_id': 's1', 'title': 'Run safe operational command', 'agent': 'ops-runner', 'status': 'queued'}],
            )

        if domain_hint == 'coding' or inputs.get('repo_path'):
            plan = [
                {'step_id': 's1', 'title': 'Inspect repo and scope the change', 'agent': 'coder-builder', 'status': 'queued'},
                {'step_id': 's2', 'title': 'Produce patch plan and validation notes', 'agent': 'coder-builder', 'status': 'queued'},
            ]
            return RouteDecision(domain='coding', assigned_agent='coder-builder', direct=False, reason='repo-aware coding workflow', plan=plan)

        if inputs.get('articles') or inputs.get('excel_template'):
            plan = [
                {'step_id': 's1', 'title': 'Resolve article inputs into candidate sources', 'agent': 'research-scout', 'status': 'queued'},
                {'step_id': 's2', 'title': 'Download PDFs, extract fields, and fill workbook', 'agent': 'document-miner', 'status': 'queued'},
                {'step_id': 's3', 'title': 'Assemble screening and evidence outputs', 'agent': 'research-scout', 'status': 'queued'},
            ]
            return RouteDecision(
                domain='systematic_review',
                assigned_agent='research-scout',
                direct=False,
                reason='article batch plus workbook workflow',
                plan=plan,
            )

        if risk == 'low' and estimated_inputs <= 1 and not task.get('constraints', {}).get('structured_output', False):
            return RouteDecision(domain='direct', assigned_agent=None, direct=True, reason='low-risk one-step task', plan=[])

        if 'systematic' in objective or 'review' in objective:
            plan = [
                {'step_id': 's1', 'title': 'Search candidate sources', 'agent': 'research-scout', 'status': 'queued'},
                {'step_id': 's2', 'title': 'Validate/download PDFs and tabular inputs', 'agent': 'document-miner', 'status': 'queued'},
                {'step_id': 's3', 'title': 'Assemble screening and evidence outputs', 'agent': 'research-scout', 'status': 'queued'},
            ]
            return RouteDecision(domain='systematic_review', assigned_agent='research-scout', direct=False, reason='multi-step literature workflow', plan=plan)

        if any(token in objective for token in ['code', 'repo', 'feature', 'bug', 'test']):
            plan = [
                {'step_id': 's1', 'title': 'Inspect repo and scope the change', 'agent': 'coder-builder', 'status': 'queued'},
                {'step_id': 's2', 'title': 'Produce patch plan and validation notes', 'agent': 'coder-builder', 'status': 'queued'},
            ]
            return RouteDecision(domain='coding', assigned_agent='coder-builder', direct=False, reason='repo-aware coding workflow', plan=plan)

        for agent_id, keywords in self.KEYWORDS.items():
            if any(keyword in objective for keyword in keywords):
                return RouteDecision(
                    domain=agent_id.replace('-', '_'),
                    assigned_agent=agent_id,
                    direct=False,
                    reason=f'keyword match for {agent_id}',
                    plan=[{'step_id': 's1', 'title': 'Handle task', 'agent': agent_id, 'status': 'queued'}],
                )

        return RouteDecision(
            domain='general_research',
            assigned_agent='research-scout',
            direct=False,
            reason='default to research-scout',
            plan=[{'step_id': 's1', 'title': 'Handle task', 'agent': 'research-scout', 'status': 'queued'}],
        )
