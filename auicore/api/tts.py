# auicore/api/tts.py
from __future__ import annotations
from typing import Protocol
from auicore.api.audio_types import PcmAudio

class TtsEngine(Protocol):
    async def synth(self, text: str) -> PcmAudio:
        """Synthesizes text to PCM audio (s16le, mono)."""
        ...
