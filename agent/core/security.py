"""
NEF Agent — Security Hardening Module
Provides:
  - TLS certificate chain verification
  - Basic process integrity / anti-tamper checks
  - Secure file wipe utility
"""

import logging
import os
import platform
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


# ── TLS certificate verification ───────────────────────────────────────────────

def verify_tls_cert(cert_path: str, ca_path: str) -> bool:
    """
    Verify that cert_path was signed by ca_path using OpenSSL.
    Returns True if verification passes OR if OpenSSL is not available.
    """
    try:
        result = subprocess.run(
            ["openssl", "verify", "-CAfile", ca_path, cert_path],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            logger.info("[security] TLS cert chain OK")
            return True
        logger.warning(f"[security] TLS cert chain FAILED: {result.stderr.strip()}")
        return False
    except FileNotFoundError:
        logger.debug("[security] openssl not in PATH — skipping TLS chain verify")
        return True
    except Exception as e:
        logger.debug(f"[security] TLS verify skipped: {e}")
        return True


# ── Process integrity ──────────────────────────────────────────────────────────

def check_process_integrity() -> bool:
    """
    Perform basic anti-debug / anti-tamper checks.
    Returns False if tampering is suspected.
    """
    system = platform.system()

    if system == "Windows":
        return _check_integrity_windows()
    elif system == "Linux":
        return _check_integrity_linux()
    return True   # No check on macOS or unknown platforms


def _check_integrity_windows() -> bool:
    """Check Windows debugger presence via IsDebuggerPresent."""
    try:
        import ctypes
        if ctypes.windll.kernel32.IsDebuggerPresent():
            logger.warning("[security] Debugger detected — agent may be tampered")
            return False
    except Exception:
        pass
    return True


def _check_integrity_linux() -> bool:
    """Check Linux TracerPid in /proc/self/status for debugger attachment."""
    try:
        status = Path("/proc/self/status").read_text()
        for line in status.splitlines():
            if line.startswith("TracerPid:"):
                tracer_pid = int(line.split(":")[1].strip())
                if tracer_pid != 0:
                    logger.warning(f"[security] TracerPid={tracer_pid} — possible debugger")
                    return False
    except Exception:
        pass
    return True


# ── Secure file wipe ───────────────────────────────────────────────────────────

def secure_wipe(path) -> bool:
    """
    Overwrite a file with random bytes then delete it.
    Falls back to normal deletion if overwrite fails.
    """
    p = Path(path)
    if not p.exists():
        return True
    try:
        size = p.stat().st_size
        with open(p, "r+b") as f:
            f.write(os.urandom(size))
            f.flush()
            os.fsync(f.fileno())
        p.unlink()
        logger.debug(f"[security] Secure-wiped: {p.name}")
        return True
    except Exception as e:
        logger.debug(f"[security] Secure wipe failed ({e}), falling back to unlink")
        try:
            p.unlink()
        except Exception:
            pass
        return False


# ── Startup checks ─────────────────────────────────────────────────────────────

def run_startup_checks(cfg: dict) -> bool:
    """
    Run all startup security checks. Log warnings but don't abort by default.
    Returns True if all checks pass.
    """
    passed = True

    # 1. Process integrity
    if not check_process_integrity():
        logger.error("[security] FAIL: Process integrity check")
        passed = False

    # 2. Certificate validation (if cert configured)
    cert_path = cfg.get("cert_path", "")
    ca_path = cfg.get("ca_cert_path", "")
    if cert_path and ca_path and Path(cert_path).exists() and Path(ca_path).exists():
        if not verify_tls_cert(cert_path, ca_path):
            logger.error("[security] FAIL: Client cert chain invalid")
            passed = False

    # 3. Config directory permissions (warn if world-readable)
    from pathlib import Path as _P
    config_dir = _P.home() / ".nef"
    if config_dir.exists() and platform.system() != "Windows":
        stat = config_dir.stat()
        perms = oct(stat.st_mode)[-3:]
        if perms[2] != "0":  # others have any permission
            logger.warning(f"[security] ~/.nef permissions are {perms} — recommend 700")

    return passed
