from __future__ import annotations

import json
import logging
from typing import Any, Generator

from jarvis import config
from jarvis.router_service import router_client, timing_mark, timing_report, timing_reset

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are JARVIS, a helpful AI assistant.

Rules:
- Keep responses short and direct.
- Use Markdown for lists or code.
- Never output shell commands or code to execute.
"""


class JarvisLLM:
    """JARVIS LLM facade — all requests go through the AI Router."""

    def __init__(self) -> None:
        self.client = router_client
        self.history: list[dict[str, str]] = []
        logger.info("JarvisLLM initialized — all AI routed through multi-provider router")

    @property
    def manager(self):
        return self

    def is_available(self) -> bool:
        return True

    def clear_history(self) -> None:
        self.history.clear()

    def _build_messages(
        self,
        message: str,
        context: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        if context:
            messages = list(context)
            if not any(m.get("role") == "system" for m in messages):
                messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
            messages.append({"role": "user", "content": message})
            system = [m for m in messages if m["role"] == "system"][:1]
            chat = [m for m in messages if m["role"] != "system"][-10:]
            return system + chat

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if self.history:
            messages.extend(self.history[-6:])
        messages.append({"role": "user", "content": message})
        return messages

    def _parse_structured_response(self, response_text: str) -> str | dict[str, Any]:
        text = (response_text or "").strip()
        if not text:
            return ""

        action_lines = []
        chat_lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("ACTION:"):
                action_lines.append(stripped)
            elif stripped.startswith("CHAT:"):
                chat_lines.append(stripped[5:].strip())

        if not action_lines:
            return text

        try:
            from jarvis.action_router import parse_action_line

            actions = []
            for line in action_lines[:2]:
                action = parse_action_line(line)
                if action:
                    actions.append(action.to_frontend_action())
            return {
                "text": " ".join(chat_lines).strip() or "Done.",
                "actions": actions,
            }
        except Exception as exc:
            logger.warning("Could not parse structured action response: %s", exc)
            return text

    def chat(
        self,
        message: str,
        context: list[dict[str, str]] | None = None,
        max_tokens: int | None = None,
    ) -> str | dict[str, Any]:
        timing_reset()

        import time
        t0 = time.time()
        messages = self._build_messages(message, context)
        timing_mark("prompt_build", t0)

        try:
            t1 = time.time()
            if max_tokens is None:
                max_tokens = config.LLM_MAX_TOKENS
            response_text = self.client.chat(
                messages,
                max_tokens=max_tokens,
                temperature=config.LLM_TEMPERATURE,
            )
            timing_mark("llm_request", t1)

            if not isinstance(response_text, str):
                response_text = "".join(response_text)

            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": response_text})
            if len(self.history) > 12:
                self.history = self.history[-12:]

            t2 = time.time()
            result = self._parse_structured_response(response_text)
            timing_mark("response_parse", t2)

            logger.info(timing_report())
            return result
        except Exception as exc:
            logger.exception("Chat error")
            raise

    def chat_stream(
        self,
        message: str,
        context: list[dict[str, str]] | None = None,
        max_tokens: int | None = None,
    ) -> Generator[str, None, None]:
        messages = self._build_messages(message, context)
        collected: list[str] = []

        try:
            if max_tokens is None:
                max_tokens = config.LLM_MAX_TOKENS
            for token in self.client.chat_stream(
                messages,
                max_tokens=max_tokens,
                temperature=config.LLM_TEMPERATURE,
            ):
                if token:
                    collected.append(token)
                    yield token

            response_text = "".join(collected)
            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": response_text})
            if len(self.history) > 12:
                self.history = self.history[-12:]
        except Exception as exc:
            logger.exception("Chat stream error")
            raise

    def quick_response(self, prompt: str, max_tokens: int = 16) -> str:
        timing_reset()
        import time
        t0 = time.time()
        messages = [
            {"role": "system", "content": "You are JARVIS. Be concise."},
            {"role": "user", "content": prompt},
        ]
        timing_mark("prompt_build", t0)
        t1 = time.time()
        response = self.client.chat(messages, max_tokens=max_tokens, temperature=0.3)
        timing_mark("llm_request", t1)
        result = response if isinstance(response, str) else "".join(response)
        logger.info(timing_report())
        return result

    def json_response(self, prompt: str, max_tokens: int = 256) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": "Return valid JSON only."},
            {"role": "user", "content": prompt},
        ]
        text = self.client.chat(
            messages,
            max_tokens=max_tokens,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw = text if isinstance(text, str) else "".join(text)
        return json.loads(raw)


_default_llm: JarvisLLM | None = None


def get_default_llm() -> JarvisLLM:
    global _default_llm
    if _default_llm is None:
        _default_llm = JarvisLLM()
    return _default_llm


def quick_chat(prompt: str) -> str:
    return get_default_llm().quick_response(prompt)
