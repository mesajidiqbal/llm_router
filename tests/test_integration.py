"""
Integration tests for provider registry, factory, and classifier.

Tests cover YAML configuration loading, provider instantiation,
and prompt classification logic.
"""

import os

import pytest
import yaml

from app.config import ProviderRegistry
from app.providers.factory import _provider_cache, get_provider
from app.routing.classifier import classify


@pytest.mark.asyncio
async def test_providers_yaml_exists():
    """Test that providers.yaml file exists and is valid."""
    assert os.path.exists("providers.yaml")
    with open("providers.yaml", "r") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)
    assert "openai" in data
    assert "google" in data


def test_provider_registry_loads_yaml():
    """Test that ProviderRegistry correctly loads from YAML."""
    providers = ProviderRegistry.providers_dict()
    assert "openai" in providers
    assert "google" in providers
    assert providers["openai"].model == "gpt-5"


@pytest.mark.asyncio
async def test_provider_factory_instantiation():
    """Test provider factory creates correct instances."""
    # clear cache to ensure fresh load
    _provider_cache.clear()

    # We are in mock env by default, so get_provider returns MockProvider
    # But let's verify it uses the correct spec from YAML
    provider = get_provider("openai")
    assert provider.name == "openai"
    assert provider.spec.quality_score == 0.95


@pytest.mark.asyncio
async def test_strategy_boost_settings():
    """Test strategy boost settings from configuration."""
    from app.models import UserPreference
    from app.routing.circuit_breaker import CircuitBreaker
    from app.routing.strategy import select_providers
    from app.storage.memory import MemoryStore

    memory = MemoryStore()
    cb = CircuitBreaker(memory)

    # Verify we can run selection without error using new settings
    providers = await select_providers(
        prompt="Write some code",
        preferences=UserPreference(priority="quality"),
        providers_list=ProviderRegistry.providers_list(),
        circuit_breaker=cb,
        memory=memory,
    )
    assert len(providers) > 0


# Classifier tests
def test_classify_code_prompts():
    """Test classification of code-related prompts."""
    assert classify("def my_function():") == "code"
    assert classify("create a class for user") == "code"
    assert classify("import the module") == "code"
    assert classify("handle this exception") == "code"


def test_classify_writing_prompts():
    """Test classification of writing-related prompts."""
    assert classify("write an essay about") == "writing"
    assert classify("create a blog post") == "writing"
    assert classify("send an email to") == "writing"
    assert classify("summarize this text") == "writing"


def test_classify_analysis_prompts():
    """Test classification defaults to analysis."""
    assert classify("what are the implications") == "analysis"
    assert classify("analyze the data") == "analysis"
    assert classify("explain this concept") == "analysis"
