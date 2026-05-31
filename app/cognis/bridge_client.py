"""Cognis Bridge HTTP client (async, httpx-based).

The cognis-ops fork uses this to talk to Cognis Bridge:

- ``GET /ops-bot/config`` — fetch tenant config (decrypted integration
  secrets, plan caps, LLM gateway URL + key, system prompt) on bot startup
  and on every poll interval.
- ``POST /ops-bot/events`` — report lifecycle events back to Bridge so the
  portal shows live status (bot_started, investigation_started,
  investigation_completed, error, etc.).
- ``POST /ops-bot/investigations`` — upsert an investigation as the
  LangGraph pipeline runs. Dedupe by externalId.

Auth: ``X-Cognis-Ops-Token: <token>`` header. Token is provisioned by Bridge
at tenant-create time and surfaced ONCE to the customer; they paste it into
the bot env as ``COGNIS_OPS_API_TOKEN``. Rotation is via the portal's
admin rotate-bot-token endpoint.

The bot must NEVER persist decrypted integration secrets to disk — they
live in memory for the bot session lifetime.

Uses httpx, an upstream opensre dependency already in pyproject.toml. No
new install required, no rebase risk from a new dep.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional

import httpx

logger = logging.getLogger(__name__)


class CognisBridgeError(RuntimeError):
    """Any failure talking to Cognis Bridge."""

    def __init__(self, message: str, *, status: Optional[int] = None) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class Integration:
    id: str
    kind: str
    label: str
    secrets: Mapping[str, Any]
    config: Mapping[str, Any]
    fingerprint: str


@dataclass(frozen=True)
class OpsCaps:
    max_concurrent_investigations: int
    max_integrations: int
    retention_days: int
    allow_live_integrations: bool
    allowed_integration_kinds: Optional[List[str]]
    daily_investigation_cap: int


@dataclass(frozen=True)
class LlmGateway:
    base_url: str
    api_key: str
    smart_model: str
    fast_model: str
    embed_model: Optional[str]


@dataclass(frozen=True)
class BotConfig:
    cognis_org_id: str
    plan: str
    caps: OpsCaps
    system_prompt: str
    prompt_version: str
    integrations: List[Integration]
    llm_gateway: LlmGateway
    server_time: str
    poll_interval_seconds: int = 30

    def integration_for(self, kind: str, label: Optional[str] = None) -> Optional[Integration]:
        for i in self.integrations:
            if i.kind == kind and (label is None or i.label == label):
                return i
        return None


class BridgeClient:
    """Async client wrapping the Cognis Bridge /ops-bot/* surface."""

    def __init__(
        self,
        bridge_url: str,
        bot_token: str,
        *,
        timeout_s: float = 15.0,
    ) -> None:
        if not bridge_url:
            raise CognisBridgeError("bridge_url is empty")
        if not bot_token or len(bot_token) < 16:
            raise CognisBridgeError("bot_token is empty or too short")
        self._bridge_url = bridge_url.rstrip("/")
        self._bot_token = bot_token
        self._timeout = httpx.Timeout(timeout_s, connect=3.0)
        self._client = httpx.AsyncClient(
            base_url=self._bridge_url,
            timeout=self._timeout,
            headers={"X-Cognis-Ops-Token": bot_token, "Accept": "application/json"},
        )

    @classmethod
    def from_env(cls) -> "BridgeClient":
        bridge_url = os.environ.get("COGNIS_BRIDGE_URL", "").strip()
        bot_token = os.environ.get("COGNIS_OPS_API_TOKEN", "").strip()
        if not bridge_url:
            raise CognisBridgeError(
                "COGNIS_BRIDGE_URL is unset. Set it to your Cognis Bridge "
                "URL (e.g. https://bridge.cognisai.com) before launching the bot."
            )
        if not bot_token:
            raise CognisBridgeError(
                "COGNIS_OPS_API_TOKEN is unset. Get a fresh token from the "
                "Cognis portal (Ops → Settings → Rotate bot token) and paste "
                "it into your bot env."
            )
        return cls(bridge_url, bot_token)

    async def fetch_config(self) -> BotConfig:
        try:
            resp = await self._client.get("/ops-bot/config")
        except httpx.HTTPError as err:
            raise CognisBridgeError(f"network: {err}") from err
        if resp.is_error:
            raise CognisBridgeError(
                f"fetch_config -> {resp.status_code}: {resp.text[:300]}",
                status=resp.status_code,
            )
        return _parse_bot_config(resp.json())

    async def post_events(self, events: List[Dict[str, Any]]) -> int:
        if not events:
            return 0
        try:
            resp = await self._client.post("/ops-bot/events", json={"events": events})
        except httpx.HTTPError as err:
            raise CognisBridgeError(f"network: {err}") from err
        if resp.is_error:
            raise CognisBridgeError(
                f"post_events -> {resp.status_code}: {resp.text[:300]}",
                status=resp.status_code,
            )
        body = resp.json()
        return int(body.get("accepted", 0))

    async def upsert_investigation(
        self,
        *,
        external_id: Optional[str],
        source: str,
        title: str,
        alert_payload: Dict[str, Any],
        status: Optional[str] = None,
        summary: Optional[str] = None,
        rca_payload: Optional[Dict[str, Any]] = None,
        last_error_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "source": source,
            "title": title,
            "alertPayload": alert_payload,
        }
        if external_id:
            body["externalId"] = external_id
        if status:
            body["status"] = status
        if summary is not None:
            body["summary"] = summary
        if rca_payload is not None:
            body["rcaPayload"] = rca_payload
        if last_error_message is not None:
            body["lastErrorMessage"] = last_error_message
        try:
            resp = await self._client.post("/ops-bot/investigations", json=body)
        except httpx.HTTPError as err:
            raise CognisBridgeError(f"network: {err}") from err
        if resp.is_error:
            raise CognisBridgeError(
                f"upsert_investigation -> {resp.status_code}: {resp.text[:300]}",
                status=resp.status_code,
            )
        return resp.json()

    async def aclose(self) -> None:
        await self._client.aclose()


def _parse_bot_config(raw: Mapping[str, Any]) -> BotConfig:
    caps_raw = raw.get("caps") or {}
    allowed_raw = caps_raw.get("allowedIntegrationKinds")
    caps = OpsCaps(
        max_concurrent_investigations=int(caps_raw.get("maxConcurrentInvestigations") or 1),
        max_integrations=int(caps_raw.get("maxIntegrations") or 1),
        retention_days=int(caps_raw.get("retentionDays") or 7),
        allow_live_integrations=bool(caps_raw.get("allowLiveIntegrations", False)),
        allowed_integration_kinds=(
            [str(k) for k in allowed_raw] if isinstance(allowed_raw, list) else None
        ),
        daily_investigation_cap=int(caps_raw.get("dailyInvestigationCap") or 5),
    )

    gateway_raw = raw.get("llmGateway") or {}
    gateway = LlmGateway(
        base_url=str(gateway_raw.get("baseUrl", "")),
        api_key=str(gateway_raw.get("apiKey", "")),
        smart_model=str(gateway_raw.get("smartModel", "cognis-smart")),
        fast_model=str(gateway_raw.get("fastModel", "cognis-fast")),
        embed_model=(str(gateway_raw["embedModel"]) if gateway_raw.get("embedModel") else None),
    )

    integrations_raw = raw.get("integrations") or []
    integrations = [
        Integration(
            id=str(i.get("id", "")),
            kind=str(i.get("kind", "")),
            label=str(i.get("label", "")),
            secrets=(i.get("secrets") or {}),
            config=(i.get("config") or {}),
            fingerprint=str(i.get("fingerprint", "")),
        )
        for i in integrations_raw
        if isinstance(i, dict) and i.get("id")
    ]

    return BotConfig(
        cognis_org_id=str(raw.get("cognisOrgId", "")),
        plan=str(raw.get("plan", "free")),
        caps=caps,
        system_prompt=str(raw.get("systemPrompt", "")),
        prompt_version=str(raw.get("promptVersion", "v1")),
        integrations=integrations,
        llm_gateway=gateway,
        server_time=str(raw.get("serverTime", "")),
        poll_interval_seconds=int(raw.get("pollIntervalSeconds") or 30),
    )
