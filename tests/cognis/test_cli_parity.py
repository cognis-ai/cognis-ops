"""Upstream stdout-parity contract (gate2 ops B4, §7 test 1 — the most
important guard).

With COGNIS_BRANDING unset, the Cognis CLI wrapper (``app.cognis.cli:main``)
must produce stdout byte-identical to upstream's CLI
(``app.cli.__main__:main``) for ``--help`` — ZERO FEATURE LOSS and the
Parity Ledger "Env-driven branding / no-ops when off" row depend on it.

Both sides run in subprocesses with identical ``sys.argv`` (click derives the
usage prog-name from it) and a COGNIS_*-stripped, COLUMNS-pinned env so the
comparison is deterministic.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("click")
pytest.importorskip("dotenv")

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Identical argv on both sides: the wrapper passes through to upstream, and
# click's prog-name detection sees the same sys.argv[0] either way.
_UPSTREAM_SNIPPET = (
    "import sys; sys.argv = ['opensre', '--help']; "
    "from app.cli.__main__ import main; raise SystemExit(main())"
)
_COGNIS_SNIPPET = (
    "import sys; sys.argv = ['opensre', '--help']; "
    "from app.cognis.cli import main; raise SystemExit(main())"
)


def _run(snippet: str) -> subprocess.CompletedProcess[bytes]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COGNIS_")}
    env["COLUMNS"] = "80"
    env["PYTHONIOENCODING"] = "utf-8"
    env["NO_COLOR"] = "1"
    return subprocess.run(
        [sys.executable, "-c", snippet],
        capture_output=True,
        cwd=_REPO_ROOT,
        env=env,
        timeout=180,
        check=False,
    )


def test_branding_off_help_stdout_is_byte_identical_to_upstream() -> None:
    upstream = _run(_UPSTREAM_SNIPPET)
    if upstream.returncode != 0 and b"ModuleNotFoundError" in upstream.stderr:
        pytest.skip("upstream CLI dependencies not installed in this environment")

    cognis = _run(_COGNIS_SNIPPET)

    # Guard against a vacuous pass: upstream --help must actually render.
    assert upstream.returncode == 0, upstream.stderr.decode(errors="replace")
    assert b"Usage" in upstream.stdout

    assert cognis.returncode == upstream.returncode
    assert cognis.stdout == upstream.stdout, (
        "COGNIS_BRANDING off must be a byte-exact stdout no-op "
        "(upstream-parity contract, cognis_brand.branding_enabled docstring)"
    )
