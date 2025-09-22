# auicore/services/tts/factory.py
from __future__ import annotations
import os
from typing import Literal

from auicore.api.tts import TtsEngine


def make_tts() -> TtsEngine:
    """
    Wählt das TTS-Backend.
    Default (wenn keine Env gesetzt): Coqui + deutsches Modell auf CPU.
      - AUI_TTS         = 'coqui' (Default) | 'piper'
      - AUI_TTS_MODEL   = Coqui-Modellname (Default: 'tts_models/de/thorsten/vits')
      - AUI_TTS_DEVICE  = 'cpu' (Default) | 'cuda'
      - AUI_PIPER_MODEL = Pfad zur .onnx (nur für Piper)
    """
    backend: Literal["coqui", "piper"] = os.getenv("AUI_TTS", "piper").lower()  # type: ignore

    if backend == "coqui":
        from auicore.services.tts.coqui_tts import CoquiTTS
        return CoquiTTS()

    # Fallback & Default: piper
    from auicore.services.tts.piper_tts import PiperTTS
    return PiperTTS()
