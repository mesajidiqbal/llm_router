"""Shared test fixtures for all tests."""

import pytest

from app.routing.circuit_breaker import CircuitBreaker
from app.routing.metrics import MetricsService
from app.storage.memory import MemoryStore


@pytest.fixture
async def memory_store():
    """
    Create a fresh MemoryStore instance for testing.

    This fixture provides an isolated memory store for each test,
    ensuring test independence.
    """
    store = MemoryStore()
    await store.reset()
    return store


@pytest.fixture
async def circuit_breaker(memory_store):
    """
    Create a fresh CircuitBreaker instance for testing.

    Args:
        memory_store: The memory store fixture (injected by pytest)
    """
    return CircuitBreaker(memory_store)


@pytest.fixture
async def metrics_service(memory_store, circuit_breaker):
    """
    Create a fresh MetricsService instance for testing.

    Args:
        memory_store: The memory store fixture (injected by pytest)
        circuit_breaker: The circuit breaker fixture (injected by pytest)
    """
    return MetricsService(memory_store, circuit_breaker)
