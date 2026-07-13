"""AI Operating System core package for JARVIS.

This package provides modular subsystems built on top of the
AI Router (`jarvis.router_service.router_client`). All LLM calls
must go through that client.
"""

from .core import AIOS
from .nlp.pipeline import NLPPipeline

__all__ = ["AIOS", "NLPPipeline"]
