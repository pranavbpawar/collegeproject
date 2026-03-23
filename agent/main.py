"""
NEF Agent v2 — Main Daemon
Production-grade NEF monitoring agent entry point.

Usage:
  python main.py --server https://tbaps.company.local --install
  python main.py
  python main.py --test-collectors
  python main.py --status
"""

import argparse
import json
import logging
import os
import platform
import signal
import sys
import time
import threading
from datetime import datetime, timezone
from pathlib import Path

from config import load_config, save_config, CONFIG_DIR
from uploader import Uploader
from core.auth import AuthManager
from core.security import run_startup_checks

from collectors import (
    sysinfo, processes, idle, usb, files, screenshot
)
from collectors import window as window_mod
from collectors import websites as websites_mod
from collectors import input_metrics as input_mod

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(CONFIG_DIR / "agent.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("nef")

# ── Graceful shutdown ─────────────────────────────────────────────────────────
_shutdown = threading.Event()

def _handle_signal(sig, frame):
    logger.info(f"[main] Signal {sig} received — shutting down")
    _shutdown.set()

signal.signal(signal.SIGINT,  _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


# ── Registration ───────────────────────────────────────────────────────────────

def register(server_url: str) -> tuple[str, str]:
    """Register this machine with the server. Returns (agent_id, api_key)."""
    import requests
    info = sysinfo.collect()
    payload = {
        "hostname":    info["hostname"],
        "username":    info["username"],
        "os":          info["os"],
        "os_version":  info["os_version"],
        "ip_address":  info["ip_address"],
        "mac_address": info["mac_address"],
    }
    resp = requests.post(
        f"{server_url.rstrip('/')}/api/v1/agent/register",
        json=payload, timeout=10
    )
    resp.raise_for_status()
    data = resp.json()
    return data["agent_id"], data["api_key"]


# ── Install as system service ──────────────────────────────────────────────────

def install(server_url: str):
    """Register, save config, and install as OS service."""
    logger.info(f"[install] Registering with {server_url}")
    agent_id, api_key = register(server_url)
    cfg = load_config()
    cfg["server_url"] = server_url
    cfg["agent_id"]   = agent_id
    cfg["api_key"]    = api_key
    save_config(cfg)
    logger.info(f"[install] Registered — agent_id={agent_id}")

    system = platform.system()
    exe_path = sys.executable if getattr(sys, "frozen", False) else sys.executable
    script   = os.path.abspath(__file__)

    if system == "Linux":
        _install_linux_service(exe_path, script)
    elif system == "Windows":
        _install_windows_service(exe_path, script)
    else:
        logger.warning("[install] Auto-install not supported on this OS. Run manually.")


def _install_linux_service(python_exe: str, script: str):
    """Install hardened systemd user service."""
    working_dir = str(Path(script).parent)
    unit = f"""[Unit]
Description=NEF Monitoring Agent
Documentation=https://tbaps.internal/docs/nef-agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={python_exe} {script}
WorkingDirectory={working_dir}
Restart=always
RestartSec=15
StartLimitIntervalSec=300
StartLimitBurst=5
PrivateTmp=true
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=%h/.nef
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
"""
    service_path = Path.home() / ".config/systemd/user/nef.service"
    service_path.parent.mkdir(parents=True, exist_ok=True)
    service_path.write_text(unit)
    os.system("systemctl --user daemon-reload")
    os.system("systemctl --user enable --now nef.service")
    logger.info(f"[install] systemd service installed: {service_path}")
    logger.info("[install] Check with: systemctl --user status nef.service")


def _install_windows_service(python_exe: str, script: str):
    """Install as a proper Windows Service using pywin32 (if available),
    otherwise fall back to registry startup key."""
    try:
        # Try pywin32 service registration
        import win32serviceutil
        # Windows service wrapper is in service/win_service.py
        from service.win_service import NEFWindowsService
        win32serviceutil.InstallService(
            NEFWindowsService,
            "NEFAgent",
            "NEF Monitoring Agent",
            startType=2,   # SERVICE_DEMAND_START; os auto-changes to auto
        )
        logger.info("[install] Windows Service 'NEFAgent' registered via pywin32")
    except ImportError:
        # Fallback: registry run-key
        try:
            import winreg
            cmd = f'"{python_exe}" "{script}"'
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE,
            )
            winreg.SetValueEx(key, "NEFAgent", 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(key)
            logger.info("[install] Windows startup registry key set (fallback)")
        except Exception as e:
            logger.error(f"[install] Windows install failed: {e}")


# ── Collector tests ────────────────────────────────────────────────────────────

def test_collectors():
    """Run every collector once and print output for debugging."""
    print("\n" + "=" * 60)
    print("  NEF Agent — Collector Test Suite")
    print("=" * 60)

    input_mod.start()  # Start pynput listeners
    import time as _t; _t.sleep(1)

    tests = [
        ("sysinfo",        sysinfo.collect),
        ("processes",      processes.collect),
        ("window",         window_mod.collect),
        ("idle",           idle.collect),
        ("usb",            usb.collect),
        ("files",          files.collect),
        ("input_metrics",  input_mod.collect),
        ("websites",       lambda: websites_mod.collect("cache")),
        ("screenshot",     lambda: {**screenshot.collect(), "image_b64": "<omitted>"}),
    ]

    passed = failed = 0
    for name, fn in tests:
        try:
            result = fn()
            snippet = json.dumps(result, indent=2, default=str)[:400]
            print(f"\n✅ {name}:\n{snippet}")
            passed += 1
        except Exception as e:
            print(f"\n❌ {name}: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"  Results: {passed} passed, {failed} failed")
    print("=" * 60)


# ── Status check ───────────────────────────────────────────────────────────────

def show_status():
    """Print current agent status from config and status.log."""
    cfg = load_config()
    print(f"\nNEF Agent Status")
    print(f"  Server:   {cfg.get('server_url') or '(not configured)'}")
    print(f"  Agent ID: {cfg.get('agent_id') or '(not registered)'}")
    print(f"  JWT:      {'yes' if cfg.get('jwt_token') else 'no (using API key)'}")
    log_path = CONFIG_DIR / "status.log"
    if log_path.exists():
        lines = log_path.read_text().splitlines()[-10:]
        print(f"\n  Last 10 status lines:")
        for l in lines:
            print(f"    {l}")


# ── Main daemon loop ───────────────────────────────────────────────────────────

def run_daemon():
    cfg = load_config()
    from config import cert_available, ca_cert_path as get_ca, validate_config

    # Auto-register if server_url is set but agent_id is missing.
    # This handles the case where postinst registration failed (backend was down)
    # but the config was seeded with server_url. The daemon will self-register
    # on first start when the backend becomes reachable.
    if cfg.get("server_url") and not cfg.get("agent_id"):
        logger.info("[main] server_url set but agent not registered — attempting auto-registration...")
        for attempt in range(1, 4):
            try:
                agent_id, api_key = register(cfg["server_url"])
                cfg["agent_id"] = agent_id
                cfg["api_key"]  = api_key
                save_config(cfg)
                logger.info(f"[main] Auto-registered successfully — agent_id={agent_id[:8]}…")
                break
            except Exception as e:
                logger.warning(f"[main] Auto-registration attempt {attempt}/3 failed: {e}")
                if attempt < 3:
                    time.sleep(10)
        else:
            logger.error("[main] Auto-registration failed after 3 attempts.")
            logger.error("[main] Run manually: python3 /opt/nef-agent/main.py --server <URL> --install")
            sys.exit(1)

    # Validate final config — catches any other missing fields
    errors = validate_config(cfg)
    if errors:
        logger.error("[main] Agent configuration is incomplete — cannot start daemon:")
        for err in errors:
            logger.error(f"  ✗ {err}")
        logger.error("[main] Fix the above issues and restart the service.")
        sys.exit(1)

    # ── Security startup checks ────────────────────────────────────────────────
    run_startup_checks(cfg)

    auth_mgr = None
    if cert_available(cfg):
        auth_mgr = AuthManager(
            server_url=cfg["server_url"],
            agent_id=cfg["agent_id"],
            api_key=cfg["api_key"],
            cert_path=cfg["cert_path"],
            key_path=cfg["key_path"],
            ca_cert_path=get_ca(cfg),
        )

    uploader = Uploader(
        server_url=cfg["server_url"],
        agent_id=cfg["agent_id"],
        api_key=cfg["api_key"],
        auth_manager=auth_mgr,
        max_buffer=cfg.get("max_buffer_events", 10_000),
        batch_size=cfg.get("batch_size", 50),
        ca_verify=get_ca(cfg),
    )

    # ── DNS sniffer (if packet mode configured) ────────────────────────────────
    dns_method = cfg.get("dns_capture_method", "cache")
    if dns_method == "packet":
        ok = websites_mod.start_packet_sniffer()
        if not ok:
            logger.warning("[main] Packet sniffer failed — falling back to dns_cache mode")
            dns_method = "cache"

    # ── Input metrics listeners ────────────────────────────────────────────────
    if cfg.get("collect_input_metrics", True):
        input_mod.start()

    # ── File watcher ───────────────────────────────────────────────────────────
    files.start_watching()

    # ── System tray ───────────────────────────────────────────────────────────
    tray = None
    if cfg.get("enable_tray_icon", True):
        try:
            from transparency.tray import TrayIcon, update_status_log
            tray = TrayIcon(get_status_fn=uploader.status)
            tray.start()
        except Exception as e:
            logger.debug(f"[main] Tray icon disabled: {e}")

    # ── Interval tracking ──────────────────────────────────────────────────────
    last_heartbeat  = 0.0
    last_upload     = 0.0
    last_screenshot = 0.0
    last_sysinfo    = 0.0
    last_websites   = 0.0
    last_input      = 0.0
    last_status_log = 0.0

    upload_interval    = cfg.get("upload_interval",        10)
    heartbeat_interval = cfg.get("heartbeat_interval",     60)
    screenshot_interval= cfg.get("screenshot_interval",   300)
    sysinfo_interval   = cfg.get("sysinfo_interval",      600)
    website_interval   = cfg.get("website_flush_interval", 300)
    input_interval     = cfg.get("input_metrics_interval",  60)
    window_poll        = cfg.get("window_poll_interval",     5)

    logger.info(f"[main] NEF Agent v2 started → {cfg['server_url']} (agent_id={cfg['agent_id'][:8]}…)")

    while not _shutdown.is_set():
        now = time.time()

        # ── Window session tracking (every 5s) ─────────────────────────────────
        session_event = window_mod.collect()
        uploader.buffer(session_event)
        # Also drain any sessions that just ended
        for completed in window_mod.get_completed_sessions():
            uploader.buffer(completed)

        # ── Processes + idle + USB + files (every 30s bucket) ─────────────────
        uploader.buffer(processes.collect())
        uploader.buffer(idle.collect())
        if cfg.get("collect_usb", True):
            uploader.buffer(usb.collect())
        if cfg.get("collect_files", True):
            uploader.buffer(files.collect())

        # ── Input metrics (every 60s) ──────────────────────────────────────────
        if cfg.get("collect_input_metrics", True) and now - last_input >= input_interval:
            uploader.buffer(input_mod.collect())
            last_input = now

        # ── Website / DNS activity (every 5 min) ──────────────────────────────
        if now - last_websites >= website_interval:
            uploader.buffer(websites_mod.collect(dns_method))
            last_websites = now

        # ── Sysinfo (every 10 min) ─────────────────────────────────────────────
        if now - last_sysinfo >= sysinfo_interval:
            uploader.buffer(sysinfo.collect())
            last_sysinfo = now

        # ── Screenshot (every N sec) ───────────────────────────────────────────
        if cfg.get("collect_screenshots", True) and now - last_screenshot >= screenshot_interval:
            uploader.buffer(screenshot.collect())
            last_screenshot = now

        # ── Heartbeat (every 60s) ──────────────────────────────────────────────
        if now - last_heartbeat >= heartbeat_interval:
            uploader.heartbeat()
            last_heartbeat = now

        # ── Upload flush (every 10s) ───────────────────────────────────────────
        if now - last_upload >= upload_interval:
            uploader.flush()
            last_upload = now

        # ── Status log + tray update (every 60s) ──────────────────────────────
        if now - last_status_log >= 60:
            try:
                from transparency.tray import update_status_log
                update_status_log(uploader.status(), cfg["server_url"])
            except Exception:
                pass
            if tray:
                st = uploader.status()
                state = (
                    "error"        if st.get("circuit_open")               else
                    "reconnecting" if st.get("consecutive_failures", 0) > 2 else
                    "connected"    if st.get("last_upload_ok")             else
                    "idle"
                )
                tray.update(state)
            last_status_log = now

        # ── Poll every ~5 seconds (window poll resolution) ───────────────────
        _shutdown.wait(window_poll)

    # ── Graceful shutdown ──────────────────────────────────────────────────────
    logger.info("[main] Shutting down — flushing remaining events")
    last_session = window_mod.flush_current_session()
    if last_session:
        uploader.buffer(last_session)
    uploader.flush()
    if tray:
        tray.stop()
    if auth_mgr:
        auth_mgr.stop()
    websites_mod.stop_packet_sniffer()
    logger.info("[main] Shutdown complete")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="NEF Monitoring Agent v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --server https://tbaps.company.local --install
  python main.py
  python main.py --test-collectors
  python main.py --status
        """
    )
    parser.add_argument("--server",          help="TBAPS server URL")
    parser.add_argument("--install",         action="store_true", help="Register and install as system service")
    parser.add_argument("--test-collectors", action="store_true", help="Test all collectors and exit")
    parser.add_argument("--status",          action="store_true", help="Show current agent status and exit")
    parser.add_argument("--gui",             action="store_true", help="Launch the employee client GUI")
    parser.add_argument("--dns-method",      choices=["packet", "cache", "browser"],
                        help="Override DNS capture method (also updateable in config.json)")
    args = parser.parse_args()

    if args.test_collectors:
        test_collectors()
    elif args.status:
        show_status()
    elif args.gui:
        # Launch the PyQt6 employee client GUI
        cfg = load_config()
        server = args.server or cfg.get("server_url") or ""
        if not server:
            print("[gui] ERROR: server URL not set. Use --server <URL> or configure via NEF_SERVER_URL.")
            sys.exit(1)
        try:
            from gui.main_window import launch_gui
            launch_gui(server)
        except ImportError as e:
            print(f"[gui] PyQt6 not installed. Install with: pip install PyQt6\n  {e}")
            sys.exit(1)
    elif args.install:
        if not args.server:
            parser.error("--server is required with --install")
        install(args.server)
    else:
        # Allow --dns-method CLI override
        if args.dns_method:
            cfg = load_config()
            cfg["dns_capture_method"] = args.dns_method
            save_config(cfg)
        run_daemon()
