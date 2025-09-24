import asyncio
from auicore.runtime.core import Services, CoreAppContext
from aui_common.audio.types import PcmAudio

class DummyTTS:
    async def preload(self): pass
    async def synth(self, text: str, cancel=None) -> PcmAudio:
        return PcmAudio(data=b"\x00\x00"*100, rate=22050)

class DummyAudioSink:
    async def play(self, audio: PcmAudio, wait: bool=False, cancel=None) -> None: return
    async def stop(self) -> None: return
    def is_busy(self)->bool: return False

class DummyInput:
    async def dtmf_events(self):
        if False:
            yield None
    async def wait_for_digit(self, timeout=None):
        return None

def test_context_say():
    s = Services(tts=DummyTTS(), audio=DummyAudioSink(), inputp=DummyInput())
    ctx = CoreAppContext(s)
    asyncio.get_event_loop().run_until_complete(ctx.say("Hallo", wait=True))
