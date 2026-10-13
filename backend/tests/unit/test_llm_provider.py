import pytest

from app.graph.supervisor import SupervisorRequest, classify
from app.llm.base import ProviderUnavailable
from app.llm.factory import create_provider
from app.llm.groq_provider import from_environment


def request() -> SupervisorRequest:
    return SupervisorRequest(user_message="What is a bond?", business_language="en", script="latin")


def test_factory_requires_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_MODEL", "test-model")
    with pytest.raises(ProviderUnavailable):
        create_provider()


def test_factory_requires_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-only-key")
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    with pytest.raises(ProviderUnavailable):
        create_provider()


def test_explicit_model_configuration_does_not_require_environment_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-only-key")
    monkeypatch.delenv("GROQ_MODEL", raising=False)

    provider = from_environment(model="qwen/test-model")

    assert provider.model == "qwen/test-model"


def test_provider_exception_is_controlled() -> None:
    class BrokenProvider:
        def invoke_structured(self, request: SupervisorRequest) -> object:
            raise TimeoutError

    assert classify(BrokenProvider(), request()).route == "fallback"
