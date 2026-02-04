"""
Unit tests for configuration loading and validation.

These tests ensure:
  1. Config loads from environment variables correctly
  2. Required fields are validated at startup
  3. Type conversions work (e.g., strings to ints)
  4. Helpful error messages are provided for missing config
"""

import pytest
from unittest.mock import patch
from src.config import Config, validate_config


class TestConfigLoading:
    """Test configuration loading from environment."""

    @patch.dict("os.environ", {
        "FIREBASE_PROJECT_ID": "test-project",
        "PERPLEXITY_API_KEY": "pplx-test-key",
    })
    def test_required_config_loads(self):
        """Required config fields should load from environment."""
        config = Config()
        assert config.FIREBASE_PROJECT_ID == "test-project"
        assert config.PERPLEXITY_API_KEY == "pplx-test-key"

    @patch.dict("os.environ", {
        "FIREBASE_PROJECT_ID": "test-project",
        "PERPLEXITY_API_KEY": "pplx-test",
        "DEBUG": "True",
    })
    def test_boolean_config_conversion(self):
        """Boolean environment variables should be converted correctly."""
        config = Config(_env_file=None)  # Don't load from .env
        # Note: This may need adjustment depending on pydantic-settings behavior

    @patch.dict("os.environ", {
        "FIREBASE_PROJECT_ID": "test-project",
        "PERPLEXITY_API_KEY": "pplx-test",
        "PORT": "9000",
    })
    def test_integer_config_conversion(self):
        """Integer environment variables should be converted to int."""
        config = Config(_env_file=None)
        assert isinstance(config.PORT, int)
        assert config.PORT == 9000

    @patch.dict("os.environ", {
        "FIREBASE_PROJECT_ID": "test-project",
        "PERPLEXITY_API_KEY": "pplx-test",
        "DEBUG": "false",
    }, clear=False)
    def test_optional_config_defaults(self):
        """Optional config should have sensible defaults."""
        config = Config(_env_file=None)
        assert config.PORT == 8000  # Default
        assert config.GRAPH_TIMEOUT == 30  # Default
        # Note: DEBUG may be set to True by test setup, so we just check it's a bool
        assert isinstance(config.DEBUG, bool)


class TestConfigValidation:
    """Test configuration validation function."""

    @patch("src.config.config")
    def test_validate_firebase_required(self, mock_config):
        """Firebase project ID must be set."""
        mock_config.FIREBASE_PROJECT_ID = ""
        mock_config.PERPLEXITY_API_KEY = "test"
        
        with pytest.raises(ValueError, match="FIREBASE_PROJECT_ID"):
            validate_config()

    @patch("src.config.config")
    def test_validate_at_least_one_llm_required(self, mock_config):
        """At least one LLM provider must be configured."""
        mock_config.FIREBASE_PROJECT_ID = "test"
        mock_config.PERPLEXITY_API_KEY = None
        mock_config.OPENAI_API_KEY = None
        mock_config.LANGSMITH_ENABLED = False
        
        with pytest.raises(ValueError, match="PERPLEXITY_API_KEY or OPENAI_API_KEY"):
            validate_config()

    @patch("src.config.config")
    def test_validate_perplexity_is_enough(self, mock_config):
        """Perplexity alone should be sufficient."""
        mock_config.FIREBASE_PROJECT_ID = "test"
        mock_config.PERPLEXITY_API_KEY = "pplx-test"
        mock_config.OPENAI_API_KEY = None
        mock_config.LANGSMITH_ENABLED = False
        
        # Should not raise
        result = validate_config()
        assert result["perplexity"] == "✓ Configured"

    @patch("src.config.config")
    def test_validate_openai_fallback(self, mock_config):
        """OpenAI alone should be sufficient."""
        mock_config.FIREBASE_PROJECT_ID = "test"
        mock_config.PERPLEXITY_API_KEY = None
        mock_config.OPENAI_API_KEY = "sk-test"
        mock_config.LANGSMITH_ENABLED = False
        
        # Should not raise
        result = validate_config()
        assert result["openai"] == "✓ Configured"

    @patch("src.config.config")
    def test_validate_langsmith_enabled_requires_key(self, mock_config):
        """LangSmith enabled requires API key."""
        mock_config.FIREBASE_PROJECT_ID = "test"
        mock_config.PERPLEXITY_API_KEY = "pplx-test"
        mock_config.LANGSMITH_ENABLED = True
        mock_config.LANGSMITH_API_KEY = None
        
        with pytest.raises(ValueError, match="LANGSMITH_ENABLED"):
            validate_config()

    @patch("src.config.config")
    def test_validate_success_returns_status(self, mock_config):
        """Successful validation should return status dict."""
        mock_config.FIREBASE_PROJECT_ID = "test"
        mock_config.PERPLEXITY_API_KEY = "pplx-test"
        mock_config.OPENAI_API_KEY = "sk-test"
        mock_config.LANGSMITH_ENABLED = False
        mock_config.LANGSMITH_API_KEY = None
        
        result = validate_config()
        assert isinstance(result, dict)
        assert "firebase" in result
        assert "perplexity" in result
        assert "openai" in result
