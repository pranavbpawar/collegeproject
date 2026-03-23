"""
NEF Agent — System Tray Transparency Module
Provides an optional system tray icon so employees can see monitoring status.

Features:
  - 🟢 "NEF Monitoring Active" when connected
  - 🟡 "NEF — Reconnecting..." when offline / circuit open
  - 🔴 "NEF — Error" on persistent failure
  - Right-click → "View Activity Summary" opens ~/.nef/status.log

Requires: pystray, Pillow
Falls back silently if no display or pystray is unavailable.
"""

import logging
import os
import platform
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# Paths
_STATUS_LOG = Path.home() / ".nef" / "status.log"
_MAX_LOG_LINES = 500

# ── Status colours ─────────────────────────────────────────────────────────────
_COLORS = {
    "connected":    (34, 197, 94),   # green
    "reconnecting": (234, 179,  8),  # yellow
    "error":        (239, 68,  68),  # red
    "idle":         (100, 116, 139), # slate
}


def _make_icon_image(color: tuple, size: int = 64):
    """Generate a simple filled-circle icon as a PIL Image."""
    try:
        from PIL import Image, ImageDraw
        img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        pad  = size // 8
        draw.ellipse([pad, pad, size - pad, size - pad], fill=(*color, 255))
        return img
    except Exception:
        return None


class TrayIcon:
    """
    Manages the system tray icon lifecycle.
    All tray operations happen in a dedicated daemon thread.
    """

    def __init__(self, get_status_fn: Optional[Callable[[], dict]] = None):
        """
        Args:
            get_status_fn: callable that returns the uploader's status() dict.
                           Used to auto-update the icon state.
        """
        self._get_status = get_status_fn
        self._icon       = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._current_state = "idle"
        self._available = False

    def start(self) -> bool:
        """Start the tray icon in a background thread. Returns True if started."""
        if not self._can_use_tray():
            logger.debug("[tray] No display or pystray unavailable — tray disabled")
            return False

        self._thread = threading.Thread(
            target=self._run, daemon=True, name="nef-tray"
        )
        self._thread.start()
        return True

    def stop(self):
        """Stop the tray icon."""
        self._stop_event.set()
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass

    def update(self, state: str):
        """
        Update tray icon state.
        state: "connected" | "reconnecting" | "error" | "idle"
        """
        if state == self._current_state:
            return
        self._current_state = state
        if self._icon:
            try:
                color = _COLORS.get(state, _COLORS["idle"])
                img   = _make_icon_image(color)
                if img:
                    self._icon.icon  = img
                    self._icon.title = self._make_title(state)
            except Exception as e:
                logger.debug(f"[tray] Icon update failed: {e}")

    def _make_title(self, state: str) -> str:
        titles = {
            "connected":    "NEF — Monitoring Active",
            "reconnecting": "NEF — Reconnecting...",
            "error":        "NEF — Connection Error",
            "idle":         "NEF — Starting...",
        }
        return titles.get(state, "NEF Agent")

    def _make_menu(self):
        """Build the right-click context menu."""
        try:
            import pystray
            return pystray.Menu(
                pystray.MenuItem("NEF Monitoring Agent", lambda: None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("View Activity Summary", self._open_log),
                pystray.MenuItem("About", self._show_about),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit Agent", self._on_quit),
            )
        except Exception:
            return None

    def _open_log(self, icon, item):
        """Open status.log in the default text viewer."""
        try:
            path = str(_STATUS_LOG)
            system = platform.system()
            if system == "Windows":
                os.startfile(path)
            elif system == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            logger.debug(f"[tray] Could not open log: {e}")

    def _show_about(self, icon, item):
        logger.info("[tray] NEF Agent v2.0 — Trust-Based Monitoring")

    def _on_quit(self, icon, item):
        """Gracefully stop the tray (agent daemon continues)."""
        logger.info("[tray] Tray icon dismissed by user")
        self.stop()

    def _run(self):
        """Main tray thread entry point."""
        try:
            import pystray
            color = _COLORS["idle"]
            img   = _make_icon_image(color)
            if img is None:
                return

            self._icon = pystray.Icon(
                name="nef-agent",
                icon=img,
                title=self._make_title("idle"),
                menu=self._make_menu(),
            )
            self._available = True

            # Start auto-update side thread
            updater = threading.Thread(
                target=self._auto_update_loop, daemon=True, name="nef-tray-updater"
            )
            updater.start()

            self._icon.run()   # Blocks until icon.stop() is called
        except Exception as e:
            logger.debug(f"[tray] Tray icon error: {e}")

    def _auto_update_loop(self):
        """Poll uploader status every 15s and update icon color."""
        while not self._stop_event.wait(15):
            try:
                if self._get_status is None:
                    continue
                status = self._get_status()
                if status.get("circuit_open"):
                    self.update("error")
                elif status.get("consecutive_failures", 0) > 2:
                    self.update("reconnecting")
                elif status.get("last_upload_ok") is not None:
                    self.update("connected")
                else:
                    self.update("idle")
            except Exception:
                pass

    @staticmethod
    def _can_use_tray() -> bool:
        """Return True if system tray is likely available."""
        try:
            import pystray    # noqa: F401
            from PIL import Image  # noqa: F401
        except ImportError:
            return False
        system = platform.system()
        if system == "Linux":
            return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
        return True  # Windows + macOS always OK


# ── Status log writer ──────────────────────────────────────────────────────────

def write_status(message: str):
    """
    Append a timestamped status line to ~/.nef/status.log.
    Rotates log when it exceeds _MAX_LOG_LINES.
    """
    try:
        _STATUS_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        line = f"[{ts}] {message}\n"

        # Read existing lines for rotation
        existing: list[str] = []
        if _STATUS_LOG.exists():
            try:
                existing = _STATUS_LOG.read_text(encoding="utf-8").splitlines(keepends=True)
            except Exception:
                pass

        # Rotate: keep last (_MAX_LOG_LINES - 1) lines
        if len(existing) >= _MAX_LOG_LINES:
            existing = existing[-((_MAX_LOG_LINES - 1)):]

        existing.append(line)
        _STATUS_LOG.write_text("".join(existing), encoding="utf-8")
    except Exception as e:
        logger.debug(f"[tray] Status log write failed: {e}")


def update_status_log(uploader_status: dict, server_url: str):
    """Write structured status lines from uploader state."""
    state = "connected" if uploader_status.get("last_upload_ok") else "disconnected"
    if uploader_status.get("circuit_open"):
        state = "circuit_open"

    write_status(f"STATUS={state} server={server_url}")
    write_status(
        f"UPLOAD last_ok={uploader_status.get('last_upload_ok')} "
        f"errors={uploader_status.get('consecutive_failures', 0)} "
        f"total={uploader_status.get('total_uploaded', 0)}"
    )
    write_status(f"BUFFER pending={uploader_status.get('pending', 0)} events")
