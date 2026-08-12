import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

# Keep these unit tests runnable in a minimal checkout before backend
# requirements are installed. Production still installs python-dotenv.
try:
    import dotenv  # noqa: F401
except ModuleNotFoundError:
    sys.modules["dotenv"] = types.SimpleNamespace(load_dotenv=lambda: None)

from app.llm import router  # noqa: E402


class _FakeMessage:
    content = "proxy answer"


class _FakeChatResponse:
    choices = [types.SimpleNamespace(message=_FakeMessage())]


class _FakeEmbeddingResponse:
    data = [types.SimpleNamespace(embedding=[0.1, 0.2, 0.3])]


class _FakeCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeChatResponse()


class _FakeEmbeddings:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeEmbeddingResponse()


class _FakeClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.completions = _FakeCompletions()
        self.embeddings = _FakeEmbeddings()
        self.chat = types.SimpleNamespace(completions=self.completions)


class LiteLLMRouterTests(unittest.TestCase):
    def setUp(self):
        self.client = _FakeClient()

        def make_client(**kwargs):
            self.client.kwargs = kwargs
            return self.client

        self.openai_module = types.SimpleNamespace(OpenAI=make_client)

    def test_generate_uses_litellm_alias_and_proxy(self):
        with patch.dict(
            os.environ,
            {
                "LITELLM_API_KEY": "test-key",
                "LITELLM_BASE_URL": "http://litellm:4000",
            },
            clear=False,
        ), patch.dict(sys.modules, {"openai": self.openai_module}):
            result = router.generate("gemini", "hello", system_instruction="be concise")

        self.assertEqual(result, "proxy answer")
        self.assertEqual(self.client.kwargs["base_url"], "http://litellm:4000")
        self.assertEqual(self.client.completions.calls[0]["model"], "claimiq-chat-gemini")
        self.assertEqual(self.client.completions.calls[0]["messages"][0]["role"], "system")

    def test_embed_uses_configured_embedding_alias(self):
        with patch.dict(
            os.environ,
            {
                "LITELLM_API_KEY": "test-key",
                "VECTOR_EMBEDDING_PROVIDER": "openai",
            },
            clear=False,
        ), patch.dict(sys.modules, {"openai": self.openai_module}):
            result = router.embed("hello")

        self.assertEqual(result, [0.1, 0.2, 0.3])
        self.assertEqual(
            self.client.embeddings.calls[0]["model"],
            "claimiq-embedding-openai",
        )

    def test_missing_proxy_key_fails_before_network_call(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(router.ProviderConfigurationError):
                router.generate("gemini", "hello")


if __name__ == "__main__":
    unittest.main()
