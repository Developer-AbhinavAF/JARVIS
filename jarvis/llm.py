"""jarvis.llm

LLM integration and tool-dispatch layer for JARVIS.

This module wraps the Groq chat completion API, maintains short-term history,
extracts tool calls (as JSON), executes tools, and performs a second pass to
synthesize a final spoken response.
"""

from __future__ import annotations

import json
import logging

from groq import Groq

from jarvis import config
from jarvis.memory import memory
from jarvis.tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)


class JarvisLLM:
    """Groq-backed chat engine with short-term memory and tool calling."""

    MAX_HISTORY_TURNS: int = 6

    def __init__(self) -> None:
        """Initialize Groq client and conversation history."""

        self.client = Groq(api_key=config.GROQ_API_KEY)
        self.history: list[dict[str, str]] = []

    def _trim_history(self) -> None:
        """Trim history to the last MAX_HISTORY_TURNS turns."""

        max_messages = self.MAX_HISTORY_TURNS * 2
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]

    def _call_groq(self, extra_messages: list[dict[str, str]] | None = None) -> str:
        """Call Groq chat completions and return assistant content.

        Returns:
            Assistant message content string. Never raises.
        """

        try:
            messages: list[dict[str, str]] = [{"role": "system", "content": config.SYSTEM_PROMPT}]
            messages.extend(self.history)
            if extra_messages:
                messages.extend(extra_messages)

            completion = self.client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=messages,
                temperature=config.GROQ_TEMPERATURE,
                max_tokens=config.GROQ_MAX_TOKENS,
            )

            content = (completion.choices[0].message.content or "").strip()
            return content
        except Exception as exc:
            logger.exception("Groq call failed")

            # Return a short error string so you can immediately see if this is a
            # model name problem, auth issue, rate limit, network error, etc.
            msg = str(exc).strip() or "Unknown Groq error"
            if len(msg) > 300:
                msg = msg[:300] + "..."
            return f"LLM backend error: {msg}"

    def _extract_tool_call(self, text: str) -> dict | None:
        """Extract and validate a tool call JSON object from model output."""

        raw = (text or "").strip()
        if not raw:
            return None

        # Models sometimes wrap JSON in fenced blocks; strip them defensively.
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw.replace("json\n", "", 1).strip()

        # Try to find JSON object in the text if it's not pure JSON
        # Pattern: look for {"tool":...} even if surrounded by text
        import re
        json_pattern = r'\{\s*"tool"[^}]+\}'
        match = re.search(json_pattern, raw)
        if match:
            raw = match.group(0)
            logger.debug("Extracted JSON from text: %s", raw)

        try:
            obj = json.loads(raw)
        except Exception as e:
            logger.debug("JSON parse failed: %s", str(e))
            return None

        if not isinstance(obj, dict):
            return None
        if "tool" not in obj:
            return None
        
        logger.info("Tool call extracted: %s", obj.get("tool"))
        return obj

    def _dispatch_tool(self, tool_call: dict) -> str:
        """Dispatch a tool call into the TOOL_REGISTRY."""

        try:
            tool_name = str(tool_call.get("tool", "")).strip()
            if not tool_name:
                return "Tool call missing tool name."

            fn = TOOL_REGISTRY.get(tool_name)
            if fn is None:
                return f"Unknown tool: {tool_name}"

            kwargs = dict(tool_call)
            kwargs.pop("tool", None)

            try:
                return str(fn(**kwargs))
            except TypeError:
                logger.exception("Tool argument mismatch for %s", tool_name)
                return "Tool call had invalid arguments."
            except Exception:
                logger.exception("Tool execution failed for %s", tool_name)
                return "Tool execution failed."
        except Exception:
            logger.exception("Unexpected tool dispatch error")
            return "Tool dispatch failed."

    def chat(self, user_input: str) -> str:
        """Process a user turn, optionally run a tool, and return final response."""

        user_input = (user_input or "").strip()
        if not user_input:
            return "Say that again."

        logger.info("Processing user input: %s", user_input[:50])
        
        self.history.append({"role": "user", "content": user_input})
        self._trim_history()

        first_pass = self._call_groq()
        logger.debug("First pass LLM response: %s", first_pass[:100] if first_pass else "EMPTY")
        
        # Handle empty response from LLM
        if not first_pass or first_pass.strip() == "":
            logger.warning("LLM returned empty response")
            return "I didn't get a response. Let me try again."
        
        tool_call = self._extract_tool_call(first_pass)

        if tool_call:
            logger.info("Tool call detected: %s", tool_call)
            # Two-pass LLM: first to detect tool, second to synthesise result.
            tool_result = self._dispatch_tool(tool_call)
            logger.debug("Tool result: %s", tool_result[:100] if tool_result else "EMPTY")

            extra = [
                {
                    "role": "system",
                    "content": (
                        "You just called a tool. Use the tool result below to answer the user. "
                        "Reply in plain conversational English (no JSON).\n\n"
                        f"TOOL_RESULT:\n{tool_result}"
                    ),
                }
            ]
            final = self._call_groq(extra_messages=extra)
            
            # Handle empty after tool call
            if not final or final.strip() == "":
                final = f"Done. {tool_result[:100]}"
        else:
            final = first_pass

        self.history.append({"role": "assistant", "content": final})
        self._trim_history()
        
        # Save conversation summary to long-term memory
        try:
            summary = f"User: {user_input[:50]}... | Assistant: {final[:50]}..."
            topics = self._extract_topics(user_input, final)
            memory.save_conversation(summary, topics, importance=1)
        except Exception:
            logger.exception("Failed to save conversation to memory")
        
        return final

    def _extract_topics(self, user_input: str, assistant_response: str) -> list[str]:
        """Extract key topics from conversation for memory indexing."""
        text = (user_input + " " + assistant_response).lower()
        
        # Simple keyword extraction
        topic_keywords = {
            "calendar": ["date", "time", "schedule", "meeting", "appointment"],
            "reminder": ["remind", "alarm", "todo", "task"],
            "system": ["cpu", "ram", "memory", "disk", "computer", "system"],
            "files": ["file", "folder", "document", "open", "close"],
            "web": ["search", "google", "web", "internet", "website"],
            "app": ["app", "application", "chrome", "notepad", "calculator"],
            "media": ["music", "video", "movie", "song", "play"],
            "settings": ["volume", "brightness", "settings", "control"],
        }
        
        found_topics = []
        for topic, keywords in topic_keywords.items():
            if any(kw in text for kw in keywords):
                found_topics.append(topic)
        
        return found_topics[:3]  # Max 3 topics per conversation

    def clear_history(self) -> None:
        """Clear the conversation history."""

        self.history.clear()
