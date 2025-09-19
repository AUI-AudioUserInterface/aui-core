"""
PC transport adapter.

- TTS/Espeak läuft lokal (gemeinsam für PC & ARI).
- Audio-Ausgabe hier: Soundkarte.
- DTMF-Eingabe hier: Tastatur.

Minimal lauffähig: liefert IO mit Platzhaltern, damit core.run_session() startet.
"""
from __future__ import annotations
import types
from typing import Any, Mapping, Optional

# --- einfache Platzhalter, bis echte Implementierungen kommen ---
class _NoopPlayer:
    async def play_file(self, path: str) -> None: pass
    async def stop(self) -> None: pass

class _NoopRecorder:
    async def record(self, max_seconds: int) -> bytes: return b""

class _DummyDtmf:
    def __init__(self) -> None: self._buf: list[str] = []
    async def get_digit(self, timeout: Optional[float] = None) -> Optional[str]:
        # bis Keyboard-Adapter implementiert ist: sofort Timeout
        return None
    def pushback(self, d: str) -> None:
        self._buf.append(d)

class _EspeakTtsWrapper:
    def __init__(self) -> None:
        # deine reale Implementierung sitzt in services/tts/espeak.py
        # hier nur eine defensive Fallback-Stimme
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

# --- Adapter-Klasse ---
class PcAdapter:
    def __init__(self, env: Mapping[str, str] | None = None) -> None:
        self._env = env or {}
        self._started = False

    async def start(self) -> None:
        # TODO: Soundkarte/Keyboard initialisieren
        self._started = True

    async def make_io(self) -> Any:
        return types.SimpleNamespace(
            tts=_EspeakTtsWrapper(),
            player=_NoopPlayer(),
            dtmf=_DummyDtmf(),
            recorder=_NoopRecorder(),
        )

    async def stop(self) -> None:
        # TODO: Ressourcen freigeben
        self._started = False
