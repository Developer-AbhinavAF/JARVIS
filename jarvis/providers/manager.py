from jarvis.router_service import NineRouterClient, router_client

LLMManager = NineRouterClient

def get_default_manager() -> NineRouterClient:
    return router_client
