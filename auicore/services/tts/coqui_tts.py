# auicore/services/tts/coqui_tts.py
from __future__ import annotations
import asyncio
import os
import sys
import threading
from typing import Optional

import numpy as np
from TTS.api import TTS  # pip install TTS

from auicore.api.audio_types import PcmAudio


def _log(msg: str) -> None:
    # nüchterne, kurze Debugausgabe auf stderr
    sys.stderr.write(f"[AUI-TTS] {msg}\n")
    sys.stderr.flush()


class CoquiTTS:
    """
    Coqui TTS Wrapper: liefert immer PcmAudio (s16le, mono).
    Default: deutsches Modell 'tts_models/de/thorsten/vits' auf CPU.

    Konfiguration (optional) via Env:
      - AUI_TTS_MODEL   (z. B. 'tts_models/de/thorsten/vits')
      - AUI_TTS_DEVICE  ('cpu' | 'cuda')
      - AUI_TTS_PROGRESS ('1' zeigt Coqui-Progressbar beim Laden/Synthese)
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        progress_bar: Optional[bool] = None,
    ) -> None:
        self.model_name = model_name or os.getenv("AUI_TTS_MODEL", "tts_models/de/thorsten/vits")
        #self.model_name = model_name or os.getenv("AUI_TTS_MODEL", "tts_models/de/css10/vits-neon")
        self.device = (device or os.getenv("AUI_TTS_DEVICE", "cpu")).lower()
        # Standard: keine laute Progressbar, außer explizit gewünscht
        env_prog = os.getenv("AUI_TTS_PROGRESS")
        self.progress_bar = (progress_bar
                             if progress_bar is not None
                             else (env_prog == "1"))

        self._tts: Optional[TTS] = None
        self._sr: Optional[int] = None
        self._loaded = False
        self._load_lock = threading.Lock()

    # -------- Public API --------

    async def preload(self) -> None:
        """Modell laden (und ggf. downloaden), damit spätere Synthese sofort startet."""
        await asyncio.to_thread(self._ensure_loaded_with_log)

    async def synth(self, text: str) -> PcmAudio:
        """Asynchroner Wrapper; blockierende Synthese im Thread."""
        return await asyncio.to_thread(self._synth_blocking, text)

    # -------- Internals --------

    def _ensure_loaded_with_log(self) -> None:
        # nur einmal laden; mit kurzer sichtbarer Meldung
        if self._loaded:
            return
        with self._load_lock:
            if self._loaded:
                return
            _log(f"Lade Coqui-Modell '{self.model_name}' auf Gerät '{self.device}' … (erstmaliger Start kann dauern)")
            use_gpu = self.device == "cuda"
            try:
                self._tts = TTS(self.model_name, progress_bar=self.progress_bar, gpu=use_gpu)
                # Sample-Rate sichern
                try:
                    self._sr = int(self._tts.synthesizer.output_sample_rate)  # type: ignore[attr-defined]
                except Exception:
                    self._sr = 22050
            except Exception as e:
                _log(f"Fehler beim Laden des Coqui-Modells: {e}")
                raise
            self._loaded = True
            _log(f"Coqui-Modell bereit (sample_rate={self._sr} Hz).")

    def _synth_blocking(self, text: str) -> PcmAudio:
        self._ensure_loaded_with_log()
        assert self._tts is not None and self._sr is not None

        # Coqui liefert float32 ndarray [-1,1] (mono)
        wav = self._tts.tts(text)  # type: ignore[operator]
        if not isinstance(wav, np.ndarray):
            wav = np.array(wav, dtype=np.float32)

        pcm = (np.clip(wav, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()
        return PcmAudio(data=pcm, rate=self._sr, channels=1, width=2)
