import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pipeline import synthesize


class ProviderFallbackTests(unittest.TestCase):
    def test_openai_uses_responses_api(self):
        response = SimpleNamespace(
            output_text="resultado",
            usage=SimpleNamespace(total_tokens=42),
        )
        with (
            patch.dict(os.environ, {"OPENAI_KEY": "openai-key"}, clear=True),
            patch("builtins.print"),
            patch("openai.OpenAI") as openai_client,
        ):
            openai_client.return_value.responses.create.return_value = response
            result = synthesize._call_openai(
                "system",
                "user",
                "Test",
                max_tokens=1234,
            )

        self.assertEqual(result, "resultado")
        openai_client.assert_called_once_with(api_key="openai-key")
        openai_client.return_value.responses.create.assert_called_once_with(
            model="gpt-5.4-mini",
            input=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": "user"},
            ],
            max_output_tokens=1234,
        )

    def test_openai_is_used_first(self):
        env = {
            "OPENAI_KEY": "openai-key",
            "GROQ_API_KEY": "groq-key",
            "AZURE_OPENAI_API_KEY": "azure-key",
            "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
        }
        with (
            patch.dict(os.environ, env, clear=True),
            patch("builtins.print"),
            patch.object(synthesize, "_call_openai", return_value="openai") as openai,
            patch.object(synthesize, "_call_groq") as groq,
            patch.object(synthesize, "_call_azure_openai") as azure,
        ):
            result = synthesize._call_llm("system", "user", "Test")

        self.assertEqual(result, "openai")
        openai.assert_called_once()
        groq.assert_not_called()
        azure.assert_not_called()

    def test_groq_is_used_when_openai_fails(self):
        env = {
            "OPENAI_KEY": "openai-key",
            "GROQ_API_KEY": "groq-key",
            "AZURE_OPENAI_API_KEY": "azure-key",
            "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
        }
        with (
            patch.dict(os.environ, env, clear=True),
            patch("builtins.print"),
            patch.object(synthesize, "_call_openai", return_value=None) as openai,
            patch.object(synthesize, "_call_groq", return_value="groq") as groq,
            patch.object(synthesize, "_call_azure_openai") as azure,
        ):
            result = synthesize._call_llm("system", "user", "Test")

        self.assertEqual(result, "groq")
        openai.assert_called_once()
        groq.assert_called_once()
        azure.assert_not_called()

    def test_azure_is_the_last_fallback(self):
        env = {
            "OPENAI_KEY": "openai-key",
            "GROQ_API_KEY": "groq-key",
            "AZURE_OPENAI_API_KEY": "azure-key",
            "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
        }
        with (
            patch.dict(os.environ, env, clear=True),
            patch("builtins.print"),
            patch.object(synthesize, "_call_openai", return_value=None),
            patch.object(synthesize, "_call_groq", return_value=None),
            patch.object(synthesize, "_call_azure_openai", return_value="azure") as azure,
        ):
            result = synthesize._call_llm("system", "user", "Test")

        self.assertEqual(result, "azure")
        azure.assert_called_once()

    def test_no_provider_returns_none(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("builtins.print"),
            patch.object(synthesize, "_call_openai") as openai,
            patch.object(synthesize, "_call_groq") as groq,
            patch.object(synthesize, "_call_azure_openai") as azure,
        ):
            result = synthesize._call_llm("system", "user", "Test")

        self.assertIsNone(result)
        openai.assert_not_called()
        groq.assert_not_called()
        azure.assert_not_called()


if __name__ == "__main__":
    unittest.main()
