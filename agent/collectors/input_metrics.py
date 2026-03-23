"""
NEF Agent — Privacy-Safe Input Metrics Collector
Tracks keyboard and mouse ACTIVITY RATES only — never records key content.

What IS captured:
  - keystrokes_per_min   : total key-down events in rolling 60s window
  - mouse_clicks_per_min : total mouse click events
  - mouse_moves_per_min  : mouse movement event frequency
  - is_active            : True if any input in last 60s

What is NEVER captured:
  - Which keys were pressed (no key values, no characters)
  - Clipboard content
  - Passwords or sensitive fields
  - Mouse position (only movement delta count)

Implementation uses pynput background listeners.
Falls back gracefully to -1 values in headless/server environments.
"""

import logging
import platform
import threading
import time
from collections import deque
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── Rolling counters ────────────────────────────────────────────────────────────
_WINDOW_SEC = 60  # rolling window duration

_key_times:   deque = deque()   # timestamps of key events
_click_times: deque = deque()   # timestamps of mouse click events
_move_times:  deque = deque()   # timestamps of mouse move events
_lock = threading.Lock()
_listeners_started = False
_listeners_available = False


# ── pynput listeners ────────────────────────────────────────────────────────────

def _on_press(_key):
    """Called on every key press — records timestamp only, no key value."""
    with _lock:
        _key_times.append(time.monotonic())


def _on_click(_x, _y, _button, pressed):
    """Called on mouse click — records timestamp only."""
    if pressed:
        with _lock:
            _click_times.append(time.monotonic())


def _on_move(_x, _y):
    """Called on mouse move — samples at most once per 100ms to avoid flooding."""
    now = time.monotonic()
    with _lock:
        if not _move_times or (now - _move_times[-1]) > 0.1:
            _move_times.append(now)


def _start_listeners():
    """Start pynput listeners in daemon threads. Fails silently in headless env."""
    global _listeners_started, _listeners_available
    if _listeners_started:
        return
    _listeners_started = True

    try:
        from pynput import keyboard, mouse

        kb_listener = keyboard.Listener(on_press=_on_press, suppress=False)
        ms_listener = mouse.Listener(on_click=_on_click, on_move=_on_move)
        kb_listener.daemon = True
        ms_listener.daemon = True
        kb_listener.start()
        ms_listener.start()
        _listeners_available = True
        logger.debug("[input_metrics] pynput listeners started")
    except Exception as e:
        # Headless environments (SSH, server) won't have a display
        logger.debug(f"[input_metrics] pynput unavailable: {e} — metrics will be -1")
        _listeners_available = False


# ── Rolling window helper ───────────────────────────────────────────────────────

def _count_in_window(timestamps: deque, window_sec: float) -> int:
    """Count and prune events within the rolling window."""
    cutoff = time.monotonic() - window_sec
    while timestamps and timestamps[0] < cutoff:
        timestamps.popleft()
    return len(timestamps)


# ── Public API ─────────────────────────────────────────────────────────────────

def start():
    """Explicitly start the input listeners (idempotent)."""
    _start_listeners()


def collect() -> dict:
    """
    Return input activity rates for the last WINDOW_SEC seconds.
    Safe to call from any thread.
    """
    # Lazy start on first collect
    if not _listeners_started:
        _start_listeners()

    now_iso = datetime.now(timezone.utc).isoformat()

    if not _listeners_available:
        # Headless / no display — return sentinel -1 values
        return {
            "type":                 "input_metrics",
            "keystrokes_per_min":   -1,
            "mouse_clicks_per_min": -1,
            "mouse_moves_per_min":  -1,
            "is_active":            False,
            "window_seconds":       _WINDOW_SEC,
            "available":            False,
            "collected_at":         now_iso,
        }

    with _lock:
        keys   = _count_in_window(_key_times,   _WINDOW_SEC)
        clicks = _count_in_window(_click_times, _WINDOW_SEC)
        moves  = _count_in_window(_move_times,  _WINDOW_SEC)

    # Normalise to per-minute
    scale = 60.0 / _WINDOW_SEC
    kpm = round(keys   * scale)
    cpm = round(clicks * scale)
    mpm = round(moves  * scale)

    is_active = (keys + clicks + moves) > 0

    return {
        "type":                 "input_metrics",
        "keystrokes_per_min":   kpm,
        "mouse_clicks_per_min": cpm,
        "mouse_moves_per_min":  mpm,
        "is_active":            is_active,
        "window_seconds":       _WINDOW_SEC,
        "available":            True,
        "collected_at":         now_iso,
    }
