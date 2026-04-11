from __future__ import annotations

from pathlib import Path
from typing import Any

from orchestrator.models import AgentResult


class AgentContext:
    def __init__(self, task: dict[str, Any], step: dict[str, Any], runtime_dir: Path):
        self.task = task
        self.step = step
        self.runtime_dir = runtime_dir


class BaseAgent:
    agent_id = 'base-agent'

    def run(self, ctx: AgentContext) -> AgentResult:
        raise NotImplementedError
