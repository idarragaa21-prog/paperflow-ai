from __future__ import annotations

import traceback

from .agents import AgentContext, build_agent_registry
from .task_store import TaskStore


class TaskExecutor:
    def __init__(self, store: TaskStore):
        self.store = store
        self.registry = build_agent_registry()

    def run_plan(self, task: dict) -> dict:
        task_id = task['task_id']
        runtime_dir = self.store.task_dir(task_id)
        constraints = task.get('constraints', {}) or {}
        continue_until_done = bool(constraints.get('continue_until_done'))
        max_step_retries = int(constraints.get('max_step_retries', 1) or 0)
        failed_steps: list[dict] = []

        for step in task.get('plan', []):
            step['status'] = 'running'
            self.store.save_task(task)
            self.store.append_event(task_id, 'step.started', {'title': step['title']}, agent=step['agent'], step_id=step['step_id'])
            agent = self.registry[step['agent']]
            result = None
            last_error: dict | None = None
            for attempt in range(max_step_retries + 1):
                try:
                    result = agent.run(AgentContext(task=task, step=step, runtime_dir=runtime_dir))
                    break
                except Exception as exc:
                    last_error = {
                        'attempt': attempt + 1,
                        'error': str(exc),
                        'traceback': traceback.format_exc(limit=6),
                    }
                    self.store.append_event(
                        task_id,
                        'step.error',
                        last_error,
                        agent=step['agent'],
                        step_id=step['step_id'],
                    )
                    if attempt < max_step_retries:
                        self.store.append_event(
                            task_id,
                            'step.retrying',
                            {'next_attempt': attempt + 2},
                            agent=step['agent'],
                            step_id=step['step_id'],
                        )

            if result is None:
                step['status'] = 'failed'
                failed_steps.append(
                    {
                        'step_id': step['step_id'],
                        'title': step['title'],
                        'agent': step['agent'],
                        'error': last_error,
                    }
                )
                self.store.save_task(task)
                if not continue_until_done:
                    task['status'] = 'failed'
                    task['error'] = last_error
                    self.store.save_task(task)
                    self.store.append_event(task_id, 'task.failed', {'failed_steps': failed_steps})
                    return task
                continue

            for artifact in result.artifacts:
                path = self.store.write_artifact(task_id, artifact['path'], artifact['payload'])
                task.setdefault('artifacts', []).append({'path': str(path), 'agent': result.agent_id})
            if result.fallbacks_used:
                task.setdefault('fallbacks_used', []).extend(result.fallbacks_used)
            self.store.append_event(
                task_id,
                'step.completed',
                {'summary': result.summary, 'warnings': result.warnings, 'next_action': result.next_action},
                agent=result.agent_id,
                step_id=step['step_id'],
            )
            step['status'] = 'completed'
        task['status'] = 'completed_with_warnings' if failed_steps else 'completed'
        task['result'] = {
            'summary': 'Task executed through orchestrator v1 runtime.',
            'artifacts_count': len(task.get('artifacts', [])),
            'fallbacks_used': task.get('fallbacks_used', []),
            'failed_steps': failed_steps,
        }
        self.store.save_task(task)
        self.store.append_event(task_id, 'task.completed', task['result'])
        return task
