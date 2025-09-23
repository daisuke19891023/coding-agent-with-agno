"""Factory for constructing provider-specific agno LLM model instances.

This module centralizes the creation of LLM model instances based on the
configured provider in ``AgentSettings``. It supports OpenAI-compatible models
including Azure OpenAI, Anthropic, and Google Gemini.

Notes:
- For the default OpenAI provider, agent modules create ``OpenAIChat`` directly
  to preserve existing test hooks that patch that symbol in those modules.
- For other providers, this factory returns the appropriate model instance if
  the corresponding integration is available in ``agno``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - types only
    from clean_interfaces.utils.settings import AgentSettings


class LLMProviderNotAvailableError(RuntimeError):
    """Raised when the requested provider integration is not available."""


def _build_openai_model(settings: "AgentSettings") -> Any:
    """Construct an OpenAIChat model using OpenAI credentials.

    Although agents instantiate OpenAI models directly, this is exposed for
    completeness and potential reuse.
    """
    # Import locally to avoid hard dependency at module import time
    try:
        from agno.models.openai import OpenAIChat
    except Exception as exc:  # pragma: no cover - environment dependent
        msg = "OpenAI model integration is not available in agno."
        raise LLMProviderNotAvailableError(msg) from exc

    kwargs: dict[str, Any] = {
        "id": settings.openai_model,
        "api_key": settings.openai_api_key,
    }
    if getattr(settings, "openai_base_url", None):
        kwargs["base_url"] = settings.openai_base_url  # type: ignore[assignment]
    return OpenAIChat(**kwargs)


def _build_azure_openai_model(settings: "AgentSettings") -> Any:
    """Construct an Azure OpenAI model instance.

    Attempts multiple import paths to accommodate possible agno versions.
    """
    model_class: Any | None = None
    for path in (
        "agno.models.azure_openai",
        "agno.models.azure",
    ):
        try:
            module = __import__(path, fromlist=["AzureOpenAIChat"])  # type: ignore[assignment]
            model_class = getattr(module, "AzureOpenAIChat")
            break
        except Exception:  # pragma: no cover - optional integration
            continue

    if model_class is None:  # pragma: no cover - optional integration
        msg = (
            "Azure OpenAI integration is not available in agno. "
            "Install a version that provides AzureOpenAIChat."
        )
        raise LLMProviderNotAvailableError(msg)

    missing: list[str] = []
    if not getattr(settings, "azure_openai_api_key", None):
        missing.append("AZURE_OPENAI_API_KEY")
    if not getattr(settings, "azure_openai_endpoint", None):
        missing.append("AZURE_OPENAI_ENDPOINT")
    if not getattr(settings, "azure_openai_api_version", None):
        missing.append("AZURE_OPENAI_API_VERSION")
    if not getattr(settings, "azure_openai_deployment", None):
        missing.append("AZURE_OPENAI_DEPLOYMENT")
    if missing:  # pragma: no cover - validated upstream usually
        joined = ", ".join(missing)
        raise ValueError(f"Missing Azure OpenAI settings: {joined}")

    return model_class(
        endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        deployment=settings.azure_openai_deployment,
    )


def _build_anthropic_model(settings: "AgentSettings") -> Any:
    """Construct an Anthropic model instance."""
    model_class: Any | None = None
    for path in (
        "agno.models.anthropic",
    ):
        try:
            module = __import__(path, fromlist=["AnthropicChat"])  # type: ignore[assignment]
            model_class = getattr(module, "AnthropicChat")
            break
        except Exception:  # pragma: no cover - optional integration
            continue

    if model_class is None:  # pragma: no cover - optional integration
        msg = (
            "Anthropic integration is not available in agno. "
            "Install a version that provides AnthropicChat."
        )
        raise LLMProviderNotAvailableError(msg)

    kwargs: dict[str, Any] = {
        "id": settings.anthropic_model,
        "api_key": settings.anthropic_api_key,
    }
    if getattr(settings, "anthropic_base_url", None):
        kwargs["base_url"] = settings.anthropic_base_url  # type: ignore[assignment]
    return model_class(**kwargs)


def _build_gemini_model(settings: "AgentSettings") -> Any:
    """Construct a Google Gemini model instance."""
    model_class: Any | None = None
    for path in (
        "agno.models.gemini",
        "agno.models.google",
    ):
        try:
            module = __import__(path, fromlist=["GeminiChat"])  # type: ignore[assignment]
            model_class = getattr(module, "GeminiChat")
            break
        except Exception:  # pragma: no cover - optional integration
            continue

    if model_class is None:  # pragma: no cover - optional integration
        msg = (
            "Gemini integration is not available in agno. "
            "Install a version that provides GeminiChat."
        )
        raise LLMProviderNotAvailableError(msg)

    kwargs: dict[str, Any] = {
        "id": settings.gemini_model,
        "api_key": settings.gemini_api_key,
    }
    if getattr(settings, "gemini_base_url", None):
        kwargs["base_url"] = settings.gemini_base_url  # type: ignore[assignment]
    return model_class(**kwargs)


def create_model(settings: "AgentSettings") -> Any:
    """Create a provider-specific agno model instance.

    Args:
        settings: The agent settings containing provider and credentials.

    Returns:
        A model instance compatible with ``agno.agent.Agent``.

    Raises:
        LLMProviderNotAvailableError: If the provider's model is not available.
        ValueError: If the provider is unsupported or configuration is incomplete.
    """
    provider = getattr(settings, "provider", "openai")
    if provider == "openai":
        return _build_openai_model(settings)
    if provider == "azure_openai":
        return _build_azure_openai_model(settings)
    if provider == "anthropic":
        return _build_anthropic_model(settings)
    if provider == "gemini":
        return _build_gemini_model(settings)
    raise ValueError(f"Unsupported LLM provider: {provider}")

