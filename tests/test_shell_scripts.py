"""Bash syntax check for every committed shell script.

Catches the kind of regression that PR #59 shipped (e.g. ``dirname`` -> ``diname``,
``warn`` -> ``wan``) which ``make ci`` previously didn't flag because it doesn't
exercise the affected scripts at runtime. ``bash -n`` parses without executing,
so every callsite of an undefined function, every malformed redirection, and
every dropped quote shows up as a parse error.

Pairs with the ``shellcheck-syntax`` Makefile target so the gate works two ways:
- ``make ci`` -> ``make test`` -> this file -> per-script parse check
- ``make ci`` -> ``make shellcheck-syntax`` -> direct loop

If a future PR introduces a typo like the PR #59 ones, this test fails by
script name in the pytest output, making the offending file obvious in CI logs.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = frozenset({".venv", "node_modules", ".git", "__pycache__", ".archive"})
BASH = shutil.which("bash") or "/bin/bash"


def _shell_scripts() -> list[Path]:
    """Every committed *.sh under the repo, minus skip dirs."""
    return sorted(
        path
        for path in REPO_ROOT.rglob("*.sh")
        if not any(part in SKIP_DIRS for part in path.parts)
    )


@pytest.mark.parametrize(
    "script",
    _shell_scripts(),
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_bash_parse_ok(script: Path) -> None:
    """Every committed shell script must parse with ``bash -n``.

    S603 is suppressed: the script path comes from a glob over the repo
    (no operator input); we pass a list (no shell=True). Trusted by construction.
    BASH is resolved to an absolute path at module load to avoid S607.
    """
    result = subprocess.run(  # noqa: S603
        [BASH, "-n", str(script)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"{script.relative_to(REPO_ROOT)} failed bash parse:\nstderr:\n{result.stderr}"
    )


def test_at_least_one_script_discovered() -> None:
    """Guard against the discovery glob silently matching nothing."""
    scripts = _shell_scripts()
    assert len(scripts) >= 5, (
        f"Expected at least 5 committed shell scripts under the repo; "
        f"found {len(scripts)}. The discovery pattern in this test may be wrong."
    )
