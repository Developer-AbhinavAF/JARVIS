"""Adaptive execution for JARVIS NLP.

Detects existing resources (open browser, open tabs, running apps)
and reuses them instead of duplicating work.

Example: If browser is already open with a YouTube tab, "search Python"
should reuse that tab instead of opening a new browser window.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


# ════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ════════════════════════════════════════════════════════════════════

@dataclass
class ActiveResource:
    """A currently active resource (app, browser tab, etc.)."""
    resource_type: str  # "app", "browser_tab", "window", "file", "folder"
    name: str
    url: str = ""
    path: str = ""
    title: str = ""
    last_active: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_stale(self, timeout: float = 600.0) -> bool:
        """Check if this resource hasn't been used recently."""
        return (time.time() - self.last_active) > timeout

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_type": self.resource_type,
            "name": self.name,
            "url": self.url,
            "path": self.path,
            "title": self.title,
            "last_active": self.last_active,
            "metadata": self.metadata,
        }


@dataclass
class AdaptivePlan:
    """Plan for adaptive execution."""
    should_reuse: bool
    resource: ActiveResource | None
    action: str  # "reuse", "create_new", "switch_tab", "reuse_tab"
    reason: str
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "should_reuse": self.should_reuse,
            "resource": self.resource.to_dict() if self.resource else None,
            "action": self.action,
            "reason": self.reason,
            "parameters": self.parameters,
        }


# ════════════════════════════════════════════════════════════════════
# ENGINE
# ════════════════════════════════════════════════════════════════════

class AdaptiveExecutor:
    """Manages active resources and provides adaptive execution plans.

    Tracks which apps, browser tabs, windows, files, and folders are
    currently active, and suggests reuse strategies to avoid duplication.
    """

    def __init__(self) -> None:
        self._active_resources: list[ActiveResource] = []
        self._resource_history: list[ActiveResource] = []

    def track_resource(self, resource: ActiveResource) -> None:
        """Register an active resource after successful execution."""
        # Update existing or add new
        for existing in self._active_resources:
            if (
                existing.resource_type == resource.resource_type
                and existing.name == resource.name
            ):
                existing.last_active = time.time()
                existing.url = resource.url or existing.url
                existing.path = resource.path or existing.path
                existing.title = resource.title or existing.title
                existing.metadata.update(resource.metadata)
                return

        resource.last_active = time.time()
        self._active_resources.append(resource)

    def get_adaptive_plan(
        self,
        intent: str,
        entities: dict[str, Any],
    ) -> AdaptivePlan:
        """Determine the best execution strategy given current resources.

        Checks if an existing resource can be reused, or if a new
        one needs to be created.
        """
        self._cleanup_stale()

        if intent == "OPEN_WEBSITE":
            return self._plan_website_open(entities)
        elif intent in ("OPEN_APP", "PROGRAMMING"):
            return self._plan_app_open(entities)
        elif intent == "SEARCH_WEB":
            return self._plan_web_search(entities)
        elif intent in ("PLAY_MUSIC", "PLAY_YOUTUBE", "PLAY_SPOTIFY"):
            return self._plan_media(entities)
        elif intent in ("OPEN_FOLDER", "FILE_MANAGEMENT"):
            return self._plan_file_ops(entities)
        elif intent == "WINDOW_CONTROL":
            return self._plan_window(entities)

        return AdaptivePlan(
            should_reuse=False,
            resource=None,
            action="create_new",
            reason="No matching active resource",
        )

    def update_after_execution(
        self,
        intent: str,
        entities: dict[str, Any],
        success: bool,
    ) -> None:
        """Track resources created by successful executions."""
        if not success:
            return

        target = str(entities.get("target", ""))
        url = str(entities.get("url", ""))
        path = str(entities.get("path", ""))

        if intent == "OPEN_WEBSITE":
            website = str(entities.get("website", target))
            self.track_resource(ActiveResource(
                resource_type="browser_tab",
                name=website,
                url=url or target,
            ))

        elif intent in ("OPEN_APP", "PROGRAMMING"):
            self.track_resource(ActiveResource(
                resource_type="app",
                name=target,
            ))

        elif intent == "OPEN_FOLDER":
            self.track_resource(ActiveResource(
                resource_type="folder",
                name=target,
                path=path or target,
            ))

        elif intent in ("PLAY_MUSIC", "PLAY_YOUTUBE", "PLAY_SPOTIFY"):
            query = str(entities.get("query", ""))
            self.track_resource(ActiveResource(
                resource_type="media",
                name=query or target,
            ))

    def get_active_resources(self) -> list[ActiveResource]:
        """Return all currently active resources."""
        self._cleanup_stale()
        return list(self._active_resources)

    def clear(self) -> None:
        """Clear all tracked resources."""
        self._active_resources.clear()

    # ── planning methods ────────────────────────────────────────────

    def _plan_website_open(self, entities: dict[str, Any]) -> AdaptivePlan:
        """Plan for opening a website."""
        target = str(entities.get("target", "")).lower()
        website = str(entities.get("website", "")).lower()

        # Check if we already have a tab for this website
        for resource in self._active_resources:
            if resource.resource_type == "browser_tab":
                if website and website in resource.name.lower():
                    return AdaptivePlan(
                        should_reuse=True,
                        resource=resource,
                        action="reuse_tab",
                        reason=f"Tab for {website} already open",
                    )
                if target and target in resource.url.lower():
                    return AdaptivePlan(
                        should_reuse=True,
                        resource=resource,
                        action="reuse_tab",
                        reason=f"Tab with {target} already open",
                    )

        # Check if any browser is open — reuse it
        for resource in self._active_resources:
            if resource.resource_type == "app" and resource.name in (
                "chrome", "firefox", "edge", "brave", "opera",
            ):
                return AdaptivePlan(
                    should_reuse=True,
                    resource=resource,
                    action="reuse_browser",
                    reason=f"Browser {resource.name} already open, opening new tab",
                )

        return AdaptivePlan(
            should_reuse=False,
            resource=None,
            action="create_new",
            reason="No browser open, launching new one",
        )

    def _plan_app_open(self, entities: dict[str, Any]) -> AdaptivePlan:
        """Plan for opening an application."""
        target = str(entities.get("target", "")).lower()

        for resource in self._active_resources:
            if resource.resource_type == "app" and resource.name == target:
                return AdaptivePlan(
                    should_reuse=True,
                    resource=resource,
                    action="switch_to",
                    reason=f"{target} is already running",
                )

        return AdaptivePlan(
            should_reuse=False,
            resource=None,
            action="create_new",
            reason=f"{target} not currently running",
        )

    def _plan_web_search(self, entities: dict[str, Any]) -> AdaptivePlan:
        """Plan for a web search."""
        # Reuse existing browser if available
        for resource in self._active_resources:
            if resource.resource_type == "app" and resource.name in (
                "chrome", "firefox", "edge", "brave",
            ):
                return AdaptivePlan(
                    should_reuse=True,
                    resource=resource,
                    action="reuse_browser",
                    reason="Reusing open browser for search",
                )

        return AdaptivePlan(
            should_reuse=False,
            resource=None,
            action="create_new",
            reason="No browser open for search",
        )

    def _plan_media(self, entities: dict[str, Any]) -> AdaptivePlan:
        """Plan for media playback."""
        # Check if media is already playing
        for resource in self._active_resources:
            if resource.resource_type == "media":
                return AdaptivePlan(
                    should_reuse=True,
                    resource=resource,
                    action="reuse_media",
                    reason="Media player already active, switching track",
                )

        return AdaptivePlan(
            should_reuse=False,
            resource=None,
            action="create_new",
            reason="Starting new media session",
        )

    def _plan_file_ops(self, entities: dict[str, Any]) -> AdaptivePlan:
        """Plan for file/folder operations."""
        target = str(entities.get("target", entities.get("path", ""))).lower()

        for resource in self._active_resources:
            if resource.resource_type == "folder" and target in resource.path.lower():
                return AdaptivePlan(
                    should_reuse=True,
                    resource=resource,
                    action="reuse_folder",
                    reason=f"Folder {target} already open",
                )

        return AdaptivePlan(
            should_reuse=False,
            resource=None,
            action="create_new",
            reason="Folder not currently open",
        )

    def _plan_window(self, entities: dict[str, Any]) -> AdaptivePlan:
        """Plan for window management."""
        target = str(entities.get("target", entities.get("title", ""))).lower()

        for resource in self._active_resources:
            if resource.resource_type in ("app", "window"):
                if target and target in resource.name.lower():
                    return AdaptivePlan(
                        should_reuse=True,
                        resource=resource,
                        action="switch_to",
                        reason=f"Window '{resource.name}' found",
                    )

        return AdaptivePlan(
            should_reuse=False,
            resource=None,
            action="create_new",
            reason="Target window not found in active resources",
        )

    # ── cleanup ─────────────────────────────────────────────────────

    def _cleanup_stale(self, timeout: float = 1800.0) -> None:
        """Remove stale resources older than timeout."""
        now = time.time()
        fresh = [r for r in self._active_resources if (now - r.last_active) < timeout]
        stale = [r for r in self._active_resources if (now - r.last_active) >= timeout]
        self._resource_history.extend(stale)
        self._active_resources = fresh

        # Cap history
        if len(self._resource_history) > 100:
            self._resource_history = self._resource_history[-100:]
