"""
NEF Agent — File Activity Collector
Watches for file open/create/modify/delete events using watchdog.
Monitors home directory and desktop.
"""

import os
import platform
import threading
from datetime import datetime
from pathlib import Path
from collections import deque

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    _WATCHDOG_AVAILABLE = True
except ImportError:
    _WATCHDOG_AVAILABLE = False

    # Stub so class _Handler definition below never hits a NameError
    class FileSystemEventHandler:  # type: ignore
        def dispatch(self, event):
            pass

# Circular buffer — stores last 200 file events
_event_buffer: deque = deque(maxlen=200)
_observer = None
_lock = threading.Lock()

# File extensions to ignore (noise reduction)
IGNORE_EXTENSIONS = {
    ".tmp", ".temp", ".log", ".lock", ".swp", ".swo",
    ".pyc", ".pyo", "__pycache__",
}

IGNORE_PATTERNS = {
    ".git", "__pycache__", ".nef", "node_modules",
}


def _should_ignore(path: str) -> bool:
    p = Path(path)
    if p.suffix.lower() in IGNORE_EXTENSIONS:
        return True
    for part in p.parts:
        if part in IGNORE_PATTERNS:
            return True
    return False


class _Handler(FileSystemEventHandler):
    def _record(self, event_type: str, path: str):
        if _should_ignore(path):
            return
        with _lock:
            _event_buffer.append({
                "event": event_type,
                "path": path,
                "timestamp": datetime.utcnow().isoformat(),
            })

    def on_created(self, event):
        if not event.is_directory:
            self._record("created", event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._record("modified", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._record("deleted", event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._record("moved", f"{event.src_path} → {event.dest_path}")


def _get_watch_dirs() -> list:
    home = str(Path.home())
    dirs = [home]
    system = platform.system()

    if system == "Windows":
        desktop = os.path.join(os.environ.get("USERPROFILE", home), "Desktop")
        docs    = os.path.join(os.environ.get("USERPROFILE", home), "Documents")
        downloads = os.path.join(os.environ.get("USERPROFILE", home), "Downloads")
    else:
        desktop   = os.path.join(home, "Desktop")
        docs      = os.path.join(home, "Documents")
        downloads = os.path.join(home, "Downloads")

    for d in [desktop, docs, downloads]:
        if os.path.exists(d) and d not in dirs:
            dirs.append(d)
    return dirs


def start_watching():
    """Start background file watcher. Call once at agent startup."""
    global _observer
    if not _WATCHDOG_AVAILABLE or _observer is not None:
        return
    handler = _Handler()
    _observer = Observer()
    for watch_dir in _get_watch_dirs():
        try:
            _observer.schedule(handler, watch_dir, recursive=True)
        except Exception:
            pass
    _observer.start()


def stop_watching():
    global _observer
    if _observer:
        _observer.stop()
        _observer.join()
        _observer = None


def collect() -> dict:
    """Drain the event buffer and return recent file events."""
    with _lock:
        events = list(_event_buffer)
        _event_buffer.clear()

    return {
        "type": "file_activity",
        "events": events,
        "count": len(events),
        "collected_at": datetime.utcnow().isoformat(),
    }
