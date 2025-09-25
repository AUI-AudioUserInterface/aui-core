from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from auicommon.pluginmanager import PluginRegistry
from auicommon.tts.base import TtsService

log = logging.getLogger("auicore.tts.manager")


class TtsManager:
    """Verwaltet TTS-Plugins aus 'aui.tts_backend' und hält genau ein aktives TTS."""

    def __init__(self) -> None:
        self._reg = PluginRegistry[TtsService](groups=("aui.tts_backend",), contract=TtsService)
        self._current: Optional[TtsService] = None
        self._current_name: Optional[str] = None
        self._lock = asyncio.Lock()

    def list(self, *, refresh: bool = False) -> list[str]:
        return self._reg.list(refresh=refresh)

    def make(self, name: str, **kwargs: Any) -> TtsService:
        """Nur Instanziierung (ohne init/start)."""
        return self._reg.make(name, **kwargs)

    @property
    def current(self) -> Optional[TtsService]:
        return self._current

    @property
    def current_name(self) -> Optional[str]:
        return self._current_name

    async def set_current(self, name: str, *, init_kwargs: Optional[dict[str, Any]] = None) -> None:
        """Aktives TTS wechseln (alt stop, neu init+start)."""
        async with self._lock:
            if self._current_name == name:
                return
            if self._current:
                try:
                    await self._current.stop()
                except Exception:
                    log.exception("Stop des bisherigen TTS schlug fehl")

            inst = self._reg.make(name)
            if init_kwargs:
                await inst.init(**init_kwargs)
            await inst.start()
            self._current, self._current_name = inst, name
            log.info("TTS aktiv: %s", name)

    async def stop_current(self) -> None:
        async with self._lock:
            if not self._current:
                return
            try:
                await self._current.stop()
            finally:
                log.info("TTS gestoppt: %s", self._current_name)
                self._current = None
                self._current_name = None
