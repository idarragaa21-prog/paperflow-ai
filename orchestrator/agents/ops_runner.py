from __future__ import annotations

from pathlib import Path

from orchestrator.agents.base import AgentContext, BaseAgent
from orchestrator.models import AgentResult
from orchestrator.tools import execute_app_action, infer_app_request, normalize_command, run_safe_command


class OpsRunnerAgent(BaseAgent):
    agent_id = 'ops-runner'

    def _objective_actions(self, objective: str) -> list[str]:
        parts = [part.strip() for part in objective.split(';') if part.strip()]
        return [part for part in parts if part.lower() not in {'sistema', 'ops', 'orquesta sistema'}]

    def run(self, ctx: AgentContext) -> AgentResult:
        objective = ctx.task.get('objective', '')
        repo_hint = (ctx.task.get('inputs') or {}).get('cwd') or (ctx.task.get('inputs') or {}).get('repo_path') or '.'
        cwd = Path(repo_hint).expanduser().resolve()
        command = normalize_command(ctx.task)
        app_request = infer_app_request(ctx.task)
        objective_actions = self._objective_actions(objective)

        if command:
            result = run_safe_command(command, cwd=cwd)
            summary = 'Ops runner executed a safe command.' if result.get('allowed') else 'Ops runner refused a non-allowlisted command.'
            log_lines = [
                f"Objective: {objective}",
                f"CWD: {cwd}",
                f"Command: {result['command']}",
                f"Allowed: {result.get('allowed')}",
                f"Return code: {result['returncode']}",
                '',
                'STDOUT:',
                result.get('stdout', ''),
                '',
                'STDERR:',
                result.get('stderr', ''),
            ]
            return AgentResult(
                agent_id=self.agent_id,
                summary=summary,
                artifacts=[
                    {'path': 'artifacts/ops_result.json', 'payload': result},
                    {'path': 'outputs/ops_log.txt', 'payload': '\n'.join(log_lines) + '\n'},
                ],
                warnings=[] if result.get('allowed') else [result.get('stderr', 'Command blocked.')],
                next_action='Inspect stdout/stderr and decide whether to run another safe command.',
            )

        if len(objective_actions) > 1:
            results: list[dict] = []
            warnings: list[str] = []
            for item in objective_actions:
                temp_task = {'objective': item, 'inputs': {'cwd': str(cwd)}}
                nested_command = normalize_command(temp_task)
                if nested_command:
                    result = run_safe_command(nested_command, cwd=cwd)
                else:
                    nested_app = infer_app_request(temp_task)
                    if nested_app:
                        result = execute_app_action(nested_app['action'], app=nested_app.get('app'), target=nested_app.get('target'))
                    else:
                        result = {
                            'command': item,
                            'returncode': -1,
                            'stdout': '',
                            'stderr': 'Action not recognized by ops-runner.',
                        }
                results.append({'objective': item, **result})
                if result.get('returncode') not in (0, None):
                    warnings.append(f"{item}: {result.get('stderr', 'failed')}")

            log_lines = [f'Objective: {objective}', f'CWD: {cwd}', '', 'SEQUENTIAL ACTIONS:']
            for idx, result in enumerate(results, start=1):
                log_lines.extend(
                    [
                        f'[{idx}] {result.get("objective")}',
                        f"Return code: {result.get('returncode')}",
                        f"STDOUT: {result.get('stdout', '')}",
                        f"STDERR: {result.get('stderr', '')}",
                        '',
                    ]
                )
            return AgentResult(
                agent_id=self.agent_id,
                summary='Ops runner executed a multi-step desktop/terminal workflow.',
                artifacts=[
                    {'path': 'artifacts/ops_sequence.json', 'payload': {'results': results}},
                    {'path': 'outputs/ops_log.txt', 'payload': '\n'.join(log_lines) + '\n'},
                ],
                warnings=warnings,
                next_action='Continue chaining app and terminal steps as needed.',
            )

        if app_request:
            result = execute_app_action(app_request['action'], app=app_request.get('app'), target=app_request.get('target'))
            summary = 'Ops runner executed an app action.' if result.get('returncode') == 0 else 'Ops runner could not complete the requested app action.'
            log_lines = [
                f"Objective: {objective}",
                f"CWD: {cwd}",
                f"App action: {app_request.get('action')}",
                f"App: {app_request.get('app')}",
                f"Target: {app_request.get('target')}",
                f"Return code: {result['returncode']}",
                '',
                'STDOUT:',
                result.get('stdout', ''),
                '',
                'STDERR:',
                result.get('stderr', ''),
            ]
            return AgentResult(
                agent_id=self.agent_id,
                summary=summary,
                artifacts=[
                    {'path': 'artifacts/app_action_result.json', 'payload': result},
                    {'path': 'outputs/ops_log.txt', 'payload': '\n'.join(log_lines) + '\n'},
                ],
                warnings=[] if result.get('returncode') == 0 else [result.get('stderr', 'App action failed.')],
                next_action='Continue with the next desktop or terminal step.',
            )

        payload = {
            'objective': objective,
            'cwd': str(cwd),
            'actions': [
                'classify requested system action',
                'check whether admin/destructive confirmation is required',
                'prepare command log and fallback path',
            ],
        }
        return AgentResult(
            agent_id=self.agent_id,
            summary='Ops task classified, but no explicit safe command was provided.',
            artifacts=[
                {'path': 'artifacts/ops_plan.json', 'payload': payload},
                {'path': 'outputs/ops_log.txt', 'payload': 'Provide inputs.command or start the objective with ! to execute a safe shell command in v1.\n'},
            ],
            warnings=['Ops-runner v1 executes only explicit allowlisted commands.'],
            next_action='Add inputs.command to the task or use a direct shell-style objective.',
        )
