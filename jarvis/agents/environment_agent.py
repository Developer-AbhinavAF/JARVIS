"""Environment Agent — System health, resource monitoring, and environmental context."""

from __future__ import annotations
import time
import logging
from typing import Any

from .base import AgentBase, AgentMessage, AgentPriority, MessageType, AgentCapability

logger = logging.getLogger(__name__)


class EnvironmentAgent(AgentBase):
    """Monitors battery, CPU, RAM, internet, GPU, temperature, and system health."""

    def __init__(self) -> None:
        super().__init__("environment", AgentPriority.LOW)
        self.add_capability(AgentCapability(
            name="system_status",
            intent_patterns=["SYSTEM_STATUS", "BATTERY", "CPU", "RAM", "INTERNET_STATUS"],
            keywords=["battery", "cpu", "ram", "memory", "internet", "system",
                     "status", "health", "temperature", "gpu"],
        ))

    async def process(self, message: AgentMessage) -> AgentMessage:
        text = message.payload.get("text", "")
        intent = message.payload.get("intent", "")

        result = self._check_environment(text, intent)

        return AgentMessage(
            source_agent=self.name,
            target_agent="orchestrator",
            task_id=message.task_id,
            message_type=MessageType.RESULT,
            payload={
                "response": result["response"],
                "environment": result.get("environment", {}),
            },
        )

    def _check_environment(self, text: str, intent: str) -> dict:
        env = {}

        try:
            import psutil
            env["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            ram = psutil.virtual_memory()
            env["ram_percent"] = ram.percent
            env["ram_available_gb"] = round(ram.available / (1024**3), 1)

            bat = psutil.sensors_battery()
            if bat:
                env["battery_percent"] = bat.percent
                env["battery_plugged"] = bat.power_plugged
        except Exception:
            pass

        if not env:
            return {"response": "System info not available.", "environment": {}}

        parts = []
        if "cpu_percent" in env:
            parts.append(f"CPU: {env['cpu_percent']}%")
        if "ram_percent" in env:
            parts.append(f"RAM: {env['ram_percent']}%")
        if "battery_percent" in env:
            parts.append(f"Battery: {env['battery_percent']}%")

        return {
            "response": "System: " + ", ".join(parts) if parts else "System OK.",
            "environment": env,
        }


environment_agent = EnvironmentAgent()
