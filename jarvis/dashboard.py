"""jarvis.dashboard

System monitoring dashboard for JARVIS.

Real-time monitoring of CPU, RAM, battery, disk, and network with voice alerts
when thresholds are exceeded. Runs in a background thread.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable

from jarvis import config

logger = logging.getLogger(__name__)

# Try to import psutil
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger.warning("psutil not available - system monitoring disabled")

# Try to import speedtest for network
try:
    import speedtest

    HAS_SPEEDTEST = True
except ImportError:
    HAS_SPEEDTEST = False

# Try to import for Windows-specific battery info
try:
    import ctypes
    from ctypes import wintypes

    HAS_WIN_BATTERY = True
except ImportError:
    HAS_WIN_BATTERY = False


@dataclass
class SystemStats:
    """Container for system statistics."""

    cpu_percent: float
    ram_percent: float
    ram_used_gb: float
    ram_total_gb: float
    disk_percent: float
    disk_free_gb: float
    battery_percent: float | None
    battery_plugged: bool | None
    network_down_mbps: float | None
    network_up_mbps: float | None
    boot_time: float | None


class SystemDashboard:
    """Background system monitoring with voice alerts."""

    def __init__(self, alert_callback: Callable[[str], None] | None = None) -> None:
        """Initialize dashboard.
        
        Args:
            alert_callback: Function to call with alert messages (e.g., TTS speak)
        """
        self.alert_callback = alert_callback
        self.monitoring = False
        self.monitor_thread: threading.Thread | None = None
        self.last_alert_time: dict[str, float] = {}
        self.alert_cooldown = 60  # seconds between same alert type

        # Alert thresholds
        self.cpu_threshold = config.CPU_ALERT_THRESHOLD
        self.ram_threshold = config.RAM_ALERT_THRESHOLD
        self.battery_low = config.BATTERY_LOW_THRESHOLD

        if not HAS_PSUTIL:
            logger.warning("Dashboard initialized but psutil not available")

    def start_monitoring(self) -> None:
        """Start background monitoring thread."""
        if not HAS_PSUTIL:
            logger.error("Cannot start monitoring - psutil not available")
            return

        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, name="JarvisDashboard", daemon=True
        )
        self.monitor_thread.start()
        logger.info("System monitoring started")

    def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
        logger.info("System monitoring stopped")

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self.monitoring:
            try:
                stats = self._get_stats()
                self._check_alerts(stats)
                time.sleep(config.DASHBOARD_UPDATE_INTERVAL)
            except Exception:
                logger.exception("Monitor loop error")
                time.sleep(5)

    def _get_stats(self) -> SystemStats:
        """Collect current system statistics."""
        if not HAS_PSUTIL:
            raise RuntimeError("psutil not available")

        # CPU - non-blocking (interval=None uses last call or 0.1s since import)
        cpu_percent = psutil.cpu_percent(interval=None)

        # RAM
        ram = psutil.virtual_memory()
        ram_percent = ram.percent
        ram_used_gb = ram.used / (1024**3)
        ram_total_gb = ram.total / (1024**3)

        # Disk
        disk = psutil.disk_usage("/")
        disk_percent = disk.percent
        disk_free_gb = disk.free / (1024**3)

        # Battery
        battery_percent = None
        battery_plugged = None
        if hasattr(psutil, "sensors_battery"):
            battery = psutil.sensors_battery()
            if battery:
                battery_percent = battery.percent
                battery_plugged = battery.power_plugged

        # Network (speed test is expensive, only run on demand)
        network_down_mbps = None
        network_up_mbps = None

        # Boot time
        boot_time = psutil.boot_time()

        return SystemStats(
            cpu_percent=cpu_percent,
            ram_percent=ram_percent,
            ram_used_gb=ram_used_gb,
            ram_total_gb=ram_total_gb,
            disk_percent=disk_percent,
            disk_free_gb=disk_free_gb,
            battery_percent=battery_percent,
            battery_plugged=battery_plugged,
            network_down_mbps=network_down_mbps,
            network_up_mbps=network_up_mbps,
            boot_time=boot_time,
        )

    def _check_alerts(self, stats: SystemStats) -> None:
        """Check if any alert conditions are met."""
        if not self.alert_callback:
            return

        now = time.time()

        # CPU alert
        if stats.cpu_percent > self.cpu_threshold:
            if self._can_alert("cpu"):
                self.alert_callback(
                    f"Warning: CPU usage is at {stats.cpu_percent:.0f} percent."
                )
                self.last_alert_time["cpu"] = now

        # RAM alert
        if stats.ram_percent > self.ram_threshold:
            if self._can_alert("ram"):
                self.alert_callback(
                    f"Warning: Memory usage is at {stats.ram_percent:.0f} percent."
                )
                self.last_alert_time["ram"] = now

        # Battery alert
        if stats.battery_percent is not None and not stats.battery_plugged:
            if stats.battery_percent < self.battery_low:
                if self._can_alert("battery"):
                    self.alert_callback(
                        f"Warning: Battery is at {stats.battery_percent:.0f} percent. Please plug in."
                    )
                    self.last_alert_time["battery"] = now

    def _can_alert(self, alert_type: str) -> bool:
        """Check if enough time has passed since last alert of this type."""
        last_time = self.last_alert_time.get(alert_type, 0)
        return (time.time() - last_time) > self.alert_cooldown

    def get_formatted_stats(self) -> str:
        """Get formatted system statistics for display/speech."""
        if not HAS_PSUTIL:
            return "System monitoring not available - psutil not installed."

        try:
            stats = self._get_stats()

            lines = [
                f"CPU: {stats.cpu_percent:.1f}%",
                f"RAM: {stats.ram_percent:.1f}% ({stats.ram_used_gb:.1f}GB / {stats.ram_total_gb:.1f}GB)",
                f"Disk: {stats.disk_percent:.1f}% used ({stats.disk_free_gb:.1f}GB free)",
            ]

            if stats.battery_percent is not None:
                power_status = "plugged in" if stats.battery_plugged else "on battery"
                lines.append(f"Battery: {stats.battery_percent:.0f}% ({power_status})")

            # Get running processes count
            process_count = len(psutil.pids())
            lines.append(f"Processes: {process_count}")

            return " | ".join(lines)

        except Exception as e:
            logger.exception("Failed to get stats")
            return f"Error getting system stats: {str(e)}"

    def get_quick_status(self) -> str:
        """Get a brief status for regular check-ins."""
        if not HAS_PSUTIL:
            return "Monitoring unavailable."

        try:
            stats = self._get_stats()
            issues = []

            if stats.cpu_percent > 80:
                issues.append(f"CPU high at {stats.cpu_percent:.0f}%")
            if stats.ram_percent > 80:
                issues.append(f"RAM high at {stats.ram_percent:.0f}%")
            if stats.battery_percent is not None and stats.battery_percent < 25 and not stats.battery_plugged:
                issues.append(f"Battery low at {stats.battery_percent:.0f}%")

            if issues:
                return "System alerts: " + ". ".join(issues)
            else:
                return f"All systems nominal. CPU {stats.cpu_percent:.0f}%, RAM {stats.ram_percent:.0f}%."

        except Exception:
            return "Unable to check system status."

    def run_speed_test(self) -> str:
        """Run network speed test (takes ~30 seconds)."""
        if not HAS_SPEEDTEST:
            return "Speed test requires speedtest-cli (pip install speedtest-cli)."

        try:
            st = speedtest.Speedtest()
            st.get_best_server()
            download_speed = st.download() / (1024**2)  # Convert to Mbps
            upload_speed = st.upload() / (1024**2)
            ping = st.results.ping

            return (
                f"Download: {download_speed:.1f} Mbps | "
                f"Upload: {upload_speed:.1f} Mbps | "
                f"Ping: {ping:.0f} ms"
            )
        except Exception as e:
            logger.exception("Speed test failed")
            return f"Speed test failed: {str(e)}"


# Global dashboard instance
dashboard = SystemDashboard()


def get_system_stats() -> str:
    """Tool function for LLM to call."""
    return dashboard.get_formatted_stats()


def get_quick_system_status() -> str:
    """Get brief status update."""
    return dashboard.get_quick_status()


def run_network_speed_test() -> str:
    """Run network speed test."""
    return dashboard.run_speed_test()


# Tool registry for dashboard functions
DASHBOARD_REGISTRY = {
    "get_system_stats": get_system_stats,
    "get_quick_system_status": get_quick_system_status,
    "run_network_speed_test": run_network_speed_test,
}
