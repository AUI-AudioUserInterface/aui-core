# aui-core

Object-oriented core runtime for the Audio User Interface (AUI) monorepo.

## Scope

* Runtime (App, AppContext)
* Adapter interfaces (PC, ARI implemented in sibling repos)
* TTS facade (interface + factory)
* Basic prompts (`say`, `say_and_get_digit`, `say_wait`) with cancel-on-input hooks
* Minimal DTMF buffer

## Non-goals

* UI widgets (go to **aui-tk**)
* Concrete adapter implementations (go to **aui-adapter-***)
* Concrete TTS engines (go to **aui-tts-***)

## Design Notes

* Everything is **OO**.
* Public API uses clear, typed interfaces.
* Adapters push input via a thread-safe queue to the runtime.
* Prompts are **cancellable on input** (e.g., a key press while speaking will interrupt TTS).

## Quickstart (editable dev)

```bash
python -m pip install -e .
```

Then in your application code:

```python
from auicore.runtime.core import App, AppContext
from auicore.prompts import say_and_get_digit

ctx = AppContext()
app = App(ctx)
# Bind your adapter before running (see adapters.BaseAdapter)
```