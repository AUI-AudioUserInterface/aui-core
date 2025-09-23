# auicore/services/tts/piper_tts.py
from __future__ import annotations
import asyncio
import io
import os
import sys
import threading
import wave
from typing import Optional, Any
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from auicore.api.audio_types import PcmAudio


def _log(msg: str) -> None:
    sys.stderr.write(f"[AUI-TTS] {msg}\n")
    sys.stderr.flush()


# Standard-Ziel im Repo (kann via AUI_PIPER_MODEL übersteuert werden)
DEFAULT_PIPER_MODEL = "./auicore/models/piper/de/de_DE-thorsten-medium.onnx"

# Kandidaten-URLs (wir probieren sie der Reihe nach)
# Falls du andere Mirrors hast, AUI_PIPER_URL_BASE setzen.
CANDIDATE_URLS = [
    # Thorsten-Voice/Piper Repo
    "https://huggingface.co/Thorsten-Voice/Piper/resolve/main/de_DE-thorsten-high.onnx",
    "https://huggingface.co/Thorsten-Voice/Piper/resolve/main/de_DE-thorsten-high.onnx.json",
    # Rhasspy/piper-voices Struktur
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE-thorsten-high.onnx",
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE-thorsten-high.onnx.json",
]


class PiperTTS:
    """
    Piper TTS Wrapper mit Auto-Download:
      - AUI_PIPER_MODEL: Pfad zur .onnx (Default: DEFAULT_PIPER_MODEL)
      - Liegt die .onnx (oder .onnx.json) nicht vor, wird versucht, beide Dateien zu laden.
      - Synthese: gibt PcmAudio (s16le, mono) zurück; verarbeitet Bytes/WAV/Chunk-Streams.
    """

    def __init__(self, model_path: Optional[str] = None) -> None:
        self.model_path = (model_path or os.getenv("AUI_PIPER_MODEL") or DEFAULT_PIPER_MODEL).strip()
        if not self.model_path:
            raise RuntimeError("PiperTTS: Kein Modellpfad angegeben.")

        # Lazy import von piper
        try:
            from piper.voice import PiperVoice  # type: ignore
        except Exception as e:
            raise RuntimeError(f"PiperTTS: piper-tts nicht installiert? pip install piper-tts — {e}")
        self._PiperVoice = PiperVoice

        self._voice = None  # lazy load
        self._load_lock = threading.Lock()
        self._loaded = False

        # Versuche sicherzustellen, dass das Modell vorhanden ist (ggf. herunterladen)
        self._ensure_model_present()

    # ---------- Public API ----------

    async def preload(self) -> None:
        await asyncio.to_thread(self._ensure_loaded_with_log)

    async def synth(self, text: str) -> PcmAudio:
        return await asyncio.to_thread(self._synth_blocking, text)

    # ---------- Internals ----------

    def _ensure_model_present(self) -> None:
        """
        Prüft, ob .onnx und .onnx.json vorhanden sind. Wenn nicht, Download-Versuche.
        """
        onnx = self.model_path
        json_path = onnx + ".json"

        # Pfad vorbereiten
        os.makedirs(os.path.dirname(os.path.abspath(onnx)), exist_ok=True)

        need_onnx = not os.path.isfile(onnx)
        need_json = not os.path.isfile(json_path)

        if not (need_onnx or need_json):
            return

        _log(f"Piper: Modell fehlt lokal – starte Download nach '{onnx}' …")

        # Umgebung erlaubt optional eigene Basen: AUI_PIPER_URL_BASE (Komma-separiert)
        extra_bases = os.getenv("AUI_PIPER_URL_BASE", "")
        extra_bases = [b.strip().rstrip("/") for b in extra_bases.split(",") if b.strip()]

        # Ladefunktion
        def _try_download(url: str, dest: str) -> bool:
            try:
                _log(f"Piper: Download: {url}")
                req = Request(url, headers={"User-Agent": "AUI-Core/1.0"})
                with urlopen(req, timeout=60) as r, open(dest, "wb") as f:
                    # Stream kopieren
                    chunk = r.read(8192)
                    total = 0
                    while chunk:
                        f.write(chunk)
                        total += len(chunk)
                        chunk = r.read(8192)
                if os.path.getsize(dest) == 0:
                    _log(f"Piper: Warnung – 0 Bytes heruntergeladen: {dest}")
                    return False
                return True
            except (HTTPError, URLError, TimeoutError) as e:
                _log(f"Piper: Download fehlgeschlagen ({type(e).__name__}): {e}")
                # aufräumen, falls angelegt
                try:
                    if os.path.exists(dest) and os.path.getsize(dest) == 0:
                        os.remove(dest)
                except Exception:
                    pass
                return False
            except Exception as e:
                _log(f"Piper: Download-Fehler: {e}")
                try:
                    if os.path.exists(dest) and os.path.getsize(dest) == 0:
                        os.remove(dest)
                except Exception:
                    pass
                return False

        # URL-Kandidaten zusammenstellen
        # Reihenfolge: ggf. benutzerdefinierte Basen, dann bekannte HG-Repos
        def candidates_for(ext: str) -> list[str]:
            name = os.path.basename(onnx)
            if ext == ".json":
                name += ".json"
            paths = [
                # Falls Basen gesetzt: base + "/" + name
                *[f"{b}/{name}" for b in extra_bases],
                # vordefinierte Kandidaten
                "https://huggingface.co/Thorsten-Voice/Piper/resolve/main/" + name,
                "https://huggingface.co/rhasspy/piper-voices/resolve/main/de/" + name,
            ]
            # Falls die Standardlisten aus CANDIDATE_URLS helfen sollen (nur für das High-Modell)
            if "thorsten-high" in name:
                if ext == "":
                    paths.insert(0, "https://huggingface.co/Thorsten-Voice/Piper/resolve/main/de_DE-thorsten-high.onnx")
                else:
                    paths.insert(0, "https://huggingface.co/Thorsten-Voice/Piper/resolve/main/de_DE-thorsten-high.onnx.json")
            if "thorsten-low" in name:
                if ext == "":
                    paths.insert(0, "https://huggingface.co/Thorsten-Voice/Piper/resolve/main/de_DE-thorsten-low.onnx")
                else:
                    paths.insert(0, "https://huggingface.co/Thorsten-Voice/Piper/resolve/main/de_DE-thorsten-low.onnx.json")
            if "thorsten-medium" in name:
                if ext == "":
                    paths.insert(0, "https://huggingface.co/Thorsten-Voice/Piper/resolve/main/de_DE-thorsten-medium.onnx")
                else:
                    paths.insert(0, "https://huggingface.co/Thorsten-Voice/Piper/resolve/main/de_DE-thorsten-medium.onnx.json")
            return paths

        ok_onnx = True
        ok_json = True

        if need_onnx:
            ok_onnx = False
            for url in candidates_for(ext=""):
                if _try_download(url, onnx):
                    ok_onnx = True
                    break

        if need_json:
            ok_json = False
            for url in candidates_for(ext=".json"):
                if _try_download(url, json_path):
                    ok_json = True
                    break

        if not (ok_onnx and ok_json):
            missing = []
            if not ok_onnx:
                missing.append(os.path.basename(onnx))
            if not ok_json:
                missing.append(os.path.basename(json_path))
            raise RuntimeError(
                "Piper: Modell-Download fehlgeschlagen. Fehlend: "
                + ", ".join(missing)
                + "\nTipp: Manuell ablegen oder AUI_PIPER_MODEL/AUI_PIPER_URL_BASE setzen."
            )

        _log("Piper: Modell erfolgreich geladen (Dateien vorhanden).")

    def _ensure_loaded_with_log(self) -> None:
        if self._loaded:
            return
        with self._load_lock:
            if self._loaded:
                return
            _log(f"Lade Piper-Modell '{self.model_path}' …")
            try:
                self._voice = self._PiperVoice.load(self.model_path)
            except Exception as e:
                _log(f"Piper: Laden fehlgeschlagen: {e}")
                raise
            self._loaded = True
            _log("Piper-Modell bereit.")

    def _synth_blocking(self, text: str) -> PcmAudio:
        self._ensure_loaded_with_log()
        assert self._voice is not None

        try:
            out = self._voice.synthesize(text)
        except TypeError:
            out = self._voice.synthesize(text=text)

        # Fall 1: komplette WAV-Bytes
        if isinstance(out, (bytes, bytearray, memoryview)):
            wav_bytes = bytes(out)
            try:
                with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
                    frames = wf.readframes(wf.getnframes())
                    rate = wf.getframerate()
                    sampwidth = wf.getsampwidth()
                    channels = wf.getnchannels()
                _log(f"Piper: interpret=wav bytes, rate={rate}, ch={channels}, sw={sampwidth}")
            except wave.Error:
                _log("Piper: WAV-Header ungültig; behandle Daten als PCM s16le/mono (Fallback).")
                frames = wav_bytes
                rate, channels, sampwidth = self._infer_sample_rate(), 1, 2
            if channels != 1 or sampwidth != 2:
                import audioop
                if channels != 1:
                    frames = audioop.tomono(frames, sampwidth, 1.0, 0.0)
                if sampwidth != 2:
                    frames = audioop.lin2lin(frames, sampwidth, 2)
            return PcmAudio(data=frames, rate=rate, channels=1, width=2)

        # Fall 2: Stream (AudioChunk / dict / Bytes-Chunks)
        buf = bytearray()
        meta = {"rate": None, "channels": None, "sampwidth": None, "format": None}

        for part in self._iter_chunks(out):
            b, m = self._extract_bytes_and_meta(part)
            if b:
                buf.extend(b)
            for k, v in m.items():
                if v is not None and meta.get(k) is None:
                    meta[k] = v

        data = bytes(buf)

        # 1) Falls zusammengesetzte WAV-Chunks → als WAV öffnen
        if data[:4] == b"RIFF" or (meta.get("format") in ("wav", "WAV")):
            try:
                with wave.open(io.BytesIO(data), "rb") as wf:
                    frames = wf.readframes(wf.getnframes())
                    rate = wf.getframerate()
                    sampwidth = wf.getsampwidth()
                    channels = wf.getnchannels()
                _log(f"Piper: interpret=wav stream, rate={rate}, ch={channels}, sw={sampwidth}")
                if channels != 1 or sampwidth != 2:
                    import audioop
                    if channels != 1:
                        frames = audioop.tomono(frames, sampwidth, 1.0, 0.0)
                    if sampwidth != 2:
                        frames = audioop.lin2lin(frames, sampwidth, 2)
                return PcmAudio(data=frames, rate=rate, channels=1, width=2)
            except wave.Error:
                _log("Piper: WAV-Stream konnte nicht geparst werden – falle auf PCM aus Metadaten zurück.")

        # 2) PCM gemäß Metadaten
        rate = int(meta["rate"] or self._infer_sample_rate())
        channels = int(meta["channels"] or 1)
        sampwidth = int(meta["sampwidth"] or 2)
        _log(f"Piper: interpret=pcm stream, rate={rate}, ch={channels}, sw={sampwidth}, bytes={len(data)}")
        if channels != 1 or sampwidth != 2:
            import audioop
            pcm = data
            if channels != 1:
                pcm = audioop.tomono(pcm, sampwidth, 1.0, 0.0)
            if sampwidth != 2:
                pcm = audioop.lin2lin(pcm, sampwidth, 2)
            data = pcm
        return PcmAudio(data=data, rate=rate, channels=1, width=2)

    # ---- Chunk-Handling ----

    def _iter_chunks(self, obj: Any):
        try:
            it = iter(obj)
        except TypeError:
            _log(f"Piper: Unerwarteter Rückgabewert von synthesize(): {type(obj)!r}")
            raise
        for part in it:
            yield part

    def _extract_bytes_and_meta(self, part: Any) -> tuple[Optional[bytes], dict]:
        """
        Liefert (bytes, meta) aus einem Chunk.
        meta-Keys: rate, channels, sampwidth, format

        Unterstützt u. a. Piper AudioChunk mit Feldern:
        - audio_int16_bytes, audio_int16_array, audio_float_array
        - sample_rate, sample_channels, sample_width
        """
        meta = {"rate": None, "channels": None, "sampwidth": None, "format": None}

        # dict-Variante
        if isinstance(part, dict):
            for k_attr, m_key in (
                ("sample_rate", "rate"),
                ("rate", "rate"),
                ("num_channels", "channels"),
                ("channels", "channels"),
                ("sample_channels", "channels"),
                ("sample_width_bytes", "sampwidth"),
                ("sample_width", "sampwidth"),
                ("format", "format"),
                ("encoding", "format"),
            ):
                if k_attr in part:
                    try:
                        meta[m_key] = int(part[k_attr]) if m_key != "format" else part[k_attr]
                    except Exception:
                        meta[m_key] = part[k_attr]
            # Bytes
            for key in ("audio_int16_bytes", "audio", "bytes", "data", "buffer", "payload"):
                if key in part:
                    b = self._bytes_like(part[key])
                    if b:
                        return b, meta
            # Arrays
            for key, to_int16 in (("audio_int16_array", False), ("audio_float_array", True)):
                if key in part:
                    arr = part[key]
                    try:
                        import numpy as np
                        a = np.asarray(arr)
                        if to_int16:
                            a = (np.clip(a, -1.0, 1.0) * 32767.0).astype(np.int16)
                        else:
                            a = a.astype(np.int16, copy=False)
                        return a.tobytes(), meta
                    except Exception:
                        pass
            return None, meta

        # AudioChunk-Objekt
        if type(part).__name__ == "AudioChunk":
            # Metadaten
            for attr, m_key in (
                ("sample_rate", "rate"),
                ("sample_channels", "channels"),
                ("channels", "channels"),
                ("sample_width", "sampwidth"),
                ("sample_width_bytes", "sampwidth"),
                ("format", "format"),
                ("encoding", "format"),
            ):
                if hasattr(part, attr):
                    try:
                        val = getattr(part, attr)
                        meta[m_key] = int(val) if m_key != "format" else val
                    except Exception:
                        meta[m_key] = getattr(part, attr)

            # 1) Direkt fertige PCM-Bytes
            for name in ("audio_int16_bytes", "audio", "bytes", "data", "buffer", "payload"):
                if hasattr(part, name):
                    b = self._bytes_like(getattr(part, name))
                    if b:
                        return b, meta

            # 2) Arrays → Bytes
            for name, to_int16 in (
                ("audio_int16_array", False),
                ("audio_float_array", True),
                ("array", True),
                ("samples", True),
            ):
                if hasattr(part, name):
                    try:
                        import numpy as np
                        a = np.asarray(getattr(part, name))
                        if to_int16:
                            if a.dtype.kind == "f":
                                a = (np.clip(a, -1.0, 1.0) * 32767.0).astype(np.int16)
                            else:
                                a = a.astype(np.int16, copy=False)
                        else:
                            a = a.astype(np.int16, copy=False)
                        return a.tobytes(), meta
                    except Exception:
                        pass

            # 3) Methoden
            for m in ("to_bytes", "tobytes"):
                if hasattr(part, m) and callable(getattr(part, m)):
                    try:
                        b = getattr(part, m)()
                        if isinstance(b, (bytes, bytearray, memoryview)):
                            return bytes(b), meta
                    except Exception:
                        pass

            # Einmaliger Attributdump zur Diagnose
            self._dump_chunk_attrs_once(part)
            return None, meta

        # rohe Bytes?
        b = self._bytes_like(part)
        return (b, meta)

    def _dump_chunk_attrs_once(self, part: Any) -> None:
        if getattr(self, "_did_dump_attrs", False):
            return
        setattr(self, "_did_dump_attrs", True)
        _log("Piper AudioChunk: unbekannter Aufbau – verfügbare Attribute:")
        try:
            for a in (n for n in dir(part) if not n.startswith("_")):
                try:
                    val = getattr(part, a)
                    t = type(val).__name__
                    extra = ""
                    try:
                        ln = len(val)  # type: ignore
                        extra = f" (len={ln})"
                    except Exception:
                        pass
                    _log(f"  - {a}: {t}{extra}")
                except Exception:
                    _log(f"  - {a}: <unzugänglich>")
        except Exception:
            pass

    @staticmethod
    def _bytes_like(x: Any) -> Optional[bytes]:
        if x is None:
            return None
        if isinstance(x, (bytes, bytearray, memoryview)):
            return bytes(x)
        try:
            import numpy as np  # optional
            if isinstance(x, np.ndarray):
                return x.tobytes()
        except Exception:
            pass
        if isinstance(x, (list, tuple)) and x and isinstance(x[0], int):
            try:
                return bytes(x)
            except Exception:
                return None
        for m in ("to_bytes", "tobytes"):
            if hasattr(x, m) and callable(getattr(x, m)):
                try:
                    b = getattr(x, m)()
                    return bytes(b) if not isinstance(b, (bytes, bytearray, memoryview)) else bytes(b)
                except Exception:
                    pass
        try:
            return bytes(x)
        except Exception:
            return None

    def _infer_sample_rate(self) -> int:
        """Samplerate aus Voice/Config ableiten; Fallback 22050."""
        sr = None
        v = self._voice
        try:
            sr = getattr(v, "sample_rate", None)
            if sr is None and hasattr(v, "config"):
                cfg = getattr(v, "config")
                for key in ("sample_rate", "sampleRate", "audio_sample_rate"):
                    if hasattr(cfg, key):
                        sr = getattr(cfg, key); break
                    if isinstance(cfg, dict) and key in cfg:
                        sr = cfg[key]; break
        except Exception:
            sr = None
        try:
            return int(sr) if sr is not None else 22050
        except Exception:
            return 22050
