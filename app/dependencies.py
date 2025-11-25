"""
Centralized dependency injection for FastAPI.

This module provides singleton instances of core services using FastAPI's
dependency injection system with @lru_cache() for singleton management.

All dependencies can be overridden in tests using app.dependency_overrides.
"""

from functools import lru_cache

from app.routing.circuit_breaker import CircuitBreaker
from app.routing.metrics import MetricsService
from app.services.router_service import RouterService
from app.storage.memory import MemoryStore


@lru_cache()
def get_memory() -> MemoryStore:
    """
    Get singleton MemoryStore instance.

    Returns:
        MemoryStore: Shared memory store for all application state
    """
    return MemoryStore()


@lru_cache()
def get_circuit_breaker() -> CircuitBreaker:
    """
    Get singleton CircuitBreaker instance.

    Returns:
        CircuitBreaker: Shared circuit breaker service
    """
    return CircuitBreaker(get_memory())


@lru_cache()
def get_metrics_service() -> MetricsService:
    """
    Get singleton MetricsService instance.

    Returns:
        MetricsService: Shared metrics collection service
    """
    return MetricsService(get_memory(), get_circuit_breaker())


@lru_cache()
def get_router_service() -> RouterService:
    """
    Get singleton RouterService instance.

    Returns:
        RouterService: Main request routing service
    """
    return RouterService(get_memory(), get_circuit_breaker(), get_metrics_service())
