"""desktop — Desktop intelligence and system monitoring.

Active app, open windows, CPU, RAM, GPU, battery, network, processes.
"""

from __future__ import annotations

import os
import time
import logging
import platform
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

_CACHE_TTL = float(os.getenv("DESKTOP_CACHE_TTL", "2.0"))
_PROCESS_LIMIT = int(os.getenv("DESKTOP_PROCESS_LIMIT", "10"))


class DesktopMonitor:
    def __init__(self) -> None:
        self._last_check: dict[str, Any] = {}
        self._check_time = 0.0
        self._cache_ttl = _CACHE_TTL

    def _check(self) -> dict[str, Any]:
        now = time.time()
        if now - self._check_time < self._cache_ttl and self._last_check:
            return self._last_check

        info: dict[str, Any] = {}
        try:
            import psutil
            info["cpu_percent"] = psutil.cpu_percent(interval=0.3)
            info["cpu_count"] = psutil.cpu_count()
            info["cpu_freq"] = psutil.cpu_freq().current if psutil.cpu_freq() else 0

            mem = psutil.virtual_memory()
            info["ram_percent"] = mem.percent
            info["ram_used_gb"] = round(mem.used / (1024**3), 1)
            info["ram_total_gb"] = round(mem.total / (1024**3), 1)
            info["ram_available_gb"] = round(mem.available / (1024**3), 1)

            disk = psutil.disk_usage('/')
            info["disk_percent"] = disk.percent
            info["disk_used_gb"] = round(disk.used / (1024**3), 1)
            info["disk_total_gb"] = round(disk.total / (1024**3), 1)
            info["disk_free_gb"] = round(disk.free / (1024**3), 1)

            bat = psutil.sensors_battery()
            if bat:
                info["battery_percent"] = bat.percent
                info["battery_charging"] = bat.power_plugged
                info["battery_remaining_sec"] = bat.secsleft if bat.secsleft > 0 else 0

            net = psutil.net_io_counters()
            info["network_bytes_sent"] = net.bytes_sent
            info["network_bytes_recv"] = net.bytes_recv

            boot_time = datetime.fromtimestamp(psutil.boot_time())
            info["boot_time"] = boot_time.isoformat()
            info["uptime_hours"] = round((datetime.now() - boot_time).total_seconds() / 3600, 1)

            info["process_count"] = len(psutil.pids())
            info["total_processes"] = len(list(psutil.process_iter()))

            try:
                info["load_avg"] = psutil.getloadavg()
            except AttributeError:
                pass
        except ImportError:
            info["cpu_percent"] = 0
            info["ram_percent"] = 0

        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                g = gpus[0]
                info["gpu_name"] = g.name
                info["gpu_percent"] = g.load * 100
                info["gpu_memory_used_mb"] = g.memoryUsed
                info["gpu_memory_total_mb"] = g.memoryTotal
                info["gpu_temp_c"] = g.temperature
        except (ImportError, Exception):
            pass

        info["os"] = platform.system()
        info["os_version"] = platform.version()
        info["machine"] = platform.machine()
        info["hostname"] = platform.node()

        info["timestamp"] = datetime.now().isoformat()

        self._last_check = info
        self._check_time = now
        return info

    def get_active_app(self) -> dict[str, Any]:
        try:
            import pygetwindow as gw
            active = gw.getActiveWindow()
            if active:
                return {"success": True, "title": active.title, "app_name": active.title}
        except ImportError:
            pass
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            return {"success": True, "title": title, "app_name": title}
        except ImportError:
            pass
        return {"success": False, "error": "Cannot detect active window"}

    def get_open_windows(self) -> dict[str, Any]:
        windows = []
        try:
            import pygetwindow as gw
            for w in gw.getAllWindows():
                if w.title.strip():
                    windows.append({"title": w.title, "visible": w.visible, "is_active": w.isActive})
            return {"success": True, "windows": windows[:50], "count": len(windows)}
        except ImportError:
            pass
        try:
            import win32gui

            def enum_windows(hwnd, results):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title.strip():
                        results.append({"title": title, "hwnd": hwnd})
            results = []
            win32gui.EnumWindows(enum_windows, results)
            return {"success": True, "windows": results[:50], "count": len(results)}
        except ImportError:
            pass
        return {"success": False, "error": "Cannot enumerate windows"}

    def get_top_processes(self, limit: int | None = None) -> dict[str, Any]:
        limit = _PROCESS_LIMIT if limit is None else limit
        try:
            import psutil
            processes = []
            for proc in sorted(psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent']), key=lambda p: p.info.get('memory_percent', 0) or 0, reverse=True)[:limit]:
                try:
                    processes.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "memory_percent": round(proc.info.get('memory_percent', 0) or 0, 1),
                        "cpu_percent": round(proc.info.get('cpu_percent', 0) or 0, 1),
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return {"success": True, "processes": processes}
        except ImportError:
            return {"success": False, "error": "psutil not available"}

    def get_all(self) -> dict[str, Any]:
        info = self._check()
        info["active_app"] = self.get_active_app()
        info["open_windows"] = self.get_open_windows()
        info["top_processes"] = self.get_top_processes()
        return info

    def format_status(self) -> str:
        info = self._check()
        lines = [f"CPU: {info.get('cpu_percent', '?')}% | RAM: {info.get('ram_percent', '?')}% ({info.get('ram_used_gb', '?')}/{info.get('ram_total_gb', '?')} GB)"]
        if "gpu_percent" in info:
            lines.append(f"GPU: {info['gpu_name']} @ {info['gpu_percent']:.0f}% ({info['gpu_memory_used_mb']:.0f}/{info['gpu_memory_total_mb']:.0f} MB)")
        if "battery_percent" in info:
            charging = "(charging)" if info.get("battery_charging") else "(battery)"
            lines.append(f"Battery: {info['battery_percent']}% {charging}")
        lines.append(f"Disk: {info.get('disk_percent', '?')}% ({info.get('disk_used_gb', '?')}/{info.get('disk_total_gb', '?')} GB)")
        lines.append(f"Processes: {info.get('process_count', '?')}")
        lines.append(f"Uptime: {info.get('uptime_hours', '?')}h")
        lines.append(f"OS: {info.get('os', '?')} {info.get('os_version', '?')[:10]}")
        return "\n".join(lines)


desktop = DesktopMonitor()
