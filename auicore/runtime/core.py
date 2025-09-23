# auicore/runtime/core.py
"""
Transport-agnostischer Runtime-Core für AUI-Core.

- Erhält ein IO-Objekt vom gewählten Adapter (PC/ARI).
- Baut den AppContext.
- Lädt Plugins (Entry-Points) oder verwendet eine Inline-Fallback-App.
- Startet/stoppt die App.
"""

from __future__ import annotations

import asyncio
import os
from importlib.metadata import entry_points
from typing import Any, Optional, Protocol, Callable, Dict


# -------------------------------
# IO-Protokolle / Typen
# -------------------------------

class TtsAdapter(Protocol):
    async def synth(self, text: str): ...  # gibt PcmAudio zurück


class PlayerAdapter(Protocol):
    async def play_file(self, path: str) -> None: ...
    async def stop(self) -> None: ...
    # Wichtig für die neue Pipeline:
    async def play_pcm(self, pcm) -> None: ...
    async def wait_until_done(self) -> None: ...


class RecorderAdapter(Protocol):
    async def record(self, max_seconds: int) -> bytes: ...


class DtmfAdapter(Protocol):
    async def get_digit(self, timeout: Optional[float] = None) -> Optional[str]: ...
    def pushback(self, d: str) -> None: ...


class ContextIO(Protocol):
    tts: TtsAdapter
    player: PlayerAdapter
    recorder: RecorderAdapter
    dtmf: DtmfAdapter


class App(Protocol):
    def init(self, ctx: "AppContext") -> None: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...


# -------------------------------
# AppContext (vereinheitlichte API)
# -------------------------------

class AppContext:
    def __init__(self, io: ContextIO) -> None:
        self.io = io

    # --- Ausgabe ---
    async def say(self, text: str, wait: bool = False) -> None:
        """Text -> PCM rendern -> abspielen; optional warten bis fertig."""
        print(f"[AUI-Core] Say: {text}")

        # Sonderzeichen für Sprach ersetzen
        text = (
            text.replace('*', ' Stern ')
                .replace('#', ' Raute ')
        )
        pcm = await self.io.tts.synth(text)
        await self.io.player.play_pcm(pcm)
        if wait and hasattr(self.io.player, "wait_until_done"):
            await self.io.player.wait_until_done()

    async def play_file(self, path: str) -> None:
        await self.io.player.play_file(path)

    async def stop_audio(self) -> None:
        await self.io.player.stop()

    # --- Eingabe ---
    async def get_digit(self, timeout: Optional[float] = None) -> Optional[str]:
        return await self.io.dtmf.get_digit(timeout)

    async def confirm(self, prompt: str, timeout: float = 10.0) -> Optional[bool]:
        await self.say(prompt)
        d = await self.get_digit(timeout)
        if d == "1":
            return True
        if d == "2":
            return False
        return None


# -------------------------------1
# Plugins laden
# -------------------------------

def load_all_apps(group: str) -> Dict[str, Callable[[], App]]:
    factories: Dict[str, Callable[[], App]] = {}
    try:
        from importlib.metadata import entry_points
        eps = entry_points()
        try:
            candidates = eps.select(group=group)  # Python 3.11+
        except Exception:
            candidates = entry_points(group=group)  # Fallback für ältere Umgebungen

        names = [ep.name for ep in candidates]
        print(f"[AUI-Core] Suche Plugins in Gruppe '{group}': gefunden EPs = {names}")

        for ep in candidates:
            try:
                factories[ep.name] = ep.load()
                print(f"[AUI-Core] Plugin-Factory geladen: {ep.name} -> {ep.value}")
            except Exception as e:
                print(f"[AUI-Core] Plugin '{ep.name}' konnte nicht geladen werden: {e}")
    except Exception as e:
        print(f"[AUI-Core] Entry-Point-Suche schlug fehl: {e}")
    return factories


# -------------------------------
# Core-Einstieg
# -------------------------------

async def run_session(io: Any) -> int:
    """
    Erwartet ein IO-Objekt mit tts/player/dtmf/recorder.
    """
    _require_io(io)
    ctx = AppContext(io)

    group = os.getenv("AUI_ENTRYPOINT_GROUP", "ivrapp.plugins")
    apps = load_all_apps(group)

    if not apps:
        # Inline-Fallback, damit etwas hörbar ist
        async def _inline() -> None:
            await ctx.say("A-U-I   Kohr läuft. Keine Plaggins gefunden.", wait=True)
        InlineApp = _make_inline_app(_inline)
        apps = {"inline": lambda: InlineApp()}

    app_name = os.getenv("AUI_APP")
    factory = apps.get(app_name) if app_name else (apps.get("menu") or next(iter(apps.values())))
    app = factory()

    try:
        app.init(ctx)
        await app.start()
    finally:
        try:
            await app.stop()
        except Exception:
            pass

    return 0


# -------------------------------
# Helpers
# -------------------------------

def _require_io(io: Any) -> None:
    for attr in ("tts", "player", "dtmf", "recorder"):
        if not hasattr(io, attr) or getattr(io, attr) is None:
            raise RuntimeError(f"Adapter IO is missing '{attr}'")
    # Zusätzliche Prüfung: Player sollte play_pcm haben
    if not hasattr(io.player, "play_pcm"):
        raise RuntimeError("PlayerAdapter fehlt 'play_pcm(pcm)'")

def _make_inline_app(async_fn: Callable[[], "asyncio.Future[Any]"]) -> type:
    class _InlineApp:
        def __init__(self) -> None:
            self._ctx: Optional[AppContext] = None
        def init(self, ctx: AppContext) -> None:
            self._ctx = ctx
        async def start(self) -> None:
            await async_fn()
        async def stop(self) -> None:
            pass
    return _InlineApp
