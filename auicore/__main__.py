"""
AUI-Core entry point.

Selects the adapter line (PC simulation or Asterisk ARI) based on
the environment variable AUI_MODE.
"""

import os
import sys


def main() -> int:
    mode = os.getenv("AUI_MODE", "pc").lower()

    if mode == "pc":
        try:
            from auicore.adapters.pc import runner
        except ImportError as e:
            sys.stderr.write(f"[AUI-Core] Failed to import PC runner: {e}\n")
            return 1
        return runner.main()

    elif mode == "ari":
        try:
            from auicore.adapters.ari import runner
        except ImportError as e:
            sys.stderr.write(f"[AUI-Core] Failed to import ARI runner: {e}\n")
            return 1
        return runner.main()

    else:
        sys.stderr.write(f"[AUI-Core] Unknown AUI_MODE='{mode}'\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
