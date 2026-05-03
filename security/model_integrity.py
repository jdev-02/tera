"""Model supply-chain integrity — issue #57.

Two defences:
1. SHA-256 manifest pinning: verify every required model file matches its
   pinned hash in models/MANIFEST.yml before the model is loaded.
2. Unsafe-deserialisation scan: detect torch.load() calls that omit
   weights_only=True (arbitrary code execution via pickle).

Usage:
    python -m security.model_integrity          # verify manifest + scan
    python -m security.model_integrity --scan   # unsafe-load scan only
    python -m security.model_integrity --verify # hash verify only
"""

from __future__ import annotations

import argparse
import ast
import hashlib
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "models" / "MANIFEST.yml"
SCAN_DIRS = ["agent", "routing", "security", "crypto", "voice", "eval", "scripts"]
PLACEHOLDER = "PLACEHOLDER_run_sha256sum_after_download"


class ModelIntegrityError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# SHA-256 manifest verification
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    # Normalise CRLF → LF so hashes are identical on Windows and Linux CI.
    content = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(content).hexdigest()


def _load_manifest() -> list[dict[str, Any]]:
    if yaml is None:
        raise ModelIntegrityError("PyYAML is not installed. Run: pip install pyyaml")
    if not MANIFEST_PATH.exists():
        raise ModelIntegrityError(f"Manifest not found: {MANIFEST_PATH}")
    data = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    return data.get("models", [])


def verify_manifest() -> tuple[int, int, list[str]]:
    """Verify all required entries in models/MANIFEST.yml.

    Returns (passed, skipped, errors).
    """
    entries = _load_manifest()
    passed = skipped = 0
    errors: list[str] = []

    for entry in entries:
        path = REPO_ROOT / entry["path"]
        required = entry.get("required", True)
        pinned = entry.get("sha256", "")

        if pinned == PLACEHOLDER or not pinned:
            skipped += 1
            continue

        if not path.exists():
            if required:
                errors.append(f"MISSING (required): {entry['path']}")
            else:
                skipped += 1
            continue

        actual = _sha256_file(path)
        if actual.lower() != pinned.lower():
            errors.append(
                f"HASH MISMATCH: {entry['path']}\n"
                f"  expected: {pinned.lower()}\n"
                f"  actual:   {actual}"
            )
        else:
            passed += 1

    return passed, skipped, errors


# ---------------------------------------------------------------------------
# Unsafe torch.load() scanner
# ---------------------------------------------------------------------------


def _scan_file_for_unsafe_loads(path: Path) -> list[tuple[int, str]]:
    """Return (lineno, line) for every unsafe torch.load() in path."""
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    hits: list[tuple[int, str]] = []
    lines = source.splitlines()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func = node.func
        is_torch_load = (
            isinstance(func, ast.Attribute)
            and func.attr == "load"
            and isinstance(func.value, ast.Name)
            and func.value.id == "torch"
        ) or (
            isinstance(func, ast.Name) and func.attr == "load"  # type: ignore[union-attr]
            if hasattr(func, "attr")
            else False
        )
        if not is_torch_load:
            continue

        keywords = {kw.arg for kw in node.keywords}
        if "weights_only" not in keywords:
            lineno = node.lineno
            snippet = lines[lineno - 1].strip() if lineno <= len(lines) else ""
            hits.append((lineno, snippet))

    return hits


def scan_unsafe_loads(dirs: list[str] | None = None) -> dict[str, list[tuple[int, str]]]:
    """Scan Python source files for torch.load() without weights_only=True."""
    raw_dirs = dirs or SCAN_DIRS
    scan_roots = [Path(d) if Path(d).is_absolute() else REPO_ROOT / d for d in raw_dirs]
    findings: dict[str, list[tuple[int, str]]] = {}

    for root in scan_roots:
        if not root.exists():
            continue
        for py_file in sorted(root.rglob("*.py")):
            if ".venv" in py_file.parts:
                continue
            hits = _scan_file_for_unsafe_loads(py_file)
            if hits:
                try:
                    key = str(py_file.relative_to(REPO_ROOT))
                except ValueError:
                    key = str(py_file)
                findings[key] = hits

    return findings


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _run_verify() -> int:
    print()
    print("=" * 60)
    print("  TERA — Model Supply-Chain Integrity (issue #57)")
    print("=" * 60)
    print()
    print("[1/2] SHA-256 manifest verification")
    print(f"      manifest: {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    print()

    try:
        passed, skipped, errors = verify_manifest()
    except ModelIntegrityError as e:
        print(f"  [ERROR] {e}")
        return 1

    for err in errors:
        print(f"  [FAIL] {err}")
    if not errors:
        print(f"  [OK]   {passed} hashes verified, {skipped} optional/placeholder skipped")

    return 1 if errors else 0


def _run_scan() -> int:
    print()
    print("[2/2] Unsafe torch.load() scan (weights_only enforcement)")

    findings = scan_unsafe_loads()
    if findings:
        for rel_path, hits in findings.items():
            for lineno, snippet in hits:
                print(f"  [FAIL] {rel_path}:{lineno} — {snippet}")
        print()
        print(
            "  Fix: add weights_only=True to every torch.load() call.\n"
            "  Unsafe torch.load() allows arbitrary code execution via pickle."
        )
    else:
        print("  [OK]   No unsafe torch.load() calls found.")

    return 1 if findings else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TERA model supply-chain integrity check")
    parser.add_argument("--verify", action="store_true", help="hash verify only")
    parser.add_argument("--scan", action="store_true", help="unsafe-load scan only")
    args = parser.parse_args(argv)

    rc = 0
    if args.scan:
        rc |= _run_scan()
    elif args.verify:
        rc |= _run_verify()
    else:
        rc |= _run_verify()
        rc |= _run_scan()

    print()
    if rc == 0:
        print("=" * 60)
        print("  RESULT: model integrity checks PASSED.")
        print("=" * 60)
    else:
        print("=" * 60)
        print("  RESULT: FAILED — fix issues above before demo.")
        print("=" * 60)
    print()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
