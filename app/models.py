from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Priority(str, Enum):
    cost = "cost"
    speed = "speed"
    quality = "quality"


class UserPreference(BaseModel):
    priority: Priority = Priority.cost
    max_cost_per_request: Optional[float] = None
    timeout_ms: int = 5000


class ChatRequest(BaseModel):
    prompt: str
    preferences: UserPreference = Field(default_factory=UserPreference)
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    provider_used: str
    content: str
    latency_ms: int
    cost: float


from app.config import ProviderSpec

class ProviderStatus(ProviderSpec):
    is_down: bool
    circuit_status: str
    success_rate: float
