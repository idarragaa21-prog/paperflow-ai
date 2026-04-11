from __future__ import annotations

from pathlib import Path
import json
import shutil
import subprocess


def inspect_audio(path: str | Path) -> dict:
    target = Path(path).expanduser().resolve()
    completed = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', str(target)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    payload = json.loads(completed.stdout or '{}') if completed.returncode == 0 else {}
    return {
        'path': str(target),
        'exists': target.exists(),
        'returncode': completed.returncode,
        'probe': payload,
        'stderr': completed.stderr.strip(),
    }


def synthesize_speech(text: str, output_path: str | Path, *, voice: str = 'Luciana') -> dict:
    target = Path(output_path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ['say', '-v', voice, '-o', str(target), text],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    return {
        'path': str(target),
        'voice': voice,
        'returncode': completed.returncode,
        'stderr': completed.stderr.strip(),
        'created': target.exists(),
    }


def transcribe_audio(path: str | Path, output_dir: str | Path) -> dict:
    target = Path(path).expanduser().resolve()
    output_root = Path(output_dir).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    if not shutil.which('whisper'):
        return {
            'path': str(target),
            'returncode': -1,
            'stderr': 'whisper CLI not installed',
            'text_path': None,
        }
    completed = subprocess.run(
        ['whisper', str(target), '--model', 'turbo', '--output_dir', str(output_root), '--output_format', 'txt'],
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    text_path = output_root / f'{target.stem}.txt'
    return {
        'path': str(target),
        'returncode': completed.returncode,
        'stderr': completed.stderr.strip(),
        'stdout': completed.stdout.strip(),
        'text_path': str(text_path) if text_path.exists() else None,
    }
