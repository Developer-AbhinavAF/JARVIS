"""Custom exceptions for the JARVIS AI Router."""

from __future__ import annotations


class RouterError(Exception):
    """Base exception for all router errors."""


# =============================================================================
# Provider-level exceptions
# =============================================================================

class ProviderError(RouterError):
    """Base exception for provider-related failures."""


class ProviderTimeoutError(ProviderError):
    """Request to provider timed out."""


class ProviderRateLimitError(ProviderError):
    """Provider returned a 429 rate limit."""
    def __init__(self, message: str = "", retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class ProviderAuthError(ProviderError):
    """Authentication failure (401/403)."""


class ProviderServerError(ProviderError):
    """Provider server error (5xx)."""


class ProviderNetworkError(ProviderError):
    """Network connectivity failure to provider."""


class ProviderEmptyResponseError(ProviderError):
    """Provider returned an empty or invalid response."""


class ProviderModelNotFoundError(ProviderError):
    """Requested model not found on provider (404)."""


class ProviderOfflineError(ProviderError):
    """Provider is marked offline."""


# =============================================================================
# Router-level exceptions
# =============================================================================

class AllProvidersExhaustedError(RouterError):
    """All eligible providers failed for the request."""


class NoProviderForCapabilityError(RouterError):
    """No provider registered for the requested capability."""


class NoProviderForModelError(RouterError):
    """No provider registered for the requested model."""


class RouterConfigurationError(RouterError):
    """Router is misconfigured."""


class RouterQuotaExceededError(RouterError):
    """All providers have exceeded their quota."""


# =============================================================================
# Streaming exceptions
# =============================================================================

class StreamError(RouterError):
    """Error during streaming."""


class StreamInterruptedError(StreamError):
    """Stream was interrupted mid-response."""


# =============================================================================
# Tool-calling exceptions
# =============================================================================

class ToolCallError(RouterError):
    """Error during tool calling."""


class ToolCallParseError(ToolCallError):
    """Failed to parse tool call response."""


# =============================================================================
# Validation exceptions
# =============================================================================

class ValidationError(RouterError):
    """Request or response validation failed."""


class InvalidRequestError(ValidationError):
    """Invalid request parameters."""


class InvalidResponseError(ValidationError):
    """Invalid response from provider."""


# =============================================================================
# Quota exceptions
# =============================================================================

class QuotaExceededError(ProviderError):
    """Provider quota has been exceeded."""


class DailyQuotaExceededError(QuotaExceededError):
    """Daily usage quota exceeded."""


class MonthlyQuotaExceededError(QuotaExceededError):
    """Monthly usage quota exceeded."""
