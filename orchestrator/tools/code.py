from __future__ import annotations

from pathlib import Path
import json
import shlex
import subprocess


def _coerce_output(value: object) -> str:
    if value is None:
        return ''
    if isinstance(value, bytes):
        return value.decode(errors='replace').strip()
    return str(value).strip()


def _run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 30) -> dict:
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            'command': shlex.join(cmd),
            'returncode': completed.returncode,
            'stdout': completed.stdout.strip(),
            'stderr': completed.stderr.strip(),
        }
    except Exception as exc:
        return {
            'command': shlex.join(cmd),
            'returncode': -1,
            'stdout': '',
            'stderr': str(exc),
        }


def find_repo_root(start: str | Path) -> Path:
    path = Path(start).expanduser().resolve()
    if path.is_file():
        path = path.parent
    for candidate in [path, *path.parents]:
        if (candidate / '.git').exists():
            return candidate
    return path


def detect_project_manifests(repo_root: Path) -> dict[str, list[str]]:
    manifests: dict[str, list[str]] = {'node': [], 'python': []}
    for rel in ['package.json', 'frontend/package.json']:
        if (repo_root / rel).exists():
            manifests['node'].append(rel)
    for rel in ['requirements.txt', 'backend/requirements.txt', 'pyproject.toml']:
        if (repo_root / rel).exists():
            manifests['python'].append(rel)
    return manifests


def recommend_validation_commands(repo_root: Path) -> list[str]:
    manifests = detect_project_manifests(repo_root)
    commands: list[str] = []
    if manifests['node']:
        for manifest in manifests['node']:
            directory = str(Path(manifest).parent)
            if directory == '.':
                directory = ''
            prefix = f"cd {shlex.quote(str(repo_root / directory))} && " if directory else f"cd {shlex.quote(str(repo_root))} && "
            package_json = repo_root / manifest
            try:
                data = json.loads(package_json.read_text())
            except Exception:
                data = {}
            scripts = data.get('scripts', {})
            for key in ['test', 'lint', 'build']:
                if key in scripts:
                    commands.append(prefix + f'npm run {key}')
    if manifests['python']:
        if (repo_root / 'backend' / 'requirements.txt').exists():
            commands.append(f"cd {shlex.quote(str(repo_root / 'backend'))} && python3 -m compileall app")
        else:
            commands.append(f"cd {shlex.quote(str(repo_root))} && python3 -m compileall .")
    return commands[:6]


def collect_repo_snapshot(repo_root: Path) -> dict:
    manifests = detect_project_manifests(repo_root)
    snapshot = {
        'repo_root': str(repo_root),
        'git_status': _run(['git', 'status', '--short'], cwd=repo_root),
        'git_branch': _run(['git', 'branch', '--show-current'], cwd=repo_root),
        'top_level': sorted(path.name for path in repo_root.iterdir())[:30],
        'manifests': manifests,
        'validation_commands': recommend_validation_commands(repo_root),
    }
    return snapshot


def search_relevant_files(repo_root: Path, query: str, *, max_results: int = 10) -> list[str]:
    tokens = [token.strip() for token in query.replace(',', ' ').split() if len(token.strip()) >= 3]
    if not tokens:
        return []
    pattern = '|'.join(tokens[:8])
    result = _run(['rg', '-l', '-i', pattern, str(repo_root)], cwd=repo_root, timeout=20)
    if result['returncode'] not in (0, 1):
        return []
    rows = [line.strip() for line in result['stdout'].splitlines() if line.strip()]
    return rows[:max_results]


def _resolve_within_scope(repo_root: Path, raw_path: str, write_scope: list[str]) -> Path:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = (repo_root / candidate).resolve()
    else:
        candidate = candidate.resolve()

    if not write_scope:
        raise ValueError('write_scope is required for file edits')

    allowed_roots: list[Path] = []
    for scope in write_scope:
        scope_path = Path(scope)
        if not scope_path.is_absolute():
            scope_path = (repo_root / scope_path).resolve()
        else:
            scope_path = scope_path.resolve()
        allowed_roots.append(scope_path)

    if not any(candidate == root or root in candidate.parents for root in allowed_roots):
        raise ValueError(f'path outside write scope: {candidate}')
    return candidate


def apply_edit_operations(repo_root: Path, operations: list[dict], write_scope: list[str]) -> dict:
    results: list[dict] = []
    for index, operation in enumerate(operations, start=1):
        op = (operation.get('op') or '').strip().lower()
        raw_path = operation.get('path')
        if not op or not raw_path:
            results.append({'index': index, 'status': 'skipped', 'reason': 'missing op/path'})
            continue

        try:
            target = _resolve_within_scope(repo_root, str(raw_path), write_scope)
        except Exception as exc:
            results.append({'index': index, 'op': op, 'path': str(raw_path), 'status': 'blocked', 'reason': str(exc)})
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        before = target.read_text() if target.exists() else ''

        try:
            if op == 'write':
                content = operation.get('content', '')
                target.write_text(str(content))
            elif op == 'append':
                content = operation.get('content', '')
                with target.open('a', encoding='utf-8') as fh:
                    fh.write(str(content))
            elif op == 'replace':
                find = operation.get('find')
                replace = operation.get('replace', '')
                if find is None:
                    raise ValueError('replace op requires find')
                if str(find) not in before:
                    raise ValueError('target text not found')
                target.write_text(before.replace(str(find), str(replace), 1))
            else:
                raise ValueError(f'unsupported op: {op}')

            after = target.read_text()
            results.append(
                {
                    'index': index,
                    'op': op,
                    'path': str(target),
                    'status': 'applied',
                    'changed': before != after,
                }
            )
        except Exception as exc:
            results.append({'index': index, 'op': op, 'path': str(target), 'status': 'failed', 'reason': str(exc)})

    return {
        'repo_root': str(repo_root),
        'write_scope': write_scope,
        'operations_requested': len(operations),
        'results': results,
    }


def run_validation_command(repo_root: Path, command: str) -> dict:
    try:
        completed = subprocess.run(
            command,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=20,
            shell=True,
            check=False,
        )
        return {
            'command': command,
            'returncode': completed.returncode,
            'stdout': completed.stdout.strip(),
            'stderr': completed.stderr.strip(),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            'command': command,
            'returncode': 124,
            'stdout': _coerce_output(exc.stdout),
            'stderr': (_coerce_output(exc.stderr) + ' Command timed out after 20 seconds.').strip(),
        }
