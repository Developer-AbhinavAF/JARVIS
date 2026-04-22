"""jarvis.error_handler

Global error handling, retry logic, health checks, and system recovery.
"""

from __future__ import annotations

import functools
import logging
import random
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class HealthStatus:
    """Health check status for a component."""
    component: str
    status: str  # "healthy", "degraded", "down"
    last_check: datetime
    response_time_ms: float
    error_count: int
    details: str


class HealthMonitor:
    """Monitor health of all JARVIS components."""
    
    def __init__(self) -> None:
        self.components: dict[str, HealthStatus] = {}
        self.check_history: list[HealthStatus] = []
        
    def check_component(self, name: str, check_func: Callable[[], bool]) -> HealthStatus:
        """Check health of a component."""
        start = time.time()
        try:
            result = check_func()
            response_time = (time.time() - start) * 1000
            
            status = HealthStatus(
                component=name,
                status="healthy" if result else "degraded",
                last_check=datetime.now(),
                response_time_ms=response_time,
                error_count=0,
                details="OK"
            )
        except Exception as e:
            response_time = (time.time() - start) * 1000
            status = HealthStatus(
                component=name,
                status="down",
                last_check=datetime.now(),
                response_time_ms=response_time,
                error_count=1,
                details=str(e)
            )
        
        self.components[name] = status
        self.check_history.append(status)
        return status
    
    def get_system_health(self) -> dict[str, Any]:
        """Get overall system health."""
        healthy = sum(1 for s in self.components.values() if s.status == "healthy")
        degraded = sum(1 for s in self.components.values() if s.status == "degraded")
        down = sum(1 for s in self.components.values() if s.status == "down")
        
        return {
            "total": len(self.components),
            "healthy": healthy,
            "degraded": degraded,
            "down": down,
            "status": "healthy" if down == 0 else "degraded" if down < 2 else "critical",
            "components": self.components
        }


class RetryConfig:
    """Configuration for retry logic."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Callable[[int, Exception], None] | None = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for retry logic with exponential backoff."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        if RetryConfig.jitter:
                            delay *= (0.5 + random.random())
                        
                        logger.warning(f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {e}")
                        if on_retry:
                            on_retry(attempt + 1, e)
                        time.sleep(delay)
                    else:
                        logger.error(f"All retries failed for {func.__name__}: {e}")
                        raise
            
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected error in retry logic")
        
        return wrapper
    return decorator


class SafeExecutor:
    """Execute functions with error handling and recovery."""
    
    def __init__(self) -> None:
        self.error_counts: dict[str, int] = {}
        self.recovery_actions: dict[str, Callable[[], None]] = {}
    
    def register_recovery(self, name: str, action: Callable[[], None]) -> None:
        """Register a recovery action for a component."""
        self.recovery_actions[name] = action
    
    def execute(
        self,
        name: str,
        func: Callable[..., T],
        *args: Any,
        fallback: T | None = None,
        **kwargs: Any
    ) -> T | None:
        """Execute function with error handling."""
        try:
            result = func(*args, **kwargs)
            self.error_counts[name] = 0
            return result
        except Exception as e:
            self.error_counts[name] = self.error_counts.get(name, 0) + 1
            logger.exception(f"Error in {name}: {e}")
            
            # Try recovery if error count is high
            if self.error_counts[name] >= 3 and name in self.recovery_actions:
                logger.info(f"Attempting recovery for {name}")
                try:
                    self.recovery_actions[name]()
                except Exception as recovery_error:
                    logger.error(f"Recovery failed for {name}: {recovery_error}")
            
            return fallback


class CrashRecovery:
    """Handle crash recovery and session restore."""
    
    def __init__(self, session_file: str = "jarvis_session.json") -> None:
        self.session_file = session_file
        self.session_data: dict[str, Any] = {}
        
    def save_session(self, data: dict[str, Any]) -> None:
        """Save current session state."""
        import json
        self.session_data = data
        try:
            with open(self.session_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
    
    def load_session(self) -> dict[str, Any] | None:
        """Load previous session state."""
        import json
        try:
            with open(self.session_file, 'r') as f:
                self.session_data = json.load(f)
                return self.session_data
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return None
    
    def clear_session(self) -> None:
        """Clear session data."""
        import os
        try:
            os.remove(self.session_file)
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error(f"Failed to clear session: {e}")


class RateLimiter:
    """Rate limiting for API calls."""
    
    def __init__(self, max_calls: int = 60, window_seconds: int = 60) -> None:
        self.max_calls = max_calls
        self.window = window_seconds
        self.calls: list[float] = []
        
    def can_call(self) -> bool:
        """Check if a call is allowed."""
        now = time.time()
        # Remove old calls outside the window
        self.calls = [c for c in self.calls if now - c < self.window]
        return len(self.calls) < self.max_calls
    
    def record_call(self) -> None:
        """Record a successful call."""
        self.calls.append(time.time())
    
    def get_wait_time(self) -> float:
        """Get seconds to wait before next call."""
        if len(self.calls) < self.max_calls:
            return 0.0
        oldest = min(self.calls)
        return max(0.0, self.window - (time.time() - oldest))


class InputSanitizer:
    """Sanitize inputs to prevent injection attacks."""
    
    @staticmethod
    def sanitize_string(text: str, max_length: int = 1000) -> str:
        """Sanitize a string input."""
        if not text:
            return ""
        
        # Remove control characters except newlines
        sanitized = "".join(char for char in text if char == '\n' or (ord(char) >= 32 and ord(char) <= 126) or char.isprintable())
        
        # Limit length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        # Remove common injection patterns
        dangerous = ["<script>", "</script>", "javascript:", "onerror=", "onload=", "eval(", "exec(", "system(", "subprocess"]
        for pattern in dangerous:
            sanitized = sanitized.replace(pattern, "")
        
        return sanitized
    
    @staticmethod
    def validate_command(cmd: str, allowed_prefixes: list[str]) -> bool:
        """Validate a command is in allowed list."""
        cmd = cmd.lower().strip()
        return any(cmd.startswith(prefix.lower()) for prefix in allowed_prefixes)


# Global instances
health_monitor = HealthMonitor()
safe_executor = SafeExecutor()
crash_recovery = CrashRecovery()
rate_limiter_groq = RateLimiter(max_calls=30, window_seconds=60)  # Groq limit
rate_limiter_tavily = RateLimiter(max_calls=100, window_seconds=60)  # Tavily limit

# Decorator for health tracking
def track_health(component_name: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to track function health."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            start = time.time()
            try:
                result = func(*args, **kwargs)
                health_monitor.components[component_name] = HealthStatus(
                    component=component_name,
                    status="healthy",
                    last_check=datetime.now(),
                    response_time_ms=(time.time() - start) * 1000,
                    error_count=0,
                    details="OK"
                )
                return result
            except Exception as e:
                health_monitor.components[component_name] = HealthStatus(
                    component=component_name,
                    status="down",
                    last_check=datetime.now(),
                    response_time_ms=(time.time() - start) * 1000,
                    error_count=1,
                    details=str(e)
                )
                raise
        return wrapper
    return decorator
