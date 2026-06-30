"""Provider-specific exceptions for the fallback chain."""


class ProviderError(Exception):
    """Base exception for all provider errors."""


class ProviderTimeoutError(ProviderError):
    """Request timed out."""


class ProviderRateLimitError(ProviderError):
    """Rate limited (HTTP 429)."""


class ProviderAuthError(ProviderError):
    """Authentication failure (HTTP 401/403)."""


class ProviderServerError(ProviderError):
    """Server error (HTTP 5xx)."""


class ProviderNetworkError(ProviderError):
    """Network connectivity failure."""


class ProviderEmptyResponseError(ProviderError):
    """Provider returned empty or invalid response."""


class ProviderStreamError(ProviderError):
    """Streaming failed mid-generation."""


class AllProvidersExhaustedError(ProviderError):
    """All providers in the chain failed."""
