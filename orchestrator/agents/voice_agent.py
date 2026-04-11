from __future__ import annotations

from pathlib import Path

from orchestrator.agents.base import AgentContext, BaseAgent
from orchestrator.models import AgentResult
from orchestrator.tools import inspect_audio, synthesize_speech, transcribe_audio


class VoiceAgent(BaseAgent):
    agent_id = 'voice-agent'

    def run(self, ctx: AgentContext) -> AgentResult:
        inputs = ctx.task.get('inputs') or {}
        files = inputs.get('files') or []
        text = inputs.get('text') or ctx.task.get('objective', '')
        runtime_outputs = ctx.runtime_dir / 'outputs'

        if files:
            source = files[0]
            probe = inspect_audio(source)
            transcription = transcribe_audio(source, runtime_outputs)
            transcript_text = ''
            if transcription.get('text_path'):
                transcript_text = Path(transcription['text_path']).read_text(errors='ignore')
            return AgentResult(
                agent_id=self.agent_id,
                summary='Voice agent inspected the audio file and attempted a real local transcription.',
                artifacts=[
                    {'path': 'artifacts/audio_probe.json', 'payload': probe},
                    {'path': 'artifacts/transcription_result.json', 'payload': transcription},
                    {'path': 'outputs/transcript.txt', 'payload': transcript_text or 'Transcription did not produce text.\n'},
                ],
                warnings=[] if transcription.get('returncode') == 0 else [transcription.get('stderr', 'Transcription failed.')],
                next_action='Review transcript quality or switch to TTS mode with inputs.text.',
            )

        tts_path = runtime_outputs / 'speech.aiff'
        synthesis = synthesize_speech(text, tts_path)
        return AgentResult(
            agent_id=self.agent_id,
            summary='Voice agent synthesized speech from text using local macOS TTS.',
            artifacts=[
                {'path': 'artifacts/tts_result.json', 'payload': synthesis},
                {'path': 'outputs/transcript.txt', 'payload': text + '\n'},
            ],
            warnings=[] if synthesis.get('returncode') == 0 else [synthesis.get('stderr', 'TTS failed.')],
            next_action='Use the generated audio file or provide an audio input for transcription.',
        )
