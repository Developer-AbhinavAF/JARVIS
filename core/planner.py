"""core/planner.py — Deterministic Planner & Confidence Engine for JARVIS vNext++.

Resides between Brain and Candidate Tool Search.
Responsibilities:
- Determine if memory, RAG, tools, or multi-step execution are required.
- Estimate decision confidence percentage.
- Select appropriate BrainProfile.
- Build structured ExecutionPlan.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from core.world_state import world_state_engine

logger = logging.getLogger(__name__)


@dataclass
class ExecutionStep:
    step_id: int
    action_type: str  # memory, rag, tool, skill, response
    target: str
    args: Dict[str, Any] = field(default_factory=dict)
    confirmed: bool = True


@dataclass
class ExecutionPlan:
    goal: str
    profile: str = "NORMAL"
    requires_memory: bool = False
    requires_rag: bool = False
    requires_tools: bool = False
    top_k_rag: int = 2
    confidence: float = 0.95
    steps: List[ExecutionStep] = field(default_factory=list)


# ── Patterns that are ALWAYS conversation / content generation ──────
# These must NEVER trigger tool execution.
_CONVERSATION_PATTERNS = re.compile(
    r"^(hello|hi|hey|hii|good morning|good evening|good night|how are you|"
    r"what'?s up|sup|namaste|kaise ho|kya hal|kya kar rahe|"
    r"who are you|what are you|who created you|who made you|"
    r"tell me something|talk to me|say something|chat with me|"
    r"what do you think|what is your opinion|do you think|"
    r"can you speak|are you able|"
    r"don'?t use|just talk|don'?t use tool|don'?t use your tool|"
    r"without tool|no tool|skip tool)$",
    re.IGNORECASE,
)

_WRITING_PATTERNS = re.compile(
    r"(write|generate|create|compose|draft|make|prepare|"
    r"translate|convert|translate this|translate it|"
    r"essay|story|poem|paragraph|note|email|code|script|"
    r"python code|java code|html|css|javascript|"
    r"in hindi|in bengali|in korean|in japanese|in spanish|in french|"
    r"in chinese|in arabic|in tamil|in telugu|in marathi|"
    r"20 languages|different languages|multiple languages|"
    r"100 words|200 words|500 words|word essay)",
    re.IGNORECASE,
)

_KNOWLEDGE_PATTERNS = re.compile(
    r"(what is|what are|who is|who was|who invented|who created|"
    r"explain|describe|tell me about|define|meaning of|"
    r"how does|how do|how to|how can|"
    r"why do|why does|why is|why are|"
    r"is it true|is there|can you explain|"
    r"what happens|what caused|what makes|"
    r"do you know|have you heard|"
    r"capital of|president of|population of|"
    r"tell me about|information about|facts about)",
    re.IGNORECASE,
)

_MEMORY_PATTERNS = re.compile(
    r"(remember|save|store|recall|what is my|what was my|"
    r"my name|my age|my preference|my sister|my brother|"
    r"my mother|my father|my friend|my project|"
    r"don'?t forget|keep in mind)",
    re.IGNORECASE,
)

# ── Patterns that ARE external actions ──────────────────────────────
# Only these trigger tool execution.
_EXTERNAL_ACTION_PATTERNS = re.compile(
    r"(open |launch |start |close |kill |stop |"
    r"search google|google search|search web|google for|"
    r"search youtube|youtube search|find youtube|youtube for|"
    r"search .+ on (google|youtube|bing|duckduckgo|web)|"
    r"download youtube|youtube download|save youtube|download video|"
    r"youtube info|youtube video info|get youtube info|"
    r"instagram info|instagram user|get instagram|insta info|"
    r"instagram posts|insta posts|get instagram posts|"
    r"open url|open website|open link|open page|open site|"
    r"visit [a-z0-9]|browse [a-z0-9]|navigate to|take me to|"
    r"go to (?:https?://|localhost|\S+\.(?:com|org|net|io|dev|ai|"
    r"me|co|app|tv|edu|gov|info|xyz|tech|site|online|store|blog|"
    r"cloud|page|pro|live|news|today|space|us|uk|de|fr|es|it|ca|"
    r"au|in|jp|cn|br|nl|se|ch|at|be|dk|fi|no|pl|pt|ru|za|kr|hk|"
    r"sg|nz|ie|cl|id|my|ph|vn|ar|cz|hu|ro|sk|ua|gr|il|th|tr))|"
    r"type this|type it|click the|press enter|paste this|copy to clipboard|"
    r"say aloud|speak this|play music|pause music|mute|"
    r"take screenshot|screenshot|"
    r"^run |^execute )",
    re.IGNORECASE,
)

# ── Patterns for NASA / visual / image requests ────────────────────────
# These are visual intent — the user wants to SEE images/videos.
# "explain NASA" or "what is NASA" should NOT match (those are knowledge).
_NASA_PATTERNS = re.compile(
    r"(nasa\s+(apod|picture|image|photo|video|search)|"
    r"apod|astronomy picture|picture of the day|space picture|"
    r"show.*(picture|image|photo|video).*of|"
    r"find.*(image|picture|photo).*of|"
    r"(black hole|mars|moon|earth|jupiter|saturn|sun|galaxy|nebula).*(image|picture|photo)|"
    r"james webb|apollo \d|artemis|hubble.*(image|picture|photo)|"
    r"nasa image|nasa photo|nasa video|nasa picture|"
    r"today.*(astronomy|space picture)|"
    r"space image|space photo|galaxy image|nebula image|"
    r"sun image|solar system image|planet image)",
    re.IGNORECASE,
)

_CODE_EXECUTION_PATTERNS = re.compile(
    r"(write.*code|generate.*code|create.*script|write.*script|"
    r"python.*script|javascript.*script|make.*program|"
    r"write.*program|create.*program|build.*script|"
    r"code.*calculator|code.*game|code.*tool|code.*utility|"
    r"write.*python|write.*javascript|write.*java|write.*cpp|"
    r"generate.*python|generate.*javascript)",
    re.IGNORECASE,
)

# ── Explicit system-status requests ONLY ────────────────────────────────
# The LLM must never see resource values otherwise. This routes only
# explicit queries ("what is my CPU usage") to the get_system_status tool.
_SYSTEM_STATUS_PATTERNS = re.compile(
    r"(system\s+(status|stats|health)|"
    r"cpu\s+usage|ram\s+usage|memory\s+usage|gpu\s+usage|disk\s+usage|"
    r"how\s+much\s+(ram|memory|cpu)\s+(am|is)\s+i\s+using|"
    r"what(?:'?s| is)\s+my\s+(cpu|ram|memory|gpu)\s+usage|"
    r"check\s+(cpu|ram|memory|gpu|system))",
    re.IGNORECASE,
)


class PlannerEngine:
    """Planner and confidence calculation engine."""

    def __init__(self):
        pass

    def build_plan(self, query: str, context: Dict[str, Any] = None) -> ExecutionPlan:
        """Analyze query and build deterministic execution plan.

        Priority:
        1. Safety / system constraints
        2. Explicit user intent
        3. Conversation (ALWAYS first for normal chat)
        4. Writing / generation
        5. Memory
        6. Knowledge / RAG
        7. External search (only explicit)
        8. Computer tools (only explicit)
        9. Speech output
        """
        query_lower = query.lower().strip()
        plan = ExecutionPlan(goal=query)

        # ── ALWAYS conversation first — never tools ────────────────
        if _CONVERSATION_PATTERNS.search(query_lower):
            plan.profile = "FAST"
            plan.confidence = 0.99
            plan.top_k_rag = 0
            plan.steps.append(ExecutionStep(step_id=1, action_type="response", target="conversation"))
            return plan

        # ── "don't use tools" — force conversation ────────────────
        if re.search(r"(don'?t use|without|no|skip|stop).{0,20}(tool|function|command)", query_lower):
            plan.profile = "FAST"
            plan.confidence = 0.99
            plan.top_k_rag = 0
            plan.steps.append(ExecutionStep(step_id=1, action_type="response", target="conversation"))
            return plan

        # ── System status — explicit resource queries only ──────────
        if _SYSTEM_STATUS_PATTERNS.search(query_lower):
            plan.profile = "FAST"
            plan.requires_tools = True
            plan.confidence = 0.97
            plan.top_k_rag = 0
            plan.steps.append(ExecutionStep(step_id=1, action_type="tool", target="system_status"))
            return plan

        # ── Memory operations — explicit only ──────────────────────
        if _MEMORY_PATTERNS.search(query_lower):
            plan.profile = "MEMORY"
            plan.requires_memory = True
            plan.confidence = 0.98
            plan.top_k_rag = 0
            plan.steps.append(ExecutionStep(step_id=1, action_type="memory", target="facts"))
            return plan

        # ── EXTERNAL ACTIONS — only explicit tool phrases ──────────
        if _EXTERNAL_ACTION_PATTERNS.search(query_lower):
            plan.profile = "FAST"
            plan.requires_tools = True
            plan.confidence = 0.95
            plan.top_k_rag = 0
            plan.steps.append(ExecutionStep(step_id=1, action_type="tool", target="tool_execution"))
            return plan

        # ── NASA / Visual intent — images, space, APOD ──────────
        if _NASA_PATTERNS.search(query_lower):
            plan.profile = "NORMAL"
            plan.requires_tools = True
            plan.confidence = 0.92
            plan.top_k_rag = 0
            plan.steps.append(ExecutionStep(step_id=1, action_type="tool", target="nasa_visual"))
            return plan

        # ── Code generation request → coding profile ────────────
        if _CODE_EXECUTION_PATTERNS.search(query_lower):
            plan.profile = "CODING"
            plan.confidence = 0.90
            plan.requires_rag = True
            plan.top_k_rag = 4
            plan.steps.append(ExecutionStep(step_id=1, action_type="rag", target="coding_docs"))
            plan.steps.append(ExecutionStep(step_id=2, action_type="response", target="coding"))
            return plan

        # ── Writing / content generation — LLM handles directly ───
        if _WRITING_PATTERNS.search(query_lower):
            plan.profile = "NORMAL"
            plan.confidence = 0.95
            plan.top_k_rag = 0
            plan.steps.append(ExecutionStep(step_id=1, action_type="response", target="writing"))
            return plan

        # ── Knowledge / explanation — LLM handles directly ────────
        if _KNOWLEDGE_PATTERNS.search(query_lower):
            plan.profile = "NORMAL"
            plan.requires_rag = True
            plan.top_k_rag = 2
            plan.confidence = 0.90
            plan.steps.append(ExecutionStep(step_id=1, action_type="response", target="knowledge"))
            return plan

        # ── Coding — LLM handles directly (no tool needed) ────────
        if any(w in query_lower for w in ["code", "python", "script", "function", "debug", "refactor", "bug", "error", "traceback"]):
            plan.profile = "CODING"
            plan.confidence = 0.90
            plan.requires_rag = True
            plan.top_k_rag = 4
            plan.steps.append(ExecutionStep(step_id=1, action_type="rag", target="coding_docs"))
            plan.steps.append(ExecutionStep(step_id=2, action_type="response", target="coding"))
            return plan

        # ── Default: general conversation / knowledge ──────────────
        plan.profile = "NORMAL"
        plan.requires_rag = True
        plan.top_k_rag = 2
        plan.confidence = 0.85
        plan.steps.append(ExecutionStep(step_id=1, action_type="response", target="general_answer"))
        return plan


planner_engine = PlannerEngine()
