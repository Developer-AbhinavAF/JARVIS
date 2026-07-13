"""Rule-based NLP pipeline for JARVIS.

This package provides the pre-LLM processing layer that handles
intent classification, entity extraction, and tool routing
without ever calling the LLM.
"""

from .normalizer import normalize, normalize_keep_case, normalize_for_matching
from .synonyms import expand_synonyms
from .patterns import PatternBank
from .confidence import ConfidenceScorer
from .entity_extractor import EntityExtractor
from .parameter_parser import ParameterParser
from .intent_classifier import IntentClassifier, IntentResult
from .command_parser import CommandParser
from .tool_router import NLPToolRouter
from .context_memory import ContextMemory, context_memory
from .self_learning import SelfLearningEngine, self_learning

__all__ = [
    "normalize",
    "normalize_keep_case",
    "normalize_for_matching",
    "expand_synonyms",
    "PatternBank",
    "ConfidenceScorer",
    "EntityExtractor",
    "ParameterParser",
    "IntentClassifier",
    "IntentResult",
    "CommandParser",
    "NLPToolRouter",
    "ContextMemory",
    "context_memory",
    "SelfLearningEngine",
    "self_learning",
]
