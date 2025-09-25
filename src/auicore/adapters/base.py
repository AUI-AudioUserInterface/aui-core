# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import Protocol, runtime_checkable, Optional


@runtime_checkable
class AdapterService(Protocol):
    """
    Minimal contract for an adapter backend.

    Implementations may be fully async. The manager safely handles
    both async and sync start/stop/is_busy methods.
    """

    async def start(self) -> None:
        """Initialize and make the adapter ready for use."""
        ...

    async def stop(self) -> None:
        """Tear down resources and stop the adapter."""
        ...

    # Optional; used by AdapterManager to decide when switching is safe.
    # If not provided, manager assumes "not busy".
    # Implementations MAY provide sync or async variants.
    def is_busy(self) -> bool:  # type: ignore[override]
        """
        Return True if the adapter is currently busy (e.g., playing audio,
        holding a device, etc.). May be synchronous. If an async variant
        is desired, declare: `async def is_busy(self) -> bool: ...`.
        """
        raise NotImplementedError
