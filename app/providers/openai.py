import time

from openai import APIError, AsyncOpenAI
from openai import RateLimitError as OpenAIRateLimitError

from app.config import ProviderSpec
from app.exceptions import RateLimitError
from app.models import ChatResponse
from app.providers.base import ProviderClient
from app.routing.strategy import estimate_cost


class OpenAIProvider(ProviderClient):
    """
    OpenAI implementation of the ProviderClient.
    Handles communication with OpenAI API.
    """

    def __init__(self, spec: ProviderSpec, api_key: str):
        super().__init__(spec.name)
        self.spec = spec
        self.client = AsyncOpenAI(api_key=api_key)

    async def chat(self, prompt: str, timeout_ms: int) -> ChatResponse:
        start_time = time.time()

        try:
            response = await self.client.chat.completions.create(
                model=self.spec.model,
                messages=[{"role": "user", "content": prompt}],
                timeout=timeout_ms / 1000,
            )
        except OpenAIRateLimitError as e:
            # Use provider-specific exception type instead of string matching
            raise RateLimitError(f"OpenAI rate limit: {str(e)}")
        except APIError as e:
            # Catch other OpenAI API errors and re-raise
            raise Exception(f"OpenAI API error: {str(e)}")

        actual_latency_ms = int((time.time() - start_time) * 1000)
        content = response.choices[0].message.content

        # Calculate cost based on usage if available, otherwise estimate
        # For simplicity in this iteration, we'll use our estimate function
        # but in a real app we might use response.usage
        cost = estimate_cost(self.spec, prompt)

        return ChatResponse(
            provider_used=self.name,
            content=content,
            latency_ms=actual_latency_ms,
            cost=cost,
        )
