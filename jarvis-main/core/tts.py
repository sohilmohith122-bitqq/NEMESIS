"""
Text-to-Speech engines for MARK XL.

EdgeTTS     – free Microsoft TTS (internet required, no API key)
Kokoro      – fully offline neural TTS (~330 MB model)
ElevenLabs  – cloud API (API key required, best quality)
"""
from __future__ import annotations

import asyncio
import json
import os
import queue as _queue
import threading
from typing import Callable, Optional

import numpy as np
import sounddevice as sd



# USE_TF=0 stops transformers from importing TensorFlow (saves 4-8 s startup).
# Do NOT set USE_TORCH or USE_JAX explicitly — forcing those values breaks
# transformers' lazy-loader on certain versions, causing AutoModel and other
# classes to vanish from the public namespace.  Auto-detection is reliable.
os.environ.setdefault("USE_TF",                 "0")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


# ---------------------------------------------------------------------------
# Audio playback helpers
# ---------------------------------------------------------------------------

def _to_numpy(samples) -> np.ndarray:
    """Convert samples to float32 numpy array.

    Handles both numpy arrays and PyTorch tensors (Kokoro >= 0.9).

    PyTorch built against numpy 1.x raises RuntimeError('Numpy is not available')
    when numpy 2.x is installed.  The .tolist() fallback always works regardless
    of PyTorch / numpy version pairing.
    """
    if hasattr(samples, "detach"):                  # PyTorch tensor
        t = samples.detach().cpu().float()
        try:
            return t.numpy()                        # fast path (compatible versions)
        except RuntimeError:
            # PyTorch/numpy version mismatch — convert via Python list (always safe)
            return np.asarray(t.tolist(), dtype=np.float32)
    return np.asarray(samples, dtype=np.float32)


def _compress_silence(
    arr: np.ndarray,
    sample_rate: int    = 24_000,
    max_silence_ms: int = 500,    # cap punctuation pauses — keeps natural rhythm
    threshold: float    = 0.003,  # RMS below this = silence; lower = less clipping
) -> np.ndarray:
    """
    Shorten Kokoro's very long punctuation pauses (1-2 s → ≤500 ms).
    Conservative settings preserve natural prosody; only trims extreme pauses.
    """
    max_samp  = int(max_silence_ms * sample_rate / 1000)
    frame_len = 240                   # ~10 ms at 24 kHz
    out: list[np.ndarray] = []
    silent_acc = 0

    for i in range(0, len(arr), frame_len):
        chunk = arr[i : i + frame_len]
        if np.sqrt(np.mean(chunk ** 2) + 1e-12) < threshold:
            silent_acc += len(chunk)
            if silent_acc <= max_samp:
                out.append(chunk)
        else:
            silent_acc = 0
            out.append(chunk)

    return np.concatenate(out) if out else arr


TTS_OUTPUT_DEVICE = None

def _play_np(samples, sample_rate: int) -> None:
    """Play float32 mono (or stereo) audio via sounddevice.
    Accepts numpy arrays or PyTorch tensors.
    """
    global TTS_OUTPUT_DEVICE
    sd.play(_to_numpy(samples), sample_rate, device=TTS_OUTPUT_DEVICE)
    sd.wait()


def _play_audio_bytes(audio_bytes: bytes) -> None:
    """Decode MP3/WAV/OGG bytes and play via sounddevice (uses miniaudio)."""
    import miniaudio
    global TTS_OUTPUT_DEVICE
    decoded = miniaudio.decode(
        audio_bytes,
        output_format=miniaudio.SampleFormat.FLOAT32,
        nchannels=1,
    )
    samples = np.array(decoded.samples, dtype=np.float32)
    sd.play(samples, decoded.sample_rate, device=TTS_OUTPUT_DEVICE)
    sd.wait()


# ---------------------------------------------------------------------------
# Engines
# ---------------------------------------------------------------------------

def _load_jarvis_config() -> dict:
    """Load JARVIS voice configuration from config/jarvis_voice.json."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "jarvis_voice.json")
    defaults = {
        "pitch_semitones": -1.5,
        "reverb_mix": 0.12,
        "reverb_delay_ms": 18,
        "reverb_decay": 0.4,
        "presence_boost": 1.08,
        "compression": 1.3,
        "limiter_threshold": 0.85,
        "limiter_output": 0.95,
    }
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        # Merge with defaults
        for k, v in defaults.items():
            if k not in cfg:
                cfg[k] = v
        return cfg
    except Exception:
        return defaults


# Cache the config on first load
_JARVIS_CFG: dict | None = None

def _get_jarvis_config() -> dict:
    global _JARVIS_CFG
    if _JARVIS_CFG is None:
        _JARVIS_CFG = _load_jarvis_config()
    return _JARVIS_CFG


def reload_jarvis_config() -> None:
    """Force reload the JARVIS voice configuration from disk."""
    global _JARVIS_CFG
    _JARVIS_CFG = _load_jarvis_config()
    print("[TTS] JARVIS voice config reloaded.")


def _jarvis_effect(
    samples: np.ndarray,
    sample_rate: int = 24_000,
) -> np.ndarray:
    """
    Apply JARVIS-style / robotic audio post-processing.

    - Pitch shift for depth
    - Ring modulation for metallic robotic tone
    - Bitcrush for digital grit
    - Flanger for sweeping metallic effect
    - Reverb for spatial presence
    - Compression for commanding tone
    """
    cfg = _get_jarvis_config()
    pitch_semitones = cfg.get("pitch_semitones", -1.5)
    reverb_mix = cfg.get("reverb_mix", 0.12)
    delay_ms = cfg.get("reverb_delay_ms", 18)
    decay = cfg.get("reverb_decay", 0.4)
    presence_boost = cfg.get("presence_boost", 1.08)
    compression = cfg.get("compression", 1.3)
    limiter_thresh = cfg.get("limiter_threshold", 0.85)
    limiter_out = cfg.get("limiter_output", 0.95)
    robotic = cfg.get("robotic_mode", False)
    ring_freq = cfg.get("ring_mod_freq", 50)
    ring_depth = cfg.get("ring_mod_depth", 0.3)
    bitcrush_bits = cfg.get("bitcrush_bits", 12)
    flanger_rate = cfg.get("flanger_rate", 0.3)
    flanger_depth = cfg.get("flanger_depth", 0.002)
    chorus_rate = cfg.get("chorus_rate", 0.5)
    chorus_depth = cfg.get("chorus_depth", 0.15)

    arr = samples.astype(np.float32)
    n = len(arr)
    t = np.arange(n, dtype=np.float32) / sample_rate

    # ── 0. Robotic effects (disabled by default — JARVIS mode) ────────
    if robotic:
        # Ring modulation — metallic robotic tone
        if ring_freq > 0 and ring_depth > 0:
            ring_osc = np.cos(2 * np.pi * ring_freq * t)
            arr = arr * (1.0 - ring_depth + ring_depth * ring_osc)

        # Bitcrush — digital grit
        if bitcrush_bits > 0 and bitcrush_bits < 16:
            levels = 2 ** bitcrush_bits
            arr = np.round(arr * levels) / levels

        # Flanger — sweeping metallic comb filter
        if flanger_rate > 0 and flanger_depth > 0:
            delay_samp = int(sample_rate * flanger_depth)
            mod = (np.sin(2 * np.pi * flanger_rate * t) * 0.5 + 0.5) * delay_samp
            mod_int = mod.astype(np.int32)
            flanged = np.zeros_like(arr)
            for i in range(delay_samp, n):
                idx = i - mod_int[i]
                if 0 <= idx < n:
                    flanged[i] = arr[i] * 0.6 + arr[idx] * 0.4
            arr = flanged

        # Chorus — slight detune and delay for thickness
        if chorus_rate > 0 and chorus_depth > 0:
            delay_ms = int(sample_rate * 0.015)  # 15ms base delay
            mod = (np.sin(2 * np.pi * chorus_rate * t + 0.7) * 0.5 + 0.5)
            chorus_delay = (mod * chorus_depth * delay_ms).astype(np.int32)
            chorused = np.zeros_like(arr)
            for i in range(delay_ms, n):
                idx = i - chorus_delay[i]
                if 0 <= idx < n:
                    chorused[i] = arr[i] * 0.7 + arr[idx] * 0.3
            arr = chorused

    # ── 1. Dynamic range compression ──────────────────────────────────
    peak = np.max(np.abs(arr)) + 1e-10
    arr = np.tanh(arr * compression / peak * 0.9) * peak

    # ── 2. Pitch shift (resampling trick) ─────────────────────────────
    if pitch_semitones != 0:
        factor = 2.0 ** (pitch_semitones / 12.0)
        new_len = int(len(arr) / factor)
        indices = np.linspace(0, len(arr) - 1, new_len)
        arr = np.interp(indices, np.arange(len(arr)), arr).astype(np.float32)
        # Resample back to original length
        indices2 = np.linspace(0, len(arr) - 1, n)
        arr = np.interp(indices2, np.arange(len(arr)), arr).astype(np.float32)

    # ── 3. Convolution reverb ─────────────────────────────────────────
    if reverb_mix > 0:
        delay_samp = int(sample_rate * delay_ms / 1000)
        reverb = np.zeros_like(arr)
        if delay_samp < len(arr):
            reverb[delay_samp:] = arr[:-delay_samp] * decay
            # Second reflection
            d2 = delay_samp * 2
            if d2 < len(arr):
                reverb[d2:] += arr[:-d2] * decay * 0.3
            # Third reflection (robotic = more reflections)
            d3 = delay_samp * 3
            if d3 < len(arr) and robotic:
                reverb[d3:] += arr[:-d3] * decay * 0.15
        arr = arr * (1 - reverb_mix) + reverb * reverb_mix

    # ── 4. Presence / clarity boost ───────────────────────────────────
    diff = np.diff(arr, prepend=arr[0])
    arr = arr * (1.0 - presence_boost) + diff * (presence_boost - 1.0) + arr

    # ── 5. Soft-clip limiter ──────────────────────────────────────────
    arr = np.tanh(arr * limiter_thresh) * limiter_out

    return arr.astype(np.float32)


class EdgeTTSEngine:
    """Microsoft EdgeTTS – free, requires internet.

    Default voice: en-GB-RyanNeural (British male – JARVIS-style).
    Reads voice and effect settings from config/jarvis_voice.json.
    """

    def __init__(
        self,
        voice: str | None = None,
        jarvis_effect: bool | None = None,
    ):
        cfg = _get_jarvis_config()
        self.voice = voice or cfg.get("voice", "en-GB-RyanNeural")
        self.jarvis_effect = jarvis_effect if jarvis_effect is not None else cfg.get("jarvis_effect", True)

    def speak(self, text: str) -> None:
        loop = asyncio.new_event_loop()
        try:
            audio_bytes = loop.run_until_complete(self._synth(text))
        finally:
            loop.close()
        if audio_bytes:
            if self.jarvis_effect:
                # Decode then apply JARVIS post-processing
                import miniaudio
                decoded = miniaudio.decode(
                    audio_bytes,
                    output_format=miniaudio.SampleFormat.FLOAT32,
                    nchannels=1,
                )
                samples = np.array(decoded.samples, dtype=np.float32)
                samples = _jarvis_effect(samples, decoded.sample_rate)
                _play_np(samples, decoded.sample_rate)
            else:
                _play_audio_bytes(audio_bytes)

    async def _synth(self, text: str) -> bytes:
        import edge_tts
        comm = edge_tts.Communicate(text, self.voice)
        buf  = bytearray()
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                buf.extend(chunk["data"])
        return bytes(buf)


# ---------------------------------------------------------------------------
# Kokoro import helper — auto-upgrades on version-mismatch errors
# ---------------------------------------------------------------------------

# Errors that indicate the installed kokoro uses old transformers classes
# (AlbertModel, AutoModel) that are no longer exported at the top level.
_KOKORO_COMPAT_ERRORS = ("AlbertModel", "AutoModel", "cannot import name")


def _import_kokoro_pipeline():
    """Import KPipeline, auto-upgrading kokoro if a version mismatch is found.

    Old kokoro (<0.9) imports AlbertModel / AutoModel from transformers.
    Newer transformers versions no longer export these at the top level,
    causing an ImportError.  kokoro>=0.9 removed these dependencies.

    When the error is detected we:
      1. Upgrade kokoro to >=0.9 via pip (silent, background)
      2. Flush stale kokoro entries from sys.modules
      3. Re-import — this time it should succeed
    """
    import sys

    def _try_import():
        from kokoro import KPipeline  # noqa: PLC0415
        return KPipeline

    try:
        return _try_import()
    except Exception as first_err:
        err_msg = str(first_err)
        if not any(marker in err_msg for marker in _KOKORO_COMPAT_ERRORS):
            # Unrelated error (kokoro not installed, etc.)
            raise RuntimeError(
                f"Kokoro import failed: {first_err}\n"
                "Run: pip install kokoro>=0.9 soundfile"
            ) from first_err

        # ── Version mismatch: upgrade kokoro silently and retry ──────────
        print("[TTS] Kokoro/transformers version mismatch detected — upgrading kokoro…")
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "kokoro>=0.9",
             "--upgrade", "--quiet", "--disable-pip-version-check"],
            capture_output=True,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace").strip()
            raise RuntimeError(
                f"Kokoro auto-upgrade failed: {stderr[:200]}\n"
                "Run manually: pip install kokoro>=0.9 soundfile"
            ) from first_err

        # Flush any stale kokoro submodules from the import cache
        stale = [k for k in sys.modules if k == "kokoro" or k.startswith("kokoro.")]
        for key in stale:
            del sys.modules[key]

        print("[TTS] Kokoro upgraded — retrying import…")
        try:
            return _try_import()
        except Exception as retry_err:
            raise RuntimeError(
                f"Kokoro still broken after upgrade: {retry_err}\n"
                "Run manually: pip install --upgrade kokoro transformers"
            ) from retry_err


# Kokoro voice prefix → KPipeline lang_code mapping
_KOKORO_LANG_CODES = {
    "a": "a",   # American English  (af_*, am_*)
    "b": "b",   # British English   (bf_*, bm_*)
    "j": "j",   # Japanese          (jf_*, jm_*)
    "z": "z",   # Mandarin Chinese  (zf_*, zm_*)
    "s": "s",   # Spanish           (sf_*, sm_*)
    "f": "f",   # French            (ff_*, fm_*)
    "h": "h",   # Hindi             (hf_*, hm_*)
    "i": "i",   # Italian           (if_*, im_*)
    "p": "p",   # Brazilian Portuguese
    "r": "r",   # Russian           (rf_*, rm_*)
    "e": "e",   # German            (ef_*, em_*)
}


class KokoroTTSEngine:
    """Fully offline Kokoro neural TTS.

    Model (~330 MB) is downloaded from HuggingFace on first use,
    then cached locally — subsequent starts load from disk.

    Warmup strategy: _init() runs synchronously in the background
    _do_tts() thread (not the UI thread).  After the pipeline loads,
    a dummy inference compiles the PyTorch JIT graph immediately so
    the first real speak() call has zero compilation overhead.
    """

    def __init__(self, voice: str = "af_heart", speed: float = 1.0):
        self.voice     = voice
        self.speed     = speed
        self._pipeline = None
        self._lock     = threading.Lock()
        self._init()   # blocking, but called from background thread

    @property
    def _lang_code(self) -> str:
        prefix = self.voice[0].lower() if self.voice else "a"
        return _KOKORO_LANG_CODES.get(prefix, "a")

    def _init(self) -> None:
        if self._pipeline is not None:
            return

        lang = self._lang_code

        # Prefer GPU — Kokoro on CUDA is ~10x faster than CPU.
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            if device == "cpu":
                import os as _os
                n_threads = max(1, min(4, (_os.cpu_count() or 4) // 2))
                try:
                    torch.set_num_threads(n_threads)
                    torch.set_num_interop_threads(2)
                except RuntimeError:
                    pass
                print(
                    f"[TTS] Kokoro on CPU — for faster speech install CUDA PyTorch:\n"
                    "      pip install torch --index-url https://download.pytorch.org/whl/cu118"
                )
        except Exception:
            device = "cpu"

        print(f"[TTS] Kokoro — loading (lang='{lang}', device='{device}')…")

        KPipeline = _import_kokoro_pipeline()

        def _create_pipeline():
            try:
                return KPipeline(lang_code=lang, device=device)
            except TypeError:
                return KPipeline(lang_code=lang)   # older build — no device param

        try:
            self._pipeline = _create_pipeline()
        except Exception as _first_err:
            # Offline flag set but model not cached yet → clear flags and download once.
            # Keywords cover multiple huggingface_hub error message variants across versions.
            _e = str(_first_err).lower()
            _offline_keywords = (
                "offline", "not found", "cache", "localentry",
                "does not exist", "outgoing", "local_files_only",
            )
            if any(k in _e for k in _offline_keywords):
                print("[TTS] Kokoro model not in local cache — downloading (one-time, internet required)…")
                os.environ.pop("HF_HUB_OFFLINE",      None)
                os.environ.pop("TRANSFORMERS_OFFLINE", None)
                os.environ.pop("HF_DATASETS_OFFLINE",  None)
                try:
                    self._pipeline = _create_pipeline()
                except Exception as _dl_err:
                    raise RuntimeError(
                        f"Kokoro model download failed.\n"
                        f"Internet access is required the first time to download the voice model (~330 MB).\n"
                        f"After the first download it runs fully offline.\n"
                        f"Tip: Switch to EdgeTTS (free, no download) in the Configure panel if offline.\n"
                        f"Details: {_dl_err}"
                    ) from _dl_err
            else:
                raise

        print("[TTS] Kokoro compiling (first-time only)…")
        # Warmup: compiles PyTorch JIT graph so first real speak() call is instant.
        try:
            for _ in self._pipeline("hello", voice=self.voice, speed=self.speed):
                pass
            print("[TTS] Kokoro ready.")
        except Exception as e:
            print(f"[TTS] Kokoro warmup warning: {e}")

    def speak(self, text: str) -> None:
        with self._lock:
            if self._pipeline is None:
                self._init()

        # ── Concurrent synthesise + playback ────────────────────────────────
        # Kokoro generates audio chunks lazily.  Without threading, we:
        #   synthesise chunk N → play N → synthesise N+1 → play N+1 …
        # With a producer/consumer pair, chunk N+1 synthesises WHILE chunk N
        # plays, cutting perceived latency by the playback duration of all but
        # the last chunk (typically 1-3 s on multi-sentence responses).
        audio_q: "_queue.Queue[np.ndarray | None]" = _queue.Queue(maxsize=4)
        synth_error: list[Exception] = []

        def _synth():
            try:
                for _, _, audio in self._pipeline(text, voice=self.voice, speed=self.speed):
                    if audio is not None:
                        arr = _to_numpy(audio)
                        arr = _compress_silence(arr)
                        if arr.size > 0:
                            audio_q.put(arr)          # blocks if player is slow (backpressure)
            except Exception as exc:
                synth_error.append(exc)
            finally:
                audio_q.put(None)                     # sentinel → player exits

        synth_thread = threading.Thread(target=_synth, daemon=True)
        synth_thread.start()

        # Player runs in this thread so sd.wait() doesn't block the synth thread.
        while True:
            arr = audio_q.get()
            if arr is None:
                break
            _play_np(arr, 24000)

        synth_thread.join()

        if synth_error:
            raise synth_error[0]


class ElevenLabsTTSEngine:
    """ElevenLabs cloud TTS – API key required."""

    def __init__(self, api_key: str, voice_id: str = "pNInz6obpgDQGcFmaJgB"):
        self.api_key  = api_key
        self.voice_id = voice_id

    def speak(self, text: str) -> None:
        import requests
        headers = {
            "xi-api-key":   self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text":     text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }
        resp = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}",
            json=payload, headers=headers, timeout=30,
        )
        resp.raise_for_status()
        _play_audio_bytes(resp.content)


# ---------------------------------------------------------------------------
# Thread-safe player wrapper
# ---------------------------------------------------------------------------

class TTSPlayer:
    """
    Wraps any *Engine. Exposes a blocking speak() method
    meant to be called from a dedicated background thread.
    """

    def __init__(self, engine):
        self._engine  = engine
        self._playing = False
        self._lock    = threading.Lock()

    @property
    def is_playing(self) -> bool:
        return self._playing

    def speak(
        self,
        text:     str,
        on_start: Optional[Callable] = None,
        on_done:  Optional[Callable] = None,
    ) -> None:
        """Synthesise and play text. BLOCKING – call from a dedicated thread."""
        try:
            with self._lock:
                self._playing = True
            if on_start:
                on_start()
            self._engine.speak(text)
        except Exception as e:
            print(f"[TTS] Error: {e}")
        finally:
            with self._lock:
                self._playing = False
            if on_done:
                on_done()

    def stop(self) -> None:
        sd.stop()
        with self._lock:
            self._playing = False


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_tts_player(config: dict) -> TTSPlayer:
    engine_name = config.get("tts_engine", "edgetts").lower()
    if engine_name == "kokoro":
        voice  = config.get("tts_voice", "af_heart")
        speed  = float(config.get("tts_speed", 1.0))
        engine = KokoroTTSEngine(voice=voice, speed=speed)
    elif engine_name == "elevenlabs":
        api_key  = config.get("elevenlabs_api_key", "")
        voice_id = config.get("tts_voice", "pNInz6obpgDQGcFmaJgB")
        engine   = ElevenLabsTTSEngine(api_key=api_key, voice_id=voice_id)
    else:   # edgetts (default — JARVIS voice)
        # Force reload config to pick up latest settings
        reload_jarvis_config()
        jarvis_cfg = _get_jarvis_config()
        voice      = config.get("tts_voice") or jarvis_cfg.get("voice", "en-GB-RyanNeural")
        jarvis     = config.get("jarvis_effect") if "jarvis_effect" in config else jarvis_cfg.get("jarvis_effect", True)
        engine     = EdgeTTSEngine(voice=voice, jarvis_effect=jarvis)
    return TTSPlayer(engine)
