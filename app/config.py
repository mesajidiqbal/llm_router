from pydantic import BaseModel


class ProviderSpec(BaseModel):
    name: str
    model: str
    cost_per_token: float
    latency_ms: int
    rate_limit_rpm: int
    specialties: list[str]
    quality_score: float


class ProviderRegistry:
    @classmethod
    def providers_dict(cls) -> dict[str, ProviderSpec]:
        return {
            "openai": ProviderSpec(
                name="openai",
                model="gpt-5.1",
                cost_per_token=0.00002,
                latency_ms=200,
                rate_limit_rpm=100,
                specialties=["code", "analysis", "writing"],
                quality_score=0.95,
            ),
            "google": ProviderSpec(
                name="google",
                model="gemini-pro",
                cost_per_token=0.000015,
                latency_ms=250,
                rate_limit_rpm=150,
                specialties=["writing", "analysis"],
                quality_score=0.94,
            ),
        }

    @classmethod
    def providers_list(cls) -> list[ProviderSpec]:
        return list(cls.providers_dict().values())
