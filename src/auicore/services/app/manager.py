from __future__ import annotations

import logging
from typing import Any, List

from auicommon.pluginmanager import PluginRegistry
from auicommon.app.base import AppService
from auicommon.app.meta import AppMeta

log = logging.getLogger("auicore.app.manager")


class AppManager:
    """Verwaltet App-Plugins aus 'aui.app'. Keine 'current'-Logik – Orchestrator startet/stoppt Apps."""

    def __init__(self) -> None:
        self._reg = PluginRegistry[AppService](groups=("aui.app",), contract=AppService)

    def list(self, *, refresh: bool = False) -> list[str]:
        return self._reg.list(refresh=refresh)

    def make(self, name: str, **kwargs: Any) -> AppService:
        """Instanziiert eine App (ohne init/start)."""
        return self._reg.make(name, **kwargs)

    def list_meta(self, *, refresh: bool = False) -> List[AppMeta]:
        """Instanziiert jede App einmal, liest meta() (leichtgewichtig), gibt Metadaten zurück."""
        metas: List[AppMeta] = []
        for n in self.list(refresh=refresh):
            try:
                app = self._reg.make(n)
                metas.append(app.meta())
            except Exception:
                log.exception("meta() von App '%s' fehlgeschlagen", n)
        return metas
