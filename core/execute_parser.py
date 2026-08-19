"""core/execute_parser.py — Execute Tag Parser for JARVIS vNext++.

Parses <execute> tags from model output and provides structured execution requests.
"""

from __future__ import annotations

import re
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExecuteRequest:
    """Structured execute request parsed from <execute> tag."""
    execution_type: str
    command: str
    is_valid: bool
    error: Optional[str] = None


class ExecuteParser:
    """Parses <execute> tags from model output."""

    # Supported execution types
    SUPPORTED_TYPES = {
        "bash",
        "sh",
        "cmd",
        "powershell",
        "python",
        "node",
        "javascript",
    }

    # Regex pattern for <execute type="..."><command>...</command></execute>
    PATTERN = re.compile(
        r'<execute\s+type=["\']([^"\']+)["\']>\s*'
        r'<command>(.*?)</command>\s*'
        r'</execute>',
        re.DOTALL | re.IGNORECASE
    )

    def __init__(self):
        pass

    def parse(self, text: str) -> List[ExecuteRequest]:
        """Parse execute tags from text.

        Args:
            text: Model output text that may contain <execute> tags

        Returns:
            List of ExecuteRequest objects (valid and invalid)
        """
        requests = []
        
        for match in self.PATTERN.finditer(text):
            execution_type = match.group(1).strip().lower()
            command = match.group(2).strip()
            
            # Validate execution type
            if execution_type not in self.SUPPORTED_TYPES:
                requests.append(ExecuteRequest(
                    execution_type=execution_type,
                    command=command,
                    is_valid=False,
                    error=f"Unsupported execution type: {execution_type}"
                ))
                logger.warning("[EXECUTE_PARSER] Unsupported type: %s", execution_type)
                continue
            
            # Validate command
            if not command:
                requests.append(ExecuteRequest(
                    execution_type=execution_type,
                    command=command,
                    is_valid=False,
                    error="Empty command"
                ))
                logger.warning("[EXECUTE_PARSER] Empty command for type: %s", execution_type)
                continue
            
            # Valid request
            requests.append(ExecuteRequest(
                execution_type=execution_type,
                command=command,
                is_valid=True,
                error=None
            ))
            logger.info("[EXECUTE_PARSER] Parsed valid execute: type=%s, command=%s", 
                       execution_type, command[:50])
        
        return requests

    def remove_execute_tags(self, text: str) -> str:
        """Remove execute tags from text for display to user.

        Args:
            text: Text containing execute tags

        Returns:
            Text with execute tags removed
        """
        return self.PATTERN.sub('[EXECUTE COMMAND]', text)

    def has_execute_tags(self, text: str) -> bool:
        """Check if text contains execute tags.

        Args:
            text: Text to check

        Returns:
            True if execute tags are present
        """
        return bool(self.PATTERN.search(text))


execute_parser = ExecuteParser()