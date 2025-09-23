# auicore/adapters/pc/adapter.py
from __future__ import annotations

import types
from typing import Any, Mapping, Optional

from auicore.services.tts.factory import make_tts
from auicore.adapters.pc.player import PcPlayerAdapter

# -------------------------------
# Tastatur-DTMF (0-9, *, #)
# -------------------------------
import asyncio
import sys
import threading
from collections import deque

_ALLOWED = set("0123456789*#")


class _DummyDtmf:
    """
    Simuliert DTMF-Eingabe über die Tastatur.
    - gültige Tasten: 0-9, *, #
    - get_digit(timeout) liefert die nächste Taste oder None bei Timeout
    - pushback(d) legt eine Taste "vorne" in den Puffer
    """

    def __init__(self) -> None:
        self._buf: deque[str] = deque()          # Pushback-Puffer (FIFO von vorne)
        self._q: asyncio.Queue[str] = asyncio.Queue()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._t: Optional[threading.Thread] = None
        self._stop = threading.Event()

        # Terminal-Rohmodus nur auf POSIX; unter Windows ggf. Zeilenmodus
        self._posix = hasattr(sys.stdin, "fileno")
        self._old_term = None  # für Wiederherstellung

        # Lazy start: Reader erst beim ersten get_digit() starten.

    def _ensure_started(self) -> None:
        if self._t is not None and self._t.is_alive():
            return
        if self._loop is None:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                # sollte nicht passieren; Fallback
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)

        self._stop.clear()
        self._t = threading.Thread(target=self._reader_loop, name="DTMF-Reader", daemon=True)
        self._t.start()

    def _reader_loop(self) -> None:
        """
        Liest Zeichen blocking von stdin in einem Thread und liefert sie
        threadsicher in die asyncio-Queue.
        """
        # POSIX: cbreak/kein Echo → zeichenweises Lesen
        term_set = False
        if self._posix:
            try:
                import termios, tty  # noqa: PLC0415
                fd = sys.stdin.fileno()
                self._old_term = termios.tcgetattr(fd)
                tty.setcbreak(fd)  # keine Zeilenpufferung
                term_set = True
            except Exception:
                term_set = False  # Fallback unten

        try:
            while not self._stop.is_set():
                try:
                    ch = sys.stdin.read(1) if term_set else sys.stdin.readline(1)
                    if not ch:
                        # EOF / kein Terminal → kurz schlafen, dann weiter
                        import time
                        time.sleep(0.01)  # vermeiden, dass die Schleife heiß läuft
                        continue
                    c = ch.strip()
                    # Zeilenmodus: readline(1) kann '\n' liefern → ignorieren
                    if not c:
                        continue
                    if c in _ALLOWED and self._loop is not None:
                        self._loop.call_soon_threadsafe(self._q.put_nowait, c)
                except Exception:
                    import time
                    time.sleep(0.01)
        finally:
            # Terminal zurücksetzen
            if term_set and self._old_term is not None:
                try:
                    import termios  # noqa: PLC0415
                    termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._old_term)
                except Exception:
                    pass

    async def get_digit(self, timeout: Optional[float] = None) -> Optional[str]:
        """
        Liefert die nächste DTMF-Taste aus Pushback-Puffer oder Tastatur.
        timeout in Sekunden; None = unendlich warten.
        """
        self._ensure_started()

        if self._buf:
            return self._buf.popleft()

        try:
            if timeout is None:
                return await self._q.get()
            else:
                return await asyncio.wait_for(self._q.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    def pushback(self, d: str) -> None:
        """Legt eine Taste vorne in den Puffer (wird als nächstes geliefert)."""
        if d and len(d) == 1 and d in _ALLOWED:
            self._buf.appendleft(d)

    async def stop(self) -> None:
        """Reader-Thread beenden und Queue leeren."""
        self._stop.set()
        if self._t and self._t.is_alive():
            self._t.join(timeout=0.2)
        try:
            while True:
                self._q.get_nowait()
        except asyncio.QueueEmpty:
            pass


# -------------------------------
# Recorder-Placeholder
# -------------------------------

class _NoopRecorder:
    async def record(self, max_seconds: int) -> bytes:
        return b""


# -------------------------------
# PC-Adapter
# -------------------------------

class PcAdapter:
    """
    PC-Transport:
      - TTS: Factory (Default Piper/Thorsten-High via Env; Coqui als Fallback)
      - Player: Soundkarte (PCM s16le/mono)
      - DTMF: Tastatur (0-9, *, #)
      - Recorder: Noop
    """

    def __init__(self, env: Mapping[str, str] | None = None) -> None:
        self._env = env or {}
        self._started = False

        # gehaltene Instanzen für sauberes Lifecycle-Management
        self._tts = None
        self._player: Optional[PcPlayerAdapter] = None
        self._dtmf: Optional[_DummyDtmf] = None
        self._recorder: Optional[_NoopRecorder] = None

    async def start(self) -> None:
        # TTS vorladen (zeigt Log, vermeidet „stilles Warten“)
        self._tts = make_tts()
        if hasattr(self._tts, "preload"):
            await self._tts.preload()  # type: ignore[attr-defined]

        # IO-Komponenten anlegen
        self._player = PcPlayerAdapter()
        self._dtmf = _DummyDtmf()          # startet den Reader lazy beim ersten get_digit()
        self._recorder = _NoopRecorder()

        self._started = True

    async def make_io(self) -> Any:
        if not self._started:
            raise RuntimeError("PcAdapter wurde nicht gestartet (start() aufrufen).")

        # Fallbacks (sollten eigentlich nicht auftreten)
        tts = self._tts or make_tts()
        player = self._player or PcPlayerAdapter()
        dtmf = self._dtmf or _DummyDtmf()
        recorder = self._recorder or _NoopRecorder()

        return types.SimpleNamespace(
            tts=tts,
            player=player,
            dtmf=dtmf,
            recorder=recorder,
        )

    async def stop(self) -> None:
        # laufende Audioausgabe stoppen
        if self._player is not None and hasattr(self._player, "stop"):
            try:
                await self._player.stop()
            except Exception:
                pass

        # DTMF-Reader beenden
        if self._dtmf is not None:
            try:
                await self._dtmf.stop()
            except Exception:
                pass

        self._started = False
        self._tts = None
        self._player = None
        self._dtmf = None
        self._recorder = None
