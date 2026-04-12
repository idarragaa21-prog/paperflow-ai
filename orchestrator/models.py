from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RouteDecision:
    domain: str
    assigned_agent: str | None
    direct: bool
    reason: str
    plan: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class AgentResult:
    agent_id: str
    summary: str
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    fallbacks_used: list[str] = field(default_factory=list)
    next_action: str | None = None
