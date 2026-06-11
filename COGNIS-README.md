# Cognis Ops

Investigates incidents, publishes the RCA.

Cognis Ops is the SRE / incident-response worker of the [Cognis AI](https://cognisai.com) platform. You hire it like an employee, wire it to your alerting stack (PagerDuty, Datadog, Grafana, Slack, Sentry, cloud), and it picks up alerts, walks your logs and metrics, and hands you the root cause + a recommended next step.

This repo is the **runtime binary** customers run on their own infrastructure. Strategies, integration credentials, plan caps, and audit history live in the [Cognis portal](https://app.cognisai.com/dashboard/ops) — the bot pulls them from Cognis Bridge over HTTPS on startup.

---

## What's in this repo

This is a soft fork of [`Tracer-Cloud/opensre`](https://github.com/Tracer-Cloud/opensre). The upstream is excellent (LangGraph pipeline, broad integration catalog); the Cognis layer adds: <!-- upstream-ok -->

- A **central control plane**: integrations, plan caps, and investigations are managed in one portal across every Cognis Ops instance you run.
- **Per-tenant integration secrets, envelope-encrypted at rest** in Cognis Bridge. The bot decrypts in-memory only.
- **Plan-tier safety caps** enforced both server-side (Bridge) and bot-side. A bug in one can't bypass the other.
- **LLM calls routed through `llm.cognisai.com`** (LiteLLM proxy) so observability (Langfuse), per-tenant billing, and the no-direct-provider rule all hold without code edits.
- **No telemetry leak**: `SENTRY_DSN` + `LANGSMITH_API_KEY` left unset by the Cognis Dockerfile per `cognis-platform/docs/specs/cost-policy.md`.

The fork stays close to upstream. Everything Cognis-specific lives under `app/cognis/`, `Dockerfile.cognis`, and `COGNIS-README.md`. The rest is upstream opensre, rebased monthly. <!-- upstream-ok -->

---

## Quick start

### Docker (recommended)

```bash
docker run --rm \
  -e COGNIS_BRIDGE_URL=https://bridge.cognisai.com \
  -e COGNIS_OPS_API_TOKEN=<your bot token> \
  -v $(pwd)/cognis-ops-logs:/var/log/cognis-ops \
  cognis/ops:latest
```

The bot will:

1. Connect to Cognis Bridge with your token.
2. Fetch tenant config (integrations, plan caps, system prompt, LLM gateway URL + key).
3. Pin `OPENAI_API_BASE` / `ANTHROPIC_BASE_URL` / `OPENAI_API_KEY` to route every LLM call through `llm.cognisai.com`.
4. Start the upstream LangGraph runtime with the integration env loaded from Bridge.
5. Report investigation lifecycle events back so the portal shows live status.

### From source

Requires Python 3.13 and `uv`. See upstream [`AGENTS.md`](./AGENTS.md) for the conda setup, then:

```bash
# Bridge-managed mode (the production path)
export COGNIS_BRANDING=on
export COGNIS_BRIDGE_URL=https://bridge.cognisai.com
export COGNIS_OPS_API_TOKEN=<your bot token from the portal>
python -m app.cognis.cli

# Stock upstream parity mode (no Cognis env set)
python -m app.cognis.cli   # falls through to the upstream CLI
```

### Getting a bot token

In the [Cognis portal](https://app.cognisai.com/dashboard/ops):

1. Open Settings → "Connect your bot".
2. Click "Generate bot token". The token shows once — copy it immediately.
3. Paste it into your bot's `COGNIS_OPS_API_TOKEN` env.

Rotating the token immediately invalidates the previous one.

---

## How integrations work

You add integrations in the portal, not in YAML on the bot host. The bot fetches them from Bridge on every config poll (default 30s) and uses them to talk to your stack.

| Surface       | Common kinds |
|---------------|--------------|
| Alerting      | `pagerduty`, `betterstack`, `splunk`, `newrelic` |
| Observability | `datadog`, `grafana`, `sentry`, `loki`, `victoriametrics`, `elastic` |
| Cloud         | `aws`, `gcp`, `azure`, `kubernetes` |
| Code / SCM    | `github`, `gitlab`, `bitbucket` |
| Chat          | `slack`, `discord`, `telegram` |
| Data          | `clickhouse`, `kafka`, `mongodb`, `mysql`, `postgres`, `azure_sql` |
| Workflow      | `airflow` |

Each integration is a `(kind, label)` pair with a JSON secrets blob (envelope-encrypted) and a JSON config blob (plaintext — never put secrets there). The portal's "Add integration" form prefills the expected shape per kind.

---

## Plan caps

| Plan       | Max integrations | Concurrent investigations | Daily cap | Retention | Live actions |
|------------|------------------|---------------------------|-----------|-----------|--------------|
| Free       | 1 (Slack or PagerDuty) | 1                    | 5         | 7 days    | No (read-only) |
| Starter    | 5                | 2                         | 100       | 30 days   | Yes          |
| Pro        | 20               | 5                         | 1,000     | 90 days   | Yes          |
| Enterprise | 200              | 25                        | 100,000   | 1 year    | Yes          |

Bridge enforces these. The bot re-validates server-side caps on every config poll.

---

## Safety rules

These are baked into the system prompt the bot loads from Bridge (`COGNIS_OPS_PROMPT_V1`):

- **Never run write actions** (kubectl apply, terraform apply, restart, deploy, rollback, kill, delete) without an explicit operator confirmation recorded as an audit event.
- **Never exfiltrate secrets in RCA output.** If the bot observes a token / API key / password in a log line, it masks it (`****`) and notes the mask was applied.
- **Never cross tenants.** Investigations are scoped to one operator's organization.
- **Be honest about uncertainty.** "I am not sure — here is what I checked" beats invented facts.

---

## License

Apache-2.0 throughout. Upstream's LICENSE applies to the opensre codebase; the Cognis layer (`app/cognis/`, `Dockerfile.cognis`, `COGNIS-README.md`) is Apache-2.0 as well, copyright Cognis AI. <!-- upstream-ok -->

---

## Support

- **Docs**: <https://cognisai.com/docs/ops>
- **Portal**: <https://app.cognisai.com/dashboard/ops>
- **Support**: <support@cognisai.com>
- **Upstream community** (for opensre-specific questions): see upstream's README. <!-- upstream-ok -->
