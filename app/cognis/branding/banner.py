"""Cognis Ops — CLI banner.

Replaces opensre's stock banner with Cognis Ops copy on startup. Plainspoken
per the Cognis brand voice (periods, not exclamation marks; no banned
marketing words; product framing as "a worker that does the job", not "a
tool you use").

Invoked from the Cognis CLI wrapper BEFORE upstream's CLI initializes, so
the very first thing the customer sees is Cognis branding. No-op when
COGNIS_BRANDING is unset.
"""

from __future__ import annotations

import sys
import textwrap
from typing import TextIO

from app.cognis.branding.cognis_brand import branding_enabled, load_brand

_BANNER_WIDTH = 78


def print_cognis_banner(stream: TextIO = sys.stdout) -> None:
    if not branding_enabled():
        return

    brand = load_brand()
    bar = "=" * _BANNER_WIDTH
    title = brand.product_name.center(_BANNER_WIDTH)
    tagline = brand.product_tagline.center(_BANNER_WIDTH)

    paragraphs = [
        bar,
        "",
        title,
        tagline,
        "",
        bar,
        "",
        "What this is",
        "-" * len("What this is"),
        textwrap.fill(brand.product_job, width=_BANNER_WIDTH),
        "",
        "Safety rules",
        "-" * len("Safety rules"),
        textwrap.fill(
            "I never run write actions (kubectl apply, terraform apply, restart, "
            "deploy, kill, delete) without an explicit operator confirmation that "
            "I'll record for audit. I never exfiltrate secrets in RCA output.",
            width=_BANNER_WIDTH,
        ),
        "",
        "Where to go for help",
        "-" * len("Where to go for help"),
        f"  Portal:  {brand.portal_url}",
        f"  Docs:    {brand.docs_url}",
        f"  Support: {brand.support_email}",
        "",
        bar,
        "",
    ]

    stream.write("\n".join(paragraphs))
    stream.flush()


def cognis_log_prefix() -> str:
    """Short brand prefix for log lines. Always returns "Cognis Ops" so log
    output is grep-friendly even when branding is off."""
    return "Cognis Ops"
