"""Cognis Ops — CLI banner.

Replaces opensre's stock banner with Cognis Ops copy on startup. Plainspoken
per the Cognis brand voice (periods, not exclamation marks; no banned
marketing words; product framing as "a worker that does the job", not "a
tool you use").

Invoked from the Cognis CLI wrapper BEFORE upstream's CLI initializes, so
the very first thing the customer sees is Cognis branding. No-op when
COGNIS_BRANDING is unset.

Colors (gate2 ops B1): the title/frame is styled with
``COGNIS_BANNER_COLOR_PRIMARY`` and section headers with
``COGNIS_BANNER_COLOR_ACCENT``, rendered via ``rich`` (an upstream dep).
The shipped hex values live ONLY in ``Dockerfile.cognis`` ENV and are
token-sourced from ``cognis-platform/packages/design-tokens/tokens.json``
(``color.brand.primary`` / ``color.brand.accent-pop``) — never hardcoded
here. A color that rich cannot parse, or a missing rich install, degrades
to the uncolored banner instead of crashing (resolve_banner_color contract).
"""

from __future__ import annotations

import sys
import textwrap
from typing import TextIO

from app.cognis.branding.cognis_brand import (
    CognisBrand,
    branding_enabled,
    load_brand,
    resolve_banner_color,
)

_BANNER_WIDTH = 78

# Style roles: "primary" → COGNIS_BANNER_COLOR_PRIMARY (frame + title),
# "accent" → COGNIS_BANNER_COLOR_ACCENT (section headers), None → unstyled.
_PRIMARY = "primary"
_ACCENT = "accent"


def _banner_lines(brand: CognisBrand) -> list[tuple[str, str | None]]:
    """The banner content as (text, style-role) pairs — single source for
    both the colored (rich) and plain renderers, so the copy can never
    drift between the two paths."""
    bar = "=" * _BANNER_WIDTH
    title = brand.product_name.center(_BANNER_WIDTH)
    tagline = brand.product_tagline.center(_BANNER_WIDTH)

    return [
        (bar, _PRIMARY),
        ("", None),
        (title, _PRIMARY),
        (tagline, None),
        ("", None),
        (bar, _PRIMARY),
        ("", None),
        ("What this is", _ACCENT),
        ("-" * len("What this is"), _ACCENT),
        (textwrap.fill(brand.product_job, width=_BANNER_WIDTH), None),
        ("", None),
        ("Safety rules", _ACCENT),
        ("-" * len("Safety rules"), _ACCENT),
        (
            textwrap.fill(
                "I never run write actions (kubectl apply, terraform apply, restart, "
                "deploy, kill, delete) without an explicit operator confirmation that "
                "I'll record for audit. I never exfiltrate secrets in RCA output.",
                width=_BANNER_WIDTH,
            ),
            None,
        ),
        ("", None),
        ("Where to go for help", _ACCENT),
        ("-" * len("Where to go for help"), _ACCENT),
        (f"  Portal:  {brand.portal_url}", None),
        (f"  Docs:    {brand.docs_url}", None),
        (f"  Support: {brand.support_email}", None),
        ("", None),
        (bar, _PRIMARY),
        ("", None),
    ]


def print_cognis_banner(stream: TextIO = sys.stdout) -> None:
    if not branding_enabled():
        return

    brand = load_brand()
    lines = _banner_lines(brand)
    styles = {
        _PRIMARY: resolve_banner_color(brand.banner_color_primary),
        _ACCENT: resolve_banner_color(brand.banner_color_accent),
    }

    if styles[_PRIMARY] or styles[_ACCENT]:
        try:
            from rich.console import Console
            from rich.text import Text
        except Exception:
            pass  # rich unavailable — fall through to the uncolored banner
        else:
            # rich emits ANSI only when `stream` is a terminal; on pipes and
            # files the output stays plain text, and hex tokens downgrade
            # automatically on non-truecolor terminals.
            console = Console(file=stream, width=_BANNER_WIDTH, highlight=False)
            for text, role in lines:
                style = styles.get(role) if role else None
                console.print(Text(text, style=style or ""), no_wrap=True)
            stream.flush()
            return

    stream.write("\n".join(text for text, _ in lines))
    stream.flush()


def cognis_log_prefix() -> str:
    """Short brand prefix for log lines. Always returns "Cognis Ops" so log
    output is grep-friendly even when branding is off."""
    return "Cognis Ops"
