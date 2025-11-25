"""
Memory store and rate limiting tests.

Tests cover memory store methods, user spend tracking,
provider downtime management, global metrics, and rate limiting behavior.
"""

import pytest

from app.exceptions import RateLimitError
from app.storage.memory import MemoryStore


@pytest.mark.asyncio
async def test_get_user_spend():
    """Test getting user spend."""
    memory = MemoryStore()
    await memory.reset()

    await memory.add_user_spend("user1", 0.5)
    spend = await memory.get_user_spend("user1")
    assert spend == 0.5

    # Test non-existent user
    spend = await memory.get_user_spend("nonexistent")
    assert spend == 0.0


@pytest.mark.asyncio
async def test_set_provider_down():
    """Test manual provider downtime."""
    memory = MemoryStore()
    await memory.reset()

    await memory.set_provider_down("openai", True)
    state = await memory.get_provider_dynamic_state("openai")
    assert state["is_down"] is True

    await memory.set_provider_down("openai", False)
    state = await memory.get_provider_dynamic_state("openai")
    assert state["is_down"] is False


@pytest.mark.asyncio
async def test_global_metrics():
    """Test global metrics calculation."""
    memory = MemoryStore()
    await memory.reset()

    # Record some metrics
    await memory.record_request_metrics("openai", 200, 0.001, True)
    await memory.record_request_metrics("google", 250, 0.002, True)
    await memory.record_request_metrics("openai", 300, 0.001, False)

    metrics = await memory.get_global_metrics()
    assert metrics["total_requests"] == 3
    assert metrics["total_success"] == 2
    assert metrics["total_failures"] == 1
    assert metrics["success_rate"] == pytest.approx(2 / 3)
    assert metrics["avg_latency_ms"] == pytest.approx((200 + 250) / 2)


@pytest.mark.asyncio
async def test_rate_limit_not_triggered_under_limit():
    """Test that requests under rate limit succeed."""
    memory = MemoryStore()
    await memory.reset()

    # Make a few requests (well under any limit)
    for i in range(3):
        await memory.check_and_increment_rate_limit("test_provider", 100)


@pytest.mark.asyncio
async def test_rate_limit_edge_cases():
    """Test rate limit window reset."""
    memory = MemoryStore()
    await memory.reset()

    # Test at exactly the limit
    for i in range(99):
        await memory.check_and_increment_rate_limit("test_provider", 100)

    # Should not raise yet
    await memory.check_and_increment_rate_limit("test_provider", 100)

    # Next one should raise
    with pytest.raises(RateLimitError):
        await memory.check_and_increment_rate_limit("test_provider", 100)
