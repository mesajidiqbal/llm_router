"""
Thread-safe in-memory storage for provider state, metrics, and user budgets.

This module implements a singleton memory store that provides thread-safe operations
for managing all application state including circuit breaker data, metrics collection,
rate limiting windows, and user spending tracking.

Thread Safety:
    All operations use an asyncio.Lock to ensure thread-safe access to shared state.
    This is critical for concurrent request handling in the FastAPI application.

Singleton Pattern:
    The MemoryStore uses a singleton pattern to ensure a single shared state across
    the entire application. Multiple instantiations return the same instance.
"""

import asyncio
import time
from typing import Optional

from app.exceptions import RateLimitError


class MemoryStore:
    """
    Thread-safe singleton store for all application state.

    This class manages provider health state, request metrics, rate limiting,
    and user budget tracking. All methods are async and use locking to ensure
    thread-safe concurrent access.

    State Categories:
        - Provider Health: is_down flags, circuit breaker state
        - Circuit Breaker: consecutive failures, open timestamps, probe flags
        - Rate Limiting: rolling 60-second windows per provider
        - Metrics: request counts, latencies, costs (global and per-provider)
        - User Budgets: spending totals per user_id

    Attributes:
        _instance: Singleton instance
        _lock: Class-level lock for singleton creation
        _provider_lock: Instance-level lock for all state operations
    """

    _instance: Optional["MemoryStore"] = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __new__(cls):
        """
        Ensure only one instance of MemoryStore exists (singleton pattern).

        Returns:
            MemoryStore: The single shared instance
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """
        Initialize memory store state (only runs once due to singleton pattern).

        Initializes all internal dictionaries and counters for tracking provider
        state, metrics, rate limits, and user budgets.
        """
        if self._initialized:
            return

        self._provider_lock = asyncio.Lock()

        # Provider health state
        self._is_down: dict[str, bool] = {}
        self._consecutive_failures: dict[str, int] = {}
        self._open_until_ts: dict[str, float] = {}
        self._half_open_probe: dict[str, bool] = {}

        # Rate limiting (rolling 60-second windows)
        self._rate_window_start: dict[str, float] = {}
        self._rate_window_count: dict[str, int] = {}

        # Global metrics
        self._total_requests = 0
        self._total_success = 0
        self._total_failures = 0
        self._total_latency_sum = 0.0
        self._total_cost = 0.0

        # Per-provider metrics
        self._provider_requests: dict[str, int] = {}
        self._provider_success: dict[str, int] = {}
        self._provider_failures: dict[str, int] = {}
        self._provider_latency_sum: dict[str, float] = {}

        # User budget tracking
        self._user_spend: dict[str, float] = {}

        self._initialized = True

    async def reset(self) -> None:
        """
        Reset all state in the memory store to initial values.

        This method clears all dictionaries and resets counters. It is thread-safe
        and primarily used for testing or system resets.

        Thread Safety:
            Acquires _provider_lock before modifying state.
        """
        async with self._provider_lock:
            self._is_down.clear()
            self._consecutive_failures.clear()
            self._open_until_ts.clear()
            self._half_open_probe.clear()
            self._rate_window_start.clear()
            self._rate_window_count.clear()
            self._total_requests = 0
            self._total_success = 0
            self._total_failures = 0
            self._total_latency_sum = 0.0
            self._total_cost = 0.0
            self._provider_requests.clear()
            self._provider_success.clear()
            self._provider_failures.clear()
            self._provider_latency_sum.clear()
            self._user_spend.clear()

    async def get_provider_dynamic_state(self, name: str) -> dict:
        """
        Get current dynamic state for a provider (circuit breaker data).

        Args:
            name: Provider name

        Returns:
            dict: Provider state containing:
                  - is_down: Manual downtime flag
                  - consecutive_failures: Number of consecutive failures
                  - open_until_ts: Timestamp when circuit can transition to HALF_OPEN
                  - half_open_probe_in_flight: Whether a probe request is active
        """
        async with self._provider_lock:
            return {
                "is_down": self._is_down.get(name, False),
                "consecutive_failures": self._consecutive_failures.get(name, 0),
                "open_until_ts": self._open_until_ts.get(name, 0),
                "half_open_probe_in_flight": self._half_open_probe.get(name, False),
            }

    async def set_provider_down(self, name: str, down: bool):
        """
        Manually mark a provider as down or up (for testing/admin purposes).

        Args:
            name: Provider name
            down: True to mark as down, False to mark as up
        """
        async with self._provider_lock:
            self._is_down[name] = down

    async def record_failure(self, name: str):
        """
        Record a provider failure (increments consecutive failure count).

        Args:
            name: Provider name
        """
        async with self._provider_lock:
            self._consecutive_failures[name] = self._consecutive_failures.get(name, 0) + 1

    async def record_success(self, name: str):
        """
        Record a provider success (resets consecutive failure count to 0).

        Args:
            name: Provider name
        """
        async with self._provider_lock:
            self._consecutive_failures[name] = 0

    async def get_user_spend(self, user_id: str) -> float:
        """
        Get total spending for a user.

        Args:
            user_id: Unique user identifier

        Returns:
            float: Total cost in USD, returns 0.0 if user has no spending history
        """
        async with self._provider_lock:
            return self._user_spend.get(user_id, 0.0)

    async def add_user_spend(self, user_id: str, cost: float):
        """
        Add to a user's total spending.

        Args:
            user_id: Unique user identifier
            cost: Cost to add in USD
        """
        async with self._provider_lock:
            self._user_spend[user_id] = self._user_spend.get(user_id, 0.0) + cost

    async def record_request_metrics(self, provider_name: str, latency_ms: int, cost: float, success: bool):
        """
        Record metrics for a completed request.

        Updates both global and per-provider metrics including request counts,
        success/failure counts, latency sums, and total cost.

        Args:
            provider_name: Name of the provider that handled the request
            latency_ms: Request latency in milliseconds
            cost: Estimated cost of the request in USD
            success: Whether the request succeeded

        Note:
            Latency is only recorded for successful requests to avoid skewing
            average latency calculations with failed requests.
        """
        async with self._provider_lock:
            self._total_requests += 1

            # Initialize provider metrics if this is the first request
            if provider_name not in self._provider_requests:
                self._provider_requests[provider_name] = 0
                self._provider_success[provider_name] = 0
                self._provider_failures[provider_name] = 0
                self._provider_latency_sum[provider_name] = 0.0

            self._provider_requests[provider_name] += 1

            if success:
                # Record success metrics
                self._total_success += 1
                self._provider_success[provider_name] += 1
                # Only record latency for successful requests
                self._total_latency_sum += latency_ms
                self._provider_latency_sum[provider_name] += latency_ms
                self._total_cost += cost
            else:
                # Record failure metrics
                self._total_failures += 1
                self._provider_failures[provider_name] += 1

    async def check_and_increment_rate_limit(self, provider_name: str, rpm_limit: int):
        """
        Check and increment the rate limit counter for a provider.

        Implements a rolling 60-second window for rate limiting. If the limit
        is exceeded, raises a RateLimitError.

        Args:
            provider_name: Name of the provider to check
            rpm_limit: Requests per minute limit

        Raises:
            RateLimitError: If the rate limit would be exceeded

        Algorithm:
            - Maintains a 60-second rolling window per provider
            - Resets the window when 60+ seconds have elapsed
            - Increments counter and checks against limit
        """
        async with self._provider_lock:
            now = time.time()

            window_start = self._rate_window_start.get(provider_name, now)
            window_count = self._rate_window_count.get(provider_name, 0)

            # Reset window if 60 seconds have elapsed
            if now - window_start >= 60:
                self._rate_window_start[provider_name] = now
                self._rate_window_count[provider_name] = 0
                window_count = 0

            # Increment counter
            self._rate_window_count[provider_name] = window_count + 1

            # Check if limit exceeded (after incrementing)
            if self._rate_window_count[provider_name] > rpm_limit:
                raise RateLimitError(f"Rate limit exceeded for {provider_name}")

    async def get_global_metrics(self) -> dict:
        """
        Get aggregated metrics across all providers.

        Returns:
            dict: Global metrics containing:
                  - total_requests: Total number of requests
                  - total_success: Number of successful requests
                  - total_failures: Number of failed requests
                  - avg_latency_ms: Average latency (successful requests only)
                  - total_cost: Total cost across all requests
                  - success_rate: Ratio of successes to total requests

        Note:
            Success rate defaults to 1.0 if no requests have been made yet.
            Average latency defaults to 0.0 if no successful requests exist.
        """
        async with self._provider_lock:
            success_rate = self._total_success / self._total_requests if self._total_requests > 0 else 1.0
            avg_latency = self._total_latency_sum / self._total_success if self._total_success > 0 else 0.0

            return {
                "total_requests": self._total_requests,
                "total_success": self._total_success,
                "total_failures": self._total_failures,
                "avg_latency_ms": avg_latency,
                "total_cost": self._total_cost,
                "success_rate": success_rate,
            }

    async def get_provider_metrics(self) -> dict[str, dict]:
        """
        Get detailed metrics for each provider.

        Returns:
            dict: Mapping of provider names to their metrics, each containing:
                  - requests: Total number of requests
                  - success: Number of successful requests
                  - failures: Number of failed requests
                  - success_rate: Ratio of successes to total requests
                  - avg_latency_ms: Average latency (successful requests only)

        Note:
            Only includes providers that have handled at least one request.
            Success rate defaults to 1.0 for providers with no requests.
            Average latency defaults to 0.0 for providers with no successes.
        """
        async with self._provider_lock:
            metrics = {}
            for provider_name in self._provider_requests.keys():
                requests = self._provider_requests[provider_name]
                successes = self._provider_success[provider_name]
                failures = self._provider_failures[provider_name]
                latency_sum = self._provider_latency_sum[provider_name]

                success_rate = successes / requests if requests > 0 else 1.0
                avg_latency = latency_sum / successes if successes > 0 else 0.0

                metrics[provider_name] = {
                    "requests": requests,
                    "success": successes,
                    "failures": failures,
                    "success_rate": success_rate,
                    "avg_latency_ms": avg_latency,
                }

            return metrics

    async def set_circuit_open(self, name: str, open_until_ts: float):
        """
        Set a provider's circuit to OPEN state until the specified timestamp.

        Args:
            name: Provider name
            open_until_ts: Unix timestamp when circuit can transition to HALF_OPEN
        """
        async with self._provider_lock:
            self._open_until_ts[name] = open_until_ts

    async def clear_circuit_open(self, name: str):
        """
        Clear a provider's circuit OPEN state (transition to CLOSED).

        Args:
            name: Provider name
        """
        async with self._provider_lock:
            self._open_until_ts[name] = 0

    async def set_half_open_probe(self, name: str, in_flight: bool):
        """
        Set or clear the HALF_OPEN probe request flag for a provider.

        Args:
            name: Provider name
            in_flight: True if a probe request is in flight, False otherwise
        """
        async with self._provider_lock:
            self._half_open_probe[name] = in_flight
