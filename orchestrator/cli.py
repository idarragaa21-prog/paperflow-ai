from __future__ import annotations

import argparse
from pathlib import Path
import json
import uuid

from .director import Director
from .task_store import TaskStore
from .utils import now_iso, read_json, slugify, write_json


def build_task(
    *,
    title: str,
    objective: str,
    priority: str = 'medium',
    mode: str | None = None,
    repo_path: str | None = None,
    command: str | None = None,
    text: str | None = None,
    files: list[str] | None = None,
    query: str | None = None,
    max_sources: int | None = None,
    write_scope: list[str] | None = None,
    edit_operations: list[dict] | None = None,
    validation_mode: str = 'normal',
    articles: list[str] | None = None,
    excel_template: str | None = None,
    continue_until_done: bool = False,
    max_step_retries: int = 1,
    urls: list[str] | None = None,
) -> dict:
    task_id = f"task_{slugify(title)}_{now_iso().replace(':', '').replace('-', '')}_{uuid.uuid4().hex[:6]}"
    domain = mode or 'unclassified'
    inputs: dict = {'query': query or objective, 'files': files or []}
    if repo_path:
        inputs['repo_path'] = repo_path
    if command:
        inputs['command'] = command
    if text:
        inputs['text'] = text
    if write_scope:
        inputs['write_scope'] = write_scope
    if edit_operations:
        inputs['edit_operations'] = edit_operations
    if articles:
        inputs['articles'] = articles
    if excel_template:
        inputs['excel_template'] = excel_template
    if urls:
        inputs['urls'] = urls

    constraints = {
        'structured_output': True,
        'allow_parallel_subtasks': True,
        'validation_mode': validation_mode,
        'continue_until_done': continue_until_done,
        'max_step_retries': max_step_retries,
    }
    if max_sources is not None:
        constraints['max_sources'] = max_sources
        constraints['must_save_pdfs'] = True

    return {
        'task_id': task_id,
        'parent_task_id': None,
        'title': title,
        'objective': objective,
        'status': 'queued',
        'priority': priority,
        'created_at': now_iso(),
        'updated_at': now_iso(),
        'requested_by': 'user',
        'orchestrator': {'director': 'openclaw', 'router_version': 'v1', 'tool_profile': 'default'},
        'classification': {'domain': domain, 'risk': 'medium', 'execution_mode': 'hybrid', 'direct_resolve_allowed': False},
        'assigned_agent': None,
        'inputs': inputs,
        'constraints': constraints,
        'plan': [],
        'artifacts': [],
        'subtasks': [],
        'fallbacks_used': [],
        'result': None,
        'error': None,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='OpenClaw Orchestrator v1 runtime')
    parser.add_argument('--runtime-root', default='.orchestrator-runtime', help='Runtime directory for task state')
    sub = parser.add_subparsers(dest='action', required=True)

    new_cmd = sub.add_parser('new', help='Create a new task file')
    new_cmd.add_argument('--title', required=True)
    new_cmd.add_argument('--objective', required=True)
    new_cmd.add_argument('--priority', default='medium')
    new_cmd.add_argument('--output', default=None)

    run_cmd = sub.add_parser('run', help='Run a task file')
    run_cmd.add_argument('--task', required=True)

    launch_cmd = sub.add_parser('launch', help='Create and run a task directly')
    launch_cmd.add_argument('--mode', choices=['research', 'review', 'coding', 'ops', 'voice'], required=True)
    launch_cmd.add_argument('--objective', required=True)
    launch_cmd.add_argument('--title', default=None)
    launch_cmd.add_argument('--priority', default='medium')
    launch_cmd.add_argument('--repo-path', default=None)
    launch_cmd.add_argument('--command', dest='shell_command', default=None)
    launch_cmd.add_argument('--text', default=None)
    launch_cmd.add_argument('--file', action='append', default=[])
    launch_cmd.add_argument('--query', default=None)
    launch_cmd.add_argument('--max-sources', type=int, default=None)
    launch_cmd.add_argument('--write-scope', action='append', default=[])
    launch_cmd.add_argument('--edit-ops-file', default=None)
    launch_cmd.add_argument('--fast', action='store_true')
    launch_cmd.add_argument('--article', action='append', default=[])
    launch_cmd.add_argument('--excel-template', default=None)
    launch_cmd.add_argument('--autonomous', action='store_true')
    launch_cmd.add_argument('--max-step-retries', type=int, default=1)
    launch_cmd.add_argument('--url', action='append', default=[])

    status_cmd = sub.add_parser('status', help='Show stored task status')
    status_cmd.add_argument('--task', required=True)

    return parser


def command_new(args: argparse.Namespace) -> int:
    task = build_task(title=args.title, objective=args.objective, priority=args.priority)
    output = Path(args.output) if args.output else Path('examples') / f"{task['task_id']}.json"
    write_json(output, task)
    print(output)
    return 0


def _extract_key_preview(runtime_dir: Path, assigned_agent: str | None) -> tuple[str | None, str | None]:
    candidate_paths: list[Path] = []
    if assigned_agent == 'research-scout':
        candidate_paths.extend([
            *sorted(runtime_dir.glob('outputs/filled_*.xlsx')),
            runtime_dir / 'outputs' / 'review_summary.md',
            runtime_dir / 'outputs' / 'research_summary.md',
            runtime_dir / 'outputs' / 'evidence_table.csv',
        ])
    elif assigned_agent == 'coder-builder':
        candidate_paths.extend([
            runtime_dir / 'outputs' / 'edit_report.json',
            runtime_dir / 'outputs' / 'patch_outline.md',
            runtime_dir / 'outputs' / 'test_report.json',
        ])
    elif assigned_agent == 'ops-runner':
        candidate_paths.append(runtime_dir / 'outputs' / 'ops_log.txt')
    elif assigned_agent == 'voice-agent':
        candidate_paths.extend([
            runtime_dir / 'outputs' / 'transcript.txt',
            runtime_dir / 'artifacts' / 'tts_result.json',
        ])
    elif assigned_agent == 'document-miner':
        candidate_paths.append(runtime_dir / 'outputs' / 'document_mining.md')

    candidate_paths.extend(sorted((runtime_dir / 'outputs').glob('*')))

    for path in candidate_paths:
        if not path.exists() or path.is_dir():
            continue
        if path.suffix.lower() in {'.aiff', '.wav', '.mp3', '.m4a', '.pdf', '.xlsx'}:
            return str(path), f"Binary artifact ready: {path.name}"
        text = path.read_text(errors='ignore').strip()
        if not text:
            continue
        if path.suffix.lower() == '.json':
            try:
                payload = json.loads(text)
                if path.name == 'edit_report.json' and isinstance(payload, dict):
                    results = payload.get('results', [])
                    applied = sum(1 for row in results if row.get('status') == 'applied')
                    blocked = sum(1 for row in results if row.get('status') in {'blocked', 'failed'})
                    preview = f"Edit report: {applied}/{len(results)} operations applied, {blocked} blocked or failed."
                elif path.name == 'test_report.json' and isinstance(payload, dict):
                    results = payload.get('results', [])
                    checks = len(payload.get('planned_checks', []))
                    failures = sum(1 for row in results if row.get('returncode', 0) not in (0, None))
                    preview = f"Validation report: {len(results)}/{checks} checks executed, {failures} non-zero results."
                else:
                    preview = json.dumps(payload, ensure_ascii=True)[:320]
            except Exception:
                preview = text[:320]
        else:
            preview = ' '.join(line.strip() for line in text.splitlines()[:6] if line.strip())[:320]
        return str(path), preview
    return None, None


def _print_result(runtime_root: Path, result: dict) -> None:
    runtime_dir = runtime_root / 'tasks' / result['task_id']
    preview_path, preview = _extract_key_preview(runtime_dir, result.get('assigned_agent'))
    print(f"task_id={result['task_id']}")
    print(f"status={result['status']}")
    print(f"assigned_agent={result.get('assigned_agent')}")
    print(f"artifacts={len(result.get('artifacts', []))}")
    print(f"runtime={runtime_dir}")
    if preview:
        print(f"summary={preview}")
    if preview_path:
        print(f"summary_path={preview_path}")


def command_run(args: argparse.Namespace) -> int:
    runtime_root = Path(args.runtime_root)
    director = Director(runtime_root)
    task = read_json(Path(args.task))
    result = director.run(task)
    _print_result(runtime_root, result)
    return 0


def command_launch(args: argparse.Namespace) -> int:
    runtime_root = Path(args.runtime_root)
    director = Director(runtime_root)
    mode_to_title = {
        'research': 'General research task',
        'review': 'Systematic review task',
        'coding': 'Coding task',
        'ops': 'Operational task',
        'voice': 'Voice task',
    }
    mode_domain = {'review': 'systematic_review'}.get(args.mode, args.mode)
    objective = args.objective
    text = args.text
    command = args.shell_command
    query = args.query
    max_sources = args.max_sources
    write_scope = args.write_scope or []
    articles = args.article or []
    excel_template = args.excel_template
    urls = args.url or []
    edit_operations: list[dict] | None = None
    if args.edit_ops_file:
        edit_operations = read_json(Path(args.edit_ops_file))

    if args.mode == 'voice' and not text and not args.file:
        text = objective
    if args.mode == 'ops' and not command and objective.strip().startswith('!'):
        command = objective.strip()[1:].strip()
    if args.mode in {'research', 'review'} and not query:
        query = objective
    if args.mode == 'review' and max_sources is None:
        max_sources = 5

    task = build_task(
        title=args.title or mode_to_title[args.mode],
        objective=objective,
        priority=args.priority,
        mode=mode_domain,
        repo_path=args.repo_path,
        command=command,
        text=text,
        files=args.file,
        query=query,
        max_sources=max_sources,
        write_scope=write_scope,
        edit_operations=edit_operations,
        validation_mode='fast' if args.fast else 'normal',
        articles=articles,
        excel_template=excel_template,
        continue_until_done=args.autonomous,
        max_step_retries=max(0, int(args.max_step_retries or 0)),
        urls=urls,
    )
    result = director.run(task)
    _print_result(runtime_root, result)
    return 0


def command_status(args: argparse.Namespace) -> int:
    store = TaskStore(Path(args.runtime_root))
    task = store.load_task(args.task)
    print(f"task_id={task['task_id']}")
    print(f"status={task['status']}")
    print(f"assigned_agent={task.get('assigned_agent')}")
    print(f"plan_steps={len(task.get('plan', []))}")
    print(f"artifacts={len(task.get('artifacts', []))}")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.action == 'new':
        return command_new(args)
    if args.action == 'run':
        return command_run(args)
    if args.action == 'launch':
        return command_launch(args)
    if args.action == 'status':
        return command_status(args)
    parser.error('unknown command')
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
