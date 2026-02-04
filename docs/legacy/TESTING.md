# Testing & QA

## Overview

The CampusConnect AI service uses **pytest** for unit, integration, and smoke testing. Tests are organized into:

- **Unit tests** (`tests/unit/`): Test individual functions in isolation (scoring, config, LLM client)
- **Integration tests** (`tests/integration/`): Test API endpoints and graph execution
- **Fixtures** (`tests/conftest.py`): Shared test setup and mocking utilities

## Running Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run Unit Tests Only
```bash
pytest tests/unit/ -v
```

### Run Integration Tests Only
```bash
pytest tests/integration/ -v
```

### Run with Coverage Report
```bash
pytest tests/ -v --cov=src --cov-report=html
```
Coverage report will be in `htmlcov/index.html`

### Run a Specific Test File
```bash
pytest tests/unit/tools/test_scoring.py -v
```

### Run a Specific Test Class
```bash
pytest tests/unit/tools/test_scoring.py::TestBaseCompatibilityScore -v
```

### Run a Specific Test Function
```bash
pytest tests/unit/tools/test_scoring.py::TestBaseCompatibilityScore::test_same_major_increases_score -v
```

## Test Coverage by Module

### Scoring Tools (`tests/unit/tools/test_scoring.py`)

**What it tests:**
- Deterministic compatibility scoring algorithm
- Distance-based scoring multipliers
- Edge cases: missing fields, extreme locations, score bounds

**Why it matters:**
These functions are the foundation of the matching algorithm. Before expensive LLM calls, we filter candidates using these fast, deterministic scores. Tests ensure the math is correct and handles edge cases.

**Key scenarios:**
- ✅ Same major increases score
- ✅ Shared interests cumulative bonus
- ✅ Year proximity bonus
- ✅ Distance scoring within/outside radius
- ✅ Score never exceeds 100 or goes negative

### LLM Client (`tests/unit/tools/test_llm_client.py`)

**What it tests:**
- Perplexity-first, OpenAI-fallback provider selection
- LLM client instantiation with correct credentials
- Configuration parameter propagation
- Provider availability checking

**Why it matters:**
The LLM client is used across all graph types (matching, safety, onboarding, recommendations). Getting provider selection wrong could silently fail in production. These tests ensure:
- Perplexity is used when available (cheaper, faster)
- OpenAI is fallback when Perplexity unavailable
- Clear error messages if no provider is configured
- Configuration is correct (model, temperature, timeout)

**Key scenarios:**
- ✅ Perplexity preferred when both keys set
- ✅ OpenAI fallback when Perplexity unavailable
- ✅ Error if neither provider configured
- ✅ Explicit provider selection works
- ✅ Provider info correctly reports availability

### Configuration (`tests/unit/test_config.py`)

**What it tests:**
- Config loading from environment variables
- Type conversions (strings to booleans, integers)
- Validation of required fields
- Helpful error messages for missing config

**Why it matters:**
Configuration errors typically fail silently or produce cryptic messages. These tests ensure:
- Required fields are present and type-correct
- Missing config fails fast at startup with helpful errors
- Optional fields have sensible defaults
- LangSmith integration is gated by proper config

**Key scenarios:**
- ✅ Firebase project ID required
- ✅ At least one LLM provider required
- ✅ LangSmith enablement requires API key
- ✅ Validation returns useful status

### API Endpoints (`tests/integration/test_smoke.py`)

**What it tests:**
- `/health` endpoint returns 200 with correct structure
- `/run-graph` endpoint accepts valid requests
- Invalid graph names return 400
- Response structure matches API contract
- Malformed JSON returns proper errors

**Why it matters:**
These are "smoke tests" - they verify the basic service infrastructure works. They don't mock Firestore or LLMs, so they may fail if the service can't connect to Firebase (expected in some environments).

**Key scenarios:**
- ✅ Health check works
- ✅ All 4 valid graph names accepted
- ✅ Unknown graph name rejected
- ✅ Response has required fields
- ✅ Missing input fields cause validation error
- ✅ Docs endpoints accessible

## Writing New Tests

### Test Template: Unit Test
```python
"""Brief description of what this module tests."""

import pytest
from src.module import function_to_test


class TestFunctionName:
    """Organize tests into classes by functionality."""

    def test_happy_path(self):
        """Test the normal, expected behavior."""
        # Arrange: Set up test data
        input_data = {"key": "value"}
        
        # Act: Call the function
        result = function_to_test(input_data)
        
        # Assert: Check the result
        assert result["expected_key"] == "expected_value"

    def test_edge_case_empty_input(self):
        """Test behavior with edge case (empty input)."""
        result = function_to_test({})
        assert result is not None  # Example assertion


class TestAnotherFunction:
    """Test a different function."""
    
    def test_error_handling(self):
        """Test that errors are handled gracefully."""
        with pytest.raises(ValueError, match="Expected error message"):
            function_to_test(invalid_input)
```

### Test Template: Integration Test
```python
"""Integration test for API endpoint."""

import pytest
from fastapi.testclient import TestClient
from src.server import app


@pytest.fixture
def client():
    """Provide TestClient for requests."""
    return TestClient(app)


class TestEndpoint:
    """Test an API endpoint."""

    def test_success_response(self, client):
        """Test successful request."""
        response = client.post("/endpoint", json={"key": "value"})
        assert response.status_code == 200
        data = response.json()
        assert data["expected_field"] is not None

    def test_error_handling(self, client):
        """Test error response."""
        response = client.post("/endpoint", json={})
        assert response.status_code == 422  # Validation error
```

### Using Fixtures
```python
"""Example using mock fixtures."""

import pytest
from unittest.mock import patch


def test_with_mock_firebase(mock_firebase_app):
    """Use the mock_firebase_app fixture."""
    # Firebase calls will be mocked
    result = function_that_uses_firestore()
    assert result == expected_value


def test_with_mock_llm(mock_llm_response):
    """Use the mock_llm_response fixture."""
    # LLM calls will return mock data
    response = llm_chain.invoke({"prompt": "test"})
    assert "expected_field" in response
```

## Common Testing Patterns

### Testing LLM Chains
When testing functions that call LLM chains, mock the LLM response:

```python
from unittest.mock import patch

@patch("src.tools.llm_tools.llm.invoke")
def test_matching_reasoning(mock_llm, mock_llm_response):
    """Test matching reasoning chain."""
    mock_llm.return_value = mock_llm_response
    
    result = get_matching_reasoning_chain().invoke({...})
    assert "why_compatible" in result
```

### Testing Firestore Integration
When testing Firestore queries, mock the database client:

```python
@patch("src.tools.firestore_tools.get_db")
def test_get_user_profile(mock_get_db):
    """Test profile retrieval."""
    mock_db = mock_get_db.return_value
    mock_db.collection("profiles").document("user1").get.return_value.to_dict.return_value = {
        "name": "Alice", "major": "CS"
    }
    
    profile = get_user_profile("user1", "tenant1")
    assert profile["name"] == "Alice"
```

### Testing Graphs
Test graph nodes individually before testing full graph:

```python
def test_graph_node(mock_firebase_app):
    """Test a single graph node."""
    from src.graphs.matching import MatchingGraph
    
    graph = MatchingGraph()
    state = {"user_id": "test", "tenant_id": "test"}
    
    result = graph.node_fetch_user_profile(state)
    assert "user_profile" in result
```

## Debugging Tests

### Run with Print Output
```bash
pytest tests/ -v -s
```
The `-s` flag shows all `print()` statements.

### Run with Pytest Debugger
```bash
pytest tests/ --pdb
```
Drops into debugger on test failure.

### Run with Verbose Logging
```bash
pytest tests/ -v --log-cli-level=DEBUG
```

### Run Single Test in Debugger
```bash
pytest tests/unit/tools/test_scoring.py::TestBaseCompatibilityScore::test_same_major_increases_score -v --pdb
```

## CI/CD Integration

These tests are designed to run in CI/CD pipelines. The commands used in `.github/workflows/` or similar would be:

```bash
# Install dependencies
pip install -r requirements.txt

# Run full test suite with coverage
pytest tests/ -v --cov=src --cov-report=xml

# Or for quick smoke tests only:
pytest tests/integration/test_smoke.py -v
```

## Known Limitations

1. **Firestore Tests**: Tests mock Firestore to avoid needing credentials in CI. For full integration testing, run with `GOOGLE_APPLICATION_CREDENTIALS` set.

2. **LLM Tests**: LLM chain tests mock responses to avoid API calls. For validation, manually test with real LLMs in staging.

3. **Graph Tests**: Individual graph execution tests may fail if Firestore is unavailable (expected for unit test environments).

## Future Enhancements

- [ ] Add E2E tests that run full flows with Firebase emulator
- [ ] Add performance benchmarks for matching algorithm
- [ ] Add load testing for concurrent /run-graph requests
- [ ] Add tests for graph timeout behavior
- [ ] Add tests for LLM provider fallback scenarios

