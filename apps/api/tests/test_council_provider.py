from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from src.providers.council import OpenAIProvider, ProviderUnavailable


class FakeResponses:
    def __init__(self, output: dict[str, object] | None = None, error: Exception | None = None) -> None:
        self.output = output or {"observations": ["Grounded observation."]}
        self.error = error
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(output_text=json.dumps(self.output))


def test_openai_provider_requests_strict_json_without_sending_server_drafts() -> None:
    responses = FakeResponses()
    provider = OpenAIProvider("gpt-test", "test-key", client=SimpleNamespace(responses=responses))
    result = provider.respond("pro", "Use supplied facts.", {"facts": [], "draft_documents": {"private": True}})

    assert result == {"observations": ["Grounded observation."]}
    request = responses.calls[0]
    assert request["store"] is False
    assert request["text"]["format"]["strict"] is True  # type: ignore[index]
    assert "draft_documents" not in str(request["input"])


def test_openai_provider_fails_closed_on_request_errors() -> None:
    responses = FakeResponses(error=RuntimeError("network unavailable"))
    provider = OpenAIProvider("gpt-test", "test-key", client=SimpleNamespace(responses=responses))
    with pytest.raises(ProviderUnavailable, match="request failed"):
        provider.respond("pro", "Use supplied facts.", {"facts": []})


def test_openai_judge_schema_restricts_ids_without_unsupported_keywords() -> None:
    responses = FakeResponses(output={"evaluations": []})
    provider = OpenAIProvider("gpt-test", "test-key", client=SimpleNamespace(responses=responses))
    provider.respond("judge", "Judge supplied facts.", {
        "registry": [{"id": "idea.uniqueness"}],
        "facts": [{"id": "fact.source.1"}],
    })

    schema = responses.calls[0]["text"]["format"]["schema"]  # type: ignore[index]
    item_properties = schema["properties"]["evaluations"]["items"]["properties"]  # type: ignore[index]
    assert item_properties["id"]["enum"] == ["idea.uniqueness"]
    assert item_properties["evidenceFactIds"]["items"]["enum"] == ["fact.source.1"]
    assert "uniqueItems" not in item_properties["evidenceFactIds"]
