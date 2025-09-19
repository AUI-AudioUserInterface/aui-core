"""
AUI-Core entry point.

Selects the transport adapter (PC simulation or Asterisk ARI)
via the environment variable AUI_MODE.
- AUI_MODE=pc  (default)
- AUI_MODE=ari
"""
from __future__ import annotations
import asyncio, os, sys

async def _main_async() -> int:
    mode = os.getenv("AUI_MODE", "pc").lower()

    if mode == "pc":
        try:
            from auicore.adapters.pc.adapter import PcAdapter as Adapter
        except Exception as e:
            sys.stderr.write(f"[AUI-Core] Failed to import PC adapter: {e}\n")
            return 1
    elif mode == "ari":
        try:
            from auicore.adapters.ari.adapter import AriAdapter as Adapter
        except Exception as e:
            sys.stderr.write(f"[AUI-Core] Failed to import ARI adapter: {e}\n")
            return 1
    else:
        sys.stderr.write(f"[AUI-Core] Unknown AUI_MODE='{mode}'\n")
        return 2

    try:
        from auicore.runtime.core import run_session
    except Exception as e:
        sys.stderr.write(f"[AUI-Core] Failed to import runtime core: {e}\n")
        return 1

    adapter = Adapter(env=os.environ)
    await adapter.start()
    try:
        io = await adapter.make_io()
        rc = await run_session(io)
    finally:
        await adapter.stop()
    return int(rc or 0)

def main() -> int:
    try:
        return asyncio.run(_main_async())
    except KeyboardInterrupt:
        return 130

if __name__ == "__main__":
    sys.exit(main())
