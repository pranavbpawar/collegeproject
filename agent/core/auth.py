"""
NEF Agent — Authentication Module
Handles two-phase authentication:
  Phase 1: mTLS client certificate verification on registration
  Phase 2: JWT access-token management with auto-refresh
            Falls back gracefully to X-API-Key if JWT not available.
"""

import hashlib
import hmac
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)


# ── JWT helpers ────────────────────────────────────────────────────────────────

def _parse_jwt_expiry(token: str) -> Optional[float]:
    """
    Decode JWT payload (base64, no verification) and return exp timestamp.
    Returns None if token is malformed.
    """
    try:
        import base64
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload_b64 = parts[1] + "=="   # pad to multiple of 4
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return float(payload.get("exp", 0))
    except Exception:
        return None


def _token_is_valid(token: Optional[str], buffer_sec: int = 120) -> bool:
    """Return True if the token exists and won't expire within buffer_sec."""
    if not token:
        return False
    exp = _parse_jwt_expiry(token)
    if exp is None:
        return False
    return time.time() < (exp - buffer_sec)


# ── Certificate loading ────────────────────────────────────────────────────────

def load_cert(cert_path: str, key_path: str) -> Optional[tuple]:
    """
    Load the NEF mTLS client certificate pair.
    Returns (cert_path, key_path) tuple for use in requests, or None if not found.
    """
    c, k = Path(cert_path), Path(key_path)
    if c.exists() and k.exists():
        logger.info(f"[auth] mTLS cert loaded: {c.name}")
        return (str(c), str(k))
    logger.debug(f"[auth] mTLS cert not found at {cert_path} — falling back to API-key auth")
    return None


def verify_cert_chain(cert_path: str, ca_path: str) -> bool:
    """
    Basic verification that cert_path was signed by ca_path.
    Uses OpenSSL subprocess if available; otherwise skips and returns True.
    """
    try:
        import subprocess
        result = subprocess.run(
            ["openssl", "verify", "-CAfile", ca_path, cert_path],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            logger.info("[auth] Certificate chain verified OK")
            return True
        logger.warning(f"[auth] Certificate chain verification failed: {result.stderr.strip()}")
        return False
    except FileNotFoundError:
        logger.debug("[auth] openssl not found — skipping chain verification")
        return True   # Best-effort; don't block agent startup
    except Exception as e:
        logger.debug(f"[auth] Chain verification skipped: {e}")
        return True


# ── Token acquisition ──────────────────────────────────────────────────────────

def _sign_challenge(agent_id: str, nonce: str, api_key: str) -> str:
    """
    Create an HMAC-SHA256 challenge signature.
    Used as the credential when requesting a JWT from the backend.
    """
    message = f"{agent_id}:{nonce}".encode()
    return hmac.new(api_key.encode(), message, hashlib.sha256).hexdigest()


def fetch_jwt(
    session: requests.Session,
    server_url: str,
    agent_id: str,
    api_key: str,
) -> Optional[str]:
    """
    Exchange agent credentials for a JWT access token.
    POST /api/v1/agent/token  (returns access_token + refresh_token)
    Falls back to None gracefully if endpoint doesn't exist.
    """
    nonce = os.urandom(16).hex()
    signature = _sign_challenge(agent_id, nonce, api_key)

    try:
        resp = session.post(
            f"{server_url.rstrip('/')}/api/v1/agent/token",
            json={
                "agent_id":  agent_id,
                "nonce":     nonce,
                "signature": signature,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            logger.info("[auth] JWT acquired successfully")
            return data.get("access_token")
        elif resp.status_code == 404:
            logger.debug("[auth] /agent/token endpoint not found — using API-key auth")
        else:
            logger.warning(f"[auth] JWT fetch failed: {resp.status_code}")
    except Exception as e:
        logger.debug(f"[auth] JWT fetch error: {e}")
    return None


# ── Auth Manager ───────────────────────────────────────────────────────────────

class AuthManager:
    """
    Manages NEF Agent authentication state.

    - Tries mTLS + JWT first.
    - Falls back to X-API-Key header if JWT unavailable.
    - Background thread refreshes token ~5 min before expiry.
    """

    def __init__(
        self,
        server_url: str,
        agent_id: str,
        api_key: str,
        cert_path:   Optional[str] = None,
        key_path:    Optional[str] = None,
        ca_cert_path              = True,   # True | path string | False
    ):
        self.server_url   = server_url.rstrip("/")
        self.agent_id     = agent_id
        self.api_key      = api_key
        self.ca_cert_path = ca_cert_path

        # mTLS certificate
        self._mtls = load_cert(cert_path or "", key_path or "") if cert_path else None

        # JWT state
        self._jwt_token: Optional[str] = None
        self._jwt_lock = threading.Lock()

        # Build authenticated session
        self.session = self._build_session()

        # Try to get initial JWT
        self._refresh_jwt()

        # Background refresh thread
        self._stop_event = threading.Event()
        self._refresh_thread = threading.Thread(
            target=self._auto_refresh_loop, daemon=True, name="nef-auth-refresh"
        )
        self._refresh_thread.start()

    # ── Session factory ────────────────────────────────────────────────────────

    def _build_session(self) -> requests.Session:
        s = requests.Session()
        # Base headers
        s.headers.update({
            "X-Agent-ID":  self.agent_id,
            "X-API-Key":   self.api_key,
            "User-Agent":  f"nef-agent/2.0 ({_platform_info()})",
            "Content-Type": "application/json",
        })
        # mTLS client certificate
        if self._mtls:
            s.cert = self._mtls
        # TLS server verification / pinning
        s.verify = self.ca_cert_path
        return s

    # ── JWT management ─────────────────────────────────────────────────────────

    def _refresh_jwt(self):
        """Attempt to get/refresh the JWT. Safe to call anytime."""
        token = fetch_jwt(self.session, self.server_url, self.agent_id, self.api_key)
        with self._jwt_lock:
            if token:
                self._jwt_token = token
                self.session.headers["Authorization"] = f"Bearer {token}"
                logger.debug("[auth] JWT applied to session headers")
            else:
                # Remove stale JWT if refresh failed; fall back to X-API-Key
                self._jwt_token = None
                self.session.headers.pop("Authorization", None)

    def _auto_refresh_loop(self):
        """Refresh JWT 5 minutes before it expires. Checks every 60s."""
        while not self._stop_event.wait(60):
            with self._jwt_lock:
                token = self._jwt_token
            if not _token_is_valid(token, buffer_sec=300):
                logger.debug("[auth] Proactive JWT refresh triggered")
                self._refresh_jwt()

    def stop(self):
        """Signal the refresh thread to stop."""
        self._stop_event.set()

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_session(self) -> requests.Session:
        """Return the authenticated requests.Session (thread-safe)."""
        return self.session

    def is_using_jwt(self) -> bool:
        with self._jwt_lock:
            return _token_is_valid(self._jwt_token)


# ── Utils ──────────────────────────────────────────────────────────────────────

def _platform_info() -> str:
    import platform
    return f"{platform.system()}; {platform.machine()}"
