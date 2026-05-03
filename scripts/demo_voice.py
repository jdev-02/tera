"""Voice-out listen-test harness.

Run interactively to evaluate Piper TTS quality across the phrase corpus
in voice/phrases.py. Plays each phrase, prints the cadence-transformed
input + a checklist of what to listen for, and lets you advance / repeat
/ adjust pace.

Usage
-----

  # Default: walk through every phrase, ops cadence (length_scale=1.15).
  python scripts/demo_voice.py

  # One phrase by id.
  python scripts/demo_voice.py --id prd-A

  # All phrases in one category.
  python scripts/demo_voice.py --category mgrs

  # Custom phrase from CLI.
  python scripts/demo_voice.py --text "Heading 030 for 2.5 kilometers."

  # Adjust pace. Higher = slower. 1.0 = piper default, 1.15 = ops, 1.3 = slow.
  python scripts/demo_voice.py --rate 1.25

  # Print-only (no audio) to dry-run the cadence transform.
  python scripts/demo_voice.py --dry-run

  # On-demand acronym explain (deterministic, no LLM):
  python scripts/demo_voice.py --explain HLZ
  python scripts/demo_voice.py --explain CASEVAC

  # List every term the glossary can explain:
  python scripts/demo_voice.py --explain-list

In interactive mode (default), at each phrase prompt:
  [Enter]   -> next phrase (no notes captured)
  r         -> replay current phrase
  s         -> slow down (length_scale +0.05)
  f         -> speed up (length_scale -0.05)
  q         -> quit and write notes file
  any text  -> save as a note for THIS phrase, then advance

At the end (or on q), notes are written to a markdown file in /tmp and the
path is printed. Paste that file back to chat to triage cadence fixes.

Listen-for checklist (printed once at start):
- clarity, pace, comma pause, sentence pause
- number disambiguation (5/9, 3/free, 2/to, 4/for)
- phonetic precision on MGRS letters
- stress on critical tokens (DANGER CLOSE, BREAK, BE ADVISED)
- compound cardinal smoothness (north-northeast)
- end-of-utterance clean stop, no clipping
"""

from __future__ import annotations

import argparse
import base64
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from voice.glossary import known_terms
from voice.phrases import PHRASES, by_category, by_id, categories
from voice.piper_client import get_piper, reset_piper
from voice.rationale import to_operator_cadence
from voice.tts import synthesize_explanation_b64, synthesize_rationale_b64

CHECKLIST = """
Listen-for checklist (operator-radio):
  [pace]      cadence slow enough to copy on the fly?
  [pause]     comma -> beat between MGRS halves; period -> sentence gap
  [numbers]   five vs nine, three vs free, two vs to, four vs for
  [phonetic]  sierra/mike/foxtrot crisp, not slurred
  [stress]    DANGER CLOSE / BREAK / BE ADVISED land with weight?
  [cardinal]  'north-northeast' smooth or weird?
  [end]       clean final stop, no clipped phoneme
  [volume]    no clipping on long phrases
"""


def _play(wav_path: Path) -> None:
    """Play a WAV file using whatever's on PATH. Cross-platform best effort.

    S603/S607 are suppressed because the args are fixed strings and we
    require the executable to exist on PATH (shutil.which check above).
    """
    cmd: list[str] | None = None
    if shutil.which("afplay"):  # macOS
        cmd = ["afplay", str(wav_path)]
    elif shutil.which("aplay"):  # linux
        cmd = ["aplay", "-q", str(wav_path)]
    elif shutil.which("ffplay"):  # ffmpeg
        cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(wav_path)]
    if cmd is None:
        print(f"  (no audio player on PATH; play manually: {wav_path})")
        return
    subprocess.run(cmd, check=False)  # noqa: S603


def _synth_to_tempfile(text: str, length_scale: float) -> Path | None:
    """Synthesize text and return path to a temp WAV. None if synth failed."""
    audio_b64 = synthesize_rationale_b64(text, length_scale=length_scale)
    if audio_b64 is None:
        return None
    out = Path(tempfile.mkstemp(prefix="tera_demo_", suffix=".wav")[1])
    out.write_bytes(base64.b64decode(audio_b64))
    return out


def _show_phrase(phrase: tuple[str, str, str, str]) -> None:
    pid, cat, text, listen_for = phrase
    print(f"\n[{pid}] ({cat})")
    print(f"  text:    {text}")
    print(f"  cadence: {to_operator_cadence(text)}")
    print(f"  listen:  {listen_for}")


def _write_notes(notes: list[tuple[str, str, str, str]], length_scale: float) -> Path:
    """Write captured notes to a timestamped markdown file. Returns the path.

    Format mirrors what's useful when triaging cadence rules: phrase id,
    category, the cadence-transformed text (so I can see what Piper actually
    received), and the operator's note.
    """
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # noqa: DTZ005 -- local time fine for filename
    out = Path(tempfile.gettempdir()) / f"tera_voice_notes_{stamp}.md"

    lines: list[str] = []
    lines.append(f"# TERA voice notes — {stamp}")
    lines.append("")
    lines.append(f"- length_scale (final): {length_scale:.2f}")
    lines.append(f"- phrases noted: {len(notes)}")
    lines.append("")
    if not notes:
        lines.append("_No notes captured. All phrases sounded clean._")
    else:
        lines.append("| id | category | cadence | note |")
        lines.append("|---|---|---|---|")
        for pid, cat, cadence, note in notes:
            # Escape pipes inside cadence/note for markdown table safety.
            cadence_safe = cadence.replace("|", "\\|")
            note_safe = note.replace("|", "\\|")
            lines.append(f"| `{pid}` | {cat} | {cadence_safe} | {note_safe} |")
    out.write_text("\n".join(lines) + "\n")
    return out


def _interactive_loop(phrases: list[tuple[str, str, str, str]], length_scale: float) -> int:
    """Walk through phrases. Returns exit code."""
    client = get_piper()
    if not client.is_available():
        print(
            "ERROR: Piper not available. Run `make install-voice` and "
            "ensure models/piper/en_US-libritts_r-medium.onnx exists."
        )
        return 1

    print(CHECKLIST)
    print(f"phrases: {len(phrases)}, starting length_scale={length_scale:.2f}")
    print("controls:")
    print("  [Enter]   -> next phrase (no note)")
    print("  r         -> replay")
    print("  s / f     -> slower / faster")
    print("  q         -> quit + write notes file")
    print("  any text  -> save as note for THIS phrase, then advance\n")

    notes: list[tuple[str, str, str, str]] = []  # (id, category, cadence, note)

    def _commands_help() -> None:
        print(
            "  -- single-char commands: r=replay s=slower f=faster q=quit; "
            "any other text becomes a note for this phrase --"
        )

    i = 0
    while i < len(phrases):
        phrase = phrases[i]
        pid, cat, raw_text, _ = phrase
        _show_phrase(phrase)

        wav = _synth_to_tempfile(raw_text, length_scale)
        if wav is None:
            print("  ! synth failed, skipping")
            i += 1
            continue

        _play(wav)
        wav.unlink(missing_ok=True)

        try:
            raw = input(f"  [{i + 1}/{len(phrases)}] note (or r/s/f/q, Enter=next) > ")
        except EOFError:
            print()
            break

        cmd = raw.strip()
        cmd_lower = cmd.lower()

        # Single-char commands.
        if cmd_lower == "q":
            break
        if cmd_lower == "r":
            continue
        if cmd_lower in ("s", "f"):
            delta = 0.05 if cmd_lower == "s" else -0.05
            length_scale = max(0.5, min(2.0, length_scale + delta))
            reset_piper()
            from voice import piper_client

            piper_client._client = piper_client.PiperClient(length_scale=length_scale)
            label = "slower" if cmd_lower == "s" else "faster"
            print(f"  -> length_scale {length_scale:.2f} ({label}); replaying")
            continue
        if cmd_lower in ("h", "help", "?"):
            _commands_help()
            continue

        # Empty Enter -> advance, no note.
        if cmd == "":
            i += 1
            continue

        # Anything else -> capture as note, then advance.
        cadence = to_operator_cadence(raw_text)
        notes.append((pid, cat, cadence, cmd))
        print(f"  noted: {cmd}")
        i += 1

    out = _write_notes(notes, length_scale)
    print(f"\nWrote {len(notes)} note(s) to {out}")
    print("Paste that file back to chat to triage cadence fixes.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--id", help="run a single phrase by id (e.g. 'prd-A')")
    p.add_argument(
        "--category",
        choices=categories(),
        help="run all phrases in one category",
    )
    p.add_argument("--text", help="custom phrase to synthesize (skips corpus)")
    p.add_argument(
        "--rate",
        type=float,
        default=1.15,
        help="length_scale (default 1.15 = ops cadence; 1.0 = piper default)",
    )
    p.add_argument("--dry-run", action="store_true", help="print cadence transform only, no audio")
    p.add_argument("--list", action="store_true", help="list phrases and exit")
    p.add_argument(
        "--explain",
        metavar="TERM",
        help="speak a deterministic explanation of the given acronym (e.g. 'HLZ')",
    )
    p.add_argument(
        "--explain-list",
        action="store_true",
        help="print every term the glossary can explain, and exit",
    )
    args = p.parse_args()

    if args.list:
        for pid, cat, text, _ in PHRASES:
            print(f"  {pid:12s} ({cat:10s}) {text}")
        return 0

    if args.explain_list:
        for term in known_terms():
            print(f"  {term}")
        return 0

    if args.explain:
        result = synthesize_explanation_b64(args.explain, length_scale=args.rate)
        if result is None:
            print(
                f"  '{args.explain}' is not in the glossary. "
                "Operator hears nothing or 'term not recognized'."
            )
            print("  Run --explain-list to see all known terms.")
            return 1
        print(f"  term:  {result['term']}")
        print(f"  text:  {result['text']}")
        if result["audio_b64"]:
            out = Path(tempfile.gettempdir()) / f"tera_explain_{result['term']}.wav"
            out.write_bytes(base64.b64decode(result["audio_b64"]))
            print(f"  wav:   {out}")
            _play(out)
        else:
            print("  (audio unavailable -- text-only explanation)")
        return 0

    # Set the global length_scale for this session.
    reset_piper()
    from voice import piper_client

    piper_client._client = piper_client.PiperClient(length_scale=args.rate)

    if args.text:
        phrases = [("custom", "custom", args.text, "your phrase")]
    elif args.id:
        hit = by_id(args.id)
        if hit is None:
            print(f"unknown phrase id: {args.id}")
            print("Use --list to see all ids.")
            return 1
        phrases = [hit]
    elif args.category:
        phrases = by_category(args.category)
    else:
        phrases = list(PHRASES)

    if args.dry_run:
        for pid, cat, text, _ in phrases:
            print(f"[{pid}] ({cat})")
            print(f"  text:    {text}")
            print(f"  cadence: {to_operator_cadence(text)}")
        return 0

    return _interactive_loop(phrases, args.rate)


if __name__ == "__main__":
    sys.exit(main())
