# auicore/api/audio_types.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class PcmAudio:
    data: bytes
    rate: int
    channels: int = 1
    width: int = 2
