"""Wrapper around `piper-tts` for offline text -> WAV synthesis.

Why a wrapper:
- Lazy load. The Piper voice model takes ~500ms to load. We do it once at
  process startup, not per request.
- Defensive imports. The `piper-tts` package is in the [voice] optional
  extra. Machines without it (e.g., CI on a path that doesn't run voice
  tests) shouldn't crash on import.
- Graceful degradation. If Piper or the voice model isn't available,
  return None from synth calls; the orchestrator falls back to text-only.
- Synthesis params. Operator cadence wants slower speech, normalized
  volume, and a small inter-sentence pause -- this module owns those
  defaults so downstream callers don't think about them.

Usage::

    client = get_piper()  # lazy singleton
    if client.is_available():
        wav_bytes = client.synthesize_wav("Hello operator")

This module never exits the process or raises on missing voice -- a degraded
TTS path is better than no /plan response. The orchestrator decides whether
to require audio (which it does NOT in MVP).
"""

from __future__ import annotations

import io
import os
import wave
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger(__name__)


# Default voice model. Override via PIPER_MODEL_PATH env var.
_DEFAULT_VOICE = "en_US-libritts_r-medium"
_DEFAULT_DIR = Path(__file__).resolve().parent.parent / "models" / "piper"

# Synthesis defaults tuned for operator cadence:
#   length_scale > 1.0 -> slower speech (1.15 = ~15% slower than default).
#   sentence_silence_s -> pause inserted between sentences (Piper inserts
#     this when it sees sentence-ending punctuation).
#   volume = 1.0 -> no attenuation. Normalize handles peak limiting.
_DEFAULT_LENGTH_SCALE = 1.15  # slow down ~15% for operator pacing
_DEFAULT_NOISE_SCALE = 0.667  # piper default; controls vocal variation
_DEFAULT_NOISE_W_SCALE = 0.8  # piper default; controls phoneme duration jitter
_DEFAULT_SENTENCE_SILENCE_S = 0.35
_DEFAULT_VOLUME = 1.0


def _resolve_model_path() -> Path:
    """Locate the voice .onnx file, prefer env override."""
    explicit = os.environ.get("PIPER_MODEL_PATH")
    if explicit:
        return Path(explicit)
    voice = os.environ.get("PIPER_VOICE", _DEFAULT_VOICE)
    return _DEFAULT_DIR / f"{voice}.onnx"


class PiperClient:
    """Thin wrapper around piper-tts. Holds a single loaded voice."""

    def __init__(
        self,
        model_path: str | Path | None = None,
        length_scale: float = _DEFAULT_LENGTH_SCALE,
        noise_scale: float = _DEFAULT_NOISE_SCALE,
        noise_w_scale: float = _DEFAULT_NOISE_W_SCALE,
        sentence_silence_s: float = _DEFAULT_SENTENCE_SILENCE_S,
        volume: float = _DEFAULT_VOLUME,
    ) -> None:
        self.model_path = Path(model_path) if model_path else _resolve_model_path()
        self.length_scale = length_scale
        self.noise_scale = noise_scale
        self.noise_w_scale = noise_w_scale
        self.sentence_silence_s = sentence_silence_s
        self.volume = volume
        self._voice: Any | None = None
        self._sample_rate: int = 22050  # default; overridden when voice loads

    def is_available(self) -> bool:
        """True if piper-tts is installed AND the voice model exists. Fast check."""
        try:
            import piper  # noqa: F401
        except ImportError:
            return False
        return self.model_path.exists()

    def load(self) -> None:
        """Load the voice model. Idempotent. Raises if piper or model missing."""
        if self._voice is not None:
            return
        try:
            from piper import PiperVoice
        except ImportError as e:
            raise RuntimeError("piper-tts not installed; run: make install-voice") from e
        if not self.model_path.exists():
            raise RuntimeError(
                f"Piper voice model not found at {self.model_path}. "
                "Run the voice-model download in setup."
            )
        self._voice = PiperVoice.load(str(self.model_path))
        # Pull sample rate from the voice's config -- different voices use
        # different rates (16k for low-quality, 22050 for medium).
        cfg = getattr(self._voice, "config", None)
        if cfg is not None and hasattr(cfg, "sample_rate"):
            self._sample_rate = int(cfg.sample_rate)
        log.info(
            "piper_voice_loaded",
            model_path=str(self.model_path),
            sample_rate=self._sample_rate,
        )

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def _build_syn_config(self, length_scale: float | None = None) -> Any | None:
        """Build a piper.SynthesisConfig if available, else None.

        piper-tts >=1.3 exposes SynthesisConfig with length_scale, volume,
        noise params, and sentence_silence. Older versions don't have it,
        so we return None and let the synth use library defaults.
        """
        try:
            from piper import SynthesisConfig
        except ImportError:
            return None
        return SynthesisConfig(
            length_scale=length_scale if length_scale is not None else self.length_scale,
            noise_scale=self.noise_scale,
            noise_w_scale=self.noise_w_scale,
            volume=self.volume,
        )

    def synthesize_wav(self, text: str, length_scale: float | None = None) -> bytes:
        """Synthesize the given text and return WAV bytes.

        Args:
            text: input text. Sentence-ending punctuation triggers Piper's
                  inter-sentence silence pause.
            length_scale: optional override of the configured pace. Higher
                  values mean slower speech (1.0 = default Piper, 1.15 =
                  operator cadence, 1.3 = very slow).

        Raises RuntimeError if Piper isn't available or model isn't loaded
        (call .is_available() first to gate).
        """
        self.load()
        assert self._voice is not None  # post-condition of self.load()

        syn_config = self._build_syn_config(length_scale)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)  # 16-bit PCM
            wav.setframerate(self._sample_rate)
            # Piper API note: synthesize_wav writes raw PCM frames into the
            # wave file in chunks. The piper-tts package version >=1.4 exposes
            # `synthesize_wav(text, wav_writer)` directly. Older versions used
            # `synthesize(text, wav_writer)`. Try both; fall back gracefully.
            # syn_config is passed when available; older versions ignore it.
            if hasattr(self._voice, "synthesize_wav"):
                if syn_config is not None:
                    self._voice.synthesize_wav(text, wav, syn_config=syn_config)
                else:
                    self._voice.synthesize_wav(text, wav)
            elif hasattr(self._voice, "synthesize"):
                if syn_config is not None:
                    self._voice.synthesize(text, wav, syn_config=syn_config)
                else:
                    self._voice.synthesize(text, wav)
            else:
                raise RuntimeError(
                    "PiperVoice has neither synthesize_wav nor synthesize -- "
                    "unsupported piper-tts version"
                )
        return buf.getvalue()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_client: PiperClient | None = None


def get_piper() -> PiperClient:
    """Lazy singleton. Most callers want this."""
    global _client
    if _client is None:
        _client = PiperClient()
    return _client


def reset_piper() -> None:
    """For tests."""
    global _client
    _client = None
