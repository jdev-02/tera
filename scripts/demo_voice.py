"""Quick voice-out demo. Writes a WAV of the canonical PRD rationale to disk
and prints a one-liner to play it on macOS. For Jon's pre-demo smoke test.

    python scripts/demo_voice.py
    afplay /tmp/tera_demo.wav
"""

from __future__ import annotations

import base64
import sys
import tempfile
from pathlib import Path

from voice.piper_client import get_piper
from voice.rationale import to_operator_cadence
from voice.tts import synthesize_rationale_b64


def main() -> int:
    rationale = (
        "Routed to Lobos Creek, distance 2.1 kilometers, "
        "ETA 38 minutes on foot covered."
    )
    if len(sys.argv) > 1:
        rationale = " ".join(sys.argv[1:])

    print(f"input:    {rationale}")
    print(f"cadence:  {to_operator_cadence(rationale)}")

    client = get_piper()
    if not client.is_available():
        print("ERROR: Piper not available. Run `make install-voice` and download the voice model.")
        return 1

    audio_b64 = synthesize_rationale_b64(rationale)
    if audio_b64 is None:
        print("ERROR: synthesis returned None.")
        return 1

    out = Path(tempfile.gettempdir()) / "tera_demo.wav"
    out.write_bytes(base64.b64decode(audio_b64))
    print(f"wrote:    {out} ({out.stat().st_size:,} bytes)")
    print(f"play:     afplay {out}  # macOS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
