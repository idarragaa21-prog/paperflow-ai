from __future__ import annotations

from pathlib import Path
import json

from orchestrator.agents.base import AgentContext, BaseAgent
from orchestrator.models import AgentResult
from orchestrator.tools import (
    apply_edit_operations,
    collect_repo_snapshot,
    find_repo_root,
    run_validation_command,
    search_relevant_files,
)


class CoderBuilderAgent(BaseAgent):
    agent_id = 'coder-builder'

    def run(self, ctx: AgentContext) -> AgentResult:
        repo_hint = (ctx.task.get('inputs') or {}).get('repo_path') or '.'
        repo_root = find_repo_root(repo_hint)
        snapshot = collect_repo_snapshot(repo_root)
        objective = ctx.task.get('objective', '')
        inputs = ctx.task.get('inputs') or {}
        constraints = ctx.task.get('constraints') or {}
        relevant_files = search_relevant_files(repo_root, objective, max_results=12)
        write_scope = [str(item) for item in (inputs.get('write_scope') or []) if item]
        edit_operations = inputs.get('edit_operations') or []
        validation_mode = constraints.get('validation_mode', 'normal')

        patch_plan = {
            'objective': objective,
            'repo_root': str(repo_root),
            'relevant_files': relevant_files,
            'write_scope': write_scope,
            'edit_operations_count': len(edit_operations),
            'minimal_change_set': [
                'inspect relevant files and choose the smallest edit surface',
                'implement the requested behavior behind existing boundaries when possible',
                'verify the change with the narrowest useful command set',
            ],
            'validation_candidates': snapshot.get('validation_commands', []),
        }

        validation_results: list[dict] = []
        edit_report: dict | None = None
        should_run_validation = ctx.step.get('step_id') == 's2'
        should_apply_edits = ctx.step.get('step_id') == 's2' and bool(edit_operations)
        if should_apply_edits:
            edit_report = apply_edit_operations(repo_root, edit_operations, write_scope)
        if should_run_validation:
            if validation_mode == 'fast':
                validation_results.append(
                    {
                        'command': 'validation skipped',
                        'returncode': 0,
                        'stdout': '',
                        'stderr': '',
                        'note': 'Fast mode enabled; validation commands were not executed.',
                    }
                )
            else:
                for command in snapshot.get('validation_commands', [])[:2]:
                    validation_results.append(run_validation_command(repo_root, command))

        outline_lines = [
            '# Patch outline',
            '',
            f"Repo root: {repo_root}",
            '',
            'Relevant files:',
        ]
        outline_lines.extend(f'- {path}' for path in relevant_files[:10])
        if not relevant_files:
            outline_lines.append('- No obvious file matches yet; inspect repo structure manually.')
        outline_lines.extend(['', 'Suggested minimal change set:'])
        outline_lines.extend(f"- {item}" for item in patch_plan['minimal_change_set'])
        patch_doc = '\n'.join(outline_lines) + '\n'

        warnings: list[str] = []
        if not snapshot['validation_commands']:
            warnings.append('No validation commands were auto-detected for this repo.')
        if should_run_validation and not validation_results:
            warnings.append('Validation step requested, but no runnable validation commands were found.')
        if should_apply_edits and edit_report and not any(row.get('status') == 'applied' for row in edit_report['results']):
            warnings.append('Edit operations were requested, but no changes were successfully applied.')
        if validation_mode == 'fast':
            warnings.append('Fast validation mode: runnable checks were skipped to keep launch latency low.')

        artifacts = [
            {'path': 'artifacts/repo_snapshot.json', 'payload': snapshot},
            {'path': 'artifacts/patch_plan.json', 'payload': patch_plan},
            {'path': 'outputs/patch_outline.md', 'payload': patch_doc},
            {'path': 'outputs/test_report.json', 'payload': {'results': validation_results, 'planned_checks': snapshot.get('validation_commands', [])}},
        ]
        if edit_report is not None:
            artifacts.append({'path': 'outputs/edit_report.json', 'payload': edit_report})

        return AgentResult(
            agent_id=self.agent_id,
            summary='Coder builder inspected the repo, mapped likely edit points, and prepared real validation commands.',
            artifacts=artifacts,
            warnings=warnings,
            next_action='Apply the change set or hand this plan to an editing execution loop.',
        )
