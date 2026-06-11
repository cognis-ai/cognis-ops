"""Branding-on output tests + upstream-residue gate (gate2 ops B4, §7 tests 2–3).

- §7 test 2: with COGNIS_BRANDING=on and overridden env, the banner carries
  the COGNIS_PRODUCT_* / portal / docs / support values.
- §7 test 3: rendered cognis-layer output (banner + cli.py status/fallback
  messages) matches ``(?i)(opensre|tracer)`` nowhere. Code comments and
  docstrings referencing upstream stay allowed — only *rendered* strings
  are gated (tools/check_brand_residue.py is the static CI twin of this).
- B1 conditions: colors apply on color terminals; unparseable color names
  degrade to the uncolored banner instead of crashing.
"""

from __future__ import annotations

import io
import re
import sys
from types import SimpleNamespace

import pytest

from app.cognis.branding.banner import cognis_log_prefix, print_cognis_banner
from app.cognis.branding.cognis_brand import load_brand
from app.cognis.cli import _bridge_connected_message, _no_bridge_notice

_RESIDUE = re.compile(r"(?i)(opensre|tracer)")

_BRANDING_ENV_VARS = (
    "COGNIS_BRANDING",
    "COGNIS_PRODUCT_NAME",
    "COGNIS_PRODUCT_TAGLINE",
    "COGNIS_PRODUCT_JOB",
    "COGNIS_SUPPORT_EMAIL",
    "COGNIS_DOCS_URL",
    "COGNIS_PORTAL_URL",
    "COGNIS_BANNER_COLOR_PRIMARY",
    "COGNIS_BANNER_COLOR_ACCENT",
)


def _reset_branding_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _BRANDING_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def _banner_output(monkeypatch: pytest.MonkeyPatch, stream=None, **env: str) -> str:
    _reset_branding_env(monkeypatch)
    monkeypatch.setenv("COGNIS_BRANDING", "on")
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    stream = stream if stream is not None else io.StringIO()
    print_cognis_banner(stream)
    return stream.getvalue()


class _TtyStringIO(io.StringIO):
    """A StringIO that claims to be a terminal so rich emits ANSI styling."""

    def isatty(self) -> bool:
        return True


def test_banner_contains_overridden_brand_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """§7 test 2: every brand env override must surface in the banner."""
    overrides = {
        "COGNIS_PRODUCT_NAME": "Acme Ops",
        "COGNIS_PRODUCT_TAGLINE": "Finds the fault, files the fix.",
        "COGNIS_PRODUCT_JOB": "Walks the telemetry and reports the root cause.",
        "COGNIS_SUPPORT_EMAIL": "help@acme.test",
        "COGNIS_DOCS_URL": "https://acme.test/docs",
        "COGNIS_PORTAL_URL": "https://acme.test/portal",
    }
    out = _banner_output(monkeypatch, **overrides)
    for value in overrides.values():
        assert value in out, f"banner must include the env-driven value {value!r}"


def test_banner_defaults_render(monkeypatch: pytest.MonkeyPatch) -> None:
    out = _banner_output(monkeypatch)
    assert "Cognis Ops" in out
    assert "Investigates incidents, publishes the RCA." in out
    assert "https://app.cognisai.com/dashboard/ops" in out


def test_banner_colored_path_keeps_content(monkeypatch: pytest.MonkeyPatch) -> None:
    """B1: with token hex set (Dockerfile.cognis values) the banner still
    carries the full copy; on a color terminal rich applies ANSI styling."""
    pytest.importorskip("rich")
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("NO_COLOR", raising=False)
    out = _banner_output(
        monkeypatch,
        stream=_TtyStringIO(),
        COGNIS_BANNER_COLOR_PRIMARY="#0099ff",
        COGNIS_BANNER_COLOR_ACCENT="#cbff97",
    )
    assert "Cognis Ops" in out
    assert "Where to go for help" in out
    if sys.platform != "win32":  # legacy-console detection can strip ANSI
        assert "\x1b[" in out, "color terminal output should carry ANSI styling"


def test_banner_non_terminal_stream_stays_plain(monkeypatch: pytest.MonkeyPatch) -> None:
    """B1: piped/non-tty output must stay plain text even with colors set."""
    pytest.importorskip("rich")
    out = _banner_output(
        monkeypatch,
        COGNIS_BANNER_COLOR_PRIMARY="#0099ff",
        COGNIS_BANNER_COLOR_ACCENT="#cbff97",
    )
    assert "\x1b[" not in out
    assert "Cognis Ops" in out


def test_banner_bad_colors_degrade_to_uncolored(monkeypatch: pytest.MonkeyPatch) -> None:
    """B1 condition (a): unparseable color names never raise — uncolored output."""
    out = _banner_output(
        monkeypatch,
        stream=_TtyStringIO(),
        COGNIS_BANNER_COLOR_PRIMARY="ansiblue",
        COGNIS_BANNER_COLOR_ACCENT="not-a-color",
    )
    assert "\x1b[" not in out
    assert "Cognis Ops" in out


def _fake_bridge_config() -> SimpleNamespace:
    return SimpleNamespace(
        cognis_org_id="org_123",
        plan="pro",
        integrations=[],
        llm_gateway=SimpleNamespace(base_url="https://llm.cognisai.com", api_key="sk-test"),
    )


def test_bridge_connected_message_content(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_branding_env(monkeypatch)
    msg = _bridge_connected_message(_fake_bridge_config(), load_brand())
    assert "connected to Bridge as org=org_123" in msg
    assert "plan=pro" in msg
    assert "OPENAI_API_BASE=https://llm.cognisai.com" in msg
    assert "https://app.cognisai.com/dashboard/ops" in msg


def test_cognis_layer_output_has_no_upstream_residue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§7 test 3: banner + status lines + fallback notice + log prefix must
    never leak the upstream brand into customer-facing output."""
    rendered = "\n".join(
        (
            _banner_output(monkeypatch),
            _bridge_connected_message(_fake_bridge_config(), load_brand()),
            _no_bridge_notice(),
            cognis_log_prefix(),
        )
    )
    match = _RESIDUE.search(rendered)
    assert match is None, f"upstream residue {match.group(0)!r} in cognis-layer output"
