"""core/capability_router.py — Capability-based AI provider routing system.

This module implements intelligent routing based on:
- Required capabilities
- Provider health and availability
- Latency and performance
- Priority and fallback logic
- Multi-key rotation

Architecture:
    Required Capabilities
        ↓
    Filter Compatible Providers
        ↓
    Filter Healthy Providers
        ↓
    Filter Available Keys
        ↓
    Sort by Priority & Performance
        ↓
    Execute with Fallback
"""

from __future__ import annotations

import logging
import time
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator, Set
from dataclasses import dataclass

from core.provider_registry import (
    provider_registry,
    BaseProvider,
    Capability,
    ProviderResponse,
)

logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    """Represents a routing decision with metadata."""
    provider_name: str
    key_id: str
    model: str
    capability_match_score: float
    health_score: float
    priority_score: float
    latency_score: float
    overall_score: float
    reasoning: str


class CapabilityRouter:
    """Intelligent capability-based provider router."""
    
    def __init__(self, max_attempts: int = 5):
        self.provider_registry = provider_registry
        self.max_attempts = max_attempts
        
        # Routing statistics
        self._routing_stats: Dict[str, Dict[str, Any]] = {}
    
    def infer_required_capabilities(self, messages: List[Dict[str, Any]], **kwargs) -> Set[Capability]:
        """Infer required capabilities from the request context."""
        capabilities = {Capability.GENERAL_CHAT}  # Default capability
        
        # Check for images in messages
        for msg in messages:
            if isinstance(msg.get("content"), list):
                for content_item in msg["content"]:
                    if isinstance(content_item, dict) and content_item.get("type") == "image_url":
                        capabilities.add(Capability.VISION)
                        break
        
        # Check for tools
        if "tools" in kwargs and kwargs["tools"]:
            capabilities.add(Capability.TOOL_CALLING)
        
        # Check for structured output request
        if "response_format" in kwargs:
            capabilities.add(Capability.STRUCTURED_OUTPUT)
        
        # Check for long context requirement
        total_tokens = sum(len(str(msg.get("content", ""))) for msg in messages)
        if total_tokens > 8000:  # Approximate token threshold
            capabilities.add(Capability.LONG_CONTEXT)
        
        # Check for coding-related content
        text_content = " ".join(str(msg.get("content", "")) for msg in messages)
        coding_keywords = ["code", "function", "python", "javascript", "algorithm", "debug"]
        if any(keyword in text_content.lower() for keyword in coding_keywords):
            capabilities.add(Capability.CODING)
        
        # Check for reasoning requirements
        reasoning_keywords = ["analyze", "explain", "compare", "evaluate", "reason", "logic"]
        if any(keyword in text_content.lower() for keyword in reasoning_keywords):
            capabilities.add(Capability.REASONING)
        
        return capabilities
    
    def select_provider(
        self,
        required_capabilities: Set[Capability],
        exclude_providers: Optional[List[str]] = None,
    ) -> Optional[RoutingDecision]:
        """Select the best provider for given capabilities."""
        
        # Reload configuration if changed
        self.provider_registry.reload_if_changed()
        
        exclude_providers = exclude_providers or []
        
        # Get all providers that support required capabilities
        compatible_providers = []
        for capability in required_capabilities:
            providers = self.provider_registry.get_providers_for_capability(capability)
            compatible_providers.extend(providers)
        
        # Remove duplicates
        seen = set()
        unique_providers = []
        for provider in compatible_providers:
            if provider.config.provider_name not in seen:
                seen.add(provider.config.provider_name)
                unique_providers.append(provider)
        
        # Filter out excluded providers
        available_providers = [
            p for p in unique_providers 
            if p.config.provider_name not in exclude_providers
        ]
        
        if not available_providers:
            logger.warning("[ROUTER] No providers available for capabilities: %s", 
                          [c.value for c in required_capabilities])
            return None
        
        # Filter by availability
        healthy_providers = [
            p for p in available_providers 
            if p.config.available and p.current_key is not None
        ]
        
        if not healthy_providers:
            logger.warning("[ROUTER] No healthy providers available")
            # Fall back to any provider with available keys
            healthy_providers = [
                p for p in available_providers 
                if p.current_key is not None
            ]
        
        if not healthy_providers:
            return None
        
        # Score each provider
        scored_providers = []
        for provider in healthy_providers:
            decision = self._score_provider(provider, required_capabilities)
            if decision:
                scored_providers.append(decision)
        
        # Sort by overall score
        scored_providers.sort(key=lambda d: d.overall_score, reverse=True)
        
        if scored_providers:
            selected = scored_providers[0]
            logger.info("[ROUTER] Selected %s (score=%.2f) for capabilities %s: %s",
                       selected.provider_name, selected.overall_score,
                       [c.value for c in required_capabilities], selected.reasoning)
            return selected
        
        return None
    
    def _score_provider(
        self,
        provider: BaseProvider,
        required_capabilities: Set[Capability],
    ) -> Optional[RoutingDecision]:
        """Score a provider for the given capabilities."""
        
        config = provider.config
        key = provider.current_key
        
        if not key:
            return None
        
        # Capability match score (0.0-1.0)
        supported_capabilities = config.capabilities
        matched_capabilities = required_capabilities & supported_capabilities
        capability_score = len(matched_capabilities) / max(len(required_capabilities), 1)
        
        # Health score (0.0-1.0)
        health_score = key.health_score
        
        # Priority score (normalized 0.0-1.0, lower priority number = higher score)
        # Priority range: 10-100, so invert and normalize
        priority_score = max(0, (100 - config.priority) / 90)
        
        # Latency score (0.0-1.0, lower latency = higher score)
        # Assume max acceptable latency is 10 seconds
        latency_score = max(0, 1 - (config.average_latency_ms / 10000))
        
        # Overall weighted score
        weights = {
            "capability": 0.4,
            "health": 0.3,
            "priority": 0.2,
            "latency": 0.1,
        }
        
        overall_score = (
            weights["capability"] * capability_score +
            weights["health"] * health_score +
            weights["priority"] * priority_score +
            weights["latency"] * latency_score
        )
        
        # Build reasoning string
        reasoning_parts = []
        reasoning_parts.append(f"capability_match={capability_score:.2f}")
        reasoning_parts.append(f"health={health_score:.2f}")
        reasoning_parts.append(f"priority={priority_score:.2f}")
        reasoning_parts.append(f"latency={latency_score:.2f}")
        
        model = config.supported_models[0] if config.supported_models else ""
        
        return RoutingDecision(
            provider_name=config.provider_name,
            key_id=key.key_id,
            model=model,
            capability_match_score=capability_score,
            health_score=health_score,
            priority_score=priority_score,
            latency_score=latency_score,
            overall_score=overall_score,
            reasoning=", ".join(reasoning_parts),
        )
    
    async def route_chat(
        self,
        messages: List[Dict[str, Any]],
        model: str = "",
        **kwargs
    ) -> ProviderResponse:
        """Route a chat request to the best available provider with fallback."""
        
        required_capabilities = self.infer_required_capabilities(messages, **kwargs)
        
        excluded_providers = []
        last_error = ""
        
        for attempt in range(self.max_attempts):
            decision = self.select_provider(required_capabilities, excluded_providers)
            
            if not decision:
                logger.error("[ROUTER] No providers available after %d attempts", attempt + 1)
                return ProviderResponse(
                    success=False,
                    error="No available providers",
                    error_category="unavailable",
                )
            
            provider = self.provider_registry.get_provider(decision.provider_name)
            if not provider:
                excluded_providers.append(decision.provider_name)
                continue
            
            try:
                logger.info("[ROUTER] Attempt %d: Using %s with key %s", 
                           attempt + 1, decision.provider_name, decision.key_id)
                
                response = await provider.chat(messages, model=decision.model, **kwargs)
                
                if response.success:
                    # Record success
                    self.provider_registry.record_provider_success(
                        decision.provider_name, response.latency_ms
                    )
                    self.provider_registry.record_key_success(
                        decision.provider_name, decision.key_id
                    )
                    
                    # Update routing stats
                    self._update_routing_stats(decision.provider_name, True, response.latency_ms)
                    
                    return response
                else:
                    # Record failure
                    self.provider_registry.record_provider_failure(
                        decision.provider_name, response.error_category
                    )
                    self.provider_registry.record_key_failure(
                        decision.provider_name, decision.key_id, response.error_category
                    )
                    
                    last_error = response.error
                    excluded_providers.append(decision.provider_name)
                    
                    logger.warning("[ROUTER] %s failed: %s", decision.provider_name, response.error)
                    
                    # Try key rotation within same provider
                    if attempt < 2:  # Only rotate keys for first 2 attempts
                        rotated_key = provider.rotate_key()
                        if rotated_key and rotated_key.key_id != decision.key_id:
                            logger.info("[ROUTER] Rotating to key %s for %s", 
                                       rotated_key.key_id, decision.provider_name)
                            continue
            
            except Exception as e:
                logger.error("[ROUTER] Exception with %s: %s", decision.provider_name, e)
                self.provider_registry.record_provider_failure(
                    decision.provider_name, "unknown"
                )
                excluded_providers.append(decision.provider_name)
                last_error = str(e)
        
        # All attempts failed
        logger.error("[ROUTER] All routing attempts failed. Last error: %s", last_error)
        
        return ProviderResponse(
            success=False,
            error=f"All providers failed. Last error: {last_error}",
            error_category="unavailable",
        )
    
    async def route_chat_stream(
        self,
        messages: List[Dict[str, Any]],
        model: str = "",
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Route a streaming chat request to the best available provider with fallback."""
        
        required_capabilities = self.infer_required_capabilities(messages, **kwargs)
        
        excluded_providers = []
        last_error = ""
        
        for attempt in range(self.max_attempts):
            decision = self.select_provider(required_capabilities, excluded_providers)
            
            if not decision:
                logger.error("[ROUTER] No providers available for streaming after %d attempts", attempt + 1)
                yield "[Error: No available providers]"
                return
            
            provider = self.provider_registry.get_provider(decision.provider_name)
            if not provider:
                excluded_providers.append(decision.provider_name)
                continue
            
            try:
                logger.info("[ROUTER] Stream attempt %d: Using %s with key %s", 
                           attempt + 1, decision.provider_name, decision.key_id)
                
                start_time = time.time()
                first_token = False
                token_count = 0
                
                async for token in provider.chat_stream(messages, model=decision.model, **kwargs):
                    if not first_token:
                        first_token = True
                        logger.info("[ROUTER] First token received from %s", decision.provider_name)
                    token_count += 1
                    yield token
                
                latency_ms = (time.time() - start_time) * 1000
                
                # Record success
                self.provider_registry.record_provider_success(
                    decision.provider_name, latency_ms
                )
                self.provider_registry.record_key_success(
                    decision.provider_name, decision.key_id
                )
                
                # Update routing stats
                self._update_routing_stats(decision.provider_name, True, latency_ms)
                
                logger.info("[ROUTER] Stream completed: %d tokens from %s in %.1fms",
                           token_count, decision.provider_name, latency_ms)
                return
                
            except Exception as e:
                logger.error("[ROUTER] Stream exception with %s: %s", decision.provider_name, e)
                self.provider_registry.record_provider_failure(
                    decision.provider_name, "unknown"
                )
                excluded_providers.append(decision.provider_name)
                last_error = str(e)
                
                # Try key rotation within same provider
                if attempt < 2:  # Only rotate keys for first 2 attempts
                    rotated_key = provider.rotate_key()
                    if rotated_key and rotated_key.key_id != decision.key_id:
                        logger.info("[ROUTER] Rotating to key %s for %s", 
                                   rotated_key.key_id, decision.provider_name)
                        continue
        
        # All attempts failed
        logger.error("[ROUTER] All streaming routing attempts failed. Last error: %s", last_error)
        yield f"[Error: All providers failed. Last error: {last_error}]"
    
    def _update_routing_stats(self, provider_name: str, success: bool, latency_ms: float) -> None:
        """Update routing statistics for a provider."""
        if provider_name not in self._routing_stats:
            self._routing_stats[provider_name] = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_latency_ms": 0.0,
                "avg_latency_ms": 0.0,
            }
        
        stats = self._routing_stats[provider_name]
        stats["total_requests"] += 1
        
        if success:
            stats["successful_requests"] += 1
            stats["total_latency_ms"] += latency_ms
            stats["avg_latency_ms"] = stats["total_latency_ms"] / stats["successful_requests"]
        else:
            stats["failed_requests"] += 1
    
    def get_routing_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get routing statistics for all providers."""
        return dict(self._routing_stats)
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive router status."""
        return {
            "provider_registry": self.provider_registry.get_provider_status(),
            "routing_stats": self.get_routing_stats(),
            "max_attempts": self.max_attempts,
        }


# Global instance
capability_router = CapabilityRouter()
