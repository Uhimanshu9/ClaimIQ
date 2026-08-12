"""Provider-neutral generation and embedding helpers.

ClaimIQ talks to a self-hosted LiteLLM Proxy through its OpenAI-compatible API.
The proxy owns provider-specific authentication and request translation; this
module owns only the small application contract used by the API and RAG code.

Embeddings remain provider-configured because Qdrant requires one consistent
vector shape for a collection. Changing the embedding alias or dimensions
requires a new collection and a full re-index.
"""

import os
from typing import Literal

from dotenv import load_dotenv

Provider = Literal["gemini", "openai", "bedrock"]

load_dotenv()

# These are LiteLLM model aliases, not provider-native model IDs. The aliases
# are defined in backend/litellm_config.yaml and can be remapped there without
# changing ClaimIQ code.
DEFAULT_MODELS = {
    "gemini": os.getenv("LITELLM_GEMINI_MODEL", "claimiq-chat-gemini"),
    "openai": os.getenv("LITELLM_OPENAI_MODEL", "claimiq-chat-openai"),
    "bedrock": os.getenv("LITELLM_BEDROCK_MODEL", "claimiq-chat-bedrock"),
}

DEFAULT_EMBEDDING_MODELS = {
    "gemini": os.getenv("LITELLM_GEMINI_EMBEDDING_MODEL", "claimiq-embedding-gemini"),
    "openai": os.getenv("LITELLM_OPENAI_EMBEDDING_MODEL", "claimiq-embedding-openai"),
}


class ProviderConfigurationError(RuntimeError):
    """Raised when the LiteLLM Proxy has not been configured."""


def supported_providers() -> list[str]:
    """Return provider choices that are mapped to LiteLLM aliases."""
    return list(DEFAULT_MODELS)


def provider_models() -> dict[str, str]:
    """Return the safe provider-to-proxy-alias map for API discovery."""
    return DEFAULT_MODELS.copy()


def _proxy_client():
    api_key = os.getenv("LITELLM_API_KEY")
    if not api_key:
        raise ProviderConfigurationError("LITELLM_API_KEY is required to call the LiteLLM Proxy.")

    from openai import OpenAI

    return OpenAI(
        api_key=api_key,
        base_url=os.getenv("LITELLM_BASE_URL", "http://localhost:4000"),
    )


def _model_for(provider: Provider, model: str | None) -> str:
    if provider not in DEFAULT_MODELS:
        raise ValueError(f"Unsupported provider '{provider}'. Choose gemini, openai, or bedrock.")
    # Explicit models are expected to be LiteLLM aliases exposed by the proxy.
    return model or DEFAULT_MODELS[provider]


def generate(
    provider: Provider,
    prompt: str,
    model: str | None = None,
    system_instruction: str | None = None,
) -> str:
    """Generate plain text through the LiteLLM Proxy."""
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    response = _proxy_client().chat.completions.create(
        model=_model_for(provider, model),
        messages=messages,
    )
    return (response.choices[0].message.content or "").strip()


def embed(text: str, provider: Provider | None = None) -> list[float]:
    """Create an embedding through the fixed LiteLLM embedding alias."""
    selected_provider = provider or os.getenv("VECTOR_EMBEDDING_PROVIDER", "openai")
    if selected_provider not in DEFAULT_EMBEDDING_MODELS:
        raise ValueError("VECTOR_EMBEDDING_PROVIDER must be 'gemini' or 'openai'.")

    response = _proxy_client().embeddings.create(
        model=DEFAULT_EMBEDDING_MODELS[selected_provider],
        input=text,
    )
    return response.data[0].embedding
