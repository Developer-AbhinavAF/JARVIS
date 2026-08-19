"""JARVIS — Unified Application Entry Point.

Adapts the core/ package (current architecture) to the API surface the
jarvis-desktop backend expects: a `JARVIS` class with `handle()`,
`get_health()`, async `boot()`, and `_boot_complete` / `_nlp` / `_execution`
attributes. Also installs shim modules under `jarvis.*` so legacy backend
imports (`from jarvis.infra.settings import settings_storage`,
`from jarvis.execution import tool_registry`) keep working.
"""

from __future__ import annotations

import asyncio
import sys
import time
import logging
from pathlib import Path
from typing import Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("jarvis")


# ═══════════════════════════════════════════════════════════════════════
# PATH SETUP — make `core` importable as a top-level package
# ═══════════════════════════════════════════════════════════════════════

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# ═══════════════════════════════════════════════════════════════════════
# LEGACY SHIM MODULES — `jarvis.infra.*` and `jarvis.execution`
# ═══════════════════════════════════════════════════════════════════════
# The jarvis-desktop backend (jarvis-desktop/backend/app.py) imports
# `from jarvis.infra.settings import settings_storage` and
# `from jarvis.execution import tool_registry`. Those names were part of
# an earlier architecture that no longer exists; we provide minimal stubs
# here so the backend's settings/health endpoints keep working.

import types as _types


def _install_legacy_shims() -> None:
    """Create stub `jarvis.infra.*` and `jarvis.execution` modules in sys.modules."""
    if "jarvis" in sys.modules:
        return

    jarvis_pkg = _types.ModuleType("jarvis")
    jarvis_pkg.__path__ = []  # mark as package
    sys.modules["jarvis"] = jarvis_pkg

    # ── jarvis.infra ────────────────────────────────────────────────
    infra_pkg = _types.ModuleType("jarvis.infra")
    infra_pkg.__path__ = []
    sys.modules["jarvis.infra"] = infra_pkg

    # jarvis.infra.settings — backed by a small JSON file
    settings_mod = _types.ModuleType("jarvis.infra.settings")

    class _SettingsStorage:
        def __init__(self) -> None:
            self._path = _ROOT / "data" / "settings.json"
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._data: dict[str, Any] = {}
            self._load()

        def _load(self) -> None:
            if self._path.exists():
                try:
                    import json as _json
                    self._data = _json.loads(self._path.read_text(encoding="utf-8"))
                except Exception as exc:
                    logger.debug("settings load failed: %s", exc)
                    self._data = {}

        def _save(self) -> None:
            try:
                import json as _json
                self._path.write_text(_json.dumps(self._data, indent=2), encoding="utf-8")
            except Exception as exc:
                logger.debug("settings save failed: %s", exc)

        def all(self) -> dict[str, Any]:
            return dict(self._data)

        def get(self, key: str, default: Any = None) -> Any:
            return self._data.get(key, default)

        def set(self, key: str, value: Any, save: bool = False) -> None:
            self._data[key] = value
            if save:
                self.save()

        def set_many(self, values: dict[str, Any], save: bool = False) -> None:
            self._data.update(values)
            if save:
                self.save()

        def save(self) -> None:
            self._save()

        def reset_all(self) -> None:
            self._data = {}

        def get_path(self) -> str:
            return str(self._path)

    settings_mod.settings_storage = _SettingsStorage()
    sys.modules["jarvis.infra.settings"] = settings_mod
    setattr(infra_pkg, "settings", settings_mod)

    # Stub the other jarvis.infra.* attributes the backend / health endpoint
    # might poke at in the future. Lightweight, lazy.
    for _name, _factory in (
        ("events", lambda: _types.SimpleNamespace(
            event_bus=_types.SimpleNamespace(),
            EventType=_types.SimpleNamespace(),
        )),
        ("state", lambda: _types.SimpleNamespace(state_manager=_types.SimpleNamespace())),
        ("services", lambda: _types.SimpleNamespace(service_registry=_types.SimpleNamespace())),
        ("security", lambda: _types.SimpleNamespace(security_layer=_types.SimpleNamespace())),
        ("benchmarks", lambda: _types.SimpleNamespace(benchmarking=_types.SimpleNamespace())),
        ("analytics", lambda: _types.SimpleNamespace(analytics=_types.SimpleNamespace())),
        ("logging_system", lambda: _types.SimpleNamespace(central_logger=logger)),
    ):
        mod = _types.ModuleType(f"jarvis.infra.{_name}")
        setattr(mod, _name.rsplit("_", 1)[-1] if "_" in _name else _name, _factory())
        # also expose the canonical attribute name from the original
        mod_name = _name
        if _name == "logging_system":
            setattr(mod, "central_logger", getattr(mod, "logging_system", logger))
        else:
            setattr(mod, mod_name.rsplit("_", 1)[-1], _factory())
        sys.modules[f"jarvis.infra.{_name}"] = mod
        setattr(infra_pkg, _name, mod)

    # ── jarvis.execution ────────────────────────────────────────────
    execution_mod = _types.ModuleType("jarvis.execution")
    execution_mod.__path__ = []
    try:
        from core.tools_registry import tool_registry as _core_tool_registry  # type: ignore
        execution_mod.tool_registry = _core_tool_registry
    except Exception:
        class _StubRegistry:
            def get_stats(self) -> dict[str, int]:
                return {"total": 0}
        execution_mod.tool_registry = _StubRegistry()
    sys.modules["jarvis.execution"] = execution_mod


_install_legacy_shims()


# ═══════════════════════════════════════════════════════════════════════
# JARVIS — adapter class bridging the backend's expectations
# ═══════════════════════════════════════════════════════════════════════

class JARVIS:
    """Adapter that exposes the legacy API the backend expects on top of
    the current `core.jarvis_core.JarvisCore` orchestrator."""

    def __init__(self) -> None:
        self._boot_start = time.time()
        self._boot_complete = False
        self._debug_mode = False

        # Lightweight references the backend reads in /health and /execute.
        self._nlp: Optional[Any] = None
        self._execution: Optional[Any] = None

        # Lazy imports — these pull in torch/transformers, so wait until boot().
        self._core = None

    # ── boot ─────────────────────────────────────────────────────────
    async def boot(self) -> None:
        """Boot the underlying core and wire up subsystem references."""
        if self._boot_complete:
            return
        try:
            from core.jarvis_core import jarvis_core as _core_orchestrator  # type: ignore
            self._core = _core_orchestrator
            # JarvisCore.boot() is sync; call it. It's idempotent.
            try:
                self._core.boot()
            except Exception as exc:
                logger.warning("core.boot() raised: %s", exc)
        except Exception as exc:
            logger.warning("core.jarvis_core import failed: %s", exc)
            self._core = None

        # Wire up the subsystems the backend asks about.
        try:
            from core.execution import execution_engine  # type: ignore
            self._execution = execution_engine
        except Exception as exc:
            logger.debug("core.execution import failed: %s", exc)
            self._execution = None

        # The new architecture doesn't have a single `nlp` singleton — its
        # NLP role is split across planner_engine, intent_engine, brain_adapter.
        # Expose a lightweight stand-in so /health can introspect.
        try:
            from core.planner_engine import planner_engine  # type: ignore
            self._nlp = _types.SimpleNamespace(
                intent_engine=getattr(planner_engine, "intent_engine", None),
                _intent_descriptions=getattr(
                    getattr(planner_engine, "intent_engine", None),
                    "_intent_descriptions",
                    {},
                ),
            )
        except Exception:
            self._nlp = None

        self._boot_complete = True
        logger.info("JARVIS boot complete in %.2fs", time.time() - self._boot_start)

    # ── handle ──────────────────────────────────────────────────────
    async def handle(self, message: str) -> dict[str, Any]:
        """Process a user message and return a dict matching the backend's
        expected schema: {response, intent, intent_confidence, tool, verified, total_ms, result}."""
        start = time.time()
        if not self._boot_complete:
            await self.boot()

        # Offline / no-LLM fallback — the safe path if the brain is unavailable.
        response_text = ""
        intent = "unknown"
        intent_confidence = 0.0
        tool = ""
        verified = False
        result_payload: dict[str, Any] = {}

        if self._core is not None:
            try:
                holder: dict[str, Any] = {}

                async def _collect() -> None:
                    async for event in self._core.process_stream(message):
                        etype = getattr(event, "event_type", "") or getattr(event, "type", "")
                        if etype == "final_response":
                            holder["text"] = getattr(event, "text", "")
                        elif etype == "planner":
                            holder["intent"] = getattr(event, "goal", "")
                            holder["confidence"] = getattr(event, "confidence", 0.0)
                        elif etype == "execution":
                            holder["tool"] = getattr(event, "target_name", "")
                        elif etype == "verification":
                            holder["verified"] = getattr(event, "verified", False)
                            holder["details"] = getattr(event, "details", {})

                await asyncio.wait_for(_collect(), timeout=120.0)
                response_text = holder.get("text", "")
                intent = holder.get("intent", "unknown")
                intent_confidence = holder.get("confidence", 0.0)
                tool = holder.get("tool", "")
                verified = holder.get("verified", False)
            except Exception as exc:
                logger.warning("process_stream failed: %s", exc)
                response_text = f"(error: {exc})"

        if not response_text:
            response_text = (
                "I heard you. The core orchestrator is wired up, but no "
                "response was produced. Check that a brain (Ollama) is configured."
            )

        return {
            "response": response_text,
            "intent": intent,
            "intent_confidence": intent_confidence,
            "tool": tool,
            "verified": verified,
            "total_ms": int((time.time() - start) * 1000),
            "result": result_payload,
        }

    # ── handle_with_image ──────────────────────────────────────────────
    async def handle_with_image(self, message: str, image_context: dict[str, Any]) -> dict[str, Any]:
        """Process a user message with an attached image.
        
        Args:
            message: User's text message
            image_context: Dict with {image_data (base64), image_type, image_name}
        
        Returns:
            Dict matching backend schema: {response, intent, intent_confidence, tool, verified, total_ms}
        """
        start = time.time()
        if not self._boot_complete:
            await self.boot()

        response_text = ""
        intent = "unknown"
        intent_confidence = 0.0
        tool = ""
        verified = False
        result_payload: dict[str, Any] = {}

        if self._core is not None:
            try:
                holder: dict[str, Any] = {}

                async def _collect() -> None:
                    async for event in self._core.process_stream_with_image(message, image_context):
                        etype = getattr(event, "event_type", "") or getattr(event, "type", "")
                        if etype == "final_response":
                            holder["text"] = getattr(event, "text", "")
                        elif etype == "planner":
                            holder["intent"] = getattr(event, "goal", "")
                            holder["confidence"] = getattr(event, "confidence", 0.0)
                        elif etype == "execution":
                            holder["tool"] = getattr(event, "target_name", "")
                        elif etype == "verification":
                            holder["verified"] = getattr(event, "verified", False)
                            holder["details"] = getattr(event, "details", {})

                await asyncio.wait_for(_collect(), timeout=120.0)
                response_text = holder.get("text", "")
                intent = holder.get("intent", "unknown")
                intent_confidence = holder.get("confidence", 0.0)
                tool = holder.get("tool", "")
                verified = holder.get("verified", False)
                result_payload = holder.get("details", {}) or {}
            except asyncio.TimeoutError:
                response_text = "(JARVIS timed out while processing your image request.)"
            except Exception as exc:
                logger.warning("process_stream_with_image failed: %s", exc)
                response_text = f"(error: {exc})"

        if not response_text:
            response_text = (
                "I heard you. The core orchestrator is wired up, but no "
                "response was produced for this image. Check that a vision-capable "
                "brain (Ollama with vision model) is configured."
            )

        return {
            "response": response_text,
            "intent": intent,
            "intent_confidence": intent_confidence,
            "tool": tool,
            "verified": verified,
            "total_ms": int((time.time() - start) * 1000),
            "result": result_payload,
        }

    # ── get_health ──────────────────────────────────────────────────
    def get_health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self._boot_complete else "booting",
            "nlp_ready": self._nlp is not None,
            "execution_ready": self._execution is not None,
            "memory_ready": True,
            "knowledge_ready": True,
            "benchmarks": {},
            "analytics": {},
        }


# Convenience re-export for `python app.py` direct usage.
__all__ = ["JARVIS"]


if __name__ == "__main__":
    print("JARVIS root entry point. Use `python main.py` to start the application,")
    print("or `python jarvis-desktop/backend/app.py` to run the desktop backend.")
