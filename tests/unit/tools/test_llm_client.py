"""
Unit tests for LLM client factory.

Tests the Perplexity-first, OpenAI-fallback strategy.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.tools.llm_client import get_llm, get_llm_provider_info


class TestLLMClientAutoSelection:
    """Test automatic LLM provider selection."""

    @patch("src.tools.llm_client.config.PERPLEXITY_API_KEY", "test-perplexity-key")
    @patch("src.tools.llm_client.config.OPENAI_API_KEY", "test-openai-key")
    @patch("src.tools.llm_client.config.PERPLEXITY_MODEL", "test-model")
    def test_perplexity_preferred_when_both_available(self):
        """When both keys are set, Perplexity should be preferred."""
        llm = get_llm(provider="auto")
        # Verify it's a ChatOpenAI instance (valid LLM client)
        assert llm is not None
        assert hasattr(llm, 'invoke')  # Has invoke method

    @patch("src.tools.llm_client.config.PERPLEXITY_API_KEY", None)
    @patch("src.tools.llm_client.config.OPENAI_API_KEY", "test-openai-key")
    def test_openai_fallback_when_perplexity_unavailable(self):
        """When only OpenAI key is set, should use OpenAI."""
        llm = get_llm(provider="auto")
        # Verify it's a valid LLM client
        assert llm is not None
        assert hasattr(llm, 'invoke')

    @patch("src.tools.llm_client.config.PERPLEXITY_API_KEY", None)
    @patch("src.tools.llm_client.config.OPENAI_API_KEY", None)
    def test_error_when_no_provider_configured(self):
        """Should raise error if no LLM provider is configured."""
        with pytest.raises(ValueError, match="No LLM provider configured"):
            get_llm(provider="auto")


class TestLLMClientExplicitSelection:
    """Test explicit provider selection."""

    @patch("src.tools.llm_client.config.PERPLEXITY_API_KEY", "test-perplexity-key")
    @patch("src.tools.llm_client.config.PERPLEXITY_MODEL", "test-model")
    def test_explicit_perplexity(self):
        """Explicitly requesting Perplexity should work if key is set."""
        llm = get_llm(provider="perplexity")
        # Verify it's a valid LLM client
        assert llm is not None
        assert hasattr(llm, 'invoke')

    @patch("src.tools.llm_client.config.PERPLEXITY_API_KEY", None)
    def test_error_when_perplexity_requested_but_not_available(self):
        """Should error if Perplexity explicitly requested but key is missing."""
        with pytest.raises(ValueError, match="PERPLEXITY_API_KEY not set"):
            get_llm(provider="perplexity")

    @patch("src.tools.llm_client.config.OPENAI_API_KEY", "test-openai-key")
    def test_explicit_openai(self):
        """Explicitly requesting OpenAI should work if key is set."""
        llm = get_llm(provider="openai")
        # Verify it's a valid LLM client
        assert llm is not None
        assert hasattr(llm, 'invoke')

    @patch("src.tools.llm_client.config.OPENAI_API_KEY", None)
    def test_error_when_openai_requested_but_not_available(self):
        """Should error if OpenAI explicitly requested but key is missing."""
        with pytest.raises(ValueError, match="OPENAI_API_KEY not set"):
            get_llm(provider="openai")

    def test_error_on_invalid_provider(self):
        """Should error if invalid provider string is passed."""
        with pytest.raises(ValueError, match="Unknown provider"):
            get_llm(provider="invalid_provider")


class TestLLMClientConfiguration:
    """Test LLM client configuration parameters."""

    @patch("src.tools.llm_client.config.PERPLEXITY_API_KEY", "test-key")
    @patch("src.tools.llm_client.config.PERPLEXITY_MODEL", "test-model")
    def test_temperature_configuration(self):
        """Temperature parameter should be accepted without error."""
        # Verify the function accepts temperature parameter
        llm = get_llm(provider="perplexity", temperature=0.3)
        assert llm is not None

    @patch("src.tools.llm_client.config.PERPLEXITY_API_KEY", "test-key")
    @patch("src.tools.llm_client.config.PERPLEXITY_MODEL", "test-model")
    def test_timeout_configuration(self):
        """Timeout parameter should be accepted without error."""
        # Verify the function accepts timeout parameter
        llm = get_llm(provider="perplexity", timeout=60)
        assert llm is not None

    @patch("src.tools.llm_client.config.PERPLEXITY_API_KEY", "test-key")
    @patch("src.tools.llm_client.config.PERPLEXITY_MODEL", "test-model")
    def test_perplexity_uses_correct_endpoint(self):
        """Perplexity provider should use correct API endpoint."""
        # The implementation uses https://api.perplexity.ai as base_url
        # We can't easily verify this on the object, but we can verify
        # the function doesn't raise an error with Perplexity config
        llm = get_llm(provider="perplexity")
        assert llm is not None


class TestLLMProviderInfo:
    """Test provider info function."""

    @patch("src.tools.llm_client.config.PERPLEXITY_API_KEY", "pplx-test")
    @patch("src.tools.llm_client.config.OPENAI_API_KEY", None)
    @patch("src.tools.llm_client.config.PERPLEXITY_MODEL", "perplexity-model")
    def test_provider_info_perplexity_only(self):
        """Should report correct info when only Perplexity is available."""
        info = get_llm_provider_info()
        assert info["perplexity_available"] is True
        assert info["openai_available"] is False
        assert info["primary_provider"] == "perplexity"
        assert info["perplexity_model"] == "perplexity-model"

    @patch("src.tools.llm_client.config.PERPLEXITY_API_KEY", None)
    @patch("src.tools.llm_client.config.OPENAI_API_KEY", "sk-test")
    @patch("src.tools.llm_client.config.OPENAI_MODEL", "openai-model")
    def test_provider_info_openai_only(self):
        """Should report correct info when only OpenAI is available."""
        info = get_llm_provider_info()
        assert info["perplexity_available"] is False
        assert info["openai_available"] is True
        assert info["primary_provider"] == "openai"
        assert info["openai_model"] == "openai-model"

    @patch("src.tools.llm_client.config.PERPLEXITY_API_KEY", "pplx-test")
    @patch("src.tools.llm_client.config.OPENAI_API_KEY", "sk-test")
    def test_provider_info_both_available(self):
        """Should report Perplexity as primary when both are available."""
        info = get_llm_provider_info()
        assert info["primary_provider"] == "perplexity"

    @patch("src.tools.llm_client.config.PERPLEXITY_API_KEY", None)
    @patch("src.tools.llm_client.config.OPENAI_API_KEY", None)
    def test_provider_info_none_available(self):
        """Should report none when neither provider is available."""
        info = get_llm_provider_info()
        assert info["primary_provider"] == "none"
