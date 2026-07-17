"""JARVIS Semantic NLP Engine v3.

Human-level NLP engine that understands meaning, not keywords.

Architecture (V3 — Advanced Cognitive NLP + Part 3):
    User Input
      → Language Detection
      → Normalization
      → Semantic Parsing
      → Context Resolution (pronouns, references, 20+ state fields)
      → Reasoning Engine (pre-action internal reasoning)
      → Intent Detection (semantic similarity + embeddings)
      → Entity Extraction (fuzzy matching)
      → Emotion Detection (12 emotional states)
      → Conversation Analysis (command vs statement vs implicit)
      → Implicit Intent Detection (goal inference from statements)
      → Goal Detection (implicit objectives)
      → Habit & Routine Detection
      → Capability Detection (28 capability types)
      → Tool Resolution (intent + entities + context + reliability → best tool)
      → Parameter Building
      → Planning (unlimited chain with dependency graph)
      → Safety Validation (dangerous operation detection)
      → Confidence Scoring (multi-signal aggregation)
      → Internet Decision (LLM vs web search)
      → User Profiling (preference learning)
      → Personal Language (user vocabulary mapping)
      → Knowledge Routing (domain source priority)
      → Response Generation (context-dependent responses)
      → Response Quality Check (pre-send validation)
      → Memory & Learning (with importance scoring & decay)
      → Self-Improvement Analysis
      → Background Learning (non-blocking tasks)
      → Context Update
      → Digital Twin Update
      → Knowledge Graph
      → Semantic Memory
      → Cognitive Architecture (Perceive → Attend → Think → Decide → Act → Reflect → Learn)
      → Planning Engine (Decompose → Graph → Dependencies → Priorities → Estimate → Recover → Optimize → Execute → Reflect)
      → Computer Vision & Environment Understanding (Screen → OCR → UI Detection → Layout → Visual Reasoning)
"""

from __future__ import annotations

import time
import logging
from typing import Any, Callable

from .utils import (
    NLPOutput, NLPInput, Entity, IntentCandidate,
    PlanStep, GoalCategory, ExecutionMode, Language,
    tokenize, remove_stop_words, semantic_similarity,
)
from .language_detector import detect_language, get_language_confidence
from .normalizer import normalize
from .semantic_parser import SemanticParser, SentenceStructure
from .intent_engine import SemanticIntentEngine
from .entity_extractor import SemanticEntityExtractor
from .context_engine import ContextEngine
from .goal_detector import GoalDetector
from .planner import Planner
from .capability_detector import CapabilityDetector
from .tool_selector import ToolSelector
from .parameter_builder import ParameterBuilder
from .validator import ConfidenceScorer, NLPOutputValidator
from .learning_engine import LearningEngine
from .memory_bridge import MemoryBridge
from .execution_bridge import ExecutionBridge

# V3 Cognitive modules
from .emotion_detector import EmotionDetector
from .conversation_analyzer import ConversationAnalyzer
from .implicit_intent import ImplicitIntentDetector
from .user_profiler import UserProfiler
from .personal_language import PersonalLanguageModel
from .self_correction import SelfCorrectionEngine
from .adaptive_executor import AdaptiveExecutor
from .safety_validator import SafetyValidator
from .confidence_engine import ConfidenceEngine, ConfidenceSignals
from .response_generator import ResponseGenerator
from .execution_feedback import ExecutionFeedback
from .knowledge_router import KnowledgeRouter

# V3 Part 3 modules (Advanced Semantic Reasoning, Tool Intelligence & Learning)
from .semantic_engine import SemanticEmbeddingEngine, semantic_engine
from .tool_registry import DynamicToolRegistry, tool_registry
from .memory_manager import MemoryManager, memory_manager
from .failure_memory import FailureMemory, failure_memory
from .reasoning_engine import ReasoningEngine, reasoning_engine
from .habit_detector import HabitDetector, habit_detector
from .self_improvement import (
    SelfImprovementEngine, self_improvement,
    ResponseQualityChecker, quality_checker,
    BackgroundLearning, background_learning,
)

# V3 Part 4 modules (Cognitive Execution, Autonomous Agent & AGI Foundation)
from .knowledge_graph import KnowledgeGraph, knowledge_graph
from .part4_modules import (
    SemanticMemoryGraph, semantic_memory_graph,
    UserDigitalTwin, user_digital_twin,
    ToolHealthSystem, tool_health_system,
    ErrorExplainer, error_explainer,
)

# Tool Intelligence Layer (Autonomous Execution)
from jarvis.tool_intelligence import ToolIntelligenceEngine, tool_intelligence

# Cognitive Architecture (Executive Brain)
from jarvis.cognitive import CognitiveEngine, cognitive_engine

# Planning Engine (Autonomous Task Management)
from jarvis.planner import PlanningEngine, planning_engine

# Computer Vision & Environment Understanding
from jarvis.vision import VisionEngine, vision_engine

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCES
# ════════════════════════════════════════════════════════════════════

semantic_parser = SemanticParser()
intent_engine = SemanticIntentEngine()
entity_extractor = SemanticEntityExtractor()
context_engine = ContextEngine()
goal_detector = GoalDetector()
planner = Planner()
capability_detector = CapabilityDetector()
tool_selector = ToolSelector()
parameter_builder = ParameterBuilder()
confidence_scorer = ConfidenceScorer()
output_validator = NLPOutputValidator()
learning_engine = LearningEngine()
memory_bridge = MemoryBridge()
execution_bridge = ExecutionBridge()

# V3 cognitive instances
emotion_detector = EmotionDetector()
conversation_analyzer = ConversationAnalyzer()
implicit_intent_detector = ImplicitIntentDetector()
user_profiler = UserProfiler()
personal_language = PersonalLanguageModel()
self_correction = SelfCorrectionEngine()
adaptive_executor = AdaptiveExecutor()
safety_validator = SafetyValidator()
confidence_engine = ConfidenceEngine()
response_generator = ResponseGenerator()
execution_feedback = ExecutionFeedback()
knowledge_router = KnowledgeRouter()


# ════════════════════════════════════════════════════════════════════
# MASTER NLP PIPELINE (V3)
# ════════════════════════════════════════════════════════════════════

class SemanticNLPEngine:
    """The master cognitive NLP engine.

    Processes user input through a 20+ phase semantic understanding pipeline.
    No module should directly parse user input except this engine.
    """

    def __init__(self) -> None:
        # Core modules
        self.parser = semantic_parser
        self.intent = intent_engine
        self.entities = entity_extractor
        self.context = context_engine
        self.goals = goal_detector
        self.planner = planner
        self.capabilities = capability_detector
        self.tools = tool_selector
        self.params = parameter_builder
        self.confidence = confidence_scorer
        self.validator = output_validator
        self.learning = learning_engine
        self.memory = memory_bridge
        self.executor = execution_bridge

        # V3 cognitive modules
        self.emotion = emotion_detector
        self.conversation = conversation_analyzer
        self.implicit_intent = implicit_intent_detector
        self.user_profiler = user_profiler
        self.personal_language = personal_language
        self.self_correction = self_correction
        self.adaptive = adaptive_executor
        self.safety = safety_validator
        self.confidence_engine = confidence_engine
        self.response_gen = response_generator
        self.feedback = execution_feedback
        self.knowledge = knowledge_router

        # V3 Part 3 modules (Advanced Semantic Reasoning, Tool Intelligence & Learning)
        self.semantic_engine = semantic_engine
        self.tool_registry = tool_registry
        self.memory_manager = memory_manager
        self.failure_memory = failure_memory
        self.reasoning = reasoning_engine
        self.habit_detector = habit_detector
        self.self_improvement = self_improvement
        self.quality_checker = quality_checker
        self.background_learning = background_learning

        # V3 Part 4 modules (Cognitive Execution, Autonomous Agent & AGI Foundation)
        self.knowledge_graph = knowledge_graph
        self.semantic_memory = semantic_memory_graph
        self.digital_twin = user_digital_twin
        self.tool_health = tool_health_system
        self.error_explainer = error_explainer

        # Tool Intelligence Layer (Autonomous Execution)
        self.tool_intelligence = tool_intelligence

        # Cognitive Architecture (Executive Brain)
        self.cognitive = cognitive_engine

        # Planning Engine (Autonomous Task Management)
        self.planning_engine = planning_engine

        # Computer Vision & Environment Understanding
        self.vision = vision_engine

    def process(self, text: str, source: str = "text") -> NLPOutput:
        """Process user input through the full V3 cognitive NLP pipeline.

        This is the single entry point for all user input.
        Returns a complete NLPOutput with intent, entities, tool, parameters,
        emotion, conversation analysis, and response.
        """
        t0 = time.time()
        output = NLPOutput(raw_text=text)

        if not text or not text.strip():
            output.processing_time_ms = (time.time() - t0) * 1000
            return output

        # Start feedback session
        self.feedback.start_session()

        # ── Phase 1: Language Detection ──
        self.feedback.update("language_detection")
        lang = detect_language(text)
        lang_conf = get_language_confidence(text)
        output.language = lang

        # ── Phase 2: Normalization ──
        self.feedback.update("normalizing")
        normalized = normalize(text)
        output.normalized_text = normalized
        if not normalized:
            self.feedback.finish(False)
            output.processing_time_ms = (time.time() - t0) * 1000
            return output

        # ── Phase 3: Semantic Parsing ──
        sentence = self.parser.parse(normalized)
        if sentence.is_compound and sentence.actions:
            output.is_multi_intent = True
            output.sub_intents = [a.action for a in sentence.actions]
            if sentence.actions:
                normalized = sentence.actions[0].raw_span or normalized
                output.normalized_text = normalized
                sentence = self.parser.parse(normalized)

        # ── Phase 4: Context Resolution (Enhanced) ──
        self.feedback.update("context_resolution")
        context = {}
        if self.context.should_use_context():
            resolved = self.context.resolve_references(normalized)
            if resolved != normalized:
                normalized = resolved
                output.normalized_text = normalized
                sentence = self.parser.parse(normalized)
            context = self.context.snapshot()

        # ── Phase 4b: Pre-Vision Capability Detection ──
        # Run vision capability detection BEFORE intent classification
        # so that visual context is available for intent resolution
        self.feedback.update("vision_capability")
        _vision_caps = self.vision.capability_detector.detect(normalized)
        _pre_vision_state = None
        if _vision_caps.any_required() and _vision_caps.confidence >= 0.5:
            try:
                _pre_vision_state = self.vision.see()
                output.parameters["_pre_vision_state"] = {
                    "windows": _pre_vision_state.window_count,
                    "focused": _pre_vision_state.focused_app,
                    "elements": _pre_vision_state.element_count,
                    "has_errors": _pre_vision_state.has_errors,
                    "error_messages": _pre_vision_state.error_messages[:3] if _pre_vision_state.error_messages else [],
                }
                output.parameters["_vision_capabilities"] = _vision_caps.to_dict()
                # Feed visual context into the context for intent classification
                if context is None:
                    context = {}
                context["pre_vision_state"] = output.parameters["_pre_vision_state"]
                context["vision_capabilities"] = output.parameters["_vision_capabilities"]
            except Exception as e:
                logger.debug("Pre-vision capture failed: %s", e)
                _pre_vision_state = None

        # ── Phase 5: Intent Detection ──
        self.feedback.update("intent_detection")
        intent_candidates = self.intent.detect(normalized, context=context)

        if not intent_candidates:
            # Try implicit intent detection before giving up
            implicit_result = self.implicit_intent.detect(normalized, context=context)
            if implicit_result.detected:
                output.intent = implicit_result.intent
                output.intent_confidence = implicit_result.confidence
                output.goal = implicit_result.goal
                output.match_method = "implicit"
            else:
                # VISUAL ANALYSIS FALLBACK: if input looks visual, classify as VISUAL_ANALYSIS
                # This ensures visual queries never result in empty intent
                _VISUAL_FALLBACK_KEYWORDS = [
                    "screen", "see", "look", "read", "error", "what", "where",
                    "this", "that", "visible", "show", "display", "active",
                    "window", "app", "button", "find", "explain", "describe",
                    "happening", "open", "running", "code", "text", "read",
                ]
                _text_lower = text.lower()
                _is_visual = any(kw in _text_lower for kw in _VISUAL_FALLBACK_KEYWORDS)

                if _is_visual:
                    output.intent = "VISUAL_ANALYSIS"
                    output.intent_confidence = 0.6
                    output.match_method = "visual_fallback"
                    output.parameters["_visual_fallback"] = True
                else:
                    # No intent found - still run conversation analysis and emotion
                    # so output is never completely empty
                    output.execution_mode = ExecutionMode.FALLBACK_LLM

                    # Phase 7: Emotion
                    self.feedback.update("emotion_detection")
                    emotion_result = self.emotion.detect(text, context=context)
                    output.emotion = emotion_result.emotion
                    output.emotion_confidence = emotion_result.confidence
                    output.emotion_valence = emotion_result.valence
                    output.emotion_arousal = emotion_result.arousal

                    # Phase 8: Conversation Analysis
                    self.feedback.update("conversation_analysis")
                    conv_analysis = self.conversation.analyze(text, context=context)
                    output.conversation_type = conv_analysis.conversation_type
                    output.conversation_behavior = conv_analysis.suggested_behavior
                    output.conversation_confidence = conv_analysis.confidence

                    # Generate a basic response
                    resp = self.response_gen.generate(
                        intent=output.intent,
                        entities={},
                        execution_mode=output.execution_mode,
                        emotion=emotion_result.emotion,
                        context=context,
                    )
                    output.response_text = resp.text if hasattr(resp, "text") else str(resp)

                    self.feedback.finish(False)
                    output.processing_time_ms = (time.time() - t0) * 1000
                    output.execution_phases = self.feedback.get_all_phases()
                    return output
        else:
            best_intent = intent_candidates[0]
            output.intent = best_intent.intent
            output.intent_confidence = best_intent.score
            output.intent_reason = best_intent.reason
            output.goal = best_intent.goal
            output.match_method = "semantic"

        # ── FAST PATH: Skip heavy processing for simple intents ──
        _FAST_INTENTS = {
            "GREETING", "CHAT", "JOKE", "QUOTE", "FLIP_COIN", "DICE_ROLL",
            "DATETIME", "GET_TIME", "GET_DATE", "SYSTEM_STATUS",
            "SCREENSHOT", "VOLUME_CONTROL", "BRIGHTNESS_CONTROL",
            "ADD_NOTE", "GET_NOTES", "LIST_NOTES", "ADD_TODO",
            "GET_TODOS", "LIST_TODOS", "SAVE_MEMORY", "RECALL_MEMORY",
            "OPEN_APP", "CLOSE_APP", "OPEN_WEBSITE", "OPEN_FOLDER",
            "SEARCH_WEB", "WEB_SEARCH", "SEARCH_YOUTUBE",
            "PROGRAMMING", "WINDOW_CONTROL", "CLIPBOARD",
            "RANDOM_FACT", "IP_LOOKUP", "NASA_APOD", "NASA_MARS",
            "ISS_LOCATION", "STOCK_QUOTE", "CALCULATOR", "TIMER",
            "SYSTEM_POWER",
        }
        _is_fast = output.intent in _FAST_INTENTS

        if _is_fast:
            # Fast path: skip reasoning, cognitive, planning, vision, knowledge graph
            # Just do entity extraction + tool selection + confidence + response
            self.feedback.update("fast_path")

            # Entity extraction
            extraction_result = self.entities.extract(normalized, output.intent, context)
            entity_dict = extraction_result.entities if hasattr(extraction_result, 'entities') else extraction_result
            output.entities = {}
            for name, e in entity_dict.items():
                if hasattr(e, 'value'):
                    output.entities[name] = {"value": e.value, "confidence": e.confidence, "type": e.entity_type}
                else:
                    output.entities[name] = {"value": str(e), "confidence": 1.0, "type": ""}

            # Tool selection
            entity_values = {k: v["value"] for k, v in output.entities.items()}
            tool_name, handler, tool_params = self.tools.select(
                output.intent, entity_values, context, [],
            )
            output.tool = tool_name
            output.handler = handler

            # Parameters
            param_entities = {}
            for name, e in entity_dict.items():
                if hasattr(e, 'value'):
                    param_entities[name] = e
                else:
                    param_entities[name] = Entity(name=name, value=str(e), raw_value=str(e))
            param_dict = self.params.build(output.intent, param_entities, context, normalized)
            merged_params = {**tool_params, **param_dict}
            output.parameters = merged_params

            # Confidence: fast path guarantees high confidence for known intents
            output.confidence_score = 0.95
            output.confidence_level = "high"
            output.execution_mode = ExecutionMode.AUTO
            output.match_method = output.match_method or "semantic"

            # Response generation
            resp = self.response_gen.generate(
                intent=output.intent,
                entities=entity_values,
                execution_mode=output.execution_mode,
                emotion="neutral",
                context=context,
            )
            output.response_text = resp.text if hasattr(resp, "text") else str(resp)
            output.response_style = resp.style if hasattr(resp, "style") else ""

            # Memory update
            output.memory_update = self.memory.prepare_memory_entry(
                output.intent, entity_values, context,
                output.goal.value if hasattr(output.goal, 'value') else str(output.goal),
            )

            self.feedback.finish(True)
            output.execution_phases = self.feedback.get_all_phases()
            output.processing_time_ms = (time.time() - t0) * 1000

            logger.info(
                "NLP fast: intent=%s conf=%.2f tool=%s latency=%.1fms",
                output.intent, output.confidence_score,
                output.tool, output.processing_time_ms,
            )
            return output

        # ── Phase 5b: Reasoning Engine (V3 Part 3) ──
        self.feedback.update("reasoning")
        reasoning_result = self.reasoning.reason(
            text, output.intent, {},
            output.intent_confidence, context,
        )
        # Apply reasoning insights
        if reasoning_result.should_search and not output.tool:
            output.parameters["needs_search"] = True
            output.parameters["search_on_platform"] = reasoning_result.suggested_action
        if reasoning_result.should_remember:
            output.parameters["should_remember"] = True
        if reasoning_result.should_plan:
            output.is_multi_intent = True

        # ── Phase 6: Entity Extraction ──
        self.feedback.update("entity_extraction")
        extraction_result = self.entities.extract(normalized, output.intent, context)
        entity_dict = extraction_result.entities if hasattr(extraction_result, 'entities') else extraction_result
        output.entities = {}
        for name, e in entity_dict.items():
            if hasattr(e, 'value'):
                output.entities[name] = {"value": e.value, "confidence": e.confidence, "type": e.entity_type}
            else:
                output.entities[name] = {"value": str(e), "confidence": 1.0, "type": ""}

        # ── Phase 7: Emotion Detection ──
        self.feedback.update("emotion_detection")
        emotion_result = self.emotion.detect(text, context=context)
        context["last_emotion"] = emotion_result.emotion
        output.emotion = emotion_result.emotion
        output.emotion_confidence = emotion_result.confidence
        output.emotion_valence = emotion_result.valence
        output.emotion_arousal = emotion_result.arousal

        # ── Phase 8: Conversation Analysis ──
        self.feedback.update("conversation_analysis")
        conv_analysis = self.conversation.analyze(text, context=context)
        output.conversation_type = conv_analysis.conversation_type
        output.conversation_behavior = conv_analysis.suggested_behavior
        output.conversation_confidence = conv_analysis.confidence

        # ── Phase 9: Implicit Intent (if explicit is weak) ──
        if output.intent_confidence < 0.5:
            implicit_result = self.implicit_intent.detect(
                normalized, output.intent, context=context,
            )
            if implicit_result.detected and self.implicit_intent.should_override_explicit(
                implicit_result, output.intent_confidence,
            ):
                output.intent = implicit_result.intent
                output.intent_confidence = implicit_result.confidence
                output.goal = implicit_result.goal
                output.match_method = "implicit"
                output.implicit_intent = implicit_result.intent
                output.implicit_confidence = implicit_result.confidence
                output.implicit_goal = str(implicit_result.goal.value) if hasattr(implicit_result.goal, 'value') else str(implicit_result.goal)

        # ── Phase 10: Goal Detection ──
        if output.goal == GoalCategory.UNKNOWN:
            entity_values = {k: v["value"] for k, v in output.entities.items()}
            goal, goal_conf = self.goals.detect(normalized, output.intent, entity_values)
            output.goal = goal

        # ── Phase 11: Capability Detection ──
        self.feedback.update("capability_detection")
        entity_values = {k: v["value"] for k, v in output.entities.items()}
        capabilities = self.capabilities.detect(output.intent, entity_values, output.goal)

        # ── Phase 12: Knowledge Routing ──
        routing = self.knowledge.route(output.intent, entity_values, output.goal)
        output.knowledge_sources = [s.to_dict() if hasattr(s, 'to_dict') else s for s in routing.sources] if hasattr(routing, 'sources') else []
        output.knowledge_domain = routing.domain if hasattr(routing, 'domain') else ""
        output.knowledge_platform = routing.platform if hasattr(routing, 'platform') else ""

        # ── Phase 12b: Knowledge Retrieval (RAG) ──
        try:
            from jarvis.knowledge import knowledge_engine
            rag_result = knowledge_engine.retrieve(text, max_tokens=1000)
            if rag_result.get("confidence", 0) > 0.2:
                output.knowledge_context = rag_result.get("context", "")
                output.knowledge_sources_found = rag_result.get("sources", [])
        except Exception:
            pass

        # ── Phase 13: Tool Resolution (with reliability check) ──
        self.feedback.update("tool_resolution")
        adaptive_plan = self.adaptive.get_adaptive_plan(output.intent, entity_values)
        output.adaptive_plan = adaptive_plan.to_dict() if hasattr(adaptive_plan, 'to_dict') else adaptive_plan
        entity_values = {k: v["value"] for k, v in output.entities.items()}
        tool_name, handler, tool_params = self.tools.select(
            output.intent, entity_values, context, capabilities,
        )

        # V3 Part 3: Check tool reliability and suggest alternatives
        if tool_name and self.failure_memory.should_avoid(tool_name):
            alternative = self.failure_memory.suggest_alternative(tool_name, capabilities[0] if capabilities else "")
            if alternative:
                tool_name = alternative
                handler = f"jarvis.tools.{alternative}"

        output.tool = tool_name
        output.handler = handler

        # ── Phase 14: Parameter Building ──
        param_entities = {}
        for name, e in entity_dict.items():
            if hasattr(e, 'value'):
                param_entities[name] = e
            else:
                param_entities[name] = Entity(name=name, value=str(e), raw_value=str(e))
        param_dict = self.params.build(output.intent, param_entities, context, normalized)
        merged_params = {**tool_params, **param_dict}
        output.parameters = merged_params

        # ── Phase 15: Personal Language Resolution ──
        vocab_match = self.personal_language.resolve(normalized)
        if vocab_match:
            output.parameters["resolved_target"] = vocab_match.resolved
            output.vocab_match = vocab_match.to_dict() if hasattr(vocab_match, 'to_dict') else {"original": vocab_match.original, "resolved": vocab_match.resolved}

        # ── Phase 16: Planning (multi-step) ──
        if output.is_multi_intent and sentence.actions:
            self.feedback.update("planning")
            steps = self.planner.plan(
                output.intent, output.entities, context, output.goal,
            )
            output.planner = [
                {
                    "step_id": s.step_id, "intent": s.intent,
                    "tool": s.tool, "handler": s.handler,
                    "parameters": s.parameters, "description": s.description,
                }
                for s in steps
            ]

        # ── Phase 17: Safety Validation ──
        self.feedback.update("safety_check")
        is_destructive = self.safety.is_destructive(output.tool, output.parameters)
        safety_check = self.safety.validate(
            output.intent, entity_values, output.parameters, context,
        )
        output.safety_level = safety_check.level
        output.safety_message = safety_check.message
        output.safety_risks = safety_check.risks if hasattr(safety_check, 'risks') else []
        if not safety_check.is_safe:
            output.execution_mode = ExecutionMode.CONFIRM
            output.requires_clarification = True
            output.clarification_message = safety_check.message

        # ── Phase 18: Confidence Scoring (Multi-signal) ──
        self.feedback.update("confidence_scoring")
        signals = ConfidenceSignals(
            intent_score=output.intent_confidence,
            entity_score=self.confidence_engine.calculate_entity_score(
                output.entities,
            ),
            goal_score=0.7 if output.goal != GoalCategory.UNKNOWN else 0.3,
            context_score=self.confidence_engine.calculate_context_score(
                bool(context), is_followup=bool(context.get("is_followup")),
            ),
            tool_score=self.confidence_engine.calculate_tool_score(
                bool(output.tool), tool_params.get("confidence", 0.0) if tool_params else 0.0,
            ),
            language_score=lang_conf,
            safety_score=1.0 if safety_check.is_safe else 0.5,
        )
        conf_result = self.confidence_engine.calculate(
            signals, is_destructive=is_destructive, has_tool=bool(output.tool),
        )
        output.confidence_score = conf_result.score
        output.confidence_level = conf_result.tier
        output.execution_mode = conf_result.execution_mode
        output.requires_clarification = conf_result.requires_confirmation
        output.clarification_message = conf_result.reasoning if conf_result.requires_confirmation else output.clarification_message
        output.confidence_signals = conf_result.signal_breakdown if hasattr(conf_result, 'signal_breakdown') else {}

        # ── Phase 19: Response Generation ──
        response = self.response_gen.generate(
            output.intent, entity_values, emotion=emotion_result.emotion,
            execution_mode=output.execution_mode, context=context,
        )
        output.response_text = response.text if hasattr(response, 'text') else str(response)
        output.response_style = response.style if hasattr(response, 'style') else ""
        output.match_method = output.match_method or "semantic"

        # ── Phase 20: Validation ──
        is_valid, missing = self.params.validate_params(output.intent, output.parameters)
        if not is_valid and not output.requires_clarification:
            output.requires_clarification = True
            output.clarification_message = f"I need more information: {', '.join(missing)}"

        # ── Phase 21: Memory Update ──
        output.memory_update = self.memory.prepare_memory_entry(
            output.intent, {k: v["value"] for k, v in output.entities.items()},
            context, output.goal.value if hasattr(output.goal, 'value') else str(output.goal),
        )

        # ── Phase 22: User Profiling ──
        self.user_profiler.update_from_interaction(
            output.intent, {k: v["value"] for k, v in output.entities.items()},
            tool_name, True,
        )
        output.user_profile_summary = str(self.user_profiler.get_profile_summary())

        # ── Phase 23: Learning ──
        self.feedback.update("learning")
        self.learning.record_interaction(
            output.intent, {k: v["value"] for k, v in output.entities.items()},
            tool_name, True,
        )

        # ── Phase 24: Context Update ──
        self.context.update(
            intent=output.intent,
            entities={k: v["value"] for k, v in output.entities.items()},
            tool_result="", success=True,
        )
        output.context_snapshot = self.context.snapshot()

        # Track adaptive resources
        self.adaptive.update_after_execution(
            output.intent,
            {k: v["value"] for k, v in output.entities.items()},
            True,
        )

        # ── Phase 25: Record for Habit Detection (V3 Part 3) ──
        self.habit_detector.record_action(
            output.intent,
            {k: v["value"] for k, v in output.entities.items()},
            tool_name, True,
        )
        # Check for suggested next action from habits
        habit_suggestion = self.habit_detector.suggest_next_action()
        if habit_suggestion:
            output.parameters["habit_suggestion"] = habit_suggestion

        # ── Phase 26: Memory Manager (V3 Part 3) ──
        if output.parameters.get("should_remember") or output.intent in ("SAVE_MEMORY", "ADD_NOTE"):
            self.memory_manager.store(
                content=output.raw_text,
                memory_type="episodic",
                importance=0.6,
                tags=[output.intent.lower()],
                entities={k: v["value"] for k, v in output.entities.items()},
                intent=output.intent,
                tool_used=tool_name,
            )

        # ── Phase 27: Response Quality Check (V3 Part 3) ──
        quality = self.quality_checker.check(
            output.response_text, output.intent, context=context,
        )
        if not quality["is_acceptable"]:
            # Try to improve response internally
            logger.debug("Response quality issues: %s", quality["issues"])

        # ── Phase 28: Self-Improvement Analysis (V3 Part 3) ──
        analysis = self.self_improvement.analyze_task(
            intent=output.intent,
            tool=tool_name,
            success=bool(output.tool),
            latency_ms=output.processing_time_ms,
            confidence=output.confidence_score,
        )

        # ── Phase 29: Tool Health Tracking (V3 Part 4) ──
        if tool_name:
            self.tool_health.record_execution(
                tool_name, bool(output.tool), output.processing_time_ms,
            )

        # ── Phase 30: Digital Twin Update (V3 Part 4) ──
        self.digital_twin.update_from_interaction(
            output.intent,
            {k: v["value"] for k, v in output.entities.items()},
            tool_name, context,
        )

        # ── Phase 31: Knowledge Graph (V3 Part 4) ──
        if output.intent and output.entities:
            entity_values = {k: v["value"] for k, v in output.entities.items()}
            for key, val in entity_values.items():
                if val and isinstance(val, str) and len(val) < 100:
                    self.knowledge_graph.add_node(val, node_type=key)
                    if output.intent:
                        self.knowledge_graph.add_edge(
                            output.intent, val, "has_entity",
                        )

        # ── Phase 32: Semantic Memory (V3 Part 4) ──
        if output.raw_text and output.intent:
            mem_node = self.semantic_memory.add_memory(
                content=output.raw_text,
                memory_type="episodic",
                importance=output.confidence_score,
                metadata={"intent": output.intent, "tool": tool_name},
            )
            # Connect to previous memory if exists
            if len(self.semantic_memory._nodes) > 1:
                prev_ids = list(self.semantic_memory._nodes.keys())
                if len(prev_ids) > 1:
                    prev_id = prev_ids[-2]
                    self.semantic_memory.connect(
                        prev_id, mem_node.id, "follows",
                    )

        # ── Phase 33: Cognitive Architecture (Executive Brain) ──
        self.feedback.update("cognitive_processing")
        cognitive_state = self.cognitive.process(
            text=text,
            intent=output.intent,
            entities=output.entities,
            context=context,
        )
        # Enrich output with cognitive insights
        if cognitive_state.thinking_ctx:
            output.parameters["thinking_mode"] = cognitive_state.thinking_ctx.mode
            output.parameters["thinking_reasoning"] = cognitive_state.thinking_ctx.reasoning
            output.parameters["estimated_steps"] = cognitive_state.thinking_ctx.estimated_steps
        if cognitive_state.focus:
            output.parameters["attention_confidence"] = cognitive_state.focus.attention_confidence
        if cognitive_state.reflection:
            output.parameters["reflection_improvements"] = [
                s for s in (cognitive_state.reflection.improvements or [])
            ]

        # ── Phase 34: Planning Engine (Autonomous Task Management) ──
        self.feedback.update("planning")
        plan = self.planning_engine.create_plan(
            text=text,
            intent=output.intent,
            entities=output.entities,
            context=context,
        )
        output.planner = [
            {
                "task_id": t.task_id,
                "name": t.name,
                "intent": t.intent,
                "handler": t.handler,
                "priority": t.priority.name,
                "estimated_ms": t.estimated_duration_ms,
                "risk": t.estimated_risk,
                "fallback": t.fallback_handler,
            }
            for t in plan.tasks
        ]
        output.parameters["plan_id"] = plan.plan_id
        output.parameters["plan_tasks"] = plan.total_tasks
        output.parameters["plan_phases"] = len(plan.phases)
        output.parameters["plan_estimated_ms"] = plan.total_estimated_ms
        output.parameters["plan_parallel_groups"] = plan.parallel_groups

        # ── Phase 35: Computer Vision & Environment Understanding ──
        self.feedback.update("vision")
        try:
            # Use pre-captured state from Phase 4b if available
            if _pre_vision_state is not None:
                desktop_state = _pre_vision_state
                output.parameters["vision_desktop"] = output.parameters.get("_pre_vision_state", {})
            else:
                # Re-run capability detection with full intent context
                _vision_caps_final = self.vision.capability_detector.detect(
                    text, intent=output.intent, context=context,
                )
                if _vision_caps_final.any_required():
                    desktop_state = self.vision.see()
                    output.parameters["vision_desktop"] = {
                        "windows": desktop_state.window_count,
                        "focused": desktop_state.focused_app,
                        "elements": desktop_state.element_count,
                        "has_errors": desktop_state.has_errors,
                        "error_messages": desktop_state.error_messages[:3] if desktop_state.error_messages else [],
                    }
                    output.parameters["_vision_capabilities"] = _vision_caps_final.to_dict()
                else:
                    desktop_state = None
                    output.parameters["vision_active"] = False

            # Process vision results if we have a desktop state
            if desktop_state is not None:
                # Run vision NLP fusion for visual questions
                fusion_result = self.vision.fusion.fuse(
                    text,
                    desktop_state=desktop_state,
                    ocr_result=None,
                    elements=None,
                    nlp_output=output,
                )
                if fusion_result.get("confidence", 0) > 0.3:
                    output.parameters["vision_answer"] = fusion_result.get("answer", "")
                    output.parameters["vision_source"] = fusion_result.get("source", "")

                # Store vision context in memory for next query
                output.parameters["vision_context"] = {
                    "app": desktop_state.focused_app,
                    "window_count": desktop_state.window_count,
                    "has_errors": desktop_state.has_errors,
                    "elements": desktop_state.element_count,
                    "timestamp": desktop_state.timestamp if hasattr(desktop_state, 'timestamp') else 0,
                }

                # Vision + Reasoning: understand the screen, not just OCR
                if output.intent == "VISUAL_ANALYSIS" or output.parameters.get("_vision_capabilities", {}).get("reasoning"):
                    # Deep analysis: combine vision with reasoning
                    output.parameters["vision_deep_analysis"] = True
                    # The reasoning engine will use vision context
                    if hasattr(output, 'parameters'):
                        output.parameters["_visual_context_for_reasoning"] = {
                            "focused_app": desktop_state.focused_app,
                            "has_errors": desktop_state.has_errors,
                            "error_messages": desktop_state.error_messages[:5] if desktop_state.error_messages else [],
                            "window_count": desktop_state.window_count,
                            "element_count": desktop_state.element_count,
                        }

                output.parameters["vision_active"] = True
        except Exception as e:
            output.parameters["vision_active"] = False
            output.parameters["vision_error"] = str(e)
            logger.debug("Vision phase failed: %s", e)

        # Finish feedback
        self.feedback.finish(True)
        output.execution_phases = self.feedback.get_all_phases()

        # Timing
        output.processing_time_ms = (time.time() - t0) * 1000

        # Fallback: ensure conversation_type is always set
        if not output.conversation_type:
            conv_result = self.conversation.analyze(
                output.raw_text, context=context,
            )
            output.conversation_type = conv_result.conversation_type
            output.conversation_behavior = conv_result.suggested_behavior

        # Fallback: generate response if still empty
        if not output.response_text and output.conversation_type:
            resp = self.response_gen.generate(
                intent=output.intent,
                entities=output.parameters,
                execution_mode=output.execution_mode,
                emotion=output.emotion,
                context=context,
            )
            output.response_text = resp.text if hasattr(resp, "text") else str(resp)

        logger.info(
            "NLP v3: intent=%s conf=%.2f tool=%s emotion=%s latency=%.1fms",
            output.intent, output.confidence_score,
            output.tool, emotion_result.emotion, output.processing_time_ms,
        )

        return output

    def execute(self, text: str, llm_callable: Callable[..., Any] | None = None) -> tuple[str, bool]:
        """Process and execute a user query.

        Uses ToolIntelligenceEngine for smart execution with:
        - Platform-aware routing
        - Health-aware tool selection
        - Autonomous recovery
        - Result validation
        - Continuous learning

        Returns (response_text, was_handled_by_tool).
        """
        output = self.process(text)

        if output.should_execute:
            # Use ToolIntelligenceEngine for intelligent execution
            response, handled = self.tool_intelligence.execute(
                output, self.executor.execute,
            )
            if handled:
                self.context.update(
                    intent=output.intent,
                    entities={k: v["value"] for k, v in output.entities.items()},
                    tool_result=response[:200] if response else "",
                    success=True,
                )
                if self.memory.should_remember(
                    output.intent,
                    {k: v["value"] for k, v in output.entities.items()},
                    output.goal.value if hasattr(output.goal, 'value') else str(output.goal),
                ):
                    self.memory.store(output.memory_update)
                return (response, True)

        if output.requires_clarification:
            return (output.clarification_message, True)

        if llm_callable:
            try:
                response = llm_callable(text)
                if isinstance(response, dict):
                    response = response.get("text", str(response))
                return (str(response) if response else "", True)
            except Exception as e:
                logger.exception("LLM fallback failed")
                return (f"Error: {e}", True)

        return ("", False)


# ════════════════════════════════════════════════════════════════════
# GLOBAL ENGINE INSTANCE
# ════════════════════════════════════════════════════════════════════

nlp_engine = SemanticNLPEngine()


# ════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ════════════════════════════════════════════════════════════════════

def process(text: str) -> NLPOutput:
    """Process user input through the NLP pipeline."""
    return nlp_engine.process(text)


def execute(text: str, llm: Callable[..., Any] | None = None) -> tuple[str, bool]:
    """Process and execute a user query."""
    return nlp_engine.execute(text, llm)


# ════════════════════════════════════════════════════════════════════
# BACKWARD COMPATIBILITY
# ════════════════════════════════════════════════════════════════════

from .normalizer import normalize, normalize_keep_case, normalize_for_matching
from .synonyms import expand_synonyms, resolve_platform, resolve_app
from .patterns import PatternBank
from .intent_classifier import IntentClassifier, IntentResult
from .command_parser import CommandParser, command_parser
from .context_memory import ContextMemory, context_memory
from .self_learning import SelfLearningEngine, self_learning
from .confidence import ConfidenceScorer as LegacyConfidenceScorer
from .entity_extractor import EntityExtractor as LegacyEntityExtractor
from .parameter_parser import ParameterParser, parameter_parser
from .tool_router import NLPToolRouter, nlp_tool_router

__all__ = [
    "SemanticNLPEngine", "nlp_engine", "process", "execute",
    "NLPOutput", "NLPInput", "Entity", "GoalCategory", "ExecutionMode", "Language",
    "detect_language", "normalize",
    # V3 modules
    "emotion_detector", "conversation_analyzer", "implicit_intent_detector",
    "user_profiler", "personal_language", "self_correction",
    "adaptive_executor", "safety_validator", "confidence_engine",
    "response_generator", "execution_feedback", "knowledge_router",
    # Core modules
    "semantic_parser", "intent_engine", "entity_extractor",
    "context_engine", "goal_detector", "planner",
    "capability_detector", "tool_selector", "parameter_builder",
    "confidence_scorer", "learning_engine", "memory_bridge", "execution_bridge",
    # Backward compatibility
    "normalize_keep_case", "normalize_for_matching",
    "expand_synonyms", "resolve_platform", "resolve_app",
    "PatternBank", "IntentClassifier", "IntentResult",
    "CommandParser", "command_parser",
    "ContextMemory", "context_memory",
    "SelfLearningEngine", "self_learning",
    "ParameterParser", "parameter_parser",
    "NLPToolRouter", "nlp_tool_router",
]


# ════════════════════════════════════════════════════════════════════
# SPEECH INTEGRATION
# ════════════════════════════════════════════════════════════════════

def create_speech_nlp():
    """Create a SpeechEngine wired to the NLP pipeline.

    Returns a configured SpeechEngine ready for voice conversation.
    """
    from jarvis.speech import SpeechEngine

    engine = SpeechEngine()
    engine.configure_nlp(nlp_engine.process)
    return engine
