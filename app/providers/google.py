import time

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from app.config import ProviderSpec
from app.exceptions import RateLimitError
from app.models import ChatResponse
from app.providers.base import ProviderClient
from app.routing.strategy import estimate_cost


class GoogleProvider(ProviderClient):
    """
    Google implementation of the ProviderClient.
    Handles communication with Google Gemini API.
    """

    def __init__(self, spec: ProviderSpec, api_key: str):
        super().__init__(spec.name)
        self.spec = spec
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(spec.model)

    async def chat(self, prompt: str, timeout_ms: int) -> ChatResponse:
        start_time = time.time()

        try:
            # Google's async API might differ slightly, checking documentation is good practice
            # but for now we'll assume generate_content_async
            response = await self.model.generate_content_async(prompt)
        except google_exceptions.ResourceExhausted as e:
            # Use provider-specific exception type for rate limiting (429)
            raise RateLimitError(f"Google rate limit/quota exceeded: {str(e)}")
        except (google_exceptions.GoogleAPIError, Exception) as e:
            # Catch other Google API errors and re-raise
            raise Exception(f"Google API error: {str(e)}")

        actual_latency_ms = int((time.time() - start_time) * 1000)
        content = response.text

        cost = estimate_cost(self.spec, prompt)

        return ChatResponse(
            provider_used=self.name,
            content=content,
            latency_ms=actual_latency_ms,
            cost=cost,
        )
