from __future__ import annotations

from pathlib import Path
import json
from typing import Any

from .utils import now_iso, read_json, write_json


class TaskStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def task_dir(self, task_id: str) -> Path:
        return self.root / 'tasks' / task_id

    def init_runtime_tree(self, task_id: str) -> Path:
        base = self.task_dir(task_id)
        for name in ['inputs', 'artifacts', 'outputs', 'scratch', 'locks']:
            (base / name).mkdir(parents=True, exist_ok=True)
        return base

    def save_task(self, task: dict[str, Any]) -> Path:
        base = self.init_runtime_tree(task['task_id'])
        task['updated_at'] = now_iso()
        write_json(base / 'task.json', task)
        return base / 'task.json'

    def load_task(self, task_ref: str | Path) -> dict[str, Any]:
        path = Path(task_ref)
        if not path.exists():
            path = self.task_dir(str(task_ref)) / 'task.json'
        return read_json(path)

    def save_plan(self, task_id: str, plan: list[dict[str, Any]]) -> Path:
        path = self.task_dir(task_id) / 'plan.json'
        write_json(path, {'task_id': task_id, 'plan': plan, 'updated_at': now_iso()})
        return path

    def append_event(
        self,
        task_id: str,
        event: str,
        payload: dict[str, Any] | None = None,
        *,
        agent: str | None = None,
        step_id: str | None = None,
    ) -> None:
        path = self.task_dir(task_id) / 'events.jsonl'
        path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            'ts': now_iso(),
            'event': event,
            'task_id': task_id,
            'agent': agent,
            'step_id': step_id,
            'payload': payload or {},
        }
        with path.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps(row) + '\n')

    def write_artifact(self, task_id: str, relative_path: str, payload: Any) -> Path:
        path = self.task_dir(task_id) / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(payload, (dict, list)):
            path.write_text(json.dumps(payload, indent=2) + '\n')
        else:
            path.write_text(str(payload))
        return path
