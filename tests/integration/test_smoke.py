"""
Integration smoke tests for FastAPI endpoints.

These tests validate that the FastAPI server:
  1. Starts correctly and responds to health checks
  2. Accepts valid graph requests with proper input
  3. Returns properly formatted responses
  4. Handles errors gracefully (bad graph name, invalid input, etc.)

These are "smoke tests" - they don't mock Firestore or LLMs,
so they may fail if the service can't connect to Firebase.
Run with real credentials to ensure full integration works.
"""

import asyncio
import pytest
from src.server import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Provide a FastAPI TestClient for making requests in tests."""
    return TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_endpoint_returns_200(self, client):
        """Health check should return 200 with status='healthy'."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_endpoint_has_status_field(self, client):
        """Health check response should contain status field."""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_health_endpoint_response_structure(self, client):
        """Health check response should be valid JSON."""
        response = client.get("/health")
        assert response.headers["content-type"].startswith("application/json")


class TestGraphEndpoint:
    """Test /run-graph endpoint."""

    def test_run_graph_accepts_valid_request(self, client):
        """POST /run-graph should accept valid request structure."""
        request_body = {
            "graph": "safety",
            "input": {
                "content": "hello world",
                "content_type": "message",
                "user_id": "test_user",
                "tenant_id": "test_tenant",
            },
        }
        response = client.post("/run-graph", json=request_body)
        # Expect either 200 (success) or 500 (Firestore error) but not 400 (bad input)
        assert response.status_code in [200, 500]

    def test_run_graph_returns_structured_response(self, client):
        """Response should have success, graph, data, error fields."""
        response = client.post(
            "/run-graph",
            json={"graph": "safety", "input": {"content": "test", "content_type": "message"}},
        )
        # Only check if response is valid JSON (may error due to Firestore)
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "graph" in data
            assert "data" in data or "error" in data

    def test_run_graph_rejects_unknown_graph(self, client):
        """POST /run-graph should return 400 for unknown graph name."""
        response = client.post(
            "/run-graph",
            json={"graph": "unknown_graph_xyz", "input": {}},
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data or "Unknown graph" in str(data)

    def test_run_graph_accepts_all_valid_graphs(self, client):
        """Should accept requests for all 4 valid graphs."""
        valid_graphs = [
            ("safety", {"content": "test", "content_type": "message"}),
            ("matching", {"user_id": "test", "tenant_id": "test"}),
            ("onboarding", {"user_id": "test", "tenant_id": "test"}),
            ("events_communities", {"user_id": "test", "tenant_id": "test"}),
        ]

        for graph_name, input_data in valid_graphs:
            response = client.post(
                "/run-graph",
                json={"graph": graph_name, "input": input_data},
            )
            # Should not be 400 (bad request)
            # May be 200 or 500 (Firestore/LLM issues)
            assert response.status_code != 400, f"Graph {graph_name} rejected as bad input"

    def test_run_graph_executes_each_graph(self, client, monkeypatch):
        """Execute each graph end-to-end through the API with safe inputs."""

        from src.graphs import matching as matching_graph
        from src.graphs import events_communities as events_graph

        monkeypatch.setattr(
            matching_graph,
            "get_user_profile",
            lambda user_id, tenant_id: None,
        )
        monkeypatch.setattr(
            events_graph,
            "get_user_profile",
            lambda user_id, tenant_id: None,
        )

        requests = [
            (
                "matching",
                {
                    "user_id": "test_user",
                    "tenant_id": "test_tenant",
                    "preferences": {"radiusMeters": 1000, "minScore": 50},
                },
            ),
            (
                "safety",
                {
                    "content": "slur1",
                    "content_type": "message",
                    "user_id": "test_user",
                    "tenant_id": "test_tenant",
                },
            ),
            (
                "onboarding",
                {
                    "user_id": "test_user",
                    "tenant_id": "test_tenant",
                    "current_step": 1,
                    "form_data": {"email": "user@example.com"},
                },
            ),
            (
                "events_communities",
                {
                    "user_id": "test_user",
                    "tenant_id": "test_tenant",
                    "request_type": "events",
                },
            ),
        ]

        for graph_name, input_data in requests:
            response = client.post(
                "/run-graph",
                json={"graph": graph_name, "input": input_data},
            )
            assert response.status_code == 200
            payload = response.json()
            assert payload.get("graph") == graph_name
            assert payload.get("success") is True

    def test_run_graph_handles_missing_input(self, client):
        """Should return 422 (validation error) for missing required fields."""
        response = client.post(
            "/run-graph",
            json={"graph": "safety"},  # Missing 'input' field
        )
        assert response.status_code == 422  # Pydantic validation error

    def test_run_graph_handles_malformed_json(self, client):
        """Should return 422 for malformed JSON request."""
        response = client.post(
            "/run-graph",
            data="not valid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code in [422, 400]


class TestOpenAPIEndpoints:
    """Test FastAPI auto-generated documentation endpoints."""

    def test_docs_endpoint_accessible(self, client):
        """OpenAPI docs endpoint should be accessible."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_schema_endpoint(self, client):
        """OpenAPI schema endpoint should return valid schema."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data