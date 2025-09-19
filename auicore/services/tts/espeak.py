# auicore/services/tts/espeak.py
"""
TTS adapter using pyttsx3 (espeak-ng on Linux).
Background thread processes a queue. `say()` is non-blocking.
`wait_until_done()` blocks until all queued speech finished.
"""

from __future__ import annotations

import threading
import queue
from typing import Optional

import pyttsx3


class TTS:
    def __init__(
        self,
        voice: Optional[str] = None,
        rate: Optional[int] = None,
        volume: Optional[float] = None,
    ) -> None:
        self._engine = pyttsx3.init()

        # Voice selection by substring match
        if voice:
            chosen = None
            for v in self._engine.getProperty("voices"):
                vid = getattr(v, "id", "") or ""
                vname = getattr(v, "name", "") or ""
                langs = " ".join(getattr(v, "languages", []) or [])
                if (voice.lower() in vid.lower()
                        or voice.lower() in vname.lower()
                        or voice.lower() in langs.lower()):
                    chosen = vid
                    break
            if chosen:
                self._engine.setProperty("voice", chosen)

        if rate is not None:
            self._engine.setProperty("rate", int(rate))
        if volume is not None:
            self._engine.setProperty("volume", float(volume))

        # Work queue + control
        self._queue: queue.Queue[Optional[str]] = queue.Queue()
        self._stop_event = threading.Event()

        # Pending counter to synchronize with wait_until_done()
        self._pending = 0
        self._pending_lock = threading.Lock()
        self._idle_event = threading.Event()
        self._idle_event.set()  # initially idle

        # Background thread
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                text = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if text is None:  # shutdown sentinel
                break

            try:
                self._engine.say(text)
                self._engine.runAndWait()
            finally:
                # One item finished
                with self._pending_lock:
                    self._pending -= 1
                    if self._pending == 0:
                        # nothing left: signal idle
                        self._idle_event.set()

    def say(self, text: str) -> None:
        """Enqueue text for speech (non-blocking)."""
        with self._pending_lock:
            # mark busy before enqueue to avoid race with wait_until_done()
            self._pending += 1
            self._idle_event.clear()
        self._queue.put(text)

    def wait_until_done(self, timeout: Optional[float] = None) -> bool:
        """
        Block until all queued speech has finished.
        Returns True if idle reached, False on timeout.
        """
        return self._idle_event.wait(timeout=timeout)

    def stop(self) -> None:
        """Stop background thread and TTS engine."""
        self._stop_event.set()
        self._queue.put(None)
        self._thread.join(timeout=1.0)
        try:
            self._engine.stop()
        except Exception:
            pass
