"""Cognis Ops — CLI wrapper.

The customer-facing entrypoint. Two paths:
1. If ``COGNIS_BRIDGE_URL`` + ``COGNIS_OPS_API_TOKEN`` are set, prints the
   Cognis banner, fetches the tenant config from Bridge (just to verify
   credentials), then defers to upstream's ``opensre`` CLI with the
   integration env vars Bridge hands back.
2. Otherwise, defers straight to upstream's ``opensre`` CLI (parity mode).

Wired via pyproject.toml as ``cognis-ops = "app.cognis.cli:main"`` in the
Dockerfile.cognis layer; the upstream ``opensre`` entrypoint stays untouched
on cognis/main so rebases against opensre's master don't conflict.
"""

from __future__ import annotations

import asyncio
import os
import sys

from app.cognis.branding.banner import cognis_log_prefix, print_cognis_banner
from app.cognis.branding.cognis_brand import branding_enabled, load_brand


def _bridge_mode_configured() -> bool:
    return bool(os.environ.get("COGNIS_BRIDGE_URL")) and bool(os.environ.get("COGNIS_OPS_API_TOKEN"))


async def _verify_bridge_credentials() -> None:
    """Fail fast on bad credentials before invoking the upstream CLI."""
    from app.cognis.bridge_client import BridgeClient, CognisBridgeError

    client = BridgeClient.from_env()
    try:
        cfg = await client.fetch_config()
    except CognisBridgeError as err:
        sys.stderr.write(
            f"{cognis_log_prefix()}: failed to fetch initial config from Cognis Bridge: {err}\n"
        )
        raise SystemExit(2) from err
    finally:
        await client.aclose()
    brand = load_brand()
    if branding_enabled():
        sys.stdout.write(
            f"{cognis_log_prefix()}: connected to Bridge as org={cfg.cognis_org_id} "
            f"plan={cfg.plan} integrations={len(cfg.integrations)}\n"
            f"{cognis_log_prefix()}: pin OPENAI_API_BASE={cfg.llm_gateway.base_url} so the "
            f"LangGraph LLM calls route through the Cognis gateway. The bot's API key for the "
            f"gateway is in the Bridge config response; set it as OPENAI_API_KEY in the upstream "
            f"opensre process env.\n"
            f"{cognis_log_prefix()}: portal {brand.portal_url}\n"
        )
    # Pin the LLM gateway env so the upstream opensre process uses the
    # LiteLLM proxy for any direct openai/anthropic SDK calls. Defense in
    # depth: cognis-platform/docs/specs/cost-policy.md asks for this at
    # deploy time, but pinning here is belt-and-suspenders.
    os.environ.setdefault("OPENAI_API_BASE", cfg.llm_gateway.base_url)
    os.environ.setdefault("OPENAI_API_KEY", cfg.llm_gateway.api_key)
    os.environ.setdefault("ANTHROPIC_BASE_URL", cfg.llm_gateway.base_url)


def _run_upstream_cli() -> int:
    """Invoke upstream opensre's CLI main. Returns its exit code."""
    from app.cli.__main__ import main as upstream_main  # noqa: WPS433 — lazy import

    rc = upstream_main()
    return int(rc) if isinstance(rc, int) else 0


def main(argv: list[str] | None = None) -> int:
    if argv is not None:
        sys.argv = ["cognis-ops", *argv]
    print_cognis_banner()
    if _bridge_mode_configured():
        asyncio.run(_verify_bridge_credentials())
    elif branding_enabled():
        sys.stdout.write(
            f"\n{cognis_log_prefix()}: no Bridge credentials set "
            f"(COGNIS_BRIDGE_URL + COGNIS_OPS_API_TOKEN). Falling back to upstream opensre CLI. "
            f"Connect via the Cognis portal to manage integrations + plan caps centrally.\n\n"
        )
    return _run_upstream_cli()


if __name__ == "__main__":
    raise SystemExit(main())
