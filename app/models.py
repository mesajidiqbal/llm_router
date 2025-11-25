from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.config import ProviderSpec


class Priority(str, Enum):
    cost = "cost"
    speed = "speed"
    quality = "quality"


class UserPreference(BaseModel):
    priority: Priority = Priority.cost
    max_cost_per_request: Optional[float] = None
    timeout_ms: int = 5000

    @field_validator("max_cost_per_request")
    @classmethod
    def validate_max_cost(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("max_cost_per_request must be positive")
        return v

    @field_validator("timeout_ms")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("timeout_ms must be positive")
        return v


class ChatRequest(BaseModel):
    prompt: str
    preferences: UserPreference = Field(default_factory=UserPreference)
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    provider_used: str
    content: str
    latency_ms: int
    cost: float


class ProviderStatus(ProviderSpec):
    is_down: bool
    circuit_status: str
    success_rate: float


# Response models for API endpoints


class RootResponse(BaseModel):
    """Response model for root endpoint."""

    message: str
    version: str
    docs: dict[str, str]


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: Literal["healthy", "degraded"]
    providers_available: int
    providers_total: int
    version: str


class FailureSimulationRequest(BaseModel):
    """Request model for failure simulation endpoint."""

    provider: str = Field(description="Provider name to simulate failure for")
    down: bool = Field(default=False, description="True to mark provider as down, False to mark as up")


class FailureSimulationResponse(BaseModel):
    """Response model for failure simulation endpoint."""

    message: str


class GlobalMetrics(BaseModel):
    """Global metrics across all providers."""

    total_requests: int
    total_success: int
    total_failures: int
    avg_latency_ms: float
    total_cost: float
    success_rate: float


class ProviderMetrics(BaseModel):
    """Metrics for a specific provider."""

    requests: int
    success: int
    failures: int
    success_rate: float
    avg_latency_ms: float
    is_down: bool
    circuit_status: str


class AnalyticsResponse(BaseModel):
    """Response model for analytics endpoint."""

    global_metrics: GlobalMetrics = Field(alias="global")
    providers: dict[str, ProviderMetrics]

    model_config = {"populate_by_name": True}
