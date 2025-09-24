# aui-core

**Ziel:** Lizenzsauberes, objektorientiertes Kernpaket für AUI.  
- Keine harten Abhängigkeiten auf TTS/Adapter.
- Dynamisches Laden über **Entry Points**.
- `AppContext` ist **OO** und **abbrechbar** (CancellationToken).

## Entry Points (von Plugins bereitgestellt)
- `aui.tts_backends`: `piper`, `coqui`, …
- `aui.adapters.audio`: `pc`, `ari`, …  → liefert `AudioSink`
- `aui.adapters.input`: `pc`, `ari`, …   → liefert `InputProvider`
