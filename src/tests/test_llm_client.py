"""
test_llm_client.py — Unit tests for src/llm/client.py

Covers:
  - generate() returns stub string when watsonx credentials absent
  - generate() returns stub when only API key is set but project ID missing
  - generate() calls ModelInference when fully configured
  - watsonx SDK exception is caught and returns error string
  - _is_configured() logic (placeholder values treated as unconfigured)
  - generate() always returns a string
"""

import os
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

STUB_PREFIX = "[watsonx.ai not configured"


def _set_env(**kwargs):
    """Context-manager-friendly: returns a dict for use with patch.dict."""
    return kwargs


# ---------------------------------------------------------------------------
# _is_configured
# ---------------------------------------------------------------------------

class TestIsConfigured:
    def test_unconfigured_when_no_env_vars(self):
        from llm.client import _is_configured
        with patch.dict(os.environ, {"WATSONX_API_KEY": "", "WATSONX_PROJECT_ID": ""}, clear=False):
            assert _is_configured() is False

    def test_unconfigured_with_placeholder_api_key(self):
        from llm.client import _is_configured
        with patch.dict(os.environ, {
            "WATSONX_API_KEY": "your_api_key_here",
            "WATSONX_PROJECT_ID": "real-project-id",
        }, clear=False):
            assert _is_configured() is False

    def test_unconfigured_with_placeholder_project_id(self):
        from llm.client import _is_configured
        with patch.dict(os.environ, {
            "WATSONX_API_KEY": "real-api-key",
            "WATSONX_PROJECT_ID": "your_project_id_here",
        }, clear=False):
            assert _is_configured() is False

    def test_configured_with_real_values(self):
        from llm.client import _is_configured
        with patch.dict(os.environ, {
            "WATSONX_API_KEY": "sk-real-api-key-123",
            "WATSONX_PROJECT_ID": "proj-abc-123",
        }, clear=False):
            assert _is_configured() is True

    def test_unconfigured_when_project_id_missing(self):
        from llm.client import _is_configured
        with patch.dict(os.environ, {"WATSONX_API_KEY": "sk-real", "WATSONX_PROJECT_ID": ""}, clear=False):
            assert _is_configured() is False


# ---------------------------------------------------------------------------
# generate() — stub path (no credentials)
# ---------------------------------------------------------------------------

class TestGenerateStubPath:
    def test_returns_stub_when_not_configured(self):
        from llm.client import generate
        with patch.dict(os.environ, {"WATSONX_API_KEY": "", "WATSONX_PROJECT_ID": ""}, clear=False):
            result = generate("test prompt")
        assert result.startswith(STUB_PREFIX)

    def test_returns_string_type(self):
        from llm.client import generate
        with patch.dict(os.environ, {"WATSONX_API_KEY": "", "WATSONX_PROJECT_ID": ""}, clear=False):
            result = generate("test prompt")
        assert isinstance(result, str)

    def test_stub_contains_env_var_names(self):
        from llm.client import generate
        with patch.dict(os.environ, {"WATSONX_API_KEY": "", "WATSONX_PROJECT_ID": ""}, clear=False):
            result = generate("test prompt")
        assert "WATSONX_API_KEY" in result

    def test_stub_returned_for_placeholder_key(self):
        from llm.client import generate
        with patch.dict(os.environ, {
            "WATSONX_API_KEY": "your_api_key_here",
            "WATSONX_PROJECT_ID": "your_project_id_here",
        }, clear=False):
            result = generate("test prompt")
        assert result.startswith(STUB_PREFIX)


# ---------------------------------------------------------------------------
# generate() — configured path (mocked watsonx SDK)
# ---------------------------------------------------------------------------

class TestGenerateConfiguredPath:
    def _configure_env(self):
        return {
            "WATSONX_API_KEY": "sk-real-key",
            "WATSONX_PROJECT_ID": "proj-123",
            "WATSONX_URL": "https://us-south.ml.cloud.ibm.com",
            "WATSONX_MODEL_ID": "ibm/granite-13b-instruct-v2",
        }

    def test_calls_model_inference_when_configured(self):
        from llm.client import generate

        mock_model = MagicMock()
        mock_model.generate_text.return_value = "Aspirin inhibits COX enzymes."
        mock_model_class = MagicMock(return_value=mock_model)
        mock_credentials = MagicMock()
        mock_credentials_class = MagicMock(return_value=mock_credentials)

        with patch.dict(os.environ, self._configure_env(), clear=False):
            with patch("llm.client._is_configured", return_value=True):
                with patch.dict("sys.modules", {
                    "ibm_watsonx_ai": MagicMock(Credentials=mock_credentials_class),
                    "ibm_watsonx_ai.foundation_models": MagicMock(ModelInference=mock_model_class),
                    "ibm_watsonx_ai.metanames": MagicMock(GenTextParamsMetaNames=MagicMock(
                        MAX_NEW_TOKENS="max_new_tokens",
                        TEMPERATURE="temperature",
                        REPETITION_PENALTY="repetition_penalty",
                    )),
                }):
                    result = generate("explain pharmacovigilance")

        assert result == "Aspirin inhibits COX enzymes."

    def test_sdk_exception_returns_error_string(self):
        from llm.client import generate

        with patch.dict(os.environ, self._configure_env(), clear=False):
            with patch("llm.client._is_configured", return_value=True):
                with patch.dict("sys.modules", {
                    "ibm_watsonx_ai": MagicMock(
                        Credentials=MagicMock(side_effect=RuntimeError("API unreachable"))
                    ),
                    "ibm_watsonx_ai.foundation_models": MagicMock(),
                    "ibm_watsonx_ai.metanames": MagicMock(
                        GenTextParamsMetaNames=MagicMock(
                            MAX_NEW_TOKENS="max_new_tokens",
                            TEMPERATURE="temperature",
                            REPETITION_PENALTY="repetition_penalty",
                        )
                    ),
                }):
                    result = generate("test prompt")

        assert isinstance(result, str)
        assert result.startswith("[LLM error:")

    def test_generate_strips_whitespace_from_model_response(self):
        from llm.client import generate

        mock_model = MagicMock()
        mock_model.generate_text.return_value = "  response with leading/trailing spaces  "
        mock_model_class = MagicMock(return_value=mock_model)

        with patch.dict(os.environ, self._configure_env(), clear=False):
            with patch("llm.client._is_configured", return_value=True):
                with patch.dict("sys.modules", {
                    "ibm_watsonx_ai": MagicMock(Credentials=MagicMock()),
                    "ibm_watsonx_ai.foundation_models": MagicMock(ModelInference=mock_model_class),
                    "ibm_watsonx_ai.metanames": MagicMock(GenTextParamsMetaNames=MagicMock(
                        MAX_NEW_TOKENS="max_new_tokens",
                        TEMPERATURE="temperature",
                        REPETITION_PENALTY="repetition_penalty",
                    )),
                }):
                    result = generate("test prompt")

        assert result == "response with leading/trailing spaces"
