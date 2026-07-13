from __future__ import annotations

from typing import Any

from .models import Capability, ChatRequest


class CapabilityDetector:
    """Detects the required capability from a chat request."""

    CAPABILITY_KEYWORDS: dict[Capability, list[str]] = {
        Capability.REASONING: ["reason", "think", "logic", "explain", "why", "how", "analyze", "solve", "math", "calculate"],
        Capability.VISION: ["image", "picture", "photo", "see", "look", "visual", "screenshot", "diagram", "chart", "graph"],
        Capability.OCR: ["read text", "extract text", "ocr", "recognize text"],
        Capability.CODE_GENERATION: ["code", "program", "function", "script", "implementation", "write a", "develop", "debug", "refactor"],
        Capability.SUMMARIZATION: ["summarize", "summary", "tl;dr", "brief", "condense"],
        Capability.TRANSLATION: ["translate", "translation", "in french", "in spanish", "in german"],
        Capability.SEARCH: ["search", "find", "look up", "google", "web search", "internet"],
        Capability.EMBEDDING: ["embed", "vector", "semantic search", "similarity"],
        Capability.TOOL_CALLING: ["tool", "function", "action", "execute", "run"],
    }

    @staticmethod
    def detect(request: ChatRequest) -> set[Capability]:
        capabilities: set[Capability] = {Capability.CHAT}

        if request.stream:
            capabilities.add(Capability.STREAMING)

        if request.tools:
            capabilities.add(Capability.TOOL_CALLING)
            capabilities.add(Capability.FUNCTION_CALLING)

        if request.response_format:
            capabilities.add(Capability.JSON_OUTPUT)

        last_msg = request.messages[-1]["content"] if request.messages else ""
        text = str(last_msg).lower()

        for cap, keywords in CapabilityDetector.CAPABILITY_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    capabilities.add(cap)
                    break

        return capabilities

    @staticmethod
    def detect_intent(request: ChatRequest) -> str:
        text = request.messages[-1]["content"] if request.messages else ""
        text = str(text).lower()

        if any(w in text for w in ["code", "program", "function", "script", "debug"]):
            if any(w in text for w in ["write", "create", "implement", "generate", "develop"]):
                return "code_generation"
            elif any(w in text for w in ["debug", "fix", "error", "bug", "issue"]):
                return "code_debugging"
            return "code_help"

        if any(w in text for w in ["translate", "translation"]):
            return "translation"

        if any(w in text for w in ["summarize", "summary", "tl;dr", "brief"]):
            return "summarization"

        if any(w in text for w in ["search", "find", "look up", "google"]):
            return "search"

        if any(w in text for w in ["explain", "why", "how", "what is", "meaning", "define"]):
            return "explanation"

        if any(w in text for w in ["image", "picture", "photo", "screenshot", "vision"]):
            return "vision"

        return "general_chat"
