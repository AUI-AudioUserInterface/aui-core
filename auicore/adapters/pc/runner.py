# auicore/adapters/pc/runner.py
from __future__ import annotations

import os
import sys

try:
    from readchar import readkey
except Exception as e:
    sys.stderr.write("[AUI-Core] Missing dependency 'readchar' (pip install readchar)\n")
    raise

try:
    from auicore.services.tts.espeak import TTS
except Exception as e:
    sys.stderr.write("[AUI-Core] Cannot import TTS adapter: " + str(e) + "\n")
    raise


def main() -> int:
    # Basic configuration via env
    lang = os.getenv("AUI_TTS_LANG", "de")   # e.g. "de", "german", "de+f3"
    rate = int(os.getenv("AUI_TTS_RATE", "170"))
    volume = float(os.getenv("AUI_TTS_VOL", "1.0"))

    tts = TTS(voice=lang, rate=rate, volume=volume)

    print("[AUI-Core] PC simulation mode")
    print("  Press digits 0-9, '*' or '#'. Press 'q' to quit.")
    tts.say("Willkommen bei A U I Core. Drücken Sie eine Taste. Q beendet.")

    dtmf_names = { "*": "Stern", "#": "Raute" }

    while True:
        k = readkey()
        if k.lower() == "q":
            tts.say("Auf Wiedersehen.")
            print("[AUI-Core] Bye.")
            return 0
        if k in "0123456789*#":
            spoken = dtmf_names.get(k, k)
            print(f"[DTMF] {repr(k)}")
            tts.say(f"Sie haben {spoken} gedrückt.")
            tts.wait_until_done()
        else:
            # ignore others, but show for visibility
            print(f"[IGN] {repr(k)}")
