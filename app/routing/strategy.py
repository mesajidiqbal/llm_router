import asyncio
import math

from app.config import ProviderSpec, settings
from app.models import UserPreference
from app.routing.circuit_breaker import CircuitBreaker
from app.routing.classifier import classify
from app.storage.memory import MemoryStore


def estimate_tokens_tiktoken(text: str, model: str) -> int:
    """
    Use tiktoken for accurate token count with fallback.
    """
    try:
        import tiktoken

        # Try to get encoding for the specific model, fallback to cl100k_base
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except (ImportError, Exception):
        # Fallback to approximation if tiktoken not available
        return math.ceil(len(text) / 4)


def estimate_cost(provider: ProviderSpec, prompt: str) -> float:
    """Estimate cost using accurate tokenization"""
    tokens = estimate_tokens_tiktoken(prompt, provider.model)
    cost = tokens * provider.cost_per_token
    return cost


async def select_providers(
    prompt: str,
    preferences: UserPreference,
    providers_list: list[ProviderSpec],
    circuit_breaker: CircuitBreaker,
    memory: MemoryStore,
) -> list[ProviderSpec]:
    """
    Select and rank providers based on user preferences and provider status.
    Returns a sorted list of best matching providers.

    Uses asyncio.gather() to check all provider states in parallel for better performance.
    """

    request_type = classify(prompt)

    # Fetch all provider states in parallel for better performance
    provider_states = await asyncio.gather(
        *[memory.get_provider_dynamic_state(provider.name) for provider in providers_list]
    )

    provider_availability = await asyncio.gather(
        *[circuit_breaker.is_available(provider.name) for provider in providers_list]
    )

    available_providers = []
    for i, provider in enumerate(providers_list):
        state = provider_states[i]
        is_down = state["is_down"]

        if is_down:
            continue

        is_available = provider_availability[i]
        if not is_available:
            continue

        cost = estimate_cost(provider, prompt)
        if preferences.max_cost_per_request is not None and cost > preferences.max_cost_per_request:
            continue

        available_providers.append((provider, cost))

    # Sort providers by score using dictionary-based priority mapping
    def get_score(item: tuple[ProviderSpec, float]) -> float:
        """
        Calculate ranking score for a provider based on user priority.

        Uses a dictionary mapping for cleaner, more maintainable code.
        Lower scores are better for cost/speed (ascending sort).
        Higher scores (more negative) are better for quality (ascending sort of negative values).

        Args:
            item: Tuple of (provider, estimated_cost)

        Returns:
            float: Ranking score (lower is better for sorting)
        """
        provider, cost = item

        # Map priority to base score - makes it easy to add new priorities
        priority_scores = {
            "cost": cost,  # Lower cost is better
            "speed": provider.latency_ms,  # Lower latency is better
            "quality": -provider.quality_score,  # Negative for descending sort (higher quality = more negative)
        }
        score = priority_scores.get(preferences.priority, cost)  # Default to cost if unknown priority

        # Apply specialty boost if provider matches the classified request type
        # This gives a 10% advantage to specialists while still allowing cheaper/faster generalists to win
        if request_type in provider.specialties:
            # Map priority to appropriate boost multiplier
            boost_multipliers = {
                "quality": settings.strategy_quality_boost,  # e.g., 1.1 (makes negative score more negative)
                "cost": settings.strategy_cost_speed_boost,  # e.g., 0.9 (makes score smaller)
                "speed": settings.strategy_cost_speed_boost,  # e.g., 0.9 (makes score smaller)
            }
            boost = boost_multipliers.get(preferences.priority, 1.0)
            score *= boost

        return score

    available_providers.sort(key=get_score)

    return [p for p, c in available_providers]
