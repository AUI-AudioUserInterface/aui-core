# AUI-Core

**AUI-Core** (Audio User Interface Core) is an engine for developing IVR and telephony applications.  
It follows the same concept as classical GUI toolkits – but instead of visual user interfaces,  
it focuses on audio- and keypad-based dialogs (DTMF, speech, audio playback).

## Goals

- Provide a **unified core engine** for Audio User Interfaces (AUI)  
- Encapsulate **audio output, input, and navigation** in consistent widgets (e.g., `Menu`, `CheckBox`)  
- Support **DTMF events** (incl. navigation, single/double press)  
- Enable easy development of **apps/modules** that run on AUI-Core  
- Modular design: adapters for PC simulation and Asterisk ARI  

## Current Status

- Initial project structure created  
- Ready for first implementation of the PC simulation line  

## Project Structure

```
.
├── auicore/               # Main Python package
│   ├── api/               # Interfaces and core data types
│   ├── runtime/           # Generic runtime (navigation, widgets, routing)
│   ├── services/          # Shared services (e.g. TTS, store, logging)
│   │   ├── store/         # Key/Value or persistence backends
│   │   └── tts/           # TTS adapters (dummy, espeak-ng, …)
│   ├── adapters/          # Environment-specific implementations
│   │   ├── pc/            # PC simulation (sound card + keyboard DTMF)
│   │   └── ari/           # Asterisk ARI integration
│   └── plugins/           # Optional built-in apps/widgets (e.g. Menu DSL)
├── tests/                 # pytest tests (unit + integration)
├── .vscode/               # VS Code configuration
│   ├── launch.json
│   ├── settings.json
│   └── tasks.json
├── CODE_OF_CONDUCT.md     # Community guidelines
├── CONTRIBUTING.md        # Contribution rules and DCO
├── .gitignore             # Git ignore rules
├── LICENSE                # GPLv3 license text
└── README.md              # Project documentation (this file)
```

## Installation (Development)

```bash
git clone https://github.com/AUI-AudioUserInterface/aui-core.git
cd aui-core
python3.11 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

Choose the adapter line via environment variable:

- PC simulation (Linux/WSL2/macOS/Windows):
  ```bash
  AUI_MODE=pc python -m auicore
  ```

- Asterisk ARI (planned):
  ```bash
  AUI_MODE=ari python -m auicore
  ```

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
- [pyttsx3](https://pyttsx3.readthedocs.io/) (MIT)  

All listed libraries are permissively licensed and allow commercial usage.  
An optional TTS adapter may use `espeak-ng` (GPLv3), which is **not** bundled with AUI-Core,  
but must be installed separately via the system package manager.
