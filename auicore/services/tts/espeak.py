# auicore/services/tts/espeak.py
"""
Minimal TTS adapter using pyttsx3 (espeak-ng backend on Linux).
Blocking .say() for simplicity; thread-safe via a lock.
"""
from __future__ import annotations

import threading
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
        # Pick a voice by substring match (e.g., "de", "german", "de+f3")
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

        self._lock = threading.Lock()

    def say(self, text: str) -> None:
        """Speak text synchronously (blocking until finished)."""
        with self._lock:
            self._engine.say(text)
            #self._engine.run()
            self._engine.runAndWait()
