"""
NEF Agent — Idle Time Collector
Measures how long since the user last moved mouse/typed.
Windows: GetLastInputInfo / Linux: xprintidle or X11
"""

import platform
import subprocess
from datetime import datetime


def _get_idle_seconds_linux() -> float:
    try:
        out = subprocess.check_output(
            ["xprintidle"], stderr=subprocess.DEVNULL
        ).decode().strip()
        return int(out) / 1000.0  # xprintidle returns milliseconds
    except Exception:
        pass

    try:
        # Fallback: read /proc/bus/input/devices and check timestamps
        import glob, os, time
        latest = 0
        for path in glob.glob("/sys/class/input/event*/device/"):
            try:
                t = os.path.getmtime(path)
                latest = max(latest, t)
            except Exception:
                pass
        if latest:
            return time.time() - latest
    except Exception:
        pass
    return -1


def _get_idle_seconds_windows() -> float:
    try:
        import ctypes
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(lii)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
        import ctypes
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return millis / 1000.0
    except Exception:
        return -1


def collect() -> dict:
    system = platform.system()
    if system == "Windows":
        idle_seconds = _get_idle_seconds_windows()
    else:
        idle_seconds = _get_idle_seconds_linux()

    return {
        "type": "idle",
        "idle_seconds": round(idle_seconds, 1),
        "is_idle": idle_seconds > 300,   # idle if no input for 5+ minutes
        "collected_at": datetime.utcnow().isoformat(),
    }
