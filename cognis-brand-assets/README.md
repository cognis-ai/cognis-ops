# Cognis Ops brand assets

Cognis Ops is CLI-only — the brand surfaces this fork ships are:

- `app/cognis/cli.py` — Cognis CLI wrapper that prints the banner and pins the LLM gateway env before deferring to upstream's `opensre` CLI.
- `app/cognis/branding/banner.py` — text banner (no SVGs needed).
- `Dockerfile.cognis` — sets `COGNIS_BRANDING=on` + brand env defaults, leaves `SENTRY_DSN` / `LANGSMITH_API_KEY` unset per cost-policy.md.
- `COGNIS-README.md` — customer-facing README overlay.

Reserved for future assets (favicon if a future dashboard page lives here, social-card SVG, splash image for a v1.5 web UI mode).

The upstream `README.md` and `docs/logo/opensre-logo-white.svg` are left untouched to keep rebase-diff minimal. The portal's "Connect your bot" wizard links to `COGNIS-README.md`, not `README.md`.
