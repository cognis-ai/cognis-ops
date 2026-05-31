"""Cognis Ops — productization surface for the cognis-ops fork.

This package is the *only* Cognis-specific code in the fork. Everything else
under ``app/`` is upstream opensre, untouched. The contract:

- ``bridge_client.BridgeClient`` — async HTTP client to Cognis Bridge for
  fetching tenant config (decrypted integration secrets, risk caps, LLM
  gateway), reporting lifecycle events, and upserting investigations as the
  LangGraph pipeline runs.
- ``branding.cognis_brand`` — env-driven brand strings (product name, support
  email, banner colours) consumed by the CLI banner + log prefixes.
- ``branding.banner`` — Cognis CLI banner printer; called from the wrapper
  entrypoint before deferring to upstream's CLI startup.

NEVER import ``openai``, ``anthropic``, ``litellm``, or any LLM SDK from this
package. The LLM gateway URL + per-tenant key come from Bridge via
``/ops-bot/config`` and the bot constructs an OpenAI-compatible client
against the LiteLLM proxy. Upstream's own LLM calls are already env-
configurable (``OPENAI_API_BASE`` / ``ANTHROPIC_BASE_URL`` etc.) — the
Dockerfile pins those at deploy time per cognis-platform/docs/specs/cost-policy.md.
"""

__all__ = ["bridge_client", "branding"]
