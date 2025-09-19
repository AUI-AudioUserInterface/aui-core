"""
Transport-agnostic runtime core for AUI-Core.

- bekommt ein IO-Objekt vom Adapter (PC/ARI)
- baut den AppContext
- lädt Plugins (Entry-Points)
- wählt und startet die App
"""
from __future__ import annotations
import os, asyncio
from importlib.metadata import entry_points
from typing import Any, Optional, Protocol, Callable, Dict

# ---- minimale IO-Protokolle ----
class TtsAdapter(Protocol):
    async def say(self, text: str) -> None: ...
    async def wait_until_done(self, timeout: Optional[float] = None) -> bool: ...

class PlayerAdapter(Protocol):
    async def play_file(self, path: str) -> None: ...
    async def stop(self) -> None: ...

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

# ---- App-Schnittstelle ----
class App(Protocol):
    def init(self, ctx: "AppContext") -> None: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...

# ---- AppContext (vereinheitlichte API) ----
class AppContext:
    def __init__(self, io: ContextIO) -> None:
        self.io = io

    async def say(self, text: str, wait: bool = False) -> None:
        await self.io.tts.say(text)
        if wait:
            await self.io.tts.wait_until_done()

    async def play_file(self, path: str) -> None:
        await self.io.player.play_file(path)

    async def stop_audio(self) -> None:
        await self.io.player.stop()

    async def get_digit(self, timeout: Optional[float] = None) -> Optional[str]:
        return await self.io.dtmf.get_digit(timeout)

# ---- Plugins laden ----
def load_all_apps(group: str) -> Dict[str, Callable[[], App]]:
    factories: Dict[str, Callable[[], App]] = {}
    try:
        for ep in entry_points(group=group):
            try:
                factories[ep.name] = ep.load()
            except Exception as e:
                print(f"[AUI-Core] Plugin '{ep.name}' konnte nicht geladen werden: {e}")
    except Exception:
        pass
    return factories

# ---- Core-Entry ----
async def run_session(io: Any) -> int:
    _require_io(io)

    ctx = AppContext(io)
    group = os.getenv("AUI_ENTRYPOINT_GROUP", "ivrapp.plugins")
    apps = load_all_apps(group)

    if not apps:
        # Inline-Fallback, damit es „lebt“
        async def _inline() -> None:
            await ctx.say("AUI-Core läuft. Keine Plugins gefunden.", wait=True)
        InlineApp = _make_inline_app(_inline)
        apps = {"inline": lambda: InlineApp()}

    name = os.getenv("AUI_APP")
    factory = apps.get(name) if name else (apps.get("menu") or next(iter(apps.values())))
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

# ---- Helpers ----
def _require_io(io: Any) -> None:
    for attr in ("tts", "player", "dtmf", "recorder"):
        if not hasattr(io, attr) or getattr(io, attr) is None:
            raise RuntimeError(f"Adapter IO is missing '{attr}'")

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
