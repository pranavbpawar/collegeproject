"""
logger.py – SQLite event and metrics persistence.

Tables
------
events  : timestamped event log (start, stop, crash, …)
metrics : per-poll snapshot of process resource usage
conns   : network connection records
"""
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import DB_PATH


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Logger:
    """Thread-safe singleton SQLite logger."""

    _instance: Optional["Logger"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "Logger":
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._init_db()          # type: ignore[attr-defined]
                cls._instance = inst
        return cls._instance

    # ── Init ────────────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        self._conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._db_lock = threading.Lock()
        self._create_tables()

    def _create_tables(self) -> None:
        ddl = """
        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ts          TEXT    NOT NULL,
            event_type  TEXT    NOT NULL,
            detail      TEXT
        );

        CREATE TABLE IF NOT EXISTS metrics (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ts          TEXT    NOT NULL,
            pid         INTEGER,
            cpu_pct     REAL,
            mem_bytes   INTEGER,
            net_sent    INTEGER,
            net_recv    INTEGER
        );

        CREATE TABLE IF NOT EXISTS conns (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ts          TEXT    NOT NULL,
            laddr       TEXT,
            raddr       TEXT,
            rport       INTEGER,
            status      TEXT
        );
        """
        with self._db_lock:
            self._conn.executescript(ddl)
            self._conn.commit()

    # ── Write ────────────────────────────────────────────────────────────────

    def log_event(self, event_type: str, detail: str = "") -> None:
        sql = "INSERT INTO events (ts, event_type, detail) VALUES (?, ?, ?)"
        with self._db_lock:
            self._conn.execute(sql, (_now_iso(), event_type, detail))
            self._conn.commit()

    def log_metrics(self, data: Dict[str, Any]) -> None:
        sql = """
        INSERT INTO metrics (ts, pid, cpu_pct, mem_bytes, net_sent, net_recv)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        with self._db_lock:
            self._conn.execute(sql, (
                _now_iso(),
                data.get("pid"),
                data.get("cpu_pct"),
                data.get("mem_bytes"),
                data.get("net_sent"),
                data.get("net_recv"),
            ))
            self._conn.commit()

    def log_connection(self, laddr: str, raddr: str,
                       rport: int, status: str) -> None:
        sql = """
        INSERT INTO conns (ts, laddr, raddr, rport, status)
        VALUES (?, ?, ?, ?, ?)
        """
        with self._db_lock:
            self._conn.execute(sql, (_now_iso(), laddr, raddr, rport, status))
            self._conn.commit()

    # ── Read ─────────────────────────────────────────────────────────────────

    def fetch_events(self, limit: int = 100) -> List[sqlite3.Row]:
        sql = "SELECT * FROM events ORDER BY id DESC LIMIT ?"
        with self._db_lock:
            return self._conn.execute(sql, (limit,)).fetchall()

    def fetch_metrics(self, limit: int = 60) -> List[sqlite3.Row]:
        sql = "SELECT * FROM metrics ORDER BY id DESC LIMIT ?"
        with self._db_lock:
            return self._conn.execute(sql, (limit,)).fetchall()

    def fetch_connections(self, limit: int = 50) -> List[sqlite3.Row]:
        sql = "SELECT * FROM conns ORDER BY id DESC LIMIT ?"
        with self._db_lock:
            return self._conn.execute(sql, (limit,)).fetchall()
