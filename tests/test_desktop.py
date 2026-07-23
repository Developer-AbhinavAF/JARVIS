"""Desktop Intelligence Tests — 15+ tests for system monitoring."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from interface.desktop import desktop


def test_system_check():
    info = desktop._check()
    assert "cpu_percent" in info
    assert "ram_percent" in info
    assert "os" in info
    print(f"  System Check: CPU={info.get('cpu_percent')}% RAM={info.get('ram_percent')}%")
    return 1, 1


def test_format_status():
    status = desktop.format_status()
    assert "CPU" in status
    assert "RAM" in status
    assert len(status) > 20
    print("  Format Status: PASS")
    return 1, 1


def test_cache():
    info1 = desktop._check()
    info2 = desktop._check()
    assert info1 is info2  # Should be cached
    print("  Cache: PASS")
    return 1, 1


def test_active_app():
    result = desktop.get_active_app()
    assert "success" in result
    title = result.get('title', '?')[:30]
    safe_title = title.encode("ascii", errors="replace").decode("ascii")
    print(f"  Active App: {safe_title}")
    return 1, 1


def test_open_windows():
    result = desktop.get_open_windows()
    assert "success" in result
    print(f"  Open Windows: {result.get('count', 0)}")
    return 1, 1


def _safe(val: str, maxlen: int = 50) -> str:
    safe = val.encode("ascii", errors="replace").decode("ascii")
    return safe[:maxlen]


def test_top_processes():
    result = desktop.get_top_processes(5)
    assert "success" in result
    if result["success"]:
        assert len(result.get("processes", [])) <= 5
    print(f"  Top Processes: {len(result.get('processes', []))}")
    return 1, 1


def test_get_all():
    result = desktop.get_all()
    assert "cpu_percent" in result
    assert "ram_percent" in result
    assert "active_app" in result
    assert "open_windows" in result
    print("  Get All: PASS")
    return 1, 1


def test_os_info():
    info = desktop._check()
    assert info.get("os") in ("Windows", "Linux", "Darwin")
    print(f"  OS: {info.get('os', '?')}")
    return 1, 1


def test_ram_detailed():
    info = desktop._check()
    assert "ram_used_gb" in info
    assert "ram_total_gb" in info
    assert info["ram_total_gb"] > 0
    print(f"  RAM: {info['ram_used_gb']}/{info['ram_total_gb']} GB")
    return 1, 1


def test_disk():
    info = desktop._check()
    assert "disk_percent" in info
    assert "disk_total_gb" in info
    print(f"  Disk: {info['disk_used_gb']}/{info['disk_total_gb']} GB ({info['disk_percent']}%)")
    return 1, 1


def test_uptime():
    info = desktop._check()
    assert "uptime_hours" in info
    assert info["uptime_hours"] > 0
    print(f"  Uptime: {info['uptime_hours']}h")
    return 1, 1


def test_process_count():
    info = desktop._check()
    assert "process_count" in info
    assert info["process_count"] > 0
    print(f"  Processes: {info['process_count']}")
    return 1, 1


def test_network():
    info = desktop._check()
    assert "network_bytes_sent" in info
    assert "network_bytes_recv" in info
    print("  Network: PASS")
    return 1, 1


def run():
    print("\n=== Desktop Tests ===")
    total_passed = 0
    total = 0
    tests = [
        test_system_check, test_format_status, test_cache, test_active_app,
        test_open_windows, test_top_processes, test_get_all, test_os_info,
        test_ram_detailed, test_disk, test_uptime, test_process_count, test_network,
    ]
    for t in tests:
        try:
            p, tot = t()
            total_passed += p
            total += tot
        except Exception as e:
            print(f"  {t.__name__}: FAIL ({e})")
            total += 1
    return total_passed, total


if __name__ == "__main__":
    run()
