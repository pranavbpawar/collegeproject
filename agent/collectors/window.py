"""
NEF Agent — Application Usage Session Tracker
Replaces the simple window snapshot with full session tracking:
  - Detects foreground application changes
  - Records start_ts, end_ts, and duration_sec per session
  - Emits 'app_session_end' on app change and 'app_session_active' on heartbeat
  - Cross-platform: Windows (pywin32/psutil) and Linux (xdotool/Xlib)
"""

import platform
import subprocess
import threading
from datetime import datetime, timezone
from typing import Optional

# ── Module-level session state (thread-safe) ────────────────────────────────────
_lock = threading.Lock()
_current: dict = {
    "application": None,
    "window_title": None,
    "start_ts": None,
}
_completed_sessions: list = []


# ── Platform-specific window detection ────────────────────────────────────────

def _get_foreground_linux() -> tuple[str, str]:
    """Returns (app_name, window_title) on Linux via xdotool."""
    try:
        win_id = subprocess.check_output(
            ["xdotool", "getactivewindow"], stderr=subprocess.DEVNULL
        ).decode().strip()
        title = subprocess.check_output(
            ["xdotool", "getwindowname", win_id], stderr=subprocess.DEVNULL
        ).decode().strip()
        pid = subprocess.check_output(
            ["xdotool", "getwindowpid", win_id], stderr=subprocess.DEVNULL
        ).decode().strip()
        try:
            with open(f"/proc/{pid}/comm") as f:
                app = f.read().strip()
        except Exception:
            app = "unknown"
        return app, title
    except Exception:
        pass

    try:
        # Fallback: wmctrl
        active_hex = subprocess.check_output(
            ["xprop", "-root", "_NET_ACTIVE_WINDOW"], stderr=subprocess.DEVNULL
        ).decode().split()[-1]
        active_id = int(active_hex, 16)
        out = subprocess.check_output(
            ["wmctrl", "-lp"], stderr=subprocess.DEVNULL
        ).decode()
        for line in out.splitlines():
            parts = line.split(None, 4)
            if len(parts) >= 5 and int(parts[0], 16) == active_id:
                return "unknown", parts[4]
    except Exception:
        pass

    return "unknown", "unknown"


def _get_foreground_windows() -> tuple[str, str]:
    """Returns (app_name, window_title) on Windows via pywin32 + psutil."""
    try:
        import win32gui
        import win32process
        import psutil
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            app = psutil.Process(pid).name()
        except Exception:
            app = "unknown"
        return app, title
    except Exception:
        return "unknown", "unknown"


def _get_foreground() -> tuple[str, str]:
    if platform.system() == "Windows":
        return _get_foreground_windows()
    return _get_foreground_linux()


# ── Session tracking ───────────────────────────────────────────────────────────

def collect() -> dict:
    """
    Called every `window_poll_interval` seconds (default: 5s).

    Returns ONE of:
      - 'app_session_active'  : ongoing session update (same app still running)
      - 'app_session_end'     : completed session (app changed); a new session starts
    Any completed sessions are also available via get_completed_sessions().
    """
    global _current, _completed_sessions

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    app, title = _get_foreground()

    with _lock:
        if _current["application"] is None:
            # First call — initialize session
            _current = {"application": app, "window_title": title, "start_ts": now_iso}
            return {
                "type": "app_session_active",
                "application": app,
                "window_title": title,
                "started_at": now_iso,
                "duration_sec": 0,
                "collected_at": now_iso,
            }

        app_changed = (app != _current["application"])

        if app_changed:
            # Close the old session
            start = _current["start_ts"]
            try:
                from datetime import datetime as _dt
                duration = (
                    now - _dt.fromisoformat(start)
                ).total_seconds()
            except Exception:
                duration = 0.0

            completed = {
                "type": "app_session_end",
                "application": _current["application"],
                "window_title": _current["window_title"],
                "started_at": start,
                "ended_at": now_iso,
                "duration_sec": round(duration, 1),
                "collected_at": now_iso,
            }
            _completed_sessions.append(completed)

            # Start new session
            _current = {"application": app, "window_title": title, "start_ts": now_iso}
            return completed

        else:
            # Same application — return heartbeat with running duration
            try:
                duration = (
                    now - datetime.fromisoformat(_current["start_ts"])
                ).total_seconds()
            except Exception:
                duration = 0.0

            return {
                "type": "app_session_active",
                "application": app,
                "window_title": title,
                "started_at": _current["start_ts"],
                "duration_sec": round(duration, 1),
                "collected_at": now_iso,
            }


def get_completed_sessions() -> list:
    """
    Return and clear the list of fully completed app sessions.
    Called by the main loop to drain finished sessions into the upload buffer.
    """
    global _completed_sessions
    with _lock:
        sessions = list(_completed_sessions)
        _completed_sessions.clear()
    return sessions


def flush_current_session() -> Optional[dict]:
    """
    Force-close the current active session (e.g., on agent shutdown).
    Returns the completed session dict, or None if no session was active.
    """
    global _current
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    with _lock:
        if _current["application"] is None:
            return None
        start = _current["start_ts"]
        try:
            duration = (now - datetime.fromisoformat(start)).total_seconds()
        except Exception:
            duration = 0.0

        completed = {
            "type": "app_session_end",
            "application": _current["application"],
            "window_title": _current["window_title"],
            "started_at": start,
            "ended_at": now_iso,
            "duration_sec": round(duration, 1),
            "collected_at": now_iso,
            "reason": "agent_shutdown",
        }
        _current = {"application": None, "window_title": None, "start_ts": None}
    return completed
