"""Tests for model supply-chain integrity — issue #57."""

from __future__ import annotations

import hashlib
import textwrap
from pathlib import Path

from security.model_integrity import (
    _sha256_file,
    scan_unsafe_loads,
    verify_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# SHA-256 manifest tests
# ---------------------------------------------------------------------------


def test_manifest_file_exists() -> None:
    assert (REPO_ROOT / "models" / "MANIFEST.yml").exists(), (
        "models/MANIFEST.yml is missing — create it with SHA-256 pins"
    )


def test_manifest_required_hashes_pass() -> None:
    passed, skipped, errors = verify_manifest()
    assert not errors, "\n".join(errors)
    assert passed > 0, "No required entries were verified — check MANIFEST.yml"


def test_sha256_file_matches_known_hash(tmp_path: Path) -> None:
    content = b"TERA model integrity test content"
    f = tmp_path / "test.bin"
    f.write_bytes(content)
    expected = hashlib.sha256(content).hexdigest()
    assert _sha256_file(f) == expected


def test_sha256_file_detects_tampered_content(tmp_path: Path) -> None:
    f = tmp_path / "model.gguf"
    f.write_bytes(b"original weights")
    original_hash = _sha256_file(f)

    f.write_bytes(b"tampered weights injected by attacker")
    assert _sha256_file(f) != original_hash


# ---------------------------------------------------------------------------
# Unsafe torch.load() scanner tests
# ---------------------------------------------------------------------------


def test_scan_detects_unsafe_torch_load(tmp_path: Path) -> None:
    """torch.load() without weights_only=True must be flagged."""
    bad = tmp_path / "bad_loader.py"
    bad.write_text(
        textwrap.dedent("""\
            import torch
            model = torch.load("model.pt")
        """),
        encoding="utf-8",
    )
    findings = scan_unsafe_loads(dirs=[str(tmp_path)])
    assert findings, "Expected unsafe torch.load() to be detected"


def test_scan_accepts_safe_torch_load(tmp_path: Path) -> None:
    """torch.load() with weights_only=True must NOT be flagged."""
    good = tmp_path / "safe_loader.py"
    good.write_text(
        textwrap.dedent("""\
            import torch
            model = torch.load("model.pt", weights_only=True)
        """),
        encoding="utf-8",
    )
    findings = scan_unsafe_loads(dirs=[str(tmp_path)])
    assert not findings, f"Safe torch.load() was incorrectly flagged: {findings}"


def test_scan_clean_on_project_source() -> None:
    """No unsafe torch.load() in TERA source directories."""
    findings = scan_unsafe_loads()
    assert not findings, (
        "Unsafe torch.load() calls found (missing weights_only=True):\n"
        + "\n".join(
            f"  {path}:{ln} — {snippet}" for path, hits in findings.items() for ln, snippet in hits
        )
    )
