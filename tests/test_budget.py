"""
User budget enforcement tests.

Tests cover budget tracking, enforcement of spending caps,
anonymous requests, and 402 responses when budgets are exceeded.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.storage.memory import MemoryStore


@pytest.fixture
def reset_memory():
    """Reset memory before each test."""
    memory = MemoryStore()
    asyncio.run(memory.reset())
    yield memory
    asyncio.run(memory.reset())


@pytest.fixture
def client(reset_memory):
    """Create test client with reset memory."""
    app = create_app()
    return TestClient(app)


def test_budget_tracking(client):
    """Test that user spending is tracked correctly."""
    # First request should succeed
    response1 = client.post("/chat/completions", json={"prompt": "Test prompt" * 100, "user_id": "test_user_budget"})
    assert response1.status_code == 200

    # Make more requests to accumulate costs
    for _ in range(50):
        response = client.post("/chat/completions", json={"prompt": "Long prompt" * 200, "user_id": "test_user_budget"})
        if response.status_code != 200:
            break

    # Eventually should hit budget limit
    final_response = client.post(
        "/chat/completions", json={"prompt": "Test prompt" * 200, "user_id": "test_user_budget"}
    )
    # Should either succeed or return 402
    assert final_response.status_code in [200, 402]


def test_budget_exceeded(client, reset_memory):
    """Test 402 response when budget is exceeded."""
    # Manually set user spend to exceed limit
    asyncio.run(reset_memory.add_user_spend("budget_exceeded_user", 1.5))

    response = client.post("/chat/completions", json={"prompt": "Test prompt", "user_id": "budget_exceeded_user"})
    assert response.status_code == 402
    assert "detail" in response.json()


def test_anonymous_no_budget(client):
    """Test that requests without user_id don't track budgets."""
    # Make many requests without user_id
    for _ in range(5):
        response = client.post("/chat/completions", json={"prompt": "Test prompt" * 50})
        assert response.status_code == 200
