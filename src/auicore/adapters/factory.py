import os
import importlib.metadata as md
from typing import Optional
from aui_common.audio.protocol import AudioSink
from aui_common.input.provider import InputProvider

EP_AUDIO = "aui.adapters.audio"
EP_INPUT = "aui.adapters.input"

def make_audio_sink(name: Optional[str] = None) -> AudioSink:
    target = (name or os.getenv("AUI_AUDIO", "pc")).lower()
    eps = md.entry_points(group=EP_AUDIO)
    for ep in eps:
        if ep.name == target:
            return ep.load()()  # type: ignore[call-arg]
    available = ", ".join(sorted(ep.name for ep in eps))
    raise RuntimeError(f"Audio sink '{target}' not found. Available: {available or 'none'}")

def make_input(name: Optional[str] = None) -> InputProvider:
    target = (name or os.getenv("AUI_INPUT", "pc")).lower()
    eps = md.entry_points(group=EP_INPUT)
    for ep in eps:
        if ep.name == target:
            return ep.load()()  # type: ignore[call-arg]
    available = ", ".join(sorted(ep.name for ep in eps))
    raise RuntimeError(f"Input provider '{target}' not found. Available: {available or 'none'}")
