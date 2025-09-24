from __future__ import annotations
from typing import Optional
from .base import TtsService

def make_tts(engine: str, **kwargs) -> Optional[TtsService]:
    """
    Very small factory stub.
    Real engines live in aui-tts-* packages and can register via import side-effects.
    """
    # Placeholder: intentionally empty to keep aui-core decoupled.
    return None