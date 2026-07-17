"""Environment Engine — Monitors system resources continuously.

CPU, GPU, RAM, disk, battery, internet, temperature.
Resource usage influences decision making.
"""

from __future__ import annotations

import time
import logging
import threading
import platform
from typing import Any
from dataclasses import dataclass, field

from .events import EventBus, EventType, event_bus

logger = logging.getLogger(__name__)


@dataclass
class SystemResources:
    """Snapshot of system resource usage."""
    cpu_percent: float = 0.0
    cpu_count: int = 0
    cpu_freq_mhz: float = 0.0
    ram_total_gb: float = 0.0
    ram_used_gb: float = 0.0
    ram_percent: float = 0.0
    disk_total_gb: float = 0.0
    disk_used_gb: float = 0.0
    disk_percent: float = 0.0
    battery_percent: float = -1.0    # -1 = no battery
    battery_charging: bool = False
    internet_connected: bool = True
    internet_latency_ms: float = 0.0
    temperature_c: float = 0.0
    gpu_percent: float = 0.0
    gpu_memory_gb: float = 0.0
    platform: str = ""
    hostname: str = ""

    @property
    def performance_mode(self) -> str:
        """Determine performance mode from resources."""
        if self.cpu_percent > 85 or self.ram_percent > 90:
            return "ultra_performance"
        elif self.cpu_percent > 70 or self.ram_percent > 75:
            return "performance"
        elif self.battery_percent >= 0 and self.battery_percent < 20 and not self.battery_charging:
            return "battery_saver"
        else:
            return "balanced"

    @property
    def is_constrained(self) -> bool:
        return self.cpu_percent > 80 or self.ram_percent > 85

    def to_dict(self) -> dict[str, Any]:
        return {
            "cpu_percent": round(self.cpu_percent, 1),
            "cpu_count": self.cpu_count,
            "ram_total_gb": round(self.ram_total_gb, 1),
            "ram_used_gb": round(self.ram_used_gb, 1),
            "ram_percent": round(self.ram_percent, 1),
            "disk_percent": round(self.disk_percent, 1),
            "battery_percent": self.battery_percent,
            "battery_charging": self.battery_charging,
            "internet_connected": self.internet_connected,
            "internet_latency_ms": round(self.internet_latency_ms, 1),
            "performance_mode": self.performance_mode,
            "platform": self.platform,
        }


class EnvironmentEngine:
    """Monitors system resources in background.

    Usage:
        env = EnvironmentEngine()
        env.start()
        resources = env.snapshot()
        if resources.cpu_percent > 80:
            # Reduce workload
    """

    def __init__(self, bus: EventBus | None = None, poll_interval: float = 5.0):
        self._bus = bus or event_bus
        self._poll_interval = poll_interval
        self._resources = SystemResources()
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._prev_cpu_high = False
        self._prev_battery_low = False

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="env-monitor")
        self._thread.start()
        self._collect_once()
        logger.info("EnvironmentEngine started (platform=%s)", self._resources.platform)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)

    def snapshot(self) -> SystemResources:
        with self._lock:
            return SystemResources(
                cpu_percent=self._resources.cpu_percent,
                cpu_count=self._resources.cpu_count,
                cpu_freq_mhz=self._resources.cpu_freq_mhz,
                ram_total_gb=self._resources.ram_total_gb,
                ram_used_gb=self._resources.ram_used_gb,
                ram_percent=self._resources.ram_percent,
                disk_total_gb=self._resources.disk_total_gb,
                disk_used_gb=self._resources.disk_used_gb,
                disk_percent=self._resources.disk_percent,
                battery_percent=self._resources.battery_percent,
                battery_charging=self._resources.battery_charging,
                internet_connected=self._resources.internet_connected,
                internet_latency_ms=self._resources.internet_latency_ms,
                temperature_c=self._resources.temperature_c,
                gpu_percent=self._resources.gpu_percent,
                gpu_memory_gb=self._resources.gpu_memory_gb,
                platform=self._resources.platform,
                hostname=self._resources.hostname,
            )

    def get_setting(self, key: str) -> Any:
        """Get a resource-derived setting."""
        res = self.snapshot()
        settings = {
            "performance_mode": res.performance_mode,
            "should_reduce_vision": res.cpu_percent > 70,
            "should_reduce_quality": res.is_constrained,
            "can_heavy_compute": not res.is_constrained,
            "is_on_battery": res.battery_percent >= 0 and not res.battery_charging,
        }
        return settings.get(key)

    def _poll_loop(self):
        while self._running:
            self._collect_once()
            time.sleep(self._poll_interval)

    def _collect_once(self):
        try:
            import psutil
        except ImportError:
            self._resources.platform = platform.system()
            self._resources.hostname = platform.node()
            return

        try:
            self._resources.cpu_percent = psutil.cpu_percent(interval=0.1)
            self._resources.cpu_count = psutil.cpu_count() or 0
            freq = psutil.cpu_freq()
            self._resources.cpu_freq_mhz = freq.current if freq else 0.0

            mem = psutil.virtual_memory()
            self._resources.ram_total_gb = mem.total / (1024 ** 3)
            self._resources.ram_used_gb = mem.used / (1024 ** 3)
            self._resources.ram_percent = mem.percent

            disk = psutil.disk_usage("/")
            self._resources.disk_total_gb = disk.total / (1024 ** 3)
            self._resources.disk_used_gb = disk.used / (1024 ** 3)
            self._resources.disk_percent = disk.percent

            try:
                bat = psutil.sensors_battery()
                if bat:
                    self._resources.battery_percent = bat.percent
                    self._resources.battery_charging = bat.power_plugged
            except (AttributeError, Exception):
                pass

            self._resources.platform = platform.system()
            self._resources.hostname = platform.node()

            # Emit events on threshold changes
            self._check_events()

        except Exception as e:
            logger.debug("Environment collect error: %s", e)

    def _check_events(self):
        cpu_high = self._resources.cpu_percent > 80
        if cpu_high and not self._prev_cpu_high:
            self._bus.emit(EventType.CPU_HIGH, source="env", data={"cpu": self._resources.cpu_percent})
        elif not cpu_high and self._prev_cpu_high:
            self._bus.emit(EventType.CPU_NORMAL, source="env", data={"cpu": self._resources.cpu_percent})
        self._prev_cpu_high = cpu_high

        if self._resources.battery_percent >= 0:
            bat_low = self._resources.battery_percent < 20
            if bat_low and not self._prev_battery_low:
                self._bus.emit(EventType.BATTERY_LOW, source="env", data={"battery": self._resources.battery_percent})
            self._prev_battery_low = bat_low


# Global instance
environment_engine = EnvironmentEngine()

__all__ = ["EnvironmentEngine", "SystemResources", "environment_engine"]
