from .base import BaseAgent, AgentContext
from .research_scout import ResearchScoutAgent
from .document_miner import DocumentMinerAgent
from .coder_builder import CoderBuilderAgent
from .ops_runner import OpsRunnerAgent
from .voice_agent import VoiceAgent


def build_agent_registry() -> dict[str, BaseAgent]:
    return {
        'research-scout': ResearchScoutAgent(),
        'document-miner': DocumentMinerAgent(),
        'coder-builder': CoderBuilderAgent(),
        'ops-runner': OpsRunnerAgent(),
        'voice-agent': VoiceAgent(),
    }
