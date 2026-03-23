"""
config.py – Application-wide constants and paths.
"""
import os
import sys
import platform

# ── Identity ────────────────────────────────────────────────────────────────
APP_NAME    = "ExecMonitor"
APP_VERSION = "1.0.0"
POLL_INTERVAL_SEC = 1.0          # stats refresh cadence

# ── Platform-aware data directory ───────────────────────────────────────────
_system = platform.system()
if _system == "Windows":
    _base = os.environ.get("APPDATA", os.path.expanduser("~"))
elif _system == "Darwin":
    _base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
else:                             # Linux / other
    _base = os.path.join(os.environ.get("XDG_DATA_HOME",
                                         os.path.join(os.path.expanduser("~"), ".local", "share")))

DATA_DIR   = os.path.join(_base, APP_NAME)
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
LOG_DIR    = os.path.join(DATA_DIR, "logs")
DB_PATH    = os.path.join(DATA_DIR, "monitor.db")

# ── Allowed executable magic bytes ──────────────────────────────────────────
MAGIC_ELF     = b"\x7fELF"
MAGIC_MZ      = b"MZ"
MAGIC_SHEBANG = b"#!"

# ── Ensure dirs exist ────────────────────────────────────────────────────────
for _d in (DATA_DIR, UPLOAD_DIR, LOG_DIR):
    os.makedirs(_d, exist_ok=True)
