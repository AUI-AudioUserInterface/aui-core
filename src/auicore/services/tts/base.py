from __future__ import annotations
from typing import Protocol, runtime_checkable

@runtime_checkable
class TtsService(Protocol):
    def say(self, text: str) -> None: ...
    def stop(self) -> None: ...