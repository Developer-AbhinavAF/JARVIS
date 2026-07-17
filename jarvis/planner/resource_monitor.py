"""Resource Monitor — System-aware planning.

Before execution, analyze:
- CPU Usage
- RAM Usage
- GPU Usage
- Internet Speed
- Battery
- Disk Space
- API Limits
- Running Applications

Avoid heavy workloads when the system is already busy.
"""

from __future__ import annotations

import os
import time
import logging
import subprocess
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# SYSTEM STATE
# ════════════════════════════════════════════════════════════════════

@dataclass
class SystemState:
    """Current system resource state."""
    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    ram_available_mb: float = 0.0
    disk_percent: float = 0.0
    disk_free_gb: float = 0.0
    battery_percent: float = 100.0
    battery_charging: bool = True
    internet_available: bool = True
    internet_latency_ms: float = 0.0
    gpu_available: bool = False
    gpu_percent: float = 0.0

    # Derived
    overall_load: float = 0.0        # 0-1 composite
    can_heavy_work: bool = True      # Enough resources for heavy tasks
    can_background: bool = True      # Enough for background tasks
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "cpu": round(self.cpu_percent, 1),
            "ram": round(self.ram_percent, 1),
            "ram_available_mb": round(self.ram_available_mb, 0),
            "disk_free_gb": round(self.disk_free_gb, 1),
            "battery": round(self.battery_percent, 0),
            "charging": self.battery_charging,
            "internet": self.internet_available,
            "internet_latency_ms": round(self.internet_latency_ms, 1),
            "overall_load": round(self.overall_load, 2),
            "can_heavy_work": self.can_heavy_work,
            "timestamp": self.timestamp,
        }


# ════════════════════════════════════════════════════════════════════
# RESOURCE MONITOR
# ════════════════════════════════════════════════════════════════════

class ResourceMonitor:
    """Monitors system resources for planning decisions.

    Provides real-time system state to the planning engine
    so it can avoid overloading the system.
    """

    def __init__(self) -> None:
        self._last_state: SystemState | None = None
        self._last_check: float = 0.0
        self._check_interval: float = 5.0  # Minimum seconds between checks
        self._history: list[SystemState] = []

    def get_state(self, force: bool = False) -> SystemState:
        """Get current system state (cached for 5s)."""
        now = time.time()
        if not force and self._last_state and (now - self._last_check) < self._check_interval:
            return self._last_state

        state = SystemState(timestamp=now)

        # CPU
        state.cpu_percent = self._get_cpu_usage()

        # RAM
        ram = self._get_ram_info()
        state.ram_percent = ram["percent"]
        state.ram_available_mb = ram["available_mb"]

        # Disk
        disk = self._get_disk_info()
        state.disk_percent = disk["percent"]
        state.disk_free_gb = disk["free_gb"]

        # Battery
        battery = self._get_battery_info()
        state.battery_percent = battery["percent"]
        state.battery_charging = battery["charging"]

        # Internet
        state.internet_available = self._check_internet()
        state.internet_latency_ms = self._get_latency()

        # Overall load
        state.overall_load = self._calculate_overall_load(state)
        state.can_heavy_work = state.overall_load < 0.7 and state.ram_percent < 85
        state.can_background = state.overall_load < 0.85

        self._last_state = state
        self._last_check = now
        self._history.append(state)
        if len(self._history) > 100:
            self._history = self._history[-50:]

        return state

    def can_execute(self, estimated_cpu: float = 0.1, estimated_ram_mb: float = 100) -> bool:
        """Check if system can handle a task with given resource needs."""
        state = self.get_state()
        if state.cpu_percent + estimated_cpu * 100 > 95:
            return False
        if state.ram_available_mb < estimated_ram_mb:
            return False
        if state.battery_percent < 10 and not state.battery_charging:
            return False
        return True

    def should_defer(self) -> bool:
        """Check if system is too busy and tasks should be deferred."""
        state = self.get_state()
        return state.overall_load > 0.9 or state.ram_percent > 90

    def get_recommendations(self) -> list[str]:
        """Get planning recommendations based on current state."""
        state = self.get_state()
        recs = []
        if state.cpu_percent > 80:
            recs.append("High CPU — prefer quick tasks, defer heavy work")
        if state.ram_percent > 80:
            recs.append("Low RAM — avoid parallel heavy tasks")
        if state.battery_percent < 20 and not state.battery_charging:
            recs.append("Low battery — minimize background tasks")
        if not state.internet_available:
            recs.append("No internet — use offline strategies only")
        if state.disk_free_gb < 1:
            recs.append("Low disk space — avoid downloads")
        return recs

    # ── Platform-Specific Methods ──

    def _get_cpu_usage(self) -> float:
        try:
            if os.name == "nt":
                # Windows
                result = subprocess.run(
                    ["powershell", "-Command", "(Get-CimInstance Win32_Processor).LoadPercentage"],
                    capture_output=True, text=True, timeout=5,
                )
                return float(result.stdout.strip())
            else:
                # Unix
                with open("/proc/stat") as f:
                    line = f.readline()
                parts = line.split()
                idle = int(parts[4])
                total = sum(int(p) for p in parts[1:])
                return min(100.0, max(0.0, (1 - idle / max(total, 1)) * 100))
        except Exception:
            return 0.0

    @staticmethod
    def _get_ram_info() -> dict[str, float]:
        try:
            if os.name == "nt":
                result = subprocess.run(
                    ["powershell", "-Command",
                     "$os=Get-CimInstance Win32_OperatingSystem; "
                     "Write-Host ([math]::Round(($os.TotalVisibleMemorySize-$os.FreePhysicalMemory)/$os.TotalVisibleMemorySize*100,1)); "
                     "Write-Host ([math]::Round($os.FreePhysicalMemory/1024,0))"],
                    capture_output=True, text=True, timeout=5,
                )
                lines = result.stdout.strip().split("\n")
                return {"percent": float(lines[0]), "available_mb": float(lines[1]) if len(lines) > 1 else 0}
        except Exception:
            pass
        return {"percent": 0.0, "available_mb": 0.0}

    @staticmethod
    def _get_disk_info() -> dict[str, float]:
        try:
            if os.name == "nt":
                result = subprocess.run(
                    ["powershell", "-Command",
                     "$d=Get-CimInstance Win32_LogicalDisk -Filter \"DeviceID='C:'\"; "
                     "Write-Host ([math]::Round((1-$d.FreeSpace/$d.Size)*100,1)); "
                     "Write-Host ([math]::Round($d.FreeSpace/1GB,1))"],
                    capture_output=True, text=True, timeout=5,
                )
                lines = result.stdout.strip().split("\n")
                return {"percent": float(lines[0]), "free_gb": float(lines[1]) if len(lines) > 1 else 0}
        except Exception:
            pass
        return {"percent": 0.0, "free_gb": 0.0}

    @staticmethod
    def _get_battery_info() -> dict[str, Any]:
        try:
            if os.name == "nt":
                result = subprocess.run(
                    ["powershell", "-Command",
                     "$b=Get-CimInstance Win32_Battery; "
                     "if($b) { Write-Host $b.EstimatedChargeRemaining; Write-Host ($b.BatteryStatus -eq 2) } "
                     "else { Write-Host 100; Write-Host True }"],
                    capture_output=True, text=True, timeout=5,
                )
                lines = result.stdout.strip().split("\n")
                return {"percent": float(lines[0]), "charging": lines[1].strip().lower() == "true" if len(lines) > 1 else True}
        except Exception:
            pass
        return {"percent": 100.0, "charging": True}

    @staticmethod
    def _check_internet() -> bool:
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Test-Connection -ComputerName 8.8.8.8 -Count 1 -Quiet"],
                capture_output=True, text=True, timeout=5,
            )
            return "true" in result.stdout.lower()
        except Exception:
            return True  # Assume available if check fails

    @staticmethod
    def _get_latency() -> float:
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "(Measure-Command { Test-Connection -ComputerName 8.8.8.8 -Count 1 }).TotalMilliseconds"],
                capture_output=True, text=True, timeout=5,
            )
            return float(result.stdout.strip())
        except Exception:
            return 0.0

    @staticmethod
    def _calculate_overall_load(state: SystemState) -> float:
        """Calculate composite load score (0-1)."""
        cpu = state.cpu_percent / 100
        ram = state.ram_percent / 100
        disk = state.disk_percent / 100
        battery_penalty = 0.0 if state.battery_charging else max(0, (100 - state.battery_percent) / 200)
        return min(1.0, (cpu * 0.4 + ram * 0.3 + disk * 0.1 + battery_penalty * 0.2))

    def get_stats(self) -> dict[str, Any]:
        state = self.get_state()
        return {
            "overall_load": round(state.overall_load, 2),
            "can_heavy_work": state.can_heavy_work,
            "checks_performed": len(self._history),
        }
