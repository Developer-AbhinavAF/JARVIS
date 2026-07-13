from __future__ import annotations

from typing import Any

from .models import ChatRequest, EmbeddingRequest
from .exceptions import InvalidRequestError


class RequestValidator:
    """Validates incoming requests before routing."""

    @staticmethod
    def validate_chat_request(request: ChatRequest) -> None:
        if not request.messages:
            raise InvalidRequestError("Messages cannot be empty")
        if not isinstance(request.messages, list):
            raise InvalidRequestError("Messages must be a list")
        for msg in request.messages:
            if not isinstance(msg, dict):
                raise InvalidRequestError("Each message must be a dict")
            if "role" not in msg:
                raise InvalidRequestError("Each message must have a 'role' field")
            if "content" not in msg:
                raise InvalidRequestError("Each message must have a 'content' field")
            if msg["role"] not in ("system", "user", "assistant", "tool"):
                raise InvalidRequestError(f"Invalid role: {msg['role']}")
        if request.max_tokens is not None and request.max_tokens < 1:
            raise InvalidRequestError("max_tokens must be >= 1")
        if request.temperature is not None and not (0 <= request.temperature <= 2):
            raise InvalidRequestError("temperature must be between 0 and 2")
        if request.tools:
            for tool in request.tools:
                if not isinstance(tool, dict):
                    raise InvalidRequestError("Each tool must be a dict")
                if "function" not in tool:
                    raise InvalidRequestError("Each tool must have a 'function' field")

    @staticmethod
    def validate_embedding_request(request: EmbeddingRequest) -> None:
        if not request.input_texts:
            raise InvalidRequestError("Input texts cannot be empty")
        if not isinstance(request.input_texts, list):
            raise InvalidRequestError("Input texts must be a list")

    @staticmethod
    def validate_response(data: dict[str, Any]) -> bool:
        if "choices" not in data:
            return False
        choices = data["choices"]
        if not isinstance(choices, list) or not choices:
            return False
        choice = choices[0]
        if not isinstance(choice, dict):
            return False
        if "message" not in choice and "delta" not in choice:
            return False
        return True

    @staticmethod
    def sanitize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        sanitized = []
        for msg in messages:
            safe: dict[str, Any] = {
                "role": str(msg.get("role", "user")),
                "content": str(msg.get("content", "")),
            }
            sanitized.append(safe)
        return sanitized
