from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


PREFIXES = ['orquesta ai', 'orquesta', 'codigo', 'coding', 'research', 'review', 'ops', 'voice', 'sistema']
INBOUND_DIR = Path('/Users/diegoalejandroidarragalopez/.openclaw/media/inbound')
OFFICE_SUFFIXES = {
    'excel': ('.xlsx',),
    'pdf': ('.pdf',),
    'powerpoint': ('.pptx',),
    'word': ('.docx',),
}


def detect_mode(text: str) -> str:
    lower = text.lower()
    if any(token in lower for token in ['voice', 'voz', 'audio', 'transcribe', 'tts', 'speech']):
        return 'voice'
    office_terms = ['excel', 'xlsx', 'pdf', 'powerpoint', 'ppt', 'pptx', 'presentacion', 'presentación', 'slides', 'word', 'docx', 'documento']
    office_action_terms = ['abre', 'open', 'crea', 'crear', 'genera', 'haz', 'exporta', 'convierte']
    office_analysis_terms = ['llena', 'llename', 'lléname', 'rellena', 'completa', 'extrae', 'extraer', 'resume', 'resumeme', 'resúmeme', 'analiza', 'interpreta', 'lee', 'leer', 'valida']
    if any(token in lower for token in office_terms) and any(token in lower for token in office_action_terms):
        return 'ops'
    if any(token in lower for token in office_terms) and any(token in lower for token in office_analysis_terms):
        return 'review'
    if any(token in lower for token in ['repo', 'code', 'codigo', ' bug', ' feature', ' automation', 'npm ', 'node ', 'python ', 'python3 ', 'git ']):
        return 'coding'
    if any(token in lower for token in ['review', 'systematic', 'paper', 'article', 'articulo', 'artículos', 'articulos', 'evidence', 'pdf', 'doi', 'pmid', 'excel', 'xlsx']):
        return 'review'
    if any(token in lower for token in ['shell', 'instala', 'install', 'abre', 'open', 'sistema', 'command', 'powerpoint', 'word', 'telegram', 'whatsapp', 'finder', 'preview', 'keynote', 'numbers', '!']):
        return 'ops'
    return 'research'


def strip_prefix(text: str) -> str:
    result = text.strip()
    lower = result.lower()
    for prefix in PREFIXES:
        token = f'{prefix} '
        if lower.startswith(token):
            return result[len(token):].strip()
    return result


def resolve_repo(value: str, default_repo: Path) -> Path:
    aliases = {
        'default': default_repo,
        'orchestrator': default_repo,
        'new project': default_repo,
        'new-project': default_repo,
        'paperflow': Path('/Users/diegoalejandroidarragalopez/paperflow-ai'),
        'paperflow-ai': Path('/Users/diegoalejandroidarragalopez/paperflow-ai'),
    }
    lowered = value.strip().lower()
    if lowered in aliases and aliases[lowered].exists():
        return aliases[lowered].resolve()
    return Path(value).expanduser().resolve()


def _recent_inbound_files(*, suffixes: tuple[str, ...], limit: int = 5) -> list[Path]:
    if not INBOUND_DIR.exists():
        return []
    items = [path for path in INBOUND_DIR.iterdir() if path.is_file() and path.suffix.lower() in suffixes]
    items.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return items[:limit]


def _infer_recent_document_refs(text: str) -> dict[str, str]:
    lowered = text.lower()
    refs: dict[str, str] = {}
    wants_recent = any(
        token in lowered
        for token in ['este ', 'esta ', 'estos ', 'estas ', 'último', 'ultimo', 'última', 'ultima', 'reciente', 'adjunto', 'adjunta']
    )
    if not wants_recent:
        return refs

    keyword_map = {
        'excel': ['excel', 'xlsx', 'formulario', 'plantilla', 'hoja de calculo', 'hoja de cálculo'],
        'pdf': ['pdf', 'articulo', 'artículos', 'articulos', 'paper', 'papers'],
        'powerpoint': ['powerpoint', 'ppt', 'pptx', 'presentacion', 'presentación', 'slides', 'diapositivas'],
        'word': ['word', 'docx', 'documento'],
    }
    for kind, words in keyword_map.items():
        if any(word in lowered for word in words):
            recent = _recent_inbound_files(suffixes=OFFICE_SUFFIXES[kind], limit=1)
            if recent:
                refs[kind] = str(recent[0])
    return refs


def _infer_review_attachments(text: str, articles: list[str], excel_template: str | None) -> tuple[list[str], str | None]:
    lowered = text.lower()
    inferred_articles = list(articles)
    inferred_excel = excel_template
    refs = _infer_recent_document_refs(text)

    if inferred_excel is None and any(token in lowered for token in ['excel', 'xlsx', 'formulario', 'plantilla']):
        inferred_excel = refs.get('excel')
        if inferred_excel is None:
            recent_excels = _recent_inbound_files(suffixes=('.xlsx',), limit=1)
            if recent_excels:
                inferred_excel = str(recent_excels[0])

    if not inferred_articles and any(token in lowered for token in ['articulo', 'artículos', 'articulos', 'pdf', 'papers', 'estudios']):
        recent_pdfs = [Path(refs['pdf'])] if refs.get('pdf') else _recent_inbound_files(suffixes=('.pdf',), limit=6)
        if inferred_excel and recent_pdfs:
            excel_mtime = Path(inferred_excel).stat().st_mtime
            windowed = [path for path in recent_pdfs if abs(path.stat().st_mtime - excel_mtime) <= 60 * 60 * 24]
            if windowed:
                recent_pdfs = windowed
        inferred_articles = [str(path) for path in recent_pdfs[:5]]

    return inferred_articles, inferred_excel


def _infer_edit_from_clause(clause: str) -> dict | None:
    trimmed = clause.strip()
    lowered = trimmed.lower()
    if any(lowered.startswith(prefix) for prefix in ['crea excel', 'crear excel', 'crea powerpoint', 'crear powerpoint', 'crea word', 'crear word']):
        return None

    match = re.match(r'^(?:crea|crear|create)\s+(?:archivo\s+)?([^:]+?)\s*:\s*(.+)$', trimmed, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return {'op': 'write', 'path': match.group(1).strip(), 'content': match.group(2)}

    match = re.match(r'^(?:agrega|añade|append)\s+(?:en\s+)?([^:]+?)\s*:\s*(.+)$', trimmed, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return {'op': 'append', 'path': match.group(1).strip(), 'content': match.group(2)}

    match = re.match(
        r'^(?:reemplaza|replace)\s+(?:en\s+)?([^:]+?)\s*:\s*(.+?)\s*=>\s*(.+)$',
        trimmed,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match:
        return {
            'op': 'replace',
            'path': match.group(1).strip(),
            'find': match.group(2),
            'replace': match.group(3),
        }

    return None


def parse_request(text: str, default_repo: Path) -> dict:
    mode = detect_mode(text)
    repo_path: Path | None = default_repo if mode == 'coding' else None
    write_scope: list[str] = []
    edit_operations: list[dict] = []
    objective_parts: list[str] = []
    files: list[str] = []
    fast = mode == 'coding'
    autonomous = any(
        token in text.lower()
        for token in ['hazlo todo', 'no te detengas', 'hasta terminar', 'completo', 'completa', 'de punta a punta']
    )
    articles: list[str] = []
    excel_template: str | None = None
    urls: list[str] = []

    clauses = [clause.strip() for clause in text.split(';') if clause.strip()]
    if not clauses:
        clauses = [text.strip()]

    for index, clause in enumerate(clauses):
        lower = clause.lower()
        if lower.startswith('repo:'):
            repo_path = resolve_repo(clause.split(':', 1)[1].strip(), default_repo)
            continue
        if lower.startswith('scope:'):
            write_scope.extend(item.strip() for item in clause.split(':', 1)[1].split(',') if item.strip())
            continue
        if lower.startswith('url:') or lower.startswith('urls:') or lower.startswith('navega:') or lower.startswith('abre web:'):
            urls.extend(item.strip() for item in clause.split(':', 1)[1].split(',') if item.strip())
            mode = 'research'
            continue
        if lower.startswith('articulos:') or lower.startswith('articles:') or lower.startswith('descargame estos articulos:') or lower.startswith('descargame estos artículos:'):
            articles.extend(item.strip() for item in clause.split(':', 1)[1].split(',') if item.strip())
            mode = 'review'
            continue
        if lower.startswith('excel:') or lower.startswith('llename este excel:') or lower.startswith('lléname este excel:'):
            excel_template = clause.split(':', 1)[1].strip()
            mode = 'review'
            continue
        if lower.startswith('write:'):
            payload = clause.split(':', 1)[1]
            parts = payload.split('::', 1)
            if len(parts) == 2:
                edit_operations.append({'op': 'write', 'path': parts[0].strip(), 'content': parts[1]})
                continue
        if lower.startswith('append:'):
            payload = clause.split(':', 1)[1]
            parts = payload.split('::', 1)
            if len(parts) == 2:
                edit_operations.append({'op': 'append', 'path': parts[0].strip(), 'content': parts[1]})
                continue
        if lower.startswith('replace:'):
            payload = clause.split(':', 1)[1]
            parts = payload.split('::', 2)
            if len(parts) == 3:
                edit_operations.append(
                    {'op': 'replace', 'path': parts[0].strip(), 'find': parts[1], 'replace': parts[2]}
                )
                continue
        if lower.startswith('fast:'):
            fast = clause.split(':', 1)[1].strip().lower() not in {'0', 'false', 'no', 'off'}
            continue
        if lower.startswith('autonomo:') or lower.startswith('autonomous:'):
            autonomous = clause.split(':', 1)[1].strip().lower() not in {'0', 'false', 'no', 'off'}
            continue

        inferred_edit = _infer_edit_from_clause(clause)
        if inferred_edit is not None:
            edit_operations.append(inferred_edit)
            continue

        cleaned = strip_prefix(clause) if index == 0 else clause
        if cleaned:
            objective_parts.append(cleaned)

    if edit_operations and not write_scope:
        write_scope = sorted({str(Path(item['path']).parent) for item in edit_operations})

    inferred_articles, inferred_excel = _infer_review_attachments(text, articles, excel_template)
    recent_refs = _infer_recent_document_refs(text)
    for key in ['pdf', 'powerpoint', 'word', 'excel']:
        value = recent_refs.get(key)
        if value and value not in files:
            files.append(value)
    if mode != 'ops' and (inferred_articles or inferred_excel):
        mode = 'review'
        articles, excel_template = inferred_articles, inferred_excel

    objective = ' ; '.join(objective_parts).strip()
    if not objective:
        objective = {
            'coding': 'aplica los cambios solicitados en write scope',
            'ops': 'ejecuta la tarea operativa',
            'voice': 'procesa la tarea de voz',
            'review': 'haz la revision sistematica solicitada',
            'research': 'investiga la consulta solicitada',
        }[mode]

    objective_lower = objective.lower()
    if mode == 'ops':
        if recent_refs.get('excel') and re.search(r'\babre\b.*\b(?:excel|xlsx|formulario|plantilla)\b', objective_lower):
            objective = f"abre excel con {recent_refs['excel']}"
        elif recent_refs.get('pdf') and re.search(r'\babre\b.*\bpdf\b', objective_lower):
            objective = f"abre archivo {recent_refs['pdf']}"
        elif recent_refs.get('powerpoint') and re.search(r'\babre\b.*\b(?:powerpoint|ppt|pptx|presentacion|presentación|slides)\b', objective_lower):
            objective = f"abre powerpoint con {recent_refs['powerpoint']}"
        elif recent_refs.get('word') and re.search(r'\babre\b.*\b(?:word|docx|documento)\b', objective_lower):
            objective = f"abre word con {recent_refs['word']}"

    return {
        'mode': mode,
        'objective': objective,
        'repo_path': str(repo_path) if repo_path else None,
        'write_scope': write_scope,
        'edit_operations': edit_operations,
        'fast': fast,
        'autonomous': autonomous or mode in {'review', 'coding', 'ops'},
        'articles': articles,
        'excel_template': excel_template,
        'urls': urls,
        'files': sorted(dict.fromkeys(files)),
    }


def run_launch(spec: dict, runtime_root: Path) -> subprocess.CompletedProcess[str]:
    launcher_root = Path(__file__).resolve().parent.parent
    cmd = [
        sys.executable,
        '-m',
        'orchestrator.cli',
        '--runtime-root',
        str(runtime_root),
        'launch',
        '--mode',
        spec['mode'],
        '--objective',
        spec['objective'],
    ]
    if spec.get('repo_path'):
        cmd.extend(['--repo-path', spec['repo_path']])
    if spec.get('fast'):
        cmd.append('--fast')
    if spec.get('autonomous'):
        cmd.append('--autonomous')
        cmd.extend(['--max-step-retries', '2'])
    if spec.get('excel_template'):
        cmd.extend(['--excel-template', spec['excel_template']])
    for url in spec.get('urls') or []:
        cmd.extend(['--url', url])
    for article in spec.get('articles') or []:
        cmd.extend(['--article', article])
    for file_path in spec.get('files') or []:
        cmd.extend(['--file', file_path])
    for scope in spec.get('write_scope') or []:
        cmd.extend(['--write-scope', scope])

    temp_file: tempfile.NamedTemporaryFile[str] | None = None
    try:
        if spec.get('edit_operations'):
            temp_file = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False)
            json.dump(spec['edit_operations'], temp_file)
            temp_file.flush()
            temp_file.close()
            cmd.extend(['--edit-ops-file', temp_file.name])

        return subprocess.run(cmd, cwd=str(launcher_root), capture_output=True, text=True, check=False)
    finally:
        if temp_file is not None:
            Path(temp_file.name).unlink(missing_ok=True)


def format_result(output: str) -> str:
    rows: dict[str, str] = {}
    for line in output.splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            rows[key.strip()] = value.strip()

    if not rows.get('task_id'):
        return output.strip()

    message = ['Orquesta lista']
    if rows.get('task_id'):
        message.append(f"task_id: {rows['task_id']}")
    if rows.get('status'):
        message.append(f"estado: {rows['status']}")
    if rows.get('assigned_agent'):
        message.append(f"agente: {rows['assigned_agent']}")
    if rows.get('summary'):
        message.append(f"resumen: {rows['summary']}")
    if rows.get('summary_path'):
        message.append(f"salida: {rows['summary_path']}")
    if rows.get('runtime'):
        message.append(f"runtime: {rows['runtime']}")
    return '\n'.join(message)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Parse OpenClaw chat requests and launch orchestrator tasks')
    parser.add_argument('--text', required=True)
    parser.add_argument('--default-repo', required=True)
    parser.add_argument('--runtime-root', default='.orchestrator-runtime')
    return parser


def main() -> int:
    args = build_parser().parse_args()
    default_repo = Path(args.default_repo).expanduser().resolve()
    spec = parse_request(args.text, default_repo)
    completed = run_launch(spec, Path(args.runtime_root))
    combined = '\n'.join(item for item in [completed.stdout.strip(), completed.stderr.strip()] if item)
    print(format_result(combined))
    return completed.returncode


if __name__ == '__main__':
    raise SystemExit(main())
