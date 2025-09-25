# aui/aui-core/src/auicore/runtime/core.py
from __future__ import annotations
import argparse
import asyncio
import logging
from dataclasses import dataclass
from typing import Sequence, Optional

from .orchestrator import Orchestrator

# ---------------------------
# Logging (OO)
# ---------------------------
@dataclass(frozen=True)
class LogConfig:
    level: int = logging.INFO
    fmt: str = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    datefmt: Optional[str] = None

class LoggerFactory:
    def __init__(self, cfg: LogConfig) -> None:
        self._cfg = cfg

    def configure_root(self) -> None:
        logging.basicConfig(level=self._cfg.level,
                            format=self._cfg.fmt,
                            datefmt=self._cfg.datefmt)

    def get(self, name: str) -> logging.Logger:
        return logging.getLogger(name)


# ---------------------------
# Runtime-Konfiguration (OO)
# ---------------------------
@dataclass(frozen=True)
class CoreConfig:
    app: str = "demo"
    adapter: str = "pc"
    tts: str = "piper"

    @classmethod
    def from_argv(cls, argv: Optional[Sequence[str]] = None) -> "CoreConfig":
        parser = argparse.ArgumentParser(prog="auicore")
        parser.add_argument("--app", default=cls.__dataclass_fields__["app"].default,
                            help="App spec (e.g. 'demo' or 'pkg.mod:Class')")
        parser.add_argument("--adapter", default=cls.__dataclass_fields__["adapter"].default,
                            help="Adapter backend (default: pc)")
        parser.add_argument("--tts", default=cls.__dataclass_fields__["tts"].default,
                            help="TTS engine (default: piper)")
        ns = parser.parse_args(argv)
        return cls(app=ns.app, adapter=ns.adapter, tts=ns.tts)


# ---------------------------
# Core-Anwendung (OO)
# ---------------------------
class CoreApp:
    def __init__(self, cfg: CoreConfig, logger_factory: LoggerFactory) -> None:
        self._cfg = cfg
        self._log = logger_factory.get("auicore")
        self._orch = Orchestrator()

    def run(self) -> int:
        try:
            asyncio.run(self._amain())
            return 0
        except KeyboardInterrupt:
            return 130
        except Exception:
            self._log.exception("Fatal in CoreApp")
            return 1

    async def _amain(self) -> None:
        self._log.info("CoreApp started")
        self._log.info("Config: app=%s adapter=%s tts=%s",
                       self._cfg.app, self._cfg.adapter, self._cfg.tts)

        # (A) Verfügbare Plugins je Domäne ausgeben (wie bisher)
        manager_list = self._orch.list_all()
        print(manager_list)

        # (B) Nur den Adapter über den Orchestrator setzen (pc o. konfiguriert)
        await self._orch.select_backends(adapter=self._cfg.adapter)

        # (C) Aktuelle Adapter-Instanz ausgeben (wie bisher)
        print(self._orch.adapters.current)

        # Keine App/TTS starten – nur Demonstration
        # Geordneter Shutdown des gesetzten Adapters
        await self._orch.shutdown()

        self._log.info("CoreApp finished (noop)")


# ---------------------------
# main
# ---------------------------
def main(argv: Optional[Sequence[str]] = None) -> int:
    cfg = CoreConfig.from_argv(argv)
    log_cfg = LogConfig()
    logger_factory = LoggerFactory(log_cfg)
    logger_factory.configure_root()

    app = CoreApp(cfg, logger_factory)
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
