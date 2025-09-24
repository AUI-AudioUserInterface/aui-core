import os
import importlib.metadata as md
from typing import Optional
from aui_common.speech.tts import SpeechProvider

EP_GROUP = "aui.tts_backends"

def make_tts(name: Optional[str] = None) -> SpeechProvider:
    backend = (name or os.getenv("AUI_TTS", "coqui")).lower()
    eps = md.entry_points(group=EP_GROUP)
    for ep in eps:
        if ep.name == backend:
            cls = ep.load()
            return cls()  # type: ignore[call-arg]
    available = ", ".join(sorted(ep.name for ep in eps))
    raise RuntimeError(f"TTS backend '{backend}' not found. Available: {available or 'none'}")
