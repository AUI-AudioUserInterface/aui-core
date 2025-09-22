# auicore/adapters/pc/player.py
from __future__ import annotations
import asyncio
import threading
from typing import Optional

import simpleaudio as sa  # pip install simpleaudio

from auicore.api.audio_types import PcmAudio


class PcPlayerAdapter:
    """
    Einfacher PCM-Player für den PC:
      - spielt s16le/mono PCM via simpleaudio ab
      - liefert ein korrektes "fertig"-Signal für wait_until_done()
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._play_obj: Optional[sa.PlayObject] = None
        self._done_evt: Optional[asyncio.Event] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def play_pcm(self, pcm: PcmAudio) -> None:
        """
        Startet eine neue Wiedergabe. Bricht vorherige ggf. ab.
        """
        if self._loop is None:
            self._loop = asyncio.get_running_loop()

        # evtl. laufende Wiedergabe stoppen
        await self.stop()

        # neues Done-Event
        self._done_evt = asyncio.Event()

        # blocking-Worker in Thread
        def _worker():
            nonlocal pcm
            # simpleaudio erwartet: (bytes, num_channels, bytes_per_sample, sample_rate)
            play_obj = sa.play_buffer(
                pcm.data,
                num_channels=max(1, int(pcm.channels)),
                bytes_per_sample=max(1, int(pcm.width)),
                sample_rate=max(8000, int(pcm.rate)),
            )
            with self._lock:
                self._play_obj = play_obj

            # blockiert bis Ende oder Stopp
            play_obj.wait_done()

            # nach Ende: Event setzen (im asyncio-Loop)
            if self._loop and self._done_evt and not self._done_evt.is_set():
                self._loop.call_soon_threadsafe(self._done_evt.set)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _worker)

    async def wait_until_done(self) -> None:
        """
        Wartet exakt bis die aktuell laufende Wiedergabe fertig ist.
        """
        if self._done_evt is None:
            return
        await self._done_evt.wait()

    async def stop(self) -> None:
        """
        Stoppt laufende Wiedergabe (falls vorhanden) und setzt das Done-Event.
        """
        with self._lock:
            po = self._play_obj
            self._play_obj = None
        if po is not None:
            try:
                po.stop()
            except Exception:
                pass
        if self._done_evt and not self._done_evt.is_set():
            self._done_evt.set()
