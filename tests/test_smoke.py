import time
from auicore.runtime.core import App, AppContext

class DummyAdapter:
    def __init__(self, ctx): self.ctx = ctx
    def speak(self, text: str) -> None: pass
    def stop_speak(self) -> None: pass
    def play(self, uri: str) -> None: pass
    def stop_play(self) -> None: pass
    def ring(self) -> None: pass
    def hangup(self) -> None: pass
    def push_digit(self, digit: str) -> None: self.ctx.digit_buffer.push_digit(digit)

class DummyTTS:
    def say(self, text: str) -> None: pass
    def stop(self) -> None: pass

def test_say_and_get_digit_basic():
    ctx = AppContext()
    app = App(ctx)
    app.bind_adapter(DummyAdapter(ctx))
    app.bind_tts(DummyTTS())
    app.start()
    # Simulate incoming digit after prompt
    ctx.digit_buffer.push_digit("5")
    d = auicore.runtime.core.say_and_get_digit(ctx, "Enter digit:")
    assert d == "5"