# auicore/adapters/pc/adapter.py
from __future__ import annotations

import types
from typing import Any, Mapping, Optional

from auicore.services.tts.factory import make_tts
from auicore.adapters.pc.player import PcPlayerAdapter


class _DummyDtmf:
    def __init__(self) -> None:
        self._buf: list[str] = []

    async def get_digit(self, timeout: Optional[float] = None) -> Optional[str]:
        # Noch keine Tastatur-Anbindung; sofortiges Timeout
        return None

    def pushback(self, d: str) -> None:
        self._buf.append(d)


class _NoopRecorder:
    async def record(self, max_seconds: int) -> bytes:
        return b""


class PcAdapter:
    """
    PC-Transport:
      - TTS: Factory (Default Coqui, deutsches Modell, CPU)
      - Player: Soundkarte
      - DTMF/Recorder: Platzhalter
    """

    def __init__(self, env: Mapping[str, str] | None = None) -> None:
        self._env = env or {}
        self._started = False
        self._tts = None

    async def start(self) -> None:
        # TTS vorladen, damit man eine Statusmeldung sieht und kein "stilles Warten" hat
        self._tts = make_tts()
        if hasattr(self._tts, "preload"):
            await self._tts.preload()  # type: ignore[attr-defined]
        self._started = True

    async def make_io(self) -> Any:
        # Player & Co anreichen
        player = PcPlayerAdapter()
        dtmf = _DummyDtmf()
        recorder = _NoopRecorder()
        # TTS kommt aus start(); falls nicht gesetzt (sollte nicht passieren), erstelle jetzt
        tts = self._tts or make_tts()
        return types.SimpleNamespace(tts=tts, player=player, dtmf=dtmf, recorder=recorder)

    async def stop(self) -> None:
        self._started = False
