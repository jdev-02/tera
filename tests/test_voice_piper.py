"""Tests for voice/piper_client.py and voice/tts.py.

These mock the actual Piper synth (slow, large model) so they run in <1s
without requiring the .onnx file to be present. A separate manual smoke
test (run by Jon Sat 2200, not in CI) verifies real synth on the Jetson.
"""

from __future__ import annotations

import base64
import io
import wave
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from voice import piper_client, tts


@pytest.fixture(autouse=True)
def _reset_piper_singleton() -> Iterator[None]:
    piper_client.reset_piper()
    yield
    piper_client.reset_piper()


def _fake_piper_voice(sample_rate: int = 22050) -> MagicMock:
    """A MagicMock that quacks like piper.PiperVoice."""
    voice = MagicMock()
    voice.config = MagicMock(sample_rate=sample_rate)

    # synthesize_wav writes silent PCM frames into the wave file so the wrapper's
    # io.BytesIO ends up with a structurally-valid WAV. Accepts syn_config kwarg
    # because piper-tts >=1.3 wrapper passes one in.
    def _synth_wav(text: str, wav_writer: wave.Wave_write, syn_config: object = None) -> None:
        n_frames = max(1000, len(text) * 100)
        wav_writer.writeframes(b"\x00\x00" * n_frames)

    voice.synthesize_wav = MagicMock(side_effect=_synth_wav)
    return voice


def test_is_available_false_when_no_model(tmp_path: Path) -> None:
    """If the model file doesn't exist, is_available() returns False even if piper is installed."""
    client = piper_client.PiperClient(model_path=tmp_path / "missing.onnx")
    # is_available() requires both the package AND the model file. Whether
    # piper is importable depends on the test env; we just check the model
    # missing case returns False regardless.
    assert client.is_available() is False


def test_load_raises_when_model_missing(tmp_path: Path) -> None:
    client = piper_client.PiperClient(model_path=tmp_path / "missing.onnx")
    with (
        patch.dict("sys.modules", {"piper": MagicMock()}),
        pytest.raises(RuntimeError, match="not found"),
    ):
        client.load()


def test_synthesize_wav_returns_valid_wav_bytes(tmp_path: Path) -> None:
    """Mock PiperVoice.synthesize_wav. Assert the wrapper produces a valid WAV."""
    fake_model = tmp_path / "fake.onnx"
    fake_model.touch()  # exist check passes

    fake_voice = _fake_piper_voice(sample_rate=22050)
    fake_module = MagicMock()
    fake_module.PiperVoice.load.return_value = fake_voice

    with patch.dict("sys.modules", {"piper": fake_module}):
        client = piper_client.PiperClient(model_path=fake_model)
        wav_bytes = client.synthesize_wav("hello operator")

    # Validate: WAV header magic + readable via wave module.
    assert wav_bytes[:4] == b"RIFF"
    assert wav_bytes[8:12] == b"WAVE"
    with wave.open(io.BytesIO(wav_bytes), "rb") as r:
        assert r.getnchannels() == 1
        assert r.getsampwidth() == 2
        assert r.getframerate() == 22050


def test_synthesize_wav_tries_legacy_method_name(tmp_path: Path) -> None:
    """Older piper-tts versions exposed `synthesize`, not `synthesize_wav`.
    Wrapper falls back to it. (Defensive against version drift.)"""
    fake_model = tmp_path / "fake.onnx"
    fake_model.touch()

    voice = MagicMock()
    voice.config = MagicMock(sample_rate=16000)

    # Drop the new-style method so the wrapper falls back to old style.
    del voice.synthesize_wav

    def _legacy_synth(text: str, wav_writer: wave.Wave_write, syn_config: object = None) -> None:
        wav_writer.writeframes(b"\x00\x00" * 100)

    voice.synthesize = MagicMock(side_effect=_legacy_synth)

    fake_module = MagicMock()
    fake_module.PiperVoice.load.return_value = voice

    with patch.dict("sys.modules", {"piper": fake_module}):
        client = piper_client.PiperClient(model_path=fake_model)
        wav_bytes = client.synthesize_wav("hello")

    voice.synthesize.assert_called_once()
    assert wav_bytes[:4] == b"RIFF"


def test_get_piper_singleton() -> None:
    a = piper_client.get_piper()
    b = piper_client.get_piper()
    assert a is b


# ---------------------------------------------------------------------------
# voice.tts -- glue layer
# ---------------------------------------------------------------------------


def test_synthesize_rationale_returns_none_for_empty() -> None:
    assert tts.synthesize_rationale_b64("") is None


def test_synthesize_rationale_returns_none_when_piper_unavailable() -> None:
    """If Piper isn't available, return None and let the orchestrator fall back."""
    fake_client = MagicMock()
    fake_client.is_available.return_value = False
    with patch("voice.tts.get_piper", return_value=fake_client):
        result = tts.synthesize_rationale_b64("Routed to Lobos Creek, 2.1 km.")
    assert result is None
    fake_client.synthesize_wav.assert_not_called()


def test_synthesize_rationale_b64_calls_piper_with_cadence(tmp_path: Path) -> None:
    """When Piper IS available, the rationale is cadence-transformed first
    THEN synthesized -- not the raw English."""
    fake_client = MagicMock()
    fake_client.is_available.return_value = True
    fake_client.synthesize_wav.return_value = b"RIFF\x00\x00\x00\x00WAVEfake"

    with patch("voice.tts.get_piper", return_value=fake_client):
        result = tts.synthesize_rationale_b64(
            "Routed to Lobos Creek, distance 2.1 km, ETA 38 minutes."
        )

    assert result is not None
    decoded = base64.b64decode(result)
    assert decoded.startswith(b"RIFF")

    # Verify Piper got the cadence-transformed text, not the raw English.
    call_args = fake_client.synthesize_wav.call_args
    spoken_text = call_args.args[0] if call_args.args else call_args.kwargs.get("text", "")
    assert "two point one" in spoken_text
    assert "three eight" in spoken_text
    assert "kilometers" in spoken_text
    # Raw forms should be GONE from the spoken text.
    assert "2.1" not in spoken_text
    assert "38 minutes" not in spoken_text


def test_synthesize_rationale_swallows_synth_errors() -> None:
    """If Piper raises during synth, return None -- never propagate to /plan caller."""
    fake_client = MagicMock()
    fake_client.is_available.return_value = True
    fake_client.synthesize_wav.side_effect = RuntimeError("synth boom")

    with patch("voice.tts.get_piper", return_value=fake_client):
        result = tts.synthesize_rationale_b64("anything")
    assert result is None
