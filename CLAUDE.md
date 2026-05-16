# Cognis Ops — repo context for Claude

This is a soft fork of `Tracer-Cloud/opensre` (open-source SRE / DevOps / on-call AI agent — automated incident investigation and RCA from Slack / Grafana / Datadog / PagerDuty / Sentry / cloud alerts). **The fork is not the product — `cognis-platform/apps/bridge` is.** Every hour spent editing upstream Python here costs 3× at next rebase.

Upstream's `AGENTS.md` (preserved at the repo root) is the canonical contributor reference for the upstream codebase — repo map, entry points (adding a Tool, Node, Integration), test commands, footguns. Read it for codebase orientation. This file (`CLAUDE.md`) carries the **Cognis-specific** posture.

## Branches

- `cognis/main` — default. Cognis work.
- `vendor/upstream` — mirror of `Tracer-Cloud/opensre:main`. NEVER edit.

## Hard rules

1. **Never `import openai` / `import anthropic` / `import litellm` directly.** Upstream `pyproject.toml` declares `anthropic` + `openai` + `langchain-anthropic` + `langchain-openai` as deps. The fork must route all LLM calls through `@cognis/llm-client` → `llm.cognisai.com` (LiteLLM proxy) so observability (Langfuse OTel), billing meters, and per-tenant key resolution all work. Bridge injects the gateway URL + tenant API key at runtime; the bot only sees an OpenAI-compatible endpoint. ESLint-equivalent grep gates live in CI.
2. **Never edit upstream Python casually.** Prefer wrapping (subclassing `BaseTool`, registering new tools / nodes via the upstream-sanctioned discovery in `app/tools/` + `app/nodes/` + `app/pipeline/graph.py`, environment-variable swaps, Bridge-side config injection) over surgical edits. If you must touch an upstream file, the PR upstream is **mandatory** before merging to `cognis/main`.
3. **Per-tenant integration secrets live in Bridge — NEVER in this repo.** PagerDuty, Datadog, Slack, Grafana, Sentry, AWS/GCP/Azure cloud creds, Kubernetes kubeconfigs, MongoDB / MySQL / Postgres connection strings, Discord / Telegram tokens — all envelope-encrypted in Bridge (`org_integrations` table), fetched at session start, held in-memory for the bot run, rotated on schedule. Any PR that adds plaintext-secret handling to this repo fails review. `.env`-style local-dev secrets are fine; production wiring is Bridge-only.
4. **Multi-tenant routing is Bridge's job, not the fork's.** Bridge resolves `org_id` from a Clerk JWT, builds a tenant-scoped runtime config (integration credentials + plan limits + audit context), and hands it to the bot. The fork stays single-tenant-shaped per running session — no tenant-switching logic in this repo.
5. **Billing meters go to Bridge `usage_events`.** Every alert-investigated / RCA-generated event must emit a `usage_events` row via Bridge's ingest endpoint. Don't add an in-process billing table here.
6. **Audit logs go to Bridge `audit_log`.** Same pattern — emit events, don't store.
7. **Fork-diff cap: 5% of upstream LOC.** Tracked per-PR. Target ≤3% (Hummingbot-tier — single-language Python fork without legacy /enterprise to strip, so we should be able to stay tight).
8. **Commit prefixes only:** `fork:` / `brand:` / `wire:` / `ci:` / `docs:`.
9. **License posture: Apache-2.0 only.** Upstream is single-tier Apache-2.0; do not introduce dependencies under AGPL, GPL-3, SSPL, BUSL, FSL, PolyForm, Commons Clause, Elastic License, or "Sustainable Use License" / "Open WebUI License" / etc. License-gate CI catches this on PR (`tools/check_no_proprietary.py` + ScanCode).
10. **Don't run `pip install` / `uv sync` from Claude.** Platform-owner instruction: no dependency installs from agent sessions. Fork-bootstrap and routine Claude work are git-topology + file-edit only.

## Stack (upstream)

- **Python 3.13** (`pyproject.toml` requires ≥3.12, `.tool-versions` pins 3.13.11)
- **uv 0.11.x** for env + deps (`uv sync`, `uv run opensre …`)
- **setuptools** build backend (`pyproject.toml`)
- **LangGraph 1.1.x** agent runtime (`langgraph.json` deploys to LangSmith / LangGraph Cloud — Cognis side will repoint or replace)
- **FastAPI** for the web surface; **click + rich + questionary + prompt_toolkit** for the CLI
- **pydantic v2** for state contracts; **pydantic-settings v2** for config
- **OpenTelemetry** SDK (api / sdk / OTLP-HTTP exporter / instrumentation-botocore / instrumentation-requests) — already wired
- **MCP** server entrypoint (`app/entrypoints/`)
- **ruff** lint + **mypy** type-check + **pytest** (with `pytest-asyncio`, `pytest-cov`, `pytest-xdist`)
- **`Makefile`** is the canonical local automation (`make install`, `make lint`, `make typecheck`, `make test-cov`, `make check`)

### Upstream layout (from `AGENTS.md`)

- `app/cli/` — CLI entrypoint (`opensre …`)
- `app/nodes/` — LangGraph nodes (alert extraction, investigation, diagnosis, publishing)
- `app/pipeline/` — graph assembly + routing
- `app/tools/` — tool registry (auto-discovers modules); `BaseTool` subclasses or `@tool` decorator
- `app/integrations/` — Datadog / Grafana / Slack / PagerDuty / Sentry / AWS / GCP / Kubernetes / Discord / Telegram / MongoDB / Kafka / ClickHouse config + verification
- `app/services/` — per-vendor API clients (e.g. `app/services/datadog/client.py`)
- `app/state/` — agent + investigation state models
- `app/entrypoints/` — SDK and MCP entrypoints
- `app/deployment/` — Railway / LangSmith / LangGraph deployment helpers (Cognis side will likely replace)
- `app/auth/` — JWT + auth helpers (Cognis side wires Clerk through here via Bridge)

## Cognis-specific surface (to be built in productization phase — Phase 7?)

Planned, all under `app/cognis/` (a single Cognis subpackage to keep fork-diff localized):

- `app/cognis/bridge_client.py` — Bridge API client (resolve `org_id` from Clerk JWT, fetch envelope-decrypted integration secrets, fetch plan-scoped limits, emit `usage_events` + `audit_log`)
- `app/cognis/auth.py` — Clerk JWT validator hook installed at `app/auth/` extension point (only if direct opensre HTTP/MCP access is offered; default = Pattern A through Bridge proxy)
- `app/cognis/llm_routing.py` — patch the LangChain provider factories to point at `llm.cognisai.com` with the per-tenant Cognis gateway key (defense-in-depth wrapper; Bridge injects env vars too)
- `app/cognis/integration_loader.py` — replace `app/integrations/store.py`-style local YAML with Bridge-fetched config
- `app/cognis/branding/` — Cognis CLI banner, default agent display names, RCA report header

What lives on `cognis/main` **today** (post-bootstrap, before productization):

- `FORK.md`, `CLAUDE.md`, `CODEOWNERS` — fork meta (this file is one of them)
- `.github/workflows/license-gate.yml` — ScanCode allowlist enforcement
- `.github/workflows/upstream-rebase.yml` — nightly rebase bot (cron disabled at bootstrap)
- `tools/check_no_proprietary.py` — license allowlist enforcement script

## Build & test

This is upstream opensre tooling — see `AGENTS.md` and `Makefile`. Common targets:

- `make install` — `uv sync` + editable install
- `make lint`, `make format-check`, `make typecheck`
- `make test-cov` — non-live unit suite (fast loop)
- `make verify-integrations`, `make test-rca`, `make test-synthetic`, `make test-full`
- `uv run opensre …` — invoke the CLI

**Don't run any of these from Claude** — they're for human contributors.

## Auth pattern with Bridge

Default = **Pattern A (Bridge proxy)**. Cognis portal calls Bridge; Bridge holds Clerk JWT validation + per-tenant config; Bridge dispatches an opensre run by either (a) starting an ephemeral worker with a tenant-scoped env / config blob, or (b) calling opensre's MCP / HTTP endpoint with a short-lived service token Bridge itself minted. Tenant secrets never reach the customer browser; tenant integrations never live on disk in this repo's filesystem.

Pattern B (direct opensre dashboard with Clerk auth in the fork) only if a future product decision requires it. One file: `app/cognis/auth.py`.

## Cost policy

This fork inherits Cognis's managed-SaaS cost policy — see `../cognis-platform/docs/specs/cost-policy.md` for the full per-fork list and rationale. For `cognis-ops` specifically, in production deploys DO NOT set: `LANGSMITH_API_KEY`, `SENTRY_DSN`. The upstream LangSmith deps stay inert without the key; LangSmith → Langfuse is a productization-time code swap tracked separately.

## What NOT to do

- Don't `import openai` / `import anthropic` / `import litellm` directly here — route through Bridge / `@cognis/llm-client`
- Don't add Bridge / billing / multi-tenant logic to this repo — that's in `cognis-platform/apps/bridge`
- Don't touch `vendor/upstream` directly — it's a mirror branch
- Don't commit credentials. Tenant integration secrets NEVER live in this repo. `.env` is gitignored upstream; `.env.example` is the template
- Don't switch off `ruff` / `mypy` / `pytest` — keep upstream's tooling to minimize rebase friction
- Don't edit Cython / C-extension files (opensre is pure Python today — but if upstream adds any, treat them like Hummingbot's Cython: avoid)
- Don't enable the nightly rebase cron until the first manual `workflow_dispatch` run has been verified clean — opensre's release pace can be noisy (large dependabot churn observed in remote branches at fork time)
- Don't run pip / uv / poetry installs from Claude (platform-owner instruction)
- Don't add a NestJS / Node / TS surface here — opensre is pure Python; Bridge handles the cross-product wiring
- Don't introduce a SaaS dep without checking the license allowlist (CI catches it on PR, but check at design time)
- Don't restore `app/deployment/methods/railway/` (or similar) wiring into Cognis runs — Cognis runs in our own infra
