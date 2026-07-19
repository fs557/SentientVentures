"""Narrow provider boundary for the bounded council workflow.

Adapters deliberately do not make network requests unless explicitly configured with
credentials.  The deterministic provider is the local/test default.
"""
from __future__ import annotations

import json
import os
from typing import Any, Protocol, cast


class ProviderUnavailable(RuntimeError):
    """A configured live provider is not safe or available to use."""


class CouncilProvider(Protocol):
    def respond(self, role: str, prompt: str, payload: dict[str, object]) -> dict[str, object]: ...


class DeterministicFakeProvider:
    """A no-network provider whose Judge output is built by the council module."""

    def respond(self, role: str, prompt: str, payload: dict[str, object]) -> dict[str, object]:
        del prompt
        if role == "judge":
            return {"documents": payload["draft_documents"]}
        if role == "repair":
            return {"documents": payload["draft_documents"]}
        return {"role": role, "observations": ["Evidence was limited to supplied fact records."]}


def _analysis_schema() -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["observations"],
        "properties": {
            "observations": {
                "type": "array", "minItems": 1, "maxItems": 40,
                "items": {"type": "string", "minLength": 1, "maxLength": 500},
            },
        },
    }


def _evaluation_schema(registry_ids: list[str], fact_ids: list[str]) -> dict[str, object]:
    nullable_score = {"anyOf": [{"type": "integer", "minimum": 1, "maximum": 100}, {"type": "null"}]}
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["evaluations"],
        "properties": {
            "evaluations": {
                "type": "array", "minItems": 75, "maxItems": 75,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "score", "confidence", "assessment", "positiveArguments", "negativeArguments", "evidenceFactIds", "missingInformation"],
                    "properties": {
                        "id": {"type": "string", "enum": registry_ids},
                        "score": nullable_score,
                        "confidence": nullable_score,
                        "assessment": {"type": "string", "minLength": 1, "maxLength": 800},
                        "positiveArguments": {"type": "array", "minItems": 1, "maxItems": 3, "items": {"type": "string", "minLength": 1, "maxLength": 400}},
                        "negativeArguments": {"type": "array", "minItems": 1, "maxItems": 3, "items": {"type": "string", "minLength": 1, "maxLength": 400}},
                        "evidenceFactIds": {
                            "type": "array", "maxItems": 4,
                            "items": {"type": "string", "enum": fact_ids},
                        },
                        "missingInformation": {"type": "array", "maxItems": 4, "items": {"type": "string", "minLength": 1, "maxLength": 300}},
                    },
                },
            },
        },
    }


class OpenAIProvider:
    """Bounded OpenAI Responses adapter returning only strict JSON."""

    def __init__(self, model: str, api_key: str | None, client: object | None = None) -> None:
        if not api_key:
            raise ProviderUnavailable("openai credentials are not configured")
        if not model:
            raise ProviderUnavailable("openai model is not configured")
        if client is None:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
            except Exception as exc:
                raise ProviderUnavailable("openai client could not be initialized") from exc
        self.model = model
        self._client = client

    def respond(self, role: str, prompt: str, payload: dict[str, object]) -> dict[str, object]:
        request_payload = {key: value for key, value in payload.items() if key != "draft_documents"}
        registry = request_payload.get("registry", [])
        facts = request_payload.get("facts", [])
        registry_ids = [str(item["id"]) for item in registry if isinstance(item, dict) and isinstance(item.get("id"), str)]
        fact_ids = [str(item["id"]) for item in facts if isinstance(item, dict) and isinstance(item.get("id"), str)]
        schema = _evaluation_schema(registry_ids, fact_ids) if role in {"judge", "repair"} else _analysis_schema()
        role_instruction = (
            "Return all 75 registry items exactly once and in registry order. Use only supplied facts. "
            "Use evidenceFactIds only from supplied fact IDs. Set score and confidence to null when evidence is insufficient. "
            "Home items and portfolio-required items must have null scores. Scores use a 1–100 scale, never a 1–10 scale: "
            "50 is neutral, 70 is promising, 85 is strong, and 95 is exceptional. Score a criterion whenever at least one "
            "relevant supplied fact supports a bounded assessment; reflect limited or unaudited evidence through lower confidence. "
            "Use null only when no supplied fact is relevant to that criterion."
            if role in {"judge", "repair"}
            else "Return concise observations grounded only in supplied facts and identify uncertainty explicitly."
        )
        try:
            responses = getattr(self._client, "responses")
            response = responses.create(
                model=self.model,
                instructions=f"{prompt}\n\n{role_instruction}",
                input=json.dumps(request_payload, ensure_ascii=False, separators=(",", ":")),
                text={"format": {"type": "json_schema", "name": f"council_{role}", "strict": True, "schema": schema}},
                max_output_tokens=int(os.getenv("SV_LLM_MAX_OUTPUT_TOKENS", "30000")),
                store=False,
                timeout=float(os.getenv("SV_LLM_TIMEOUT_SECONDS", "120")),
            )
            parsed = json.loads(str(response.output_text))
        except Exception as exc:
            raise ProviderUnavailable("openai council request failed") from exc
        if not isinstance(parsed, dict):
            raise ProviderUnavailable("openai council returned invalid JSON")
        return cast(dict[str, object], parsed)


class EnvironmentProvider:
    """Fail-closed provider used for disabled or unsupported live integrations."""

    def __init__(self, name: str, model: str, api_key: str | None) -> None:
        self.name, self.model, self._api_key = name, model, api_key

    def respond(self, role: str, prompt: str, payload: dict[str, object]) -> dict[str, object]:
        del role, prompt, payload
        if not self._api_key:
            raise ProviderUnavailable(f"{self.name} credentials are not configured")
        raise ProviderUnavailable(f"{self.name} live council adapter is not enabled")


def configured_provider() -> CouncilProvider:
    provider = os.getenv("SV_LLM_PROVIDER", "disabled").strip().lower()
    # The deterministic implementation exists for explicitly injected tests and
    # local demonstrations only.  A production default must never turn sparse
    # submission data into plausible-looking investment claims.
    if provider in {"fake", "deterministic"} and os.getenv("SV_DEMO_MODE", "").strip().lower() in {"1", "true", "yes"}:
        return DeterministicFakeProvider()
    if provider in {"", "disabled", "fake", "deterministic"}:
        return EnvironmentProvider("council", "", None)
    if provider == "openai":
        return OpenAIProvider(os.getenv("SV_LLM_MODEL", ""), os.getenv("OPENAI_API_KEY"))
    if provider == "anthropic":
        return EnvironmentProvider("anthropic", os.getenv("SV_LLM_MODEL", ""), os.getenv("ANTHROPIC_API_KEY"))
    raise ProviderUnavailable("Configured council provider is unsupported")
