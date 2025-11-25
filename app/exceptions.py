class LLMException(Exception):
    """Base exception for all LLM Router errors."""

    pass


class ProviderError(LLMException):
    """Base exception for provider-related errors."""

    def __init__(self, message: str, provider_name: str = None):
        super().__init__(message)
        self.provider_name = provider_name


class RateLimitError(ProviderError):
    """Raised when a provider's rate limit is exceeded."""

    pass


class ContextWindowExceededError(ProviderError):
    """Raised when the prompt exceeds the provider's context window."""

    pass


class ServiceUnavailableError(LLMException):
    """Raised when no providers are available to handle the request."""

    pass
