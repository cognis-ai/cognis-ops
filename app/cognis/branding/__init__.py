"""Cognis Ops branding — CLI banner + brand identity constants.

Two surfaces:
- ``cognis_brand`` — env-driven product brand strings.
- ``banner`` — Cognis CLI banner printer; called by the wrapper entry
  before deferring to upstream's ``opensre`` CLI.

Both are safe to import without any Cognis env set (they fall back to
sensible defaults so the upstream `opensre` CLI works for parity-testing).
Production deploys MUST set ``COGNIS_BRANDING=on`` so the banner replaces
upstream's banner; otherwise the customer sees opensre/OpenSRE copy and the
brand promise breaks. See feedback_full_cognis_branding memory.
"""

__all__ = ["cognis_brand", "banner"]
