"""Provider-neutral generation and embedding helpers.

The provider is selected per request for generation. Embeddings are configured
once through VECTOR_EMBEDDING_PROVIDER because a Qdrant collection must contain
vectors with one consistent dimension.
"""

import os
from typing import Literal

from dotenv import load_dotenv

Provider = Literal["gemini", "openai", "bedrock"]

load_dotenv()

DEFAULT_MODELS = {
    "gemini": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    "openai": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
    "bedrock": os.getenv("BEDROCK_MODEL", "amazon.nova-lite-v1:0"),
}


class ProviderConfigurationError(RuntimeError):
    """Raised when a selected provider has not been configured."""


def supported_providers() -> list[str]:
    return list(DEFAULT_MODELS)


def _model_for(provider: Provider, model: str | None) -> str:
    if provider not in DEFAULT_MODELS:
        raise ValueError(f"Unsupported provider '{provider}'. Choose gemini, openai, or bedrock.")
    return model or DEFAULT_MODELS[provider]


def generate(provider: Provider, prompt: str, model: str | None = None, system_instruction: str | None = None) -> str:
    """Generate plain text from the selected provider using a common interface."""
    selected_model = _model_for(provider, model)

    if provider == "gemini":
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ProviderConfigurationError("GEMINI_API_KEY is required for the Gemini provider.")
        client = genai.Client(api_key=api_key)
        config = types.GenerateContentConfig(system_instruction=system_instruction) if system_instruction else None
        response = client.models.generate_content(model=selected_model, contents=prompt, config=config)
        return response.text.strip()

    if provider == "openai":
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ProviderConfigurationError("OPENAI_API_KEY is required for the OpenAI provider.")
        client = OpenAI(api_key=api_key)
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(model=selected_model, messages=messages)
        return (response.choices[0].message.content or "").strip()

    if provider == "bedrock":
        import boto3

        region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
        if not region:
            raise ProviderConfigurationError("AWS_REGION is required for the Bedrock provider.")
        client = boto3.client("bedrock-runtime", region_name=region)
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        kwargs = {"modelId": selected_model, "messages": messages}
        if system_instruction:
            kwargs["system"] = [{"text": system_instruction}]
        response = client.converse(**kwargs)
        return "".join(block.get("text", "") for block in response["output"]["message"]["content"]).strip()

    raise ValueError(f"Unsupported provider '{provider}'.")


def embed(text: str, provider: Provider | None = None) -> list[float]:
    """Create an embedding using the configured vector provider."""
    selected_provider = provider or os.getenv("VECTOR_EMBEDDING_PROVIDER", "openai")

    if selected_provider == "gemini":
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ProviderConfigurationError("GEMINI_API_KEY is required for Gemini embeddings.")
        client = genai.Client(api_key=api_key)
        response = client.models.embed_content(
            model=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"),
            contents=text,
            config=types.EmbedContentConfig(output_dimensionality=int(os.getenv("VECTOR_DIMENSIONS", "768"))),
        )
        return response.embeddings[0].values

    if selected_provider == "openai":
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ProviderConfigurationError("OPENAI_API_KEY is required for OpenAI embeddings.")
        client = OpenAI(api_key=api_key)
        response = client.embeddings.create(
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"), input=text
        )
        return response.data[0].embedding

    raise ValueError("VECTOR_EMBEDDING_PROVIDER must be 'gemini' or 'openai'.")
