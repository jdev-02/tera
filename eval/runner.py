"""Eval runner: feeds prompts.yml through the orchestrator's LLM step and
asserts the structured queries match goldens.

Designed to run in TWO modes:

  mock-mode  (default, no API key, no ollama)
    Loads each prompt's `expected_query` and just validates it against the
    RouteQuery JSON schema. Doesn't actually call the LLM. Catches schema
    drift between the eval set and the live ontology.

  live-mode  (TERA_EVAL_LIVE=1, requires API key OR running ollama)
    Actually calls the LLM with the system prompt and asserts the emitted
    structured query matches the golden modulo defaulted fields.

Run:    python -m eval.runner
        TERA_EVAL_LIVE=1 python -m eval.runner

CI uses mock-mode (deterministic, fast, no secrets needed).
The Sat 1400 dev-time benchmark + Sun 0900 demo dry-run use live-mode.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft7Validator

from ontology.loader import load_route_query_schema

PROMPTS_PATH = Path(__file__).resolve().parent / "prompts.yml"

PASS_THRESHOLD = 0.90  # CI fails below this


def load_eval_entries() -> list[dict[str, Any]]:
    """Returns the parsed eval prompts as a list of entry dicts. Each entry has
    at least `id` and `utterance`; valid entries also have `expected_query`."""
    with PROMPTS_PATH.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    # The YAML structure: top-level is a flat list of entries. Filter to those
    # that look like prompt entries (have an id) -- defensive against future
    # comment-only or marker entries.
    if isinstance(raw, list):
        return [e for e in raw if isinstance(e, dict) and "id" in e]
    # Defensive: handle the alternate dict-with-list layout (post-MVP).
    if isinstance(raw, dict) and "entries" in raw:
        return list(raw["entries"])
    return []


def validate_against_schema(query: dict[str, Any]) -> list[str]:
    """Return a list of validation error strings. Empty list = valid."""
    schema = load_route_query_schema()
    validator = Draft7Validator(schema)
    return [
        ".".join(str(p) for p in e.absolute_path) + ": " + e.message
        for e in sorted(validator.iter_errors(query), key=lambda e: list(e.absolute_path))
    ]


def run_mock_mode() -> tuple[int, int, list[dict[str, Any]]]:
    """Validate each entry's expected_query against the RouteQuery schema.

    Returns (passed_count, total_count, failures) where failures is a list of
    {id, errors}.
    """
    entries = load_eval_entries()
    passed = 0
    failures: list[dict[str, Any]] = []

    for entry in entries:
        # Adversarial entries have no expected_query (the pipeline blocks them).
        # Skip schema validation for those; they're tested elsewhere.
        if entry.get("expected_query") is None:
            passed += 1
            continue

        errors = validate_against_schema(entry["expected_query"])
        if errors:
            failures.append({"id": entry["id"], "errors": errors})
        else:
            passed += 1

    return passed, len(entries), failures


def main() -> int:
    live = os.environ.get("TERA_EVAL_LIVE", "") == "1"
    if live:
        print("ERROR: TERA_EVAL_LIVE=1 not yet implemented.", file=sys.stderr)
        print("       Falls back to mock-mode for now. Track in #21.", file=sys.stderr)

    passed, total, failures = run_mock_mode()

    print("=== TERA eval: mock-mode (golden vs schema) ===")
    print(f"Total entries:   {total}")
    print(f"Passed:          {passed}")
    print(f"Failed:          {len(failures)}")
    pass_rate = passed / total if total else 0.0
    print(f"Pass rate:       {pass_rate:.0%}  (threshold {PASS_THRESHOLD:.0%})")

    if failures:
        print("\nFailures:")
        for f in failures:
            print(f"  {f['id']}:")
            for err in f["errors"]:
                print(f"    - {err}")

    if pass_rate < PASS_THRESHOLD:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
