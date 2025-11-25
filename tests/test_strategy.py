"""
Provider selection strategy tests.

Tests cover provider selection logic, ranking by priority,
cost estimation, and preference handling.
"""

import pytest

from app.config import ProviderRegistry, ProviderSpec
from app.models import UserPreference
from app.routing.circuit_breaker import CircuitBreaker
from app.routing.strategy import estimate_cost, estimate_tokens_tiktoken, select_providers
from app.storage.memory import MemoryStore


@pytest.mark.asyncio
async def test_select_providers(memory_store, circuit_breaker):
    """Test basic provider selection with different priorities."""
    providers = [
        ProviderSpec(
            name="p1",
            model="m1",
            cost_per_token=1.0,
            latency_ms=100,
            rate_limit_rpm=10,
            specialties=[],
            quality_score=1.0,
        ),
        ProviderSpec(
            name="p2",
            model="m2",
            cost_per_token=2.0,
            latency_ms=50,
            rate_limit_rpm=10,
            specialties=[],
            quality_score=1.0,
        ),
    ]

    # Test Cost Priority
    prefs = UserPreference(priority="cost")
    selected = await select_providers("test", prefs, providers, circuit_breaker, memory_store)
    assert selected[0].name == "p1"

    # Test Speed Priority
    prefs = UserPreference(priority="speed")
    selected = await select_providers("test", prefs, providers, circuit_breaker, memory_store)
    assert selected[0].name == "p2"


@pytest.mark.asyncio
async def test_cost_estimation():
    """Test token estimation and cost calculation."""
    from app.config import ProviderSpec

    prompt = "This is a test prompt"
    tokens = estimate_tokens_tiktoken(prompt, "gpt-4")
    assert tokens > 0

    # Create a test provider spec
    test_provider = ProviderSpec(
        name="test",
        model="gpt-4",
        cost_per_token=0.00002,
        latency_ms=100,
        rate_limit_rpm=10,
        specialties=[],
        quality_score=0.9,
    )

    cost = estimate_cost(test_provider, prompt)
    assert cost > 0
    assert cost == tokens * 0.00002


@pytest.mark.asyncio
async def test_preference_priorities():
    """Test different priority preferences."""
    memory = MemoryStore()
    await memory.reset()
    cb = CircuitBreaker(memory)

    # Test each priority
    for priority in ["cost", "speed", "quality"]:
        providers = await select_providers(
            prompt="test",
            preferences=UserPreference(priority=priority),
            providers_list=ProviderRegistry.providers_list(),
            circuit_breaker=cb,
            memory=memory,
        )
        assert len(providers) > 0
