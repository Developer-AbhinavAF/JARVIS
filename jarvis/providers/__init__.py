from jarvis.router_service import NineRouterClient, RouterResponse, RouterHealth, router_client
from jarvis.router.exceptions import (
    ProviderError,
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderAuthError,
    ProviderServerError,
    ProviderNetworkError,
    ProviderEmptyResponseError,
    ProviderOfflineError,
    ProviderModelNotFoundError,
    StreamError,
    AllProvidersExhaustedError,
)

LLMManager = NineRouterClient

def get_default_manager() -> NineRouterClient:
    return router_client

__all__ = [
    "LLMManager", "get_default_manager",
    "NineRouterClient", "RouterResponse", "RouterHealth", "router_client",
    "ProviderError", "ProviderTimeoutError", "ProviderRateLimitError",
    "ProviderAuthError", "ProviderServerError", "ProviderNetworkError",
    "ProviderEmptyResponseError", "ProviderOfflineError",
    "ProviderModelNotFoundError", "StreamError", "AllProvidersExhaustedError",
]
