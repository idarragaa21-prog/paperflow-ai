from __future__ import annotations

from pathlib import Path
from typing import Any

from .executor import TaskExecutor
from .router import TaskRouter
from .task_store import TaskStore


class Director:
    def __init__(self, runtime_root: Path):
        self.store = TaskStore(runtime_root)
        self.router = TaskRouter()
        self.executor = TaskExecutor(self.store)

    def prepare(self, task: dict[str, Any]) -> dict[str, Any]:
        self.store.init_runtime_tree(task['task_id'])
        self.store.append_event(task['task_id'], 'task.created', {'title': task['title']})
        decision = self.router.route(task)
        task.setdefault('classification', {})['domain'] = decision.domain
        task['assigned_agent'] = decision.assigned_agent
        task['plan'] = decision.plan
        task['status'] = 'routing' if not decision.direct else 'running'
        self.store.save_task(task)
        self.store.save_plan(task['task_id'], decision.plan)
        self.store.append_event(task['task_id'], 'task.routed', {
            'domain': decision.domain,
            'assigned_agent': decision.assigned_agent,
            'direct': decision.direct,
            'reason': decision.reason,
        })
        return task

    def run(self, task: dict[str, Any]) -> dict[str, Any]:
        prepared = self.prepare(task)
        prepared['status'] = 'running'
        self.store.save_task(prepared)
        return self.executor.run_plan(prepared)
