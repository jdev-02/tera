"""Tests for voice/audio_fx.py.

We don't try to test 'sounds like a soldier' -- that's subjective. We DO
test:
  - WAV in / WAV out, same sample rate, same length, mono 16-bit
  - 'clean' is exact pass-through (no float drift)
  - 'comms' band-pass actually attenuates out-of-band energy
  - Compressor reduces dynamic range
  - Errors raise on malformed inputs
  - Deterministic output when seed is provided

Spectrogram-based test uses numpy FFT only -- no scipy dependency.
"""

from __future__ import annotations

import io
import wave

import numpy as np
import pytest

from voice.audio_fx import apply_radio_fx

# ---------------------------------------------------------------------------
# Helpers: synthesize a known test signal
# ---------------------------------------------------------------------------


def _make_wav(samples: np.ndarray, sr: int = 22050) -> bytes:
    """Encode float samples in [-1, 1] to 16-bit PCM mono WAV bytes."""
    int_samples = (np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(int_samples.tobytes())
    return buf.getvalue()


def _read_wav(wav_bytes: bytes) -> tuple[np.ndarray, int]:
    with wave.open(io.BytesIO(wav_bytes), "rb") as r:
        sr = r.getframerate()
        raw = r.readframes(r.getnframes())
    samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    return samples, sr


def _band_energy(samples: np.ndarray, sr: int, low_hz: float, high_hz: float) -> float:
    """RMS energy in [low_hz, high_hz] via FFT. Returns dB-relative-full-scale."""
    n = len(samples)
    spec = np.abs(np.fft.rfft(samples)) ** 2
    freqs = np.fft.rfftfreq(n, d=1.0 / sr)
    mask = (freqs >= low_hz) & (freqs <= high_hz)
    energy = float(spec[mask].sum())
    if energy <= 0:
        return -200.0
    return 10.0 * np.log10(energy / max(1, mask.sum()))


# ---------------------------------------------------------------------------
# Structural tests
# ---------------------------------------------------------------------------


def test_clean_is_pass_through() -> None:
    sr = 22050
    sig = (np.random.default_rng(42).standard_normal(sr) * 0.3).astype(np.float32)
    in_wav = _make_wav(sig, sr)
    out_wav = apply_radio_fx(in_wav, intensity="clean")
    assert in_wav == out_wav, "'clean' must be byte-for-byte pass-through"


@pytest.mark.parametrize("intensity", ["light", "comms", "degraded"])
def test_output_is_valid_mono_wav(intensity: str) -> None:
    sr = 22050
    sig = np.sin(2 * np.pi * 1000 * np.arange(sr) / sr).astype(np.float32) * 0.5
    out = apply_radio_fx(_make_wav(sig, sr), intensity=intensity)  # type: ignore[arg-type]
    assert out[:4] == b"RIFF"
    assert out[8:12] == b"WAVE"
    samples, sr_out = _read_wav(out)
    assert sr_out == sr, "sample rate must be preserved"
    assert len(samples) == len(sig), "sample count must be preserved"


def test_rejects_stereo_input() -> None:
    """Piper output is mono; FX explicitly requires mono."""
    sr = 22050
    samples = np.zeros(sr * 2, dtype=np.float32)
    int_s = (samples * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(2)  # stereo!
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(int_s.tobytes())
    with pytest.raises(ValueError, match="mono"):
        apply_radio_fx(buf.getvalue(), intensity="comms")


def test_rejects_8bit_input() -> None:
    sr = 22050
    samples = np.zeros(sr, dtype=np.uint8) + 128  # silence at midpoint for 8-bit
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)  # 8-bit!
        w.setframerate(sr)
        w.writeframes(samples.tobytes())
    with pytest.raises(ValueError, match="16-bit"):
        apply_radio_fx(buf.getvalue(), intensity="comms")


# ---------------------------------------------------------------------------
# Spectrogram sanity tests
# ---------------------------------------------------------------------------


def test_comms_attenuates_low_band() -> None:
    """A 100 Hz tone (well below 300 Hz cutoff) should be heavily attenuated
    under 'comms' intensity. 4th-order Butterworth at 1.5 octaves below
    cutoff: theoretical -36 dB; we ask for >= 18 dB observed (conservative)."""
    sr = 22050
    t = np.arange(sr) / sr
    sig = np.sin(2 * np.pi * 100 * t).astype(np.float32) * 0.5
    in_wav = _make_wav(sig, sr)
    clean_samples, _ = _read_wav(in_wav)
    comms_samples, _ = _read_wav(apply_radio_fx(in_wav, intensity="comms"))

    e_clean = _band_energy(clean_samples, sr, 80, 200)
    e_comms = _band_energy(comms_samples, sr, 80, 200)
    assert e_comms < e_clean - 18, (
        f"comms FX did not attenuate 100 Hz tone: clean={e_clean:.1f} dB, comms={e_comms:.1f} dB"
    )


def test_comms_attenuates_high_band() -> None:
    """A 6 kHz tone (~0.8 octaves above 3.4 kHz cutoff) should be
    measurably attenuated. Theoretical Butterworth -19 dB; we ask for
    >= 10 dB observed which is comfortably above the engineering floor."""
    sr = 22050
    t = np.arange(sr) / sr
    sig = np.sin(2 * np.pi * 6000 * t).astype(np.float32) * 0.5
    in_wav = _make_wav(sig, sr)
    clean_samples, _ = _read_wav(in_wav)
    comms_samples, _ = _read_wav(apply_radio_fx(in_wav, intensity="comms"))

    e_clean = _band_energy(clean_samples, sr, 5500, 6500)
    e_comms = _band_energy(comms_samples, sr, 5500, 6500)
    assert e_comms < e_clean - 10, (
        f"comms FX did not attenuate 6 kHz tone: clean={e_clean:.1f} dB, comms={e_comms:.1f} dB"
    )


def test_comms_passes_voice_band() -> None:
    """A 1 kHz tone (squarely inside 300-3400 Hz comms band) should be
    largely preserved -- the FX adds a compressor and band-pass ripple,
    so we allow up to 10 dB drop (well below 'attenuated')."""
    sr = 22050
    t = np.arange(sr) / sr
    sig = np.sin(2 * np.pi * 1000 * t).astype(np.float32) * 0.5
    in_wav = _make_wav(sig, sr)
    clean_samples, _ = _read_wav(in_wav)
    comms_samples, _ = _read_wav(apply_radio_fx(in_wav, intensity="comms"))

    e_clean = _band_energy(clean_samples, sr, 900, 1100)
    e_comms = _band_energy(comms_samples, sr, 900, 1100)
    assert e_comms > e_clean - 10, (
        f"comms FX over-attenuated 1 kHz tone: clean={e_clean:.1f} dB, comms={e_comms:.1f} dB"
    )


def test_degraded_seed_is_deterministic() -> None:
    """Same seed -> same noise -> same bytes. Required for stable tests + audit."""
    sr = 22050
    sig = np.sin(2 * np.pi * 1000 * np.arange(sr) / sr).astype(np.float32) * 0.3
    in_wav = _make_wav(sig, sr)
    a = apply_radio_fx(in_wav, intensity="degraded", seed=42)
    b = apply_radio_fx(in_wav, intensity="degraded", seed=42)
    assert a == b, "seeded degraded output must be deterministic"


def test_compressor_reduces_dynamic_range_on_amplitude_modulation() -> None:
    """An amplitude-modulated 1 kHz tone (in-band, so band-pass passes it)
    has predictable dynamic range. Compressor should reduce the difference
    between the loud and quiet halves."""
    sr = 22050
    n = sr
    t = np.arange(n) / sr
    carrier = np.sin(2 * np.pi * 1000 * t).astype(np.float32)
    # First half quiet (0.1), second half loud (0.7).
    envelope = np.concatenate(
        [np.full(n // 2, 0.1, dtype=np.float32), np.full(n - n // 2, 0.7, dtype=np.float32)]
    )
    sig = carrier * envelope
    in_wav = _make_wav(sig, sr)
    out_samples, _ = _read_wav(apply_radio_fx(in_wav, intensity="comms"))

    # RMS of the loud half / RMS of the quiet half should be smaller after
    # compression.
    half = n // 2
    in_ratio = float(np.sqrt(np.mean(sig[half:] ** 2)) / np.sqrt(np.mean(sig[:half] ** 2)))
    out_ratio = float(
        np.sqrt(np.mean(out_samples[half:] ** 2))
        / max(1e-9, np.sqrt(np.mean(out_samples[:half] ** 2)))
    )
    assert out_ratio < in_ratio, (
        f"compressor failed to compress dynamic range: "
        f"in_ratio={in_ratio:.2f}, out_ratio={out_ratio:.2f}"
    )
