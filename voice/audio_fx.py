"""Radio-comms post-processing FX for Piper TTS output.

Why: a stock TTS voice sounds like a TTS voice. The difference between
a clean voice and 'a soldier on net' is mostly the **gear**, not the
voice -- band-limited audio (300-3400 Hz, classic radio bandwidth),
slight compression, and barely-perceptible noise floor.

Implementation is pure numpy -- no scipy dependency, no extra MB on the
Jetson. Uses a 4th-order Butterworth band-pass realized as cascaded
biquads. Single-pass, low-latency, runs in real-time on Piper's output.

Usage::

    from voice.audio_fx import apply_radio_fx
    cleaned_wav = apply_radio_fx(wav_bytes, intensity="comms")

Intensities (dial-tunable for #54 severity routing):
    clean    -- pass-through, no FX (sanity check / control)
    light    -- subtle band-pass, full bandwidth retained at edges
    comms    -- 300-3400 Hz hard band-pass, light compression  [default]
    degraded -- comms + slight noise floor + harder compression

Test note: this module's correctness is checked by spectrogram
sanity tests (energy outside the band drops by N dB, RMS within
expected range). We don't try to test 'sounds like a soldier'.
"""

from __future__ import annotations

import io
import math
import wave
from typing import Literal

import numpy as np

Intensity = Literal["clean", "light", "comms", "degraded"]


# ---------------------------------------------------------------------------
# Biquad filter primitives (Direct Form II Transposed)
# ---------------------------------------------------------------------------


def _biquad_coeffs_lp(fc: float, q: float, sr: int) -> tuple[np.ndarray, np.ndarray]:
    """Low-pass biquad coefficients (RBJ cookbook)."""
    w = 2 * math.pi * fc / sr
    cosw, sinw = math.cos(w), math.sin(w)
    alpha = sinw / (2 * q)
    b0 = (1 - cosw) / 2
    b1 = 1 - cosw
    b2 = (1 - cosw) / 2
    a0 = 1 + alpha
    a1 = -2 * cosw
    a2 = 1 - alpha
    b = np.array([b0, b1, b2]) / a0
    a = np.array([1.0, a1 / a0, a2 / a0])
    return b, a


def _biquad_coeffs_hp(fc: float, q: float, sr: int) -> tuple[np.ndarray, np.ndarray]:
    """High-pass biquad coefficients (RBJ cookbook)."""
    w = 2 * math.pi * fc / sr
    cosw, sinw = math.cos(w), math.sin(w)
    alpha = sinw / (2 * q)
    b0 = (1 + cosw) / 2
    b1 = -(1 + cosw)
    b2 = (1 + cosw) / 2
    a0 = 1 + alpha
    a1 = -2 * cosw
    a2 = 1 - alpha
    b = np.array([b0, b1, b2]) / a0
    a = np.array([1.0, a1 / a0, a2 / a0])
    return b, a


def _biquad_apply(samples: np.ndarray, b: np.ndarray, a: np.ndarray) -> np.ndarray:
    """Direct Form II Transposed. y[n] = b0*x[n] + z1[n-1]; ...

    Vectorized over the input but inherently sequential per-sample due to
    feedback. Pure-Python loop is fast enough at 22050 Hz Piper output.
    """
    y = np.empty_like(samples, dtype=np.float64)
    z1 = z2 = 0.0
    b0, b1, b2 = b
    _, a1, a2 = a
    for n, x in enumerate(samples):
        out = b0 * x + z1
        z1 = b1 * x - a1 * out + z2
        z2 = b2 * x - a2 * out
        y[n] = out
    return y


def _bandpass(samples: np.ndarray, low_hz: float, high_hz: float, sr: int) -> np.ndarray:
    """4th-order Butterworth band-pass via two cascaded biquads (HP -> LP).

    Q = 0.7071 for Butterworth response.
    """
    q = 0.7071
    b_hp, a_hp = _biquad_coeffs_hp(low_hz, q, sr)
    b_lp, a_lp = _biquad_coeffs_lp(high_hz, q, sr)
    out = _biquad_apply(samples, b_hp, a_hp)
    return _biquad_apply(out, b_lp, a_lp)


# ---------------------------------------------------------------------------
# Compressor + noise floor
# ---------------------------------------------------------------------------


def _compress(samples: np.ndarray, threshold_db: float, ratio: float) -> np.ndarray:
    """Soft-knee downward compressor. Reduces dynamic range so loud peaks
    don't dominate -- gives the 'radio-tight' sound."""
    threshold = 10 ** (threshold_db / 20)
    abs_s = np.abs(samples)
    over = np.where(abs_s > threshold, abs_s, threshold)
    gain = (threshold + (over - threshold) / ratio) / over
    return samples * gain


def _add_noise_floor(samples: np.ndarray, level_db: float, rng: np.random.Generator) -> np.ndarray:
    """Add a barely-audible white-noise floor for the 'live mic' feel."""
    amp = 10 ** (level_db / 20)
    noise = rng.standard_normal(len(samples)).astype(np.float32) * amp
    out: np.ndarray = samples + noise
    return out


# ---------------------------------------------------------------------------
# WAV I/O helpers
# ---------------------------------------------------------------------------


def _wav_to_float(wav_bytes: bytes) -> tuple[np.ndarray, int]:
    """Decode a 16-bit PCM mono WAV into float32 samples in [-1, 1] and sr."""
    with wave.open(io.BytesIO(wav_bytes), "rb") as r:
        if r.getnchannels() != 1:
            raise ValueError("apply_radio_fx expects mono WAV (Piper outputs mono)")
        if r.getsampwidth() != 2:
            raise ValueError("apply_radio_fx expects 16-bit PCM")
        sr = r.getframerate()
        raw = r.readframes(r.getnframes())
    samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    return samples, sr


def _float_to_wav(samples: np.ndarray, sr: int) -> bytes:
    """Encode float samples [-1, 1] back to 16-bit PCM mono WAV."""
    clipped = np.clip(samples, -1.0, 1.0)
    int_samples = (clipped * 32767.0).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(int_samples.tobytes())
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


_PROFILES: dict[Intensity, dict[str, float]] = {
    "clean": {},
    "light": {
        "low_hz": 200,
        "high_hz": 5000,
        "compress_threshold_db": -18,
        "compress_ratio": 2.0,
    },
    "comms": {
        "low_hz": 300,
        "high_hz": 3400,
        "compress_threshold_db": -20,
        "compress_ratio": 4.0,
    },
    "degraded": {
        "low_hz": 400,
        "high_hz": 3000,
        "compress_threshold_db": -22,
        "compress_ratio": 6.0,
        "noise_db": -50,
    },
}


def apply_radio_fx(
    wav_bytes: bytes,
    intensity: Intensity = "comms",
    seed: int | None = None,
) -> bytes:
    """Apply radio-comms FX to a Piper WAV. Returns a new WAV.

    Args:
        wav_bytes: 16-bit PCM mono WAV input (Piper output).
        intensity: 'clean' (no-op), 'light', 'comms' (default), 'degraded'.
        seed: optional RNG seed for deterministic noise floor (tests).

    Returns:
        16-bit PCM mono WAV bytes, same sample rate as input.
    """
    if intensity == "clean":
        return wav_bytes

    profile = _PROFILES[intensity]
    samples, sr = _wav_to_float(wav_bytes)

    samples = _bandpass(samples, profile["low_hz"], profile["high_hz"], sr)
    samples = _compress(samples, profile["compress_threshold_db"], profile["compress_ratio"])

    if "noise_db" in profile:
        rng = np.random.default_rng(seed) if seed is not None else np.random.default_rng()
        samples = _add_noise_floor(samples, profile["noise_db"], rng)

    return _float_to_wav(samples, sr)
