"""
Circuit breaker pattern implementation for provider fault tolerance.

This module implements the circuit breaker pattern to prevent cascading failures
when providers become unhealthy. The circuit breaker monitors consecutive failures
and temporarily blocks requests to failing providers, allowing them time to recover.

States:
    CLOSED: Normal operation, requests flow through
    OPEN: Provider is failing, requests are blocked
    HALF_OPEN: Testing provider recovery with probe requests

Configuration is loaded from settings for threshold and duration.
"""

import time

from app.config import settings
from app.storage.memory import MemoryStore


class CircuitBreaker:
    """
    Circuit breaker pattern implementation using configurable thresholds.

    The circuit breaker prevents cascading failures by monitoring provider health
    and temporarily blocking requests to failing providers. After a timeout period,
    it allows probe requests to test if the provider has recovered.

    Attributes:
        memory: Memory store for persisting circuit breaker state
        failure_threshold: Number of consecutive failures before opening circuit
        open_duration_s: Duration in seconds to keep circuit open before testing recovery
    """

    config = settings

    def __init__(self, memory: MemoryStore):
        """
        Initialize the circuit breaker with configuration from settings.

        Args:
            memory: Memory store instance for state persistence
        """
        self.memory = memory
        # Use configuration settings
        self.failure_threshold = settings.circuit_breaker_failure_threshold
        self.open_duration_s = settings.circuit_breaker_open_duration_s

    async def is_available(self, provider_name: str) -> bool:
        """
        Check if a provider is available based on circuit breaker state.

        This method implements the core circuit breaker logic:
        - CLOSED state: Provider is available
        - OPEN state: Provider is blocked (returns False)
        - HALF_OPEN state: One probe request is allowed to test recovery

        Args:
            provider_name: Name of the provider to check

        Returns:
            bool: True if requests can be sent to this provider, False otherwise

        State Transitions:
            - CLOSED → OPEN: When consecutive failures >= threshold
            - OPEN → HALF_OPEN: When open_duration has elapsed
            - HALF_OPEN → CLOSED: When probe request succeeds
            - HALF_OPEN → OPEN: When probe request fails
        """
        state = await self.memory.get_provider_dynamic_state(provider_name)
        consecutive_failures = state["consecutive_failures"]
        open_until_ts = state["open_until_ts"]

        # Circuit is CLOSED - provider is healthy
        if consecutive_failures < self.failure_threshold:
            return True

        now = time.time()

        # Circuit is OPEN - still within timeout period
        if open_until_ts > 0 and now < open_until_ts:
            return False

        # Timeout expired - transition to HALF_OPEN for one probe request
        if open_until_ts > 0 and now >= open_until_ts:
            if not state["half_open_probe_in_flight"]:
                # Allow one probe request
                await self.memory.set_half_open_probe(provider_name, True)
                return True
            else:
                # Probe already in flight, block other requests
                return False

        return True

    async def record_outcome(self, provider_name: str, success: bool):
        """
        Record the outcome of a request and update circuit breaker state.

        This method updates failure counts and manages state transitions based
        on request outcomes. Successful requests reset the failure count and
        close the circuit. Failed requests increment the failure count and
        may open the circuit if the threshold is reached.

        Args:
            provider_name: Name of the provider that handled the request
            success: True if request succeeded, False if it failed

        Side Effects:
            - Success: Resets consecutive failures, closes circuit, clears probe flag
            - Failure: Increments failures, may open circuit, clears probe flag
        """
        state = await self.memory.get_provider_dynamic_state(provider_name)

        if success:
            # Success resets the circuit to CLOSED state
            await self.memory.record_success(provider_name)
            await self.memory.clear_circuit_open(provider_name)
            await self.memory.set_half_open_probe(provider_name, False)
        else:
            # Record failure and check if we need to open the circuit
            await self.memory.record_failure(provider_name)

            state = await self.memory.get_provider_dynamic_state(provider_name)
            consecutive_failures = state["consecutive_failures"]

            # Open the circuit if threshold is reached
            if consecutive_failures >= self.failure_threshold:
                open_until = time.time() + self.open_duration_s
                await self.memory.set_circuit_open(provider_name, open_until)

            await self.memory.set_half_open_probe(provider_name, False)

    async def get_status(self, provider_name: str) -> str:
        """
        Get the current circuit breaker status for a provider.

        Args:
            provider_name: Name of the provider to check

        Returns:
            str: One of "CLOSED", "OPEN", or "HALF_OPEN"

        Status Meanings:
            - CLOSED: Provider is healthy and accepting requests
            - OPEN: Provider is failing and requests are blocked
            - HALF_OPEN: Timeout expired, testing recovery with probe requests
        """
        state = await self.memory.get_provider_dynamic_state(provider_name)
        consecutive_failures = state["consecutive_failures"]
        open_until_ts = state["open_until_ts"]

        # Healthy - circuit is CLOSED
        if consecutive_failures < self.failure_threshold:
            return "CLOSED"

        now = time.time()

        # Currently in timeout period - circuit is OPEN
        if open_until_ts > 0 and now < open_until_ts:
            return "OPEN"

        # Timeout expired - circuit is HALF_OPEN
        if open_until_ts > 0 and now >= open_until_ts:
            return "HALF_OPEN"

        return "CLOSED"
