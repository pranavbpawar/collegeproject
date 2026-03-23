"""
NEF Agent — System Info + Metadata Collector
Collects hostname, OS, IP, MAC, CPU, RAM, disk on first run and periodically.
"""

import platform
import socket
import uuid
import psutil
import os
from datetime import datetime


def get_mac_address() -> str:
    mac = uuid.getnode()
    return ":".join(f"{(mac >> (8 * i)) & 0xFF:02x}" for i in range(5, -1, -1))


def get_primary_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "unknown"


def collect() -> dict:
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    cpu_freq = psutil.cpu_freq()

    return {
        "type": "sysinfo",
        "hostname": socket.gethostname(),
        "username": os.getlogin(),
        "os": platform.system(),
        "os_version": platform.version(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "cpu_model": platform.processor(),
        "cpu_cores": psutil.cpu_count(logical=True),
        "cpu_freq_mhz": round(cpu_freq.current, 1) if cpu_freq else None,
        "cpu_percent": psutil.cpu_percent(interval=1),
        "ram_total_gb": round(mem.total / 1024**3, 2),
        "ram_used_gb": round(mem.used / 1024**3, 2),
        "ram_percent": mem.percent,
        "disk_total_gb": round(disk.total / 1024**3, 2),
        "disk_used_gb": round(disk.used / 1024**3, 2),
        "disk_percent": disk.percent,
        "ip_address": get_primary_ip(),
        "mac_address": get_mac_address(),
        "collected_at": datetime.utcnow().isoformat(),
    }
