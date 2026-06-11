"""Tests for the Cognis release image (Dockerfile.cognis).

Mirrors the structure of tests/test_dockerfile.py (which guards the upstream
Dockerfile — deliberately untouched here). These tests pin the Cognis-specific
invariants:

- Gate-1 defect 7: the base tag must match pyproject.toml's
  ``requires-python = ">=3.12"`` (the old 3.11 base made ``pip install``
  refuse at first build).
- Gate-1 AR-4: the three telemetry unsets + COGNIS_BRANDING default must
  never silently disappear; tools/check_dockerfile_cognis.py is the CI
  enforcement and is exercised here against good and mutated inputs.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parent.parent.parent
_CHECK_SCRIPT = _REPO_ROOT / "tools" / "check_dockerfile_cognis.py"


@pytest.fixture
def dockerfile_path() -> Path:
    """Return the path to Dockerfile.cognis at the repo root."""
    return _REPO_ROOT / "Dockerfile.cognis"


def _run_check(dockerfile: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_CHECK_SCRIPT), str(dockerfile)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_dockerfile_cognis_exists(dockerfile_path: Path) -> None:
    """Dockerfile.cognis must exist at the repo root."""
    assert dockerfile_path.exists(), "Dockerfile.cognis not found at repo root"
    assert dockerfile_path.is_file(), "Dockerfile.cognis is not a file"


def test_dockerfile_cognis_base_matches_requires_python(dockerfile_path: Path) -> None:
    """The base tag must satisfy pyproject's requires-python >=3.12 (defect 7)."""
    content = dockerfile_path.read_text()
    assert "FROM langchain/langgraph-api:3.12" in content, (
        "Base image must be the Python 3.12 langgraph-api variant"
    )
    assert "langgraph-api:3.11" not in content, (
        "Python 3.11 base conflicts with requires-python >=3.12 (Gate-1 defect 7)"
    )


def test_dockerfile_cognis_unsets_telemetry(dockerfile_path: Path) -> None:
    """The three telemetry unsets must be present (cost-policy.md / AR-4)."""
    content = dockerfile_path.read_text()
    assert 'SENTRY_DSN=""' in content, "Sentry DSN must be explicitly unset"
    assert 'LANGSMITH_API_KEY=""' in content, "LangSmith key must be explicitly unset"
    assert 'LANGCHAIN_TRACING_V2="false"' in content, "LangChain tracing must be off"


def test_dockerfile_cognis_defaults_branding_on(dockerfile_path: Path) -> None:
    """The Cognis image must default COGNIS_BRANDING=on."""
    content = dockerfile_path.read_text()
    assert "COGNIS_BRANDING=on" in content, "Cognis image must default to branded output"


def test_dockerfile_cognis_ships_full_brand_env(dockerfile_path: Path) -> None:
    """Gate-2 ops B2: the image must be brand-self-describing — every
    CognisBrand env var ships in the ENV block so a sub-brand rename is
    env-only. Banner color hex is token-sourced from
    cognis-platform/packages/design-tokens/tokens.json
    (color.brand.primary / color.brand.accent-pop)."""
    content = dockerfile_path.read_text()
    assert 'COGNIS_PRODUCT_NAME="Cognis Ops"' in content
    assert 'COGNIS_PRODUCT_TAGLINE="Investigates incidents, publishes the RCA."' in content
    assert "COGNIS_PRODUCT_JOB=" in content
    assert 'COGNIS_SUPPORT_EMAIL="support@cognisai.com"' in content
    assert 'COGNIS_DOCS_URL="https://cognisai.com/docs/ops"' in content
    assert 'COGNIS_PORTAL_URL="https://app.cognisai.com/dashboard/ops"' in content
    # token: color.brand.primary
    assert 'COGNIS_BANNER_COLOR_PRIMARY="#0099ff"' in content
    # token: color.brand.accent-pop
    assert 'COGNIS_BANNER_COLOR_ACCENT="#cbff97"' in content


def test_dockerfile_cognis_uses_cognis_entrypoint(dockerfile_path: Path) -> None:
    """The image must launch the Cognis CLI wrapper, not upstream's CMD."""
    content = dockerfile_path.read_text()
    assert 'CMD ["python", "-m", "app.cognis.cli"]' in content, (
        "Should run the Cognis CLI wrapper as the container command"
    )


def test_check_script_passes_on_current_dockerfile(dockerfile_path: Path) -> None:
    """The AR-4 CI guard must pass against the checked-in Dockerfile.cognis."""
    result = _run_check(dockerfile_path)
    assert result.returncode == 0, f"guard failed:\n{result.stderr}"
    assert "OK" in result.stdout


@pytest.mark.parametrize(
    "dropped_line_marker",
    [
        'SENTRY_DSN=""',
        'LANGSMITH_API_KEY=""',
        'LANGCHAIN_TRACING_V2="false"',
        "COGNIS_BRANDING=on",
    ],
)
def test_check_script_fails_when_guard_dropped(
    dockerfile_path: Path, tmp_path: Path, dropped_line_marker: str
) -> None:
    """Removing any guarded ENV assignment must fail the AR-4 CI check."""
    lines = dockerfile_path.read_text().splitlines()
    mutated = [line for line in lines if dropped_line_marker not in line]
    assert len(mutated) < len(lines), "fixture must actually drop a line"
    mutated_path = tmp_path / "Dockerfile.cognis"
    mutated_path.write_text("\n".join(mutated) + "\n")

    result = _run_check(mutated_path)
    assert result.returncode == 1, "guard must fail when an unset disappears"
    var_name = dropped_line_marker.split("=")[0]
    assert var_name in result.stderr


def test_check_script_fails_on_missing_file(tmp_path: Path) -> None:
    """A missing Dockerfile.cognis is a failure, not a silent pass."""
    result = _run_check(tmp_path / "does-not-exist")
    assert result.returncode == 1
