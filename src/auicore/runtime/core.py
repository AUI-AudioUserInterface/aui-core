import asyncio
from aui_common.audio.types import PcmAudio
from aui_common.audio.protocol import AudioSink
from aui_common.speech.tts import SpeechProvider
from aui_common.util.textnorm import map_star_hash
from aui_common.util.async_utils import CancellationToken, OperationHandle
from aui_common.input.provider import InputProvider

class Services:
    def __init__(self, tts: SpeechProvider, audio: AudioSink, inputp: InputProvider) -> None:
        self.tts = tts
        self.audio = audio
        self.inputp = inputp
        self.interrupt_on_dtmf: bool = True

class CoreAppContext:
    def __init__(self, services: Services) -> None:
        self.s = services

    async def say(self, text: str, wait: bool=False, cancel: CancellationToken | None = None) -> OperationHandle:
        token = cancel or CancellationToken()
        handle = OperationHandle(token)
        text = map_star_hash(text)

        async def _talk():
            pcm = await self.s.tts.synth(text, cancel=token)  # type: ignore[arg-type]
            await self.s.audio.play(pcm, wait=True, cancel=token)  # type: ignore[arg-type]

        tasks = {asyncio.create_task(_talk())}
        if self.s.interrupt_on_dtmf:
            tasks.add(asyncio.create_task(self._watch_for_interrupt(token)))

        if wait:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for t in pending: t.cancel()
        return handle

    async def play(self, audio: PcmAudio, wait: bool=False, cancel: CancellationToken | None = None) -> OperationHandle:
        token = cancel or CancellationToken()
        handle = OperationHandle(token)
        task = asyncio.create_task(self.s.audio.play(audio, wait=True, cancel=token))  # type: ignore[arg-type]
        if wait:
            try:
                await task
            finally:
                if not task.done():
                    task.cancel()
        return handle

    async def stop_audio(self) -> None:
        try:
            await self.s.audio.stop()  # type: ignore[attr-defined]
        except AttributeError:
            pass

    async def _watch_for_interrupt(self, token: CancellationToken) -> None:
        async for _ in self.s.inputp.dtmf_events():
            token.cancel()
            try:
                await self.s.audio.stop()  # type: ignore[attr-defined]
            except AttributeError:
                pass
            break
