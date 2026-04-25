"""jarvis.llm

LLM integration and tool-dispatch layer for JARVIS.

This module wraps the Groq chat completion API, maintains short-term history,
extracts tool calls (as JSON), executes tools, and performs a second pass to
synthesize a final spoken response.
"""

from __future__ import annotations

import json
import logging
import os

# CRITICAL: Clear all proxy env vars BEFORE importing groq/httpx
# This fixes: "Client.__init__() got an unexpected keyword argument 'proxies'"
for key in list(os.environ.keys()):
    if 'proxy' in key.lower():
        del os.environ[key]

import httpx
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
        
        self.api_keys = config.GROQ_API_KEYS if config.GROQ_API_KEYS else [config.GROQ_API_KEY] if config.GROQ_API_KEY else []
        self.current_key_index = 0
        self.client = None
        
        # Try each API key until one works
        for i, api_key in enumerate(self.api_keys):
            try:
                # Create custom httpx client without proxies
                http_client = httpx.Client(trust_env=False)
                
                # Initialize Groq client with custom http_client (no proxies)
                self.client = Groq(
                    api_key=api_key,
                    http_client=http_client
                )
                self.current_key_index = i
                logger.info(f"Groq client initialized successfully with key {i+1}/{len(self.api_keys)}")
                break
            except Exception as e:
                logger.warning(f"API key {i+1} failed: {e}")
                continue
        
        if not self.client:
            logger.error("All Groq API keys failed to initialize!")
            
        self.history: list[dict[str, str]] = []
    
    def _rotate_api_key(self) -> bool:
        """Rotate to next available API key when current one fails."""
        if len(self.api_keys) <= 1:
            return False
            
        original_index = self.current_key_index
        for i in range(1, len(self.api_keys)):
            next_index = (self.current_key_index + i) % len(self.api_keys)
            api_key = self.api_keys[next_index]
            
            try:
                http_client = httpx.Client(trust_env=False)
                self.client = Groq(
                    api_key=api_key,
                    http_client=http_client
                )
                self.current_key_index = next_index
                logger.info(f"Rotated to API key {next_index + 1}/{len(self.api_keys)}")
                return True
            except Exception as e:
                logger.warning(f"API key {next_index + 1} also failed: {e}")
                continue
                
        return False

    def _trim_history(self) -> None:
        """Trim history to the last MAX_HISTORY_TURNS turns."""

        max_messages = self.MAX_HISTORY_TURNS * 2
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]
    
    def _load_memory_context(self) -> str:
        """Load recent conversation summaries from long-term memory."""
        try:
            from jarvis.memory import memory
            # Get last 5 important conversations
            recent = memory.get_recent_conversations(limit=5)
            if not recent:
                return ""
            
            context_parts = ["📚 Previous conversation context:"]
            for conv in recent:
                context_parts.append(f"- {conv.get('summary', '')}")
            
            return "\n".join(context_parts)
        except Exception as e:
            logger.debug(f"Could not load memory context: {e}")
            return ""

    def _call_groq(self, extra_messages: list[dict[str, str]] | None = None, retry_count: int = 0) -> str:
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
            error_msg = str(exc).lower()
            
            # Check if it's a rate limit or auth error that might be fixed by rotating keys
            is_rate_limit = any(x in error_msg for x in ['rate limit', '429', 'quota', 'insufficient', 'credits'])
            is_auth_error = any(x in error_msg for x in ['auth', 'api key', 'invalid', 'unauthorized', '401', '403'])
            
            if (is_rate_limit or is_auth_error) and retry_count < len(self.api_keys):
                logger.warning(f"API key {self.current_key_index + 1} failed ({'rate limit' if is_rate_limit else 'auth error'}), rotating...")
                if self._rotate_api_key():
                    # Retry with new key
                    return self._call_groq(extra_messages, retry_count + 1)
            
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
        # Pattern: look for {"tool":...} or {'tool':...} even if surrounded by text
        import re
        # Handle both single and double quotes, and nested braces
        json_pattern = r'\{\s*[\'"]?tool[\'"]?\s*:\s*[\'"]([^\'"]+)[\'"][^}]*\}'
        match = re.search(json_pattern, raw)
        if match:
            raw = match.group(0)
            logger.debug("Extracted JSON from text: %s", raw)
        
        # Convert single quotes to double quotes for valid JSON parsing
        if raw.startswith("{") and "'" in raw and '"' not in raw.replace("'", ""):
            raw = raw.replace("'", '"')
            logger.debug("Converted single quotes to double quotes")

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

    def chat(self, user_input: str) -> dict:
        """Process a user turn, optionally run a tool, and return structured response with actions."""

        user_input = (user_input or "").strip()
        if not user_input:
            return {"text": "I didn't receive any message. How can I help you today?", "actions": []}

        logger.info("Processing user input: %s", user_input[:50])
        
        # === LOAD MEMORY CONTEXT ===
        memory_context = self._load_memory_context()
        if memory_context:
            logger.info("🧠 Loaded memory context with recent conversations")
        
        # === SELF-LEARNING CHECK ===
        # Check if we have a correction for this or similar query
        from jarvis.learning_memory import learning_memory
        correction = learning_memory.find_correction(user_input, threshold=0.85)
        
        if correction:
            logger.info(f"💡 Learning memory applied! Found correction (similarity: {correction.get('similarity', 1.0):.2f})")
            # Use corrected response but still check if tool call needed
            corrected_response = correction['correct_response']
            
            # Still add to history for context
            self.history.append({"role": "user", "content": user_input})
            self._trim_history()
            
            # Check if correction contains tool call
            tool_call = self._extract_tool_call(corrected_response)
            if tool_call:
                actions = [tool_call]
                tool_result = self._dispatch_tool(tool_call)
                
                # Synthesize final response with tool result
                extra = [
                    {
                        "role": "system",
                        "content": (
                            f"You previously made a mistake but learned the correct answer. "
                            f"Use this CORRECTED approach:\n{corrected_response}\n\n"
                            f"Tool result: {tool_result}\n"
                            f"Respond naturally acknowledging what was done."
                        ),
                    }
                ]
                final = self._call_groq(extra_messages=extra)
                self.history.append({"role": "assistant", "content": final})
                self._trim_history()
                return {"text": final, "actions": actions}
            else:
                # No tool needed, just return corrected response
                self.history.append({"role": "assistant", "content": corrected_response})
                self._trim_history()
                return {"text": corrected_response, "actions": []}
        
        # === NORMAL LLM FLOW ===
        # Inject memory context before user message
        if memory_context:
            self.history.append({"role": "system", "content": memory_context})
        
        self.history.append({"role": "user", "content": user_input})
        self._trim_history()

        first_pass = self._call_groq()
        logger.debug("First pass LLM response: %s", first_pass[:100] if first_pass else "EMPTY")
        
        # Handle empty response from LLM
        if not first_pass or first_pass.strip() == "":
            logger.warning("LLM returned empty response")
            return {"text": "I didn't get a response. Let me try again.", "actions": []}
        
        tool_call = self._extract_tool_call(first_pass)
        actions = []

        if tool_call:
            logger.info("Tool call detected: %s", tool_call)
            # Store action info for frontend
            actions.append(tool_call)
            
            # Two-pass LLM: first to detect tool, second to synthesise result.
            tool_result = self._dispatch_tool(tool_call)
            logger.debug("Tool result: %s", tool_result[:100] if tool_result else "EMPTY")

            extra = [
                {
                    "role": "system",
                    "content": (
                        "You just called a tool. Use the tool result below to create a helpful, natural response. "
                        "Reply in plain conversational English (no JSON, no code, no brackets).\n\n"
                        f"TOOL_RESULT:\n{tool_result}\n\n"
                        "Instructions:\n"
                        "- Acknowledge what was done\n"
                        "- NEVER output raw JSON, arrays, or code\n"
                        "- Be concise and friendly\n"
                        "- Example: 'I've opened Chrome for you.'"
                    ),
                }
            ]
            final = self._call_groq(extra_messages=extra)
            
            # Handle empty after tool call - provide a clean fallback
            if not final or final.strip() == "":
                # Create a clean human-readable message from tool result
                clean_result = str(tool_result).replace('{"tool":', '').replace('"target":', '').replace('[', '').replace(']', '').replace('"', '').strip()
                if len(clean_result) > 50:
                    clean_result = clean_result[:50] + "..."
                final = f"Done! {clean_result}"
            
            # Clean up any JSON-like artifacts that might have slipped through
            import re
            json_pattern = r'\{[^}]*\}|\[[^\]]*\]|"tool"\s*:\s*"[^"]*"'
            final = re.sub(json_pattern, '', final)
            final = final.replace('  ', ' ').strip()
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
        
        return {"text": final, "actions": actions}

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
