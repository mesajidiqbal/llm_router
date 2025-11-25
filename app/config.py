from typing import Literal

from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    env: str = "local"
    mock: bool = True
    openai_api_key: SecretStr = SecretStr("")
    openai_api_model: str = "gpt-5"
    google_api_key: SecretStr = SecretStr("")
    google_api_model: str = "gemini-3-pro"
    mock_failure_rate: float = 0.1

    # Budget Configuration
    user_budget_cap: float = Field(
        default=1.00, gt=0, description="Per-user spending limit in USD"
    )

    # Circuit Breaker Configuration
    circuit_breaker_failure_threshold: int = 3
    circuit_breaker_open_duration_s: int = 60

    # Routing Strategy Configuration
    strategy_quality_boost: float = 1.1
    strategy_cost_speed_boost: float = 0.9

    @field_validator("mock_failure_rate")
    @classmethod
    def validate_failure_rate(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("mock_failure_rate must be between 0.0 and 1.0")
        return v

    @field_validator("circuit_breaker_failure_threshold")
    @classmethod
    def validate_cb_threshold(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("circuit_breaker_failure_threshold must be positive")
        return v

    @field_validator("circuit_breaker_open_duration_s")
    @classmethod
    def validate_cb_duration(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("circuit_breaker_open_duration_s must be positive")
        return v

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()


class ProviderSpec(BaseModel):
    """
    Specification for an LLM provider with validated configuration.

    Validates that all numeric values are in acceptable ranges and
    specialties are from known types.
    """

    name: str
    model: str
    cost_per_token: float = Field(gt=0, description="Cost per token must be positive")
    latency_ms: int = Field(gt=0, description="Latency in milliseconds must be positive")
    rate_limit_rpm: int = Field(gt=0, description="Rate limit (requests per minute) must be positive")
    specialties: list[Literal["code", "writing", "analysis"]] = Field(
        description="Provider specialties from allowed types"
    )
    quality_score: float = Field(ge=0.0, le=1.0, description="Quality score must be between 0.0 and 1.0")
    api_key_var: str | None = None
    provider_class: str | None = None


class ProviderRegistry:
    """
    Registry for available LLM providers and their specifications.
    This acts as the source of truth for provider capabilities and configuration.
    """

    @classmethod
    def providers_dict(cls) -> dict[str, ProviderSpec]:
        import yaml

        try:
            with open("providers.yaml", "r") as f:
                data = yaml.safe_load(f)

            providers = {}
            for key, value in data.items():
                # Allow model overrides from settings if needed, or just use YAML
                # For now, we trust the YAML.
                # If we wanted validation, we'd use pydantic models to validate 'value'
                providers[key] = ProviderSpec(**value)

            return providers
        except FileNotFoundError:
            # Fallback or error? For now let's raise error as it is critical
            raise RuntimeError("providers.yaml not found")
        except Exception as e:
            raise RuntimeError(f"Failed to load providers.yaml: {e}")

    @classmethod
    def providers_list(cls) -> list[ProviderSpec]:
        return list(cls.providers_dict().values())
