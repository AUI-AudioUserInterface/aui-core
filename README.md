# AUI-Core

**AUI-Core** (Audio User Interface Core) is an engine for developing IVR and telephony applications.  
It follows the same concept as classical GUI toolkits – but instead of visual user interfaces,  
it focuses on audio- and keypad-based dialogs (DTMF, speech, audio playback).

## Goals

- Provide a **unified core engine** for Audio User Interfaces (AUI)  
- Encapsulate **audio output, input, and navigation** in consistent widgets (e.g., `Menu`, `CheckBox`)  
- Support **DTMF events** (incl. navigation, single/double press)  
- Enable easy development of **apps/modules** that run on AUI-Core  
- Modular design: future adapters for Asterisk/ARI, MQTT, external TTS engines  

## Current Status

- Initial PC-core implementation (Linux/WSL2, macOS, Windows)  
- Audio output via sound card (`sounddevice`)  
- DTMF input via keyboard (`readchar`)  
- Dummy-TTS (to be replaced later by engines like `espeak-ng`, Piper, or Cloud-TTS)  

## Project Structure

```
aui-core/
├── auicore/               # Python package
│   ├── app_context.py     # AppContext (central API for apps)
│   ├── audio_pc.py        # Audio adapter (sound card)
│   ├── dtmf_keyboard.py   # Keyboard input (DTMF simulation)
│   ├── tts_dummy.py       # Dummy-TTS
│   └── runner_pc.py       # Entry point for PC simulation
├── tests/                 # pytest tests
└── .vscode/               # VS Code configuration
```

## Installation (Development)

```bash
git clone https://github.com/AUI-AudioUserInterface/aui-core.git
cd aui-core
python3.12 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

## Usage (PC Simulation)

```bash
python -m auicore.runner_pc
```

- Audio output via the default sound card  
- DTMF input via keyboard (`0–9`, `*`, `#`)  
- Navigation extensions (e.g., `**` = Back, `##` = Enter) can be enabled optionally  

## License

- **AUI-Core** is licensed under the **GNU General Public License v3.0** (see [LICENSE](LICENSE)).  
- Commercial licensing is available. Please contact:  
  **CoPiCo2Co** <CoPiCo2Co@googlemail.com>

### Third-Party Libraries

This project uses the following third-party libraries:  
- [sounddevice](https://python-sounddevice.readthedocs.io/) (BSD)  
- [soundfile](https://pysoundfile.readthedocs.io/) (BSD)  
- [numpy](https://numpy.org/) (BSD)  
- [anyio](https://anyio.readthedocs.io/) (MIT)  
- [readchar](https://github.com/magmax/python-readchar) (MIT)  

All listed libraries are permissively licensed and allow commercial usage.  
An optional TTS adapter may use `espeak-ng` (GPLv3), which is **not** bundled with AUI-Core,  
but must be installed separately via the system package manager.
