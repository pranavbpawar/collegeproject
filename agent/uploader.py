"""
NEF Agent — Enhanced Event Uploader (v2)
Changes from v1:
  - JWT Bearer token auth (via AuthManager), falls back to X-API-Key
  - 10-second flush interval (configurable)
  - SQLite WAL mode + integrity check on startup
  - Circuit-breaker: stops retrying after 10 consecutive failures
  - Buffer cap: configurable max_buffer_events
  - Batch size: configurable (default 50)
  - Structured status reporting for the transparency layer
"""

import json
import logging
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from core.auth import AuthManager

logger = logging.getLogger(__name__)


class Uploader:
    """
    Buffered, resilient event uploader for the NEF Agent.

    Thread-safe: buffer() and flush() can be called from different threads.
    """

    def __init__(
        self,
        server_url: str,
        agent_id:   str,
        api_key:    str,
        *,
        auth_manager: Optional["AuthManager"] = None,
        buffer_db:    Optional[Path] = None,
        max_buffer:   int = 10_000,
        batch_size:   int = 50,
        ca_verify                   = True,   # True | CA path | False
        mtls_cert:    Optional[tuple] = None, # (cert_path, key_path) or None
    ):
        from config import BUFFER_DB, CONFIG_DIR

        self.server_url   = server_url.rstrip("/")
        self.agent_id     = agent_id
        self.api_key      = api_key
        self.max_buffer   = max_buffer
        self.batch_size   = batch_size

        # Use session from AuthManager if provided, else build a basic one
        if auth_manager is not None:
            self.session = auth_manager.get_session()
        else:
            self.session = requests.Session()
            self.session.headers.update({
                "X-Agent-ID":   agent_id,
                "X-API-Key":    api_key,
                "Content-Type": "application/json",
                "User-Agent":   "nef-agent/2.0",
            })
            self.session.verify = ca_verify
            if mtls_cert:
                self.session.cert = mtls_cert

        # SQLite buffer
        self._db_path: Path = buffer_db or BUFFER_DB
        self._init_db()

        # Circuit-breaker state
        self._consecutive_failures = 0
        self._circuit_open         = False
        self._circuit_open_until   = 0.0
        self._CIRCUIT_FAIL_THRESHOLD = 10
        self._CIRCUIT_COOLDOWN_SEC   = 300  # 5 min backoff when circuit opens

        # Stats for transparency layer
        self.last_upload_ok:  Optional[float] = None
        self.last_upload_err: Optional[str]   = None
        self.total_uploaded   = 0

    # ── Startup ────────────────────────────────────────────────────────────────

    def _init_db(self):
        """Create/verify local SQLite buffer; enable WAL mode."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS event_buffer (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT    NOT NULL,
                    payload    TEXT    NOT NULL,
                    created_at TEXT    NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_state (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.commit()

        # Integrity check
        try:
            with self._connect() as conn:
                result = conn.execute("PRAGMA integrity_check").fetchone()
                if result and result[0] != "ok":
                    logger.warning(f"[uploader] SQLite integrity issue: {result[0]}")
        except Exception as e:
            logger.warning(f"[uploader] SQLite integrity check failed: {e}")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    # ── Buffering ──────────────────────────────────────────────────────────────

    def buffer(self, event: dict):
        """
        Add an event to the SQLite buffer.
        If buffer is at capacity, drops the oldest event (FIFO eviction).
        """
        if not isinstance(event, dict):
            return
        with self._connect() as conn:
            # Enforce cap
            count = conn.execute("SELECT COUNT(*) FROM event_buffer").fetchone()[0]
            if count >= self.max_buffer:
                # Evict oldest 10%
                evict = max(1, self.max_buffer // 10)
                conn.execute(
                    "DELETE FROM event_buffer WHERE id IN "
                    "(SELECT id FROM event_buffer ORDER BY id ASC LIMIT ?)",
                    (evict,)
                )
                logger.warning(f"[uploader] Buffer cap reached — evicted {evict} oldest events")

            conn.execute(
                "INSERT INTO event_buffer (event_type, payload, created_at) VALUES (?, ?, ?)",
                (
                    event.get("type", "unknown"),
                    json.dumps(event, default=str),
                    datetime.now(timezone.utc).isoformat(),
                )
            )
            conn.commit()

    def _get_buffered(self, limit: int = None) -> list:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, payload FROM event_buffer ORDER BY id ASC LIMIT ?",
                (limit or self.batch_size,)
            ).fetchall()
        return rows

    def _delete_buffered(self, ids: list):
        if not ids:
            return
        with self._connect() as conn:
            conn.execute(
                f"DELETE FROM event_buffer WHERE id IN ({','.join('?' * len(ids))})",
                ids
            )
            conn.commit()

    def pending_count(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM event_buffer").fetchone()[0]

    # ── Circuit breaker ────────────────────────────────────────────────────────

    def _circuit_allows(self) -> bool:
        """Return True if we should attempt an upload."""
        if not self._circuit_open:
            return True
        if time.time() > self._circuit_open_until:
            logger.info("[uploader] Circuit breaker reset — retrying uploads")
            self._circuit_open = False
            self._consecutive_failures = 0
            return True
        return False

    def _record_success(self):
        self._consecutive_failures = 0
        self._circuit_open = False
        self.last_upload_ok = time.time()
        self.last_upload_err = None

    def _record_failure(self, reason: str):
        self._consecutive_failures += 1
        self.last_upload_err = reason
        if self._consecutive_failures >= self._CIRCUIT_FAIL_THRESHOLD:
            logger.error(
                f"[uploader] Circuit breaker OPEN after {self._consecutive_failures} failures. "
                f"Pausing uploads for {self._CIRCUIT_COOLDOWN_SEC}s"
            )
            self._circuit_open = True
            self._circuit_open_until = time.time() + self._CIRCUIT_COOLDOWN_SEC

    # ── Upload ─────────────────────────────────────────────────────────────────

    def flush(self) -> bool:
        """
        Upload all buffered events in batches.
        Returns True if buffer is empty (fully synced) after the call.
        """
        if not self._circuit_allows():
            return False

        while True:
            rows = self._get_buffered(self.batch_size)
            if not rows:
                return True  # Buffer clear

            ids    = [r["id"] for r in rows]
            events = [json.loads(r["payload"]) for r in rows]

            payload = {
                "agent_id": self.agent_id,
                "events":   events,
                "sent_at":  datetime.now(timezone.utc).isoformat(),
            }

            success = False
            for attempt in range(4):
                try:
                    resp = self.session.post(
                        f"{self.server_url}/api/v1/agent/events",
                        json=payload,
                        timeout=15,
                    )
                    if resp.status_code < 300:
                        self._delete_buffered(ids)
                        self.total_uploaded += len(ids)
                        self._record_success()
                        success = True
                        break
                    elif resp.status_code in (401, 403):
                        logger.warning("[uploader] Auth error — check credentials")
                        self._record_failure(f"HTTP {resp.status_code}")
                        return False  # Don't retry auth errors
                except requests.exceptions.SSLError as e:
                    logger.error(f"[uploader] TLS error: {e}")
                    self._record_failure(f"TLS: {e}")
                    return False  # Don't retry TLS failures
                except requests.exceptions.ConnectionError:
                    pass  # Network down — retry
                except Exception as e:
                    logger.debug(f"[uploader] Upload attempt {attempt+1} failed: {e}")

                if attempt < 3:
                    time.sleep(min(2 ** attempt, 30))  # 1s, 2s, 4s cap at 30s

            if not success:
                self._record_failure("Max retries exceeded")
                return False

    def heartbeat(self):
        """POST a heartbeat to keep agent_machines.last_seen fresh."""
        try:
            self.session.post(
                f"{self.server_url}/api/v1/agent/heartbeat",
                json={
                    "agent_id":  self.agent_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                timeout=5,
            )
        except Exception:
            pass  # Heartbeat failure is silent — flush() circuit-breaker covers it

    def status(self) -> dict:
        """Return current uploader state (for transparency layer)."""
        return {
            "pending":              self.pending_count(),
            "total_uploaded":       self.total_uploaded,
            "last_upload_ok":       self.last_upload_ok,
            "last_upload_err":      self.last_upload_err,
            "circuit_open":         self._circuit_open,
            "consecutive_failures": self._consecutive_failures,
        }
