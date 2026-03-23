"""
NEF Agent — Extended Configuration
Reads/writes ~/.nef/config.json
Supports environment variable overrides so VMs can be configured
without editing config.json manually:
  - NEF_SERVER_URL → server_url
  - NEF_UPLOAD_INTERVAL → upload_interval
  - NEF_AGENT_ID → agent_id
  - NEF_API_KEY → api_key
"""

import json
import os
import platform
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
CONFIG_DIR  = Path.home() / ".nef"
CONFIG_FILE = CONFIG_DIR / "config.json"
BUFFER_DB   = CONFIG_DIR / "buffer.db"
STATUS_LOG  = CONFIG_DIR / "status.log"
CERT_DIR    = CONFIG_DIR / "certs"


def get_default_config() -> dict:
    return {
        # ── Server connection ──────────────────────────────────────────────────
        "server_url":     "",
        "agent_id":       None,
        "api_key":        None,

        # ── Authentication ─────────────────────────────────────────────────────
        "cert_path":      str(CERT_DIR / "nef.crt"),   # mTLS client cert
        "key_path":       str(CERT_DIR / "nef.key"),   # mTLS private key
        "ca_cert_path":   str(CERT_DIR / "ca.crt"),    # backend CA for pinning
        "tls_verify":     True,             # True = system CAs, str = custom CA path

        # ── JWT cache (written by auth.py at runtime) ─────────────────────────
        "jwt_token":      None,
        "jwt_expires_at": None,
        "jwt_refresh":    None,

        # ── Intervals (seconds) ───────────────────────────────────────────────
        "heartbeat_interval":     60,
        "upload_interval":        10,       # flush every 10s (configurable)
        "screenshot_interval":    300,
        "website_flush_interval": 300,      # aggregate DNS every 5 min
        "sysinfo_interval":       600,
        "input_metrics_interval": 60,
        "window_poll_interval":   5,        # session tracking resolution

        # ── Collection toggles ────────────────────────────────────────────────
        "collect_screenshots":    True,
        "collect_files":          True,
        "collect_browser_history": True,
        "collect_input_metrics":  True,
        "collect_usb":            True,

        # ── DNS / Website monitoring ──────────────────────────────────────────
        # "packet"  — real-time Scapy sniffer (needs elevated or CAP_NET_RAW)
        # "cache"   — DNS cache snapshot (ipconfig/resolvectl)
        # "browser" — browser SQLite history only
        "dns_capture_method":     "cache",  # default: safest, no elevated needed

        # ── Offline buffer ─────────────────────────────────────────────────────
        "max_buffer_events":      10000,    # cap to prevent disk exhaustion
        "batch_size":             50,       # events per POST

        # ── Transparency ──────────────────────────────────────────────────────
        "enable_tray_icon":       True,     # False in headless/server mode
    }


def _apply_env_overrides(cfg: dict) -> dict:
    """
    Allow environment variables to override config.json values.
    This is the recommended way to configure agents on VMs — set the env vars
    in the task scheduler / systemd service definition instead of editing files.

    LOCAL:  set NEF_SERVER_URL=http://192.168.1.100:8000
    PROD:   set NEF_SERVER_URL=https://your-backend.onrender.com
    """
    overrides = {
        "server_url":          os.environ.get("NEF_SERVER_URL",          ""),
        "agent_id":            os.environ.get("NEF_AGENT_ID",            ""),
        "api_key":             os.environ.get("NEF_API_KEY",             ""),
        "upload_interval":     os.environ.get("NEF_UPLOAD_INTERVAL",     ""),
        "heartbeat_interval":  os.environ.get("NEF_HEARTBEAT_INTERVAL",  ""),
        "screenshot_interval": os.environ.get("NEF_SCREENSHOT_INTERVAL", ""),
    }
    numeric_fields = {"upload_interval", "heartbeat_interval", "screenshot_interval"}
    for key, value in overrides.items():
        if value:  # Only override if env var is non-empty
            if key in numeric_fields and value.isdigit():
                cfg[key] = int(value)
            else:
                cfg[key] = value
    return cfg


def load_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                data = json.load(f)
            cfg = get_default_config()
            cfg.update(data)
            return _apply_env_overrides(cfg)
        except (json.JSONDecodeError, OSError):
            pass
    cfg = get_default_config()
    return _apply_env_overrides(cfg)


def save_config(cfg: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    # Never write JWT fields back to disk if they are cleared to None
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def validate_config(cfg: dict) -> list[str]:
    """
    FIX #3: Validate the config before starting the daemon.
    Returns a list of human-readable error strings.
    An empty list means the config is valid and the daemon can start.

    This prevents cryptic sys.exit(1) crashes and gives the systemd
    journal useful diagnostic output instead.
    """
    errors = []

    server_url = cfg.get("server_url", "").strip()
    if not server_url:
        errors.append(
            "server_url is not set. "
            "Set it via: NEF_SERVER_URL env var or re-run with --install."
        )
    elif not (server_url.startswith("http://") or server_url.startswith("https://")):
        errors.append(
            f"server_url '{server_url}' is invalid. Must start with http:// or https://."
        )

    if not cfg.get("agent_id"):
        errors.append(
            "agent_id is not set. "
            "Run: python3 /opt/nef-agent/main.py --server <URL> --install"
        )

    if not cfg.get("api_key"):
        errors.append(
            "api_key is not set. "
            "This is set automatically during --install registration."
        )

    return errors


def cert_available(cfg: dict) -> bool:
    """Return True when both the client cert and key files exist on disk."""
    return (
        Path(cfg.get("cert_path", "")).exists()
        and Path(cfg.get("key_path", "")).exists()
    )


def ca_cert_path(cfg: dict):
    """
    Return the CA cert path for TLS pinning, or True (system CAs), or False.
    Falls back to system CAs if the custom CA file doesn't exist.
    """
    ca = cfg.get("ca_cert_path", "")
    if ca and Path(ca).exists():
        return ca
    return cfg.get("tls_verify", True)
