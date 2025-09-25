from __future__ import annotations
from typing import Optional, Protocol, runtime_checkable, Deque
from dataclasses import dataclass, field
from collections import deque
import threading
import time
import argparse
import logging
import sys
import importlib.metadata as md

log = logging.getLogger("auicore")

# --- kleine Text-Normalisierung --------------------------------------------

def map_star_hash(text: str) -> str:
    # Sehr simpel; bei Bedarf später durch aui-common/util ersetzen
    return text.replace("*", " Stern ").replace("#", " Raute ")

# --- Events / Input ---------------------------------------------------------

@dataclass(slots=True)
class InputEvent:
    """Generic input event, primarily DTMF digit events."""
    timestamp: float
    kind: str  # e.g. "digit"
    value: str

class DigitBuffer:
    """Thread-safe FIFO for DTMF digits and other input events."""
    def __init__(self) -> None:
        self._q: Deque[InputEvent] = deque()
        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)

    def push_digit(self, digit: str) -> None:
        if digit not in "0123456789*#ABCDabcd":
            return
        d = digit.upper()
        with self._cv:
            self._q.append(InputEvent(time.time(), "digit", d))
            self._cv.notify_all()

    def pop(self, timeout: Optional[float] = None) -> Optional[InputEvent]:
        with self._cv:
            if not self._q:
                self._cv.wait(timeout=timeout)
            return self._q.popleft() if self._q else None

    def drain_digits(self) -> str:
        with self._cv:
            digits = "".join(e.value for e in self._q if e.kind == "digit")
            self._q.clear()
            return digits

# --- Adapter / TTS Protocols -----------------------------------------------

@runtime_checkable
class BaseAdapter(Protocol):
    """Adapter abstraction (PC, ARI, ...)."""
    def speak(self, text: str) -> None: ...
    def stop_speak(self) -> None: ...
    def play(self, uri: str) -> None: ...
    def stop_play(self) -> None: ...
    def ring(self) -> None: ...
    def hangup(self) -> None: ...
    def push_digit(self, digit: str) -> None: ...  # Adapters may feed digits to the runtime

@runtime_checkable
class TtsService(Protocol):
    """TTS engine interface (implemented in aui-tts-*)."""
    def say(self, text: str) -> None: ...
    def stop(self) -> None: ...

# --- App / Context ----------------------------------------------------------

@dataclass
class AppContext:
    """Shared runtime context for an application session."""
    digit_buffer: DigitBuffer = field(default_factory=DigitBuffer)
    adapter: Optional[BaseAdapter] = None
    tts: Optional[TtsService] = None
    is_running: bool = False
    cancel_on_input: bool = True  # Policy: Eingabe unterbricht Ausgabe

class App:
    """Main runtime orchestrator."""
    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx

    def bind_adapter(self, adapter: BaseAdapter) -> None:
        self.ctx.adapter = adapter

    def bind_tts(self, tts: TtsService) -> None:
        self.ctx.tts = tts

    def start(self) -> None:
        self.ctx.is_running = True

    def stop(self) -> None:
        self.ctx.is_running = False
        if self.ctx.tts:
            self.ctx.tts.stop()
        if self.ctx.adapter:
            try:
                self.ctx.adapter.stop_speak()
                self.ctx.adapter.stop_play()
            except Exception:
                pass

# --- Factories via Entry Points --------------------------------------------

EP_TTS = "aui.tts_backends"
EP_ADAPTER = "aui.adapters"

def _load_from_entrypoint(group: str, name: str):
    eps = md.entry_points(group=group)
    for ep in eps:
        if ep.name == name:
            cls = ep.load()
            return cls()
    available = ", ".join(sorted(ep.name for ep in eps))
    raise RuntimeError(f"Entry point '{name}' not found in group '{group}'. Available: {available or 'none'}")

def make_tts(name: Optional[str]) -> Optional[TtsService]:
    if not name:
        return None
    inst = _load_from_entrypoint(EP_TTS, name.lower())
    if not isinstance(inst, TtsService):  # runtime duck-check ist optional
        log.warning("Loaded TTS '%s' does not conform to TtsService Protocol", name)
    return inst  # type: ignore[return-value]

def make_adapter(name: Optional[str], ctx: AppContext) -> Optional[BaseAdapter]:
    if not name:
        return None
    inst = _load_from_entrypoint(EP_ADAPTER, name.lower())
    # Optional: Adapter kann eigene Events in den Buffer pushen
    try:
        inst.push_digit = ctx.digit_buffer.push_digit  # type: ignore[attr-defined]
    except Exception:
        pass
    if not isinstance(inst, BaseAdapter):
        log.warning("Loaded adapter '%s' does not conform to BaseAdapter Protocol", name)
    return inst  # type: ignore[return-value]

# --- Prompt utilities (cancellable) ----------------------------------------

def cancellable_say(ctx: AppContext, text: str, cancel_on_input: bool = True, check_interval: float = 0.05) -> bool:
    """
    Speak text via TTS or adapter. Returns True if fully completed, False if cancelled by input.
    """
    text = map_star_hash(text)

    if ctx.tts:
        ctx.tts.say(text)
    elif ctx.adapter:
        ctx.adapter.speak(text)
    else:
        log.info("No TTS/adapter available; skipping say()")
        return True  # nowhere to speak; treat as completed

    # Simple polling cancellation: if any input arrives, stop.
    if not cancel_on_input:
        # NOTE: Hier wissen wir nicht, wann der TTS/Adapter fertig ist (kein Playback-Ende-Signal).
        # Minimal-Timeout, um den Demo-Fluss nicht zu blockieren:
        time.sleep(1.0)
        return True

    start = time.time()
    while True:
        evt = ctx.digit_buffer.pop(timeout=check_interval)
        if evt is not None:
            # Cancel speech
            if ctx.tts:
                ctx.tts.stop()
            if ctx.adapter:
                ctx.adapter.stop_speak()
            # Re-inject the digit for later consumers
            ctx.digit_buffer.push_digit(evt.value)
            return False
        # In einer echten Engine würden wir das reale Ende erkennen.
        # Für das Sync-Demo begrenzen wir die Sprechdauer künstlich:
        if time.time() - start > 1.0:
            return True

def say_and_get_digit(ctx: AppContext, prompt: str, timeout: float = 5.0) -> Optional[str]:
    """
    Say a prompt (cancellable), then wait for a single digit (0-9, *, #, A-D).
    Returns the digit or None on timeout/cancel.
    """
    completed = cancellable_say(ctx, prompt, cancel_on_input=ctx.cancel_on_input)
    # whether cancelled or not, we now wait for the next digit
    evt = ctx.digit_buffer.pop(timeout=timeout)
    return evt.value if evt and evt.kind == "digit" else None

# --- Optional: STDIN-DTMF Feeder -------------------------------------------

def _stdin_dtmf_feeder(buf: DigitBuffer, stop_flag: threading.Event) -> None:
    """
    Liest von STDIN einzelne Zeichen und schiebt sie als DTMF in den Buffer.
    Nützlich für schnelle Demos ohne echten Adapter.
    """
    log.info("STDIN DTMF feeder active. Type digits (0-9,* ,#, A-D). Ctrl+C to exit.")
    try:
        while not stop_flag.is_set():
            ch = sys.stdin.read(1)
            if not ch:
                time.sleep(0.01)
                continue
            if ch in "0123456789*#ABCDabcd":
                buf.push_digit(ch)
    except Exception as e:
        log.debug("stdin feeder stopped: %s", e)

# --- CLI / main -------------------------------------------------------------

def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="auicore", description="AUI Core (sync demo runner)")
    p.add_argument("--tts", default=None, help="TTS backend (Entry-Point-Name, z.B. coqui, piper)")
    p.add_argument("--adapter", default=None, help="Adapter (Entry-Point-Name, z.B. pc, ari)")
    p.add_argument("--text", default="Hallo AUI", help="Text, der gesprochen werden soll")
    p.add_argument("--no-cancel", action="store_true", help="Eingaben brechen Ausgabe NICHT ab")
    p.add_argument("--stdin-dtmf", action="store_true", help="DTMF von STDIN lesen (Demo)")
    p.add_argument("--digits", default=None, help="DTMF-Digitfolge vorab einspeisen (z.B. '12#')")
    p.add_argument("--log-level", default="INFO", help="Logging-Level (DEBUG, INFO, ...)")
    return p

def _bootstrap_from_args(args: argparse.Namespace) -> App:
    ctx = AppContext()
    ctx.cancel_on_input = (not args.no_cancel)

    # Vorab-DTMF (Simulation)
    if args.digits:
        for ch in args.digits:
            ctx.digit_buffer.push_digit(ch)

    app = App(ctx)

    # Factories (Entry-Points)
    if args.tts:
        try:
            tts = make_tts(args.tts)
            if tts:
                app.bind_tts(tts)
        except Exception as e:
            log.error("Konnte TTS '%s' nicht laden: %s", args.tts, e)

    if args.adapter:
        try:
            adapter = make_adapter(args.adapter, ctx)
            if adapter:
                app.bind_adapter(adapter)
        except Exception as e:
            log.error("Konnte Adapter '%s' nicht laden: %s", args.adapter, e)

    return app

def main(argv: list[str] | None = None) -> int:
    parser = _build_argparser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    app = _bootstrap_from_args(args)

    # Optional STDIN-Feeder einschalten
    feeder_stop = threading.Event()
    feeder_th: Optional[threading.Thread] = None
    if args.stdin_dtmf:
        feeder_th = threading.Thread(target=_stdin_dtmf_feeder, args=(app.ctx.digit_buffer, feeder_stop), daemon=True)
        feeder_th.start()

    try:
        log.info("AUI-Core started (tts=%s, adapter=%s, cancel_on_input=%s)",
                 args.tts or "<none>", args.adapter or "<none>", app.ctx.cancel_on_input)
        app.start()

        # Mini-Demo: sagen und ggf. Digit abfragen
        completed = cancellable_say(app.ctx, args.text, cancel_on_input=app.ctx.cancel_on_input)
        log.info("say() completed=%s", completed)

        digit = say_and_get_digit(app.ctx, "Bitte Ziffer eingeben.", timeout=5.0)
        if digit:
            log.info("Empfangenes Digit: %s", digit)
        else:
            log.info("Keine Eingabe innerhalb des Timeouts.")

        app.stop()
        log.info("AUI-Core finished")
        return 0

    except KeyboardInterrupt:
        log.warning("Interrupted by user")
        return 130
    except Exception as e:
        log.exception("Fatal error: %s", e)
        return 1
    finally:
        feeder_stop.set()
        if feeder_th and feeder_th.is_alive():
            try:
                feeder_th.join(timeout=0.2)
            except Exception:
                pass
