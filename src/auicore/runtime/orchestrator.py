# aui-core/src/auicore/runtime/orchestrator.py
from __future__ import annotations

import asyncio
import logging
from typing import Optional

# Domänen-Manager (bauen intern auf auicommon.pluginmanager.PluginRegistry auf)
from auicore.services.adapter.manager import AdapterManager
from auicore.services.tts.manager import TtsManager
from auicore.services.app.manager import AppManager

# Contracts/Protocols (nur für Typen & init)
from auicommon.adapter.base import AdapterService
from auicommon.tts.base import TtsService
from auicommon.app.base import AppService
from auicommon.runtime.app_api import AppContext as AppContextProtocol

# Konkrete Context-Implementierung (Toolkit-Fassade über TTS/Adapter)
#from .context import AppContextImpl  # <- implementierst du separat

log = logging.getLogger("auicore.orchestrator")


class Orchestrator:
    """
    Zentrale Orchestrierung:
    - Hält Domänen-Manager (Adapter, TTS, App)
    - Baut AppContext (Toolkit) und injiziert ihn in Apps
    - Startet/stoppt ausgewählte App
    - Stellt Listen der verfügbaren Plugins je Domäne bereit
    """

    def __init__(self) -> None:
        # Domänen-Manager
        self.adapters = AdapterManager()
        self.tts = TtsManager()
        self.apps = AppManager()

        # Laufende App
        self._app: Optional[AppService] = None
        self._ctx: Optional[AppContextProtocol] = None

        # Shutdown-Sperre (optional, falls parallele Aufrufe)
        self._lock = asyncio.Lock()

    # ---------------------------------------------------------------------
    # Query/Listing
    # ---------------------------------------------------------------------
    def list_all(self) -> dict[str, list[str]]:
        """
        Liefert alle bekannten Plugins je Domäne.
        """
        return {
            "adapters": self.adapters.list(),
            "tts": self.tts.list(),
            "apps": self.apps.list(),
        }

    # ---------------------------------------------------------------------
    # Backend-Auswahl
    # ---------------------------------------------------------------------
    async def select_backends(
        self,
        *,
        adapter: Optional[str] = None,
        tts: Optional[str] = None,
        adapter_kwargs: Optional[dict] = None,
        tts_kwargs: Optional[dict] = None,
    ) -> None:
        """
        Wählt (und startet) je ein Backend pro Domäne (sofern angegeben).
        Reihenfolge: zuerst Adapter, dann TTS.
        """
        async with self._lock:
            if adapter:
                await self.adapters.set_current(adapter, **(adapter_kwargs or {}))
            if tts:
                await self.tts.set_current(tts, **(tts_kwargs or {}))

            # Kontext neu aufbauen, falls beide vorhanden
            if self.adapters.current and self.tts.current:
                self._ctx = self._make_context(self.tts.current, self.adapters.current)

    # ---------------------------------------------------------------------
    # App-Lifecycle
    # ---------------------------------------------------------------------
    async def start_app(self, name: str) -> None:
        """
        Lädt App-Plugin, injiziert AppContext und startet die App.
        """
        async with self._lock:
            # Bestehende App stoppen
            if self._app is not None:
                await self._stop_app_locked()

            if self._ctx is None:
                # Optional: Context lazy bauen, falls Backends schon gewählt
                if self.adapters.current and self.tts.current:
                    self._ctx = self._make_context(self.tts.current, self.adapters.current)
                else:
                    raise RuntimeError("Kein AppContext verfügbar (Adapter/TTS nicht gesetzt)")

            # App erstellen und starten
            app = self.apps.make(name)
            app.init(self._ctx)
            await app.start()
            self._app = app
            log.info("App '%s' gestartet.", name)

    async def stop_app(self) -> None:
        """
        Stoppt die laufende App (falls vorhanden).
        """
        async with self._lock:
            await self._stop_app_locked()

    # ---------------------------------------------------------------------
    # Shutdown (geordnet)
    # ---------------------------------------------------------------------
    async def shutdown(self) -> None:
        """
        Stoppt App, dann TTS, dann Adapter – in dieser Reihenfolge.
        """
        async with self._lock:
            await self._stop_app_locked()

            # Backends geordnet stoppen (falls Manager Start/Stop delegieren)
            if self.tts.current:
                try:
                    await self.tts.current.stop()
                except Exception:  # nüchtern: Fehler loggen, weiter fahren
                    log.exception("TTS stop failed")

            if self.adapters.current:
                try:
                    await self.adapters.current.stop()
                except Exception:
                    log.exception("Adapter stop failed")

            self._ctx = None
            log.info("Orchestrator shutdown complete.")

    # ---------------------------------------------------------------------
    # Internals
    # ---------------------------------------------------------------------
    def _make_context(self, tts: TtsService, adapter: AdapterService) -> AppContextProtocol:
        """
        Baut den konkreten AppContext (Toolkit) für Apps.
        """
        return AppContextImpl(tts=tts, adapter=adapter)

    async def _stop_app_locked(self) -> None:
        """
        Interner Helper: läuft nur unter self._lock.
        """
        if self._app is None:
            return
        try:
            await self._app.stop()
        finally:
            log.info("App gestoppt.")
            self._app = None

    # ---------------------------------------------------------------------
    # Optional: Properties für Statusabfragen
    # ---------------------------------------------------------------------
    @property
    def current_app(self) -> Optional[AppService]:
        return self._app

    @property
    def context(self) -> Optional[AppContextProtocol]:
        return self._ctx
