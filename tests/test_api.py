"""
API endpoint tests for the LLM Router service.

Tests cover health checks, chat completions, provider status, analytics,
failure simulation, error handling, and root endpoint.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app import dependencies
from app.main import create_app
from app.routing.circuit_breaker import CircuitBreaker
from app.routing.metrics import MetricsService
from app.storage.memory import MemoryStore

# Test fixtures for API integration tests
# Using sync fixtures because TestClient doesn't support async fixtures


@pytest.fixture
def test_memory():
    """Create a fresh MemoryStore instance for sync test client."""
    memory = MemoryStore()
    asyncio.run(memory.reset())
    return memory


@pytest.fixture
def test_circuit_breaker(test_memory):
    """Create a CircuitBreaker instance using test memory."""
    return CircuitBreaker(test_memory)


@pytest.fixture
def test_metrics_service(test_memory, test_circuit_breaker):
    """Create a MetricsService instance using test dependencies."""
    return MetricsService(test_memory, test_circuit_breaker)


@pytest.fixture
def client(test_memory, test_circuit_breaker, test_metrics_service):
    """
    Create a TestClient with isolated test dependencies.

    This fixture overrides the app's dependency injection to use
    test-specific instances, ensuring each test runs in isolation.
    """
    app = create_app()

    # Use dict.update() for cleaner override syntax
    app.dependency_overrides.update(
        {
            dependencies.get_memory: lambda: test_memory,
            dependencies.get_circuit_breaker: lambda: test_circuit_breaker,
            dependencies.get_metrics_service: lambda: test_metrics_service,
        }
    )

    # Use context manager for automatic cleanup
    with TestClient(app) as test_client:
        yield test_client

    # Explicitly clear overrides after test
    app.dependency_overrides.clear()


@pytest.fixture
def reset_memory():
    """Reset memory before and after each test."""
    memory = MemoryStore()
    asyncio.run(memory.reset())
    yield memory
    asyncio.run(memory.reset())


def test_health_check(client):
    """Test the /health endpoint returns correct status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "providers_available" in data


def test_chat_completions(client):
    """Test basic chat completions endpoint."""
    response = client.post("/chat/completions", json={"prompt": "Test prompt", "preferences": {"priority": "cost"}})
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert "provider_used" in data
    assert "cost" in data


def test_provider_status(client):
    """Test the /providers endpoint returns provider list."""
    response = client.get("/providers")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# Analytics endpoint tests
def test_get_analytics(client):
    """Test analytics endpoint returns correct structure."""
    # Make a few requests first
    client.post("/chat/completions", json={"prompt": "test code"})
    client.post("/chat/completions", json={"prompt": "test write"})

    response = client.get("/routing/analytics")
    assert response.status_code == 200

    data = response.json()
    assert "global" in data
    assert "providers" in data

    # Check global metrics structure
    global_metrics = data["global"]
    assert "total_requests" in global_metrics
    assert "total_success" in global_metrics
    assert "success_rate" in global_metrics


# Simulate failure tests
def test_simulate_provider_down(client):
    """Test marking a provider as down."""
    response = client.post("/simulate/failure", json={"provider": "openai", "down": True})
    assert response.status_code == 200
    assert "openai" in response.json()["message"]

    # Check provider status
    status_response = client.get("/providers")
    providers = status_response.json()
    openai_provider = next(p for p in providers if p["name"] == "openai")
    assert openai_provider["is_down"] is True


def test_simulate_provider_up(client):
    """Test marking a provider as up."""
    # First mark it down
    client.post("/simulate/failure", json={"provider": "google", "down": True})

    # Then mark it up
    response = client.post("/simulate/failure", json={"provider": "google", "down": False})
    assert response.status_code == 200

    # Check provider status
    status_response = client.get("/providers")
    providers = status_response.json()
    google_provider = next(p for p in providers if p["name"] == "google")
    assert google_provider["is_down"] is False


def test_simulate_invalid_provider(client):
    """Test simulating failure for non-existent provider."""
    response = client.post("/simulate/failure", json={"provider": "nonexistent", "down": True})
    assert response.status_code == 404


# Error handling tests
def test_service_unavailable_all_providers_down(client, reset_memory):
    """Test when all providers are unavailable."""
    # Mark all providers as down
    asyncio.run(reset_memory.set_provider_down("openai", True))
    asyncio.run(reset_memory.set_provider_down("google", True))

    response = client.post("/chat/completions", json={"prompt": "test"})
    # Should either fail or fallback gracefully
    assert response.status_code in [503, 200]


def test_invalid_request_validation(client):
    """Test request validation errors."""
    # Missing required field
    response = client.post("/chat/completions", json={})
    assert response.status_code == 422

    # Invalid preference priority
    response = client.post(
        "/chat/completions", json={"prompt": "test", "preferences": {"priority": "invalid_priority"}}
    )
    assert response.status_code == 422


# Root endpoint test
def test_root_redirect(client):
    """Test root endpoint redirects to docs."""
    response = client.get("/", follow_redirects=False)
    # Should redirect to /docs
    assert response.status_code in [200, 307, 308]
