# Fork of Tracer-Cloud/opensre

This repo is a **soft fork** of [`Tracer-Cloud/opensre`](https://github.com/Tracer-Cloud/opensre), maintained as `cognis-ops` under the Cognis AI platform. License posture: Apache-2.0 throughout — upstream is single-tier Apache-2.0 (copyright 2026 Tracer Cloud), no Commons Clause / SSPL / BUSL rider, no enterprise/proprietary directory to strip at fork time.

`cognis-ops` is the AI-worker product for **SRE / DevOps / on-call teams** — automated incident investigation, alert triage, and root-cause analysis. It joins Support / Hire / Concierge / Voice / Trade in the customer-facing line; Cognis Brain (vLLM / RAGFlow / Axolotl) is the internal infra tier underneath. See [`cognis-platform`](https://github.com/cognis-ai/cognis-platform) for the shared brain (Bridge, LiteLLM proxy, Clerk auth, billing).

## Branches

| Branch | Purpose |
|---|---|
| `vendor/upstream` | Mirror of `Tracer-Cloud/opensre:main`. NEVER edit. Rebased by the nightly bot. |
| `cognis/main` | Cognis work. Rebased monthly onto `vendor/upstream`. Default branch. |

## Commit prefixes (grep-friendly across rebases)

- `fork:` — surgical edits to upstream files (last resort; prefer Bridge integration)
- `brand:` — branding (CLI banner, default prompts, logos)
- `wire:` — Cognis integration plumbing (Clerk-via-Bridge auth, `@cognis/llm-client` routing, Bridge API calls for tenant config / integration secret resolution)
- `ci:` — GitHub Actions, license gate, rebase bot
- `docs:` — FORK.md, CLAUDE.md, CODEOWNERS, READMEs

## License-trap status

Verified 2026-05-13 at upstream SHA `c67ab17f22d60fef5c8a4e2b651de95f79940d29`:

- `LICENSE` is plain Apache-2.0 (Copyright 2026 Tracer Cloud). No Commons Clause rider, no addendum, no separate `COPYING` / `NOTICE` files.
- No `enterprise/`, `ee/`, `cloud/`, `pro/`, `premium/`, `commercial/`, `saas/`, `platform/` directories at any depth in the upstream tree (verified via `git ls-tree -d -r upstream/main`).
- Top-level upstream tree: `.claude/`, `.cursor/`, `.devcontainer/`, `.github/`, `.understand-anything/`, `app/`, `docs/`, `infra/`, `packaging/`, `scripts/`, `tests/`. All Apache-2.0.
- `pyproject.toml` declares only standard optional extras (`dev`, `opensre-hub`, `kafka`, `clickhouse`, `postgresql`, `azure_sql`) — no premium / pro / enterprise extras group.
- `README.md` contains no commercial-license or proprietary-feature language.

If upstream introduces an `enterprise/`, `pro/`, `cloud/`, or equivalent directory in a future rebase, the strip happens in a **separate commit** before merging — same doctrine as `cognis-support`.

## Productization notes (Phase 7 staging)

For the eventual Phase 7 productization plan doc:

- **Stack:** Python 3.13 (3.12+ required), uv-managed deps (`uv sync`), `setuptools` build backend, LangGraph 1.x agent runtime, FastAPI + click CLI (`opensre`), pydantic v2, OpenTelemetry SDK.
- **Direct LLM SDK deps in upstream:** `anthropic`, `openai`, `langchain-anthropic`, `langchain-openai`, `langsmith`. **These need wrapping through `@cognis/llm-client` → `llm.cognisai.com` proxy** — same pattern as every other Cognis product. The fork doesn't import these directly today; Bridge will inject a config that routes via the gateway.
- **SaaS deps noted in passing (full survey deferred):**
  - `langsmith` — LangChain's hosted tracing. Likely replace with Langfuse via OTel (Cognis platform standard).
  - `sentry-sdk` — error reporting. Either keep, or route to Cognis's own Sentry org, or drop in favor of OTel + Langfuse.
  - `boto3` / AWS — fine as a tenant-credentialed integration (Bridge holds the keys).
  - `google-api-python-client` / `google-auth` — tenant Google Workspace integration.
  - `pymongo`, `pymysql`, `psycopg2-binary` (optional), `pyodbc` (optional), `clickhouse-connect` (optional), `confluent-kafka` (optional) — these are tenant data-store integrations, not Cognis runtime deps. Keep gated behind extras.
  - `kubernetes` — first-class SRE primitive. Stays.
- **Investigation surface (Slack, Grafana, Datadog, Discord, Telegram, AWS, GCP, Kubernetes, Sentry) is the productizable surface.** Per-tenant integration credentials and connection configs live in Bridge — never in this repo's `conf/`, never in `.env`, never on disk in the bot's filesystem.
- **MCP entrypoints** (`app/entrypoints/`) — opensre exposes itself as an MCP server. Will likely be one Cognis productization surface.

## Fork-diff target

≤3% of upstream LOC (default per fork-ops.md). Tracked on every PR via `git diff vendor/upstream...cognis/main --stat`. Hard cap 5% — build fails above that.

Most Cognis-specific logic stays out of the fork:

- **Per-tenant integration secrets (PagerDuty / Datadog / Slack / Grafana / cloud creds)** → Bridge (`org_integrations` table, envelope-encrypted at rest).
- **LLM routing** → `@cognis/llm-client` → `llm.cognisai.com` (LiteLLM proxy with Langfuse OTel observability).
- **Billing meters (alerts investigated / RCAs generated)** → Bridge `usage_events` ingest.
- **Audit logs** → Bridge `audit_log` table.
- **Multi-tenant routing** → Bridge resolves `org_id` from Clerk JWT, hands a tenant-scoped runtime config to the bot.

## Rebase cadence

- Nightly bot: `.github/workflows/upstream-rebase.yml` (workflow lives on `cognis/main`; cron is **commented out** at bootstrap — flip it on AFTER the first manual `workflow_dispatch` run confirms a clean rebase against opensre's pace).
- Auto-merge clean rebases via Mergify (configured at platform level once first rebase lands).
- Conflicts → bot opens issue labeled `rebase-conflict`; human review.
- Shared `rerere-cache` committed to `cognis-platform/infra/rerere-cache/cognis-ops/` once the first conflict is resolved.

## Upstream-PR policy

Contribute back to `Tracer-Cloud/opensre` *before* merging to `cognis/main`:

- Bug fixes, perf patches, test improvements, type fixes
- New integration / tool support (the upstream community benefits, and we shrink fork diff)
- Refactors that shrink fork diff

Keep in fork (do NOT upstream):

- Clerk / Stripe / LiteLLM-gateway / Cognis-branded code
- Bridge client + per-tenant credential plumbing
- Cognis billing-meter integration
- Cognis audit-log wiring

## References

- Fork-ops doctrine: `cognis-platform/docs/specs/fork-ops.md`
- Bridge integration spec: `cognis-platform/docs/specs/bridge-service.md`
- LLM gateway: `cognis-platform/docs/specs/ai-gateway.md`
- Upstream contributor doc: `AGENTS.md` in this repo (preserved from upstream)
