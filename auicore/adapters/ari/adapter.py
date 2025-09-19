"""
Asterisk ARI transport adapter.

- TTS/Espeak bleibt lokal; Wiedergabe aber via ARI (externalMedia/HTTP).
- DTMF über ARI-Events.
"""
from __future__ import annotations
import types
from typing import Any, Mapping, Optional

class _AriPlayer:
    def __init__(self, client: Any) -> None: self._client = client
    async def play_file(self, path: str) -> None:
        # TODO: Datei oder Stream über ARI abspielen
        pass
    async def stop(self) -> None:
        # TODO: laufende Wiedergabe stoppen (channels/stop oder RTP schließen)
        pass

class _AriDtmf:
    def __init__(self, client: Any) -> None:
        self._client = client
        self._queue: list[str] = []
    async def get_digit(self, timeout: Optional[float] = None) -> Optional[str]:
        # TODO: aus Event-Queue liefern, mit Timeout
        return None
    def pushback(self, d: str) -> None:
        self._queue.append(d)

class _EspeakTtsWrapper:
    def __init__(self) -> None:
        try:
            from auicore.services.tts.espeak import TTS
            self._tts = TTS(voice="de", rate=150, volume=1.0)
        except Exception:
            self._tts = None
    async def say(self, text: str) -> None:
        if self._tts: self._tts.say(text)
    async def wait_until_done(self, timeout: Optional[float] = None) -> bool:
        if self._tts: return self._tts.wait_until_done(timeout)
        return True

class _NoopRecorder:
    async def record(self, max_seconds: int) -> bytes: return b""

class AriAdapter:
    def __init__(self, env: Mapping[str, str] | None = None) -> None:
        self._env = env or {}
        self._started = False
        self._client = None  # ARI-Client später

    async def start(self) -> None:
        # TODO: ARI verbinden (HTTP+WS)
        self._started = True

    async def make_io(self) -> Any:
        return types.SimpleNamespace(
            tts=_EspeakTtsWrapper(),
            player=_AriPlayer(self._client),
            dtmf=_AriDtmf(self._client),
            recorder=_NoopRecorder(),
        )

    async def stop(self) -> None:
        # TODO: ARI sauber schließen
        self._started = False
