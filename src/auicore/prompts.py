from __future__ import annotations
from typing import Optional
from .runtime.core import AppContext, cancellable_say, say_and_get_digit

__all__ = ["cancellable_say", "say_and_get_digit", "say_wait"]

def say_wait(ctx: AppContext, text: str, seconds: float = 0.5) -> None:
    """Say text (cancellable) and then sleep for a short, fixed delay."""
    cancellable_say(ctx, text, cancel_on_input=True)