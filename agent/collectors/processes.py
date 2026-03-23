"""
NEF Agent — Process Collector
Lists all running processes with name, PID, CPU%, RAM%, user.
Cross-platform via psutil.
"""

import psutil
from datetime import datetime


def collect() -> dict:
    processes = []
    for proc in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_percent", "status", "create_time"]):
        try:
            info = proc.info
            processes.append({
                "pid":        info["pid"],
                "name":       info["name"],
                "username":   info["username"],
                "cpu_pct":    round(info["cpu_percent"] or 0, 2),
                "ram_pct":    round(info["memory_percent"] or 0, 2),
                "status":     info["status"],
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Sort by CPU desc, take top 50 to keep payload size reasonable
    processes.sort(key=lambda x: x["cpu_pct"], reverse=True)

    return {
        "type": "processes",
        "count": len(processes),
        "top_processes": processes[:50],
        "collected_at": datetime.utcnow().isoformat(),
    }
