"""Cognis Ops — brand identity constants.

Env-driven so a single binary can ship per Cognis sub-brand without recompile.
Defaults match the Cognis Ops product identity (the "AI worker that picks up
the alert, walks your logs and metrics, hands you the root cause" framing —
see cognis-platform/apps/portal/lib/products.ts).

Every customer-facing string the bot prints — CLI banner, log prefixes,
status messages — pulls from this module rather than hard-coding opensre
copy.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CognisBrand:
    product_name: str = "Cognis Ops"
    product_tagline: str = "Investigates incidents, publishes the RCA."
    product_job: str = (
        "Picks up the alert, walks your logs and metrics, hands you the root cause "
        "and a recommended next step."
    )
    support_email: str = "support@cognisai.com"
    docs_url: str = "https://cognisai.com/docs/ops"
    portal_url: str = "https://app.cognisai.com/dashboard/ops"
    # rich-valid color names (gate2 ops B1: the previous prompt_toolkit names
    # "ansiblue"/"ansigreen" raise rich.color.ColorParseError). Renderers must
    # resolve via resolve_banner_color() so a bad env override degrades to
    # uncolored output instead of crashing the banner.
    banner_color_primary: str = "blue"
    banner_color_accent: str = "green"


def load_brand() -> CognisBrand:
    return CognisBrand(
        product_name=os.environ.get("COGNIS_PRODUCT_NAME", CognisBrand.product_name),
        product_tagline=os.environ.get("COGNIS_PRODUCT_TAGLINE", CognisBrand.product_tagline),
        product_job=os.environ.get("COGNIS_PRODUCT_JOB", CognisBrand.product_job),
        support_email=os.environ.get("COGNIS_SUPPORT_EMAIL", CognisBrand.support_email),
        docs_url=os.environ.get("COGNIS_DOCS_URL", CognisBrand.docs_url),
        portal_url=os.environ.get("COGNIS_PORTAL_URL", CognisBrand.portal_url),
        banner_color_primary=os.environ.get(
            "COGNIS_BANNER_COLOR_PRIMARY", CognisBrand.banner_color_primary
        ),
        banner_color_accent=os.environ.get(
            "COGNIS_BANNER_COLOR_ACCENT", CognisBrand.banner_color_accent
        ),
    )


def resolve_banner_color(name: str) -> str | None:
    """Return ``name`` if rich can parse it as a color, else ``None``.

    Safe-fallback contract per gate2 ops verification (B1): banner renderers
    pass the env-driven color through this resolver and emit *uncolored*
    output when it returns ``None`` — a typo'd ``COGNIS_BANNER_COLOR_*``
    (or a missing rich install) must never raise ``ColorParseError`` at the
    customer. Branding-off output is unaffected: this is only consulted
    behind the ``branding_enabled()`` gate.
    """
    if not name:
        return None
    try:
        from rich.color import Color

        Color.parse(name)
    except Exception:
        return None
    return name


def branding_enabled() -> bool:
    """True iff the operator opted into the Cognis overlay.

    Default is OFF so a fork checkout still passes upstream parity tests
    that compare exact stdout. Production deploys set ``COGNIS_BRANDING=on``
    in the container env (set by ``Dockerfile.cognis``).
    """
    raw = os.environ.get("COGNIS_BRANDING", "").strip().lower()
    return raw in ("on", "true", "1", "yes")
