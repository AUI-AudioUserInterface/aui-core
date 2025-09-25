from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from auicommon.pluginmanager import PluginRegistry
from auicommon.adapter.base import AdapterService

log = logging.getLogger("auicore.adapter.manager")


class AdapterManager:
    """Verwaltet Adapter-Plugins aus 'aui.adapters' und hält genau einen aktiven Adapter."""

    def __init__(self) -> None:
        self._reg = PluginRegistry[AdapterService](groups=("aui.adapters",), contract=AdapterService)
        self._current: Optional[AdapterService] = None
        self._current_name: Optional[str] = None
        self._lock = asyncio.Lock()

    def list(self, *, refresh: bool = False) -> list[str]:
        return self._reg.list(refresh=refresh)

    def make(self, name: str, **kwargs: Any) -> AdapterService:
        """Nur Instanziierung (ohne init/start)."""
        return self._reg.make(name, **kwargs)

    @property
    def current(self) -> Optional[AdapterService]:
        return self._current

    @property
    def current_name(self) -> Optional[str]:
        return self._current_name

    async def set_current(self, name: str, *, init_kwargs: Optional[dict[str, Any]] = None) -> None:
        """Aktiven Adapter wechseln (alt stop, neu init+start)."""
        async with self._lock:
            if self._current_name == name:
                return
            # alten stoppen
            if self._current:
                try:
                    await self._current.stop()
                except Exception:
                    log.exception("Stop des bisherigen Adapters schlug fehl")
            # neuen bauen + initialisieren + starten
            inst = self._reg.make(name)
            if init_kwargs:
                await inst.init(**init_kwargs)
            try:
                await inst.start()
            except Exception as e:
                print (f"Adapter konnte nicht gestartet werden: {e}")
            self._current, self._current_name = inst, name
            log.info("Adapter aktiv: %s", name)

    async def stop_current(self) -> None:
        async with self._lock:
            if not self._current:
                return
            try:
                await self._current.stop()
            finally:
                log.info("Adapter gestoppt: %s", self._current_name)
                self._current = None
                self._current_name = None
