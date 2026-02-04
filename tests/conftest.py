"""
Pytest configuration and shared fixtures for all tests.

This file is automatically loaded by pytest and provides:
  - Common test fixtures (FastAPI TestClient, mock Firebase, etc.)
  - Test configuration (env vars, logging, etc.)
  - Test markers and hooks
"""

import os
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Setup test environment variables before running any tests.
    
    This ensures tests run with predictable configuration and don't
    depend on local .env files.
    """
    # Set required env vars for testing
    test_env = {
        "FIREBASE_PROJECT_ID": "test-project",
        "GOOGLE_APPLICATION_CREDENTIALS": "/config/test-serviceAccountKey.json",
        "PERPLEXITY_API_KEY": "test-perplexity-key",
        "OPENAI_API_KEY": "test-openai-key",
        "DEBUG": "True",
    }
    
    for key, value in test_env.items():
        os.environ[key] = value


@pytest.fixture
def mock_firebase_app(monkeypatch):
    """
    Provide a mock Firebase app for testing.
    
    Use this fixture in tests that need to mock Firestore calls.
    
    Example:
        def test_something(mock_firebase_app):
            # Firestore calls will use mock
            pass
    """
    mock_app = MagicMock()
    mock_db = MagicMock()
    
    monkeypatch.setattr("firebase_admin._apps", [mock_app])
    monkeypatch.setattr("firebase_admin.initialize_app", MagicMock(return_value=mock_app))
    monkeypatch.setattr("firebase_admin.firestore.client", MagicMock(return_value=mock_db))
    
    return {"app": mock_app, "db": mock_db}


@pytest.fixture
def mock_llm_response():
    """
    Provide a mock LLM response for testing LLM chains.
    
    Use this fixture to avoid making real LLM API calls in tests.
    
    Example:
        def test_matching_chain(mock_llm_response):
            # LLM calls will return mock data
            pass
    """
    return MagicMock(
        content="""{
            "why_compatible": "Both are CS majors interested in AI",
            "conversation_starter": "Have you taken the ML course?",
            "compatibility_score": 85
        }""",
        response_metadata={},
    )
