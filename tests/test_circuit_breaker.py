"""
Circuit breaker pattern tests.

Tests cover circuit breaker state transitions (CLOSED, OPEN, HALF_OPEN),
failure tracking, and recovery behavior.
"""

import time

import pytest


@pytest.mark.asyncio
async def test_circuit_breaker_logic(memory_store, circuit_breaker):
    """Test basic circuit breaker state transitions."""
    provider = "test_provider"

    # Defaults: threshold=3
    assert await circuit_breaker.is_available(provider)
    assert await circuit_breaker.get_status(provider) == "CLOSED"

    # Record 2 failures
    await circuit_breaker.record_outcome(provider, False)
    await circuit_breaker.record_outcome(provider, False)
    assert await circuit_breaker.is_available(provider)

    # 3rd failure -> OPEN
    await circuit_breaker.record_outcome(provider, False)
    assert not await circuit_breaker.is_available(provider)
    assert await circuit_breaker.get_status(provider) == "OPEN"

    # Success clear failures (if we manually reset or wait, but here testing logic)
    await memory_store.record_success(provider)
    # Check manual clear logic usually done by record_outcome(True)
    await circuit_breaker.record_outcome(provider, True)
    assert await circuit_breaker.is_available(provider)


@pytest.mark.asyncio
async def test_half_open_state(memory_store, circuit_breaker):
    """Test HALF_OPEN state behavior."""
    # Trigger failures to open circuit
    for _ in range(3):
        await circuit_breaker.record_outcome("test_provider", False)

    # Check OPEN state
    status = await circuit_breaker.get_status("test_provider")
    assert status == "OPEN"

    # Wait for timeout (simulate by clearing the timestamp)
    await memory_store.set_circuit_open("test_provider", time.time() - 1)

    # Should be HALF_OPEN now
    status = await circuit_breaker.get_status("test_provider")
    assert status == "HALF_OPEN"

    # Successful probe should close circuit
    await circuit_breaker.record_outcome("test_provider", True)
    status = await circuit_breaker.get_status("test_provider")
    assert status == "CLOSED"
