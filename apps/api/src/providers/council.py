"""Narrow provider boundary for the bounded council workflow.

Adapters deliberately do not make network requests unless explicitly configured with
credentials.  The deterministic provider is the local/test default.
"""
from __future__ import annotations

import os
from typing import Any, Protocol


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


class EnvironmentProvider:
    """Fail closed placeholder for a live provider until an adapter is authorized."""

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
        return EnvironmentProvider("openai", os.getenv("SV_LLM_MODEL", ""), os.getenv("OPENAI_API_KEY"))
    if provider == "anthropic":
        return EnvironmentProvider("anthropic", os.getenv("SV_LLM_MODEL", ""), os.getenv("ANTHROPIC_API_KEY"))
    raise ProviderUnavailable("Configured council provider is unsupported")
