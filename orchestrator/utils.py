from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import re
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def slugify(value: str) -> str:
    normalized = re.sub(r'[^a-zA-Z0-9]+', '-', value.strip()).strip('-').lower()
    return normalized or 'task'


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + '\n')
