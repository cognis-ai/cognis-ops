"""Tests for the Cognis branding layer (app/cognis/branding/*).

Gate-2 ops verification conditions:

- B1: banner color defaults must be rich-valid names (the old prompt_toolkit
  names ``ansiblue``/``ansigreen`` raise ``rich.color.ColorParseError``), and
  bad env overrides must degrade to uncolored output via
  ``resolve_banner_color`` instead of crashing.
- B4 / §7 parity: with COGNIS_BRANDING off, the branding layer must be a
  byte-exact no-op so upstream stdout-parity tests keep passing.
"""

from __future__ import annotations

import io

import pytest

from app.cognis.branding.banner import print_cognis_banner
from app.cognis.branding.cognis_brand import (
    CognisBrand,
    branding_enabled,
    load_brand,
    resolve_banner_color,
)

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


@pytest.fixture
def clean_branding_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip all COGNIS_* branding env vars so defaults are under test."""
    for var in _BRANDING_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_default_banner_colors_are_rich_valid(clean_branding_env: None) -> None:
    """The dataclass defaults must parse under rich (gate2 B1 condition a)."""
    rich_color = pytest.importorskip("rich.color")
    brand = load_brand()
    for name in (brand.banner_color_primary, brand.banner_color_accent):
        rich_color.Color.parse(name)  # raises ColorParseError on regression


def test_default_banner_colors_survive_resolver(clean_branding_env: None) -> None:
    """resolve_banner_color must pass the defaults through unchanged."""
    pytest.importorskip("rich.color")
    assert resolve_banner_color(CognisBrand.banner_color_primary) == "blue"
    assert resolve_banner_color(CognisBrand.banner_color_accent) == "green"


@pytest.mark.parametrize("bad_name", ["ansiblue", "ansigreen", "not-a-color", ""])
def test_resolver_falls_back_to_uncolored_on_bad_names(bad_name: str) -> None:
    """Unparseable color names resolve to None (uncolored), never raise."""
    assert resolve_banner_color(bad_name) is None


def test_env_override_still_flows_through(
    clean_branding_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Env-driven branding contract: overrides land on the loaded brand."""
    monkeypatch.setenv("COGNIS_BANNER_COLOR_PRIMARY", "magenta")
    monkeypatch.setenv("COGNIS_BANNER_COLOR_ACCENT", "ansigreen")
    brand = load_brand()
    assert brand.banner_color_primary == "magenta"
    # A bad override is preserved on the brand (env contract) but resolves
    # to uncolored at render time (safe fallback).
    assert brand.banner_color_accent == "ansigreen"
    assert resolve_banner_color(brand.banner_color_accent) is None


def test_branding_off_is_byte_exact_noop(
    clean_branding_env: None,
) -> None:
    """With COGNIS_BRANDING unset, the banner writes nothing (§7 parity)."""
    assert branding_enabled() is False
    stream = io.StringIO()
    print_cognis_banner(stream)
    assert stream.getvalue() == ""


def test_branding_off_explicit_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Off-flavored values keep the no-op contract."""
    for raw in ("off", "0", "false", "no", ""):
        monkeypatch.setenv("COGNIS_BRANDING", raw)
        assert branding_enabled() is False, f"COGNIS_BRANDING={raw!r} must be off"
    for raw in ("on", "true", "1", "yes", "ON"):
        monkeypatch.setenv("COGNIS_BRANDING", raw)
        assert branding_enabled() is True, f"COGNIS_BRANDING={raw!r} must be on"
