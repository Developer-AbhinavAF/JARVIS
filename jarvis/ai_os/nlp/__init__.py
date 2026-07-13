"""NLP subsystem for the AI OS.

This package contains the NLP pipeline implementations that always use
the AI Router via `jarvis.router_service.router_client`.
"""

from .pipeline import NLPPipeline

__all__ = ["NLPPipeline"]
