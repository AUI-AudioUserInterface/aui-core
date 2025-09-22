# auicore/adapters/ari/adapter.py
from __future__ import annotations

import types
from typing import Any, Mapping, Optional

from auicore.services.tts.factory import make_tts
# TODO: Implementiere einen AriPlayerAdapter mit play_pcm(PcmAudio)
# from auicore.adapters.ari.player import AriPlayerAdapter


class _AriPlayerAdapter:
    async def play_file(self, path: str) -> None:
        # Optional: Datei-Playback (nicht benötigt, wenn PCM gestreamt wird)
        pass

    async def play_pcm(self, pcm) -> None:
        # TODO: PCM via ARI transportieren (z. B. externalMedia / HTTP-Playback)
        # Signatur bewusst generisch gelassen; PcmAudio-Objekt wird erwartet.
        raise NotImplementedError("AriPlayerAdapter.play_pcm ist noch nicht implementiert.")

    async def stop(self) -> None:
        # TODO: Wiedergabe abbrechen
        pass


class _AriDtmf:
    def __init__(self) -> None:
        self._buf: list[str] = []

    async def get_digit(self, timeout: Optional[float] = None) -> Optional[str]:
        # TODO: DTMF aus ARI-Events lesen
        return None

    def pushback(self, d: str) -> None:
        self._buf.append(d)


class _NoopRecorder:
    async def record(self, max_seconds: int) -> bytes:
        return b""


class AriAdapter:
    """
    ARI-Transport:
      - TTS: Factory (Default Coqui, deutsches Modell, CPU)
      - Player: ARI-Streaming (noch zu implementieren)
      - DTMF: ARI-Events (noch zu implementieren)
      - Recorder: Platzhalter
    """

    def __init__(self, env: Mapping[str, str] | None = None) -> None:
        self._env = env or {}
        self._started = False

    async def start(self) -> None:
        # TODO: ARI-Verbindung aufbauen
        self._started = True

    async def make_io(self) -> Any:
        tts = make_tts()
        player = _AriPlayerAdapter()
        dtmf = _AriDtmf()
        recorder = _NoopRecorder()
        return types.SimpleNamespace(tts=tts, player=player, dtmf=dtmf, recorder=recorder)

    async def stop(self) -> None:
        # TODO: ARI-Verbindung schließen
        self._started = False
