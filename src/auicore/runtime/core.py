from __future__ import annotations
from typing import Optional, Protocol, runtime_checkable, Iterable, Deque, Callable
from dataclasses import dataclass, field
from collections import deque
import threading
import time

# --- Events / Input -------------------------------------------------------

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
        if digit not in "0123456789*#":
            return
        with self._cv:
            self._q.append(InputEvent(time.time(), "digit", digit))
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

# --- Adapter / TTS Protocols ----------------------------------------------

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

# --- App / Context ---------------------------------------------------------

@dataclass
class AppContext:
    """Shared runtime context for an application session."""
    digit_buffer: DigitBuffer = field(default_factory=DigitBuffer)
    adapter: Optional[BaseAdapter] = None
    tts: Optional[TtsService] = None
    is_running: bool = False

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

# --- Prompt utilities (cancellable) ---------------------------------------

def cancellable_say(ctx: AppContext, text: str, cancel_on_input: bool = True, check_interval: float = 0.05) -> bool:
    """
    Speak text via TTS or adapter. Returns True if fully completed, False if cancelled by input.
    """
    if ctx.tts:
        ctx.tts.say(text)
    elif ctx.adapter:
        ctx.adapter.speak(text)
    else:
        return True  # nowhere to speak; treat as completed

    # Simple polling cancellation: if any input arrives, stop.
    if not cancel_on_input:
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
        # In a real engine we would detect playback end; here we timeout quickly.
        if time.time() - start > 1.0:
            return True

def say_and_get_digit(ctx: AppContext, prompt: str, timeout: float = 5.0) -> Optional[str]:
    """
    Say a prompt (cancellable), then wait for a single digit (0-9, *, #).
    Returns the digit or None on timeout/cancel.
    """
    completed = cancellable_say(ctx, prompt, cancel_on_input=True)
    # whether cancelled or not, we now wait for the next digit
    evt = ctx.digit_buffer.pop(timeout=timeout)
    return evt.value if evt and evt.kind == "digit" else None