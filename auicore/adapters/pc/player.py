# auicore/adapters/pc/player.py
from __future__ import annotations
import asyncio
from typing import Optional
import numpy as np
import sounddevice as sd

from auicore.api.audio_types import PcmAudio


class PcPlayerAdapter:
    def __init__(self) -> None:
        # _play_task ist ein asyncio.Future (Executor-Job) oder None
        self._play_task: Optional[asyncio.Future] = None

    async def play_pcm(self, pcm: PcmAudio) -> None:
        # laufende Wiedergabe (Barge-In) stoppen
        await self.stop()

        if pcm.channels != 1 or pcm.width != 2:
            raise ValueError("PcPlayerAdapter erwartet s16le mono")

        # Blocking-Playback in Thread ausführen
        def _play_blocking():
            arr = np.frombuffer(pcm.data, dtype=np.int16)
            sd.play(arr, samplerate=pcm.rate, blocking=True)  # blockiert im Worker-Thread
            sd.stop()

        loop = asyncio.get_running_loop()
        # Variante A: direkt das Future aus run_in_executor speichern (keine create_task!)
        self._play_task = loop.run_in_executor(None, _play_blocking)

        # Variante B (Alternative): asyncio.to_thread
        # self._play_task = asyncio.create_task(asyncio.to_thread(_play_blocking))

    async def wait_until_done(self) -> None:
        if self._play_task is not None:
            try:
                await self._play_task
            finally:
                self._play_task = None

    async def stop(self) -> None:
        """Sofort stoppen (Barge-In): Audio stoppen und auf Worker warten."""
        if self._play_task is not None:
            # Stoppt die PortAudio-Wiedergabe sofort
            sd.stop()
            try:
                await self._play_task
            finally:
                self._play_task = None
