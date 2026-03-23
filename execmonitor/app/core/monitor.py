"""
monitor.py – Background QThread that polls psutil metrics every POLL_INTERVAL_SEC.

Emits stats_updated(dict) so the GUI can update labels without blocking the
main thread.  Also writes metrics and connection records to the Logger.
"""
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import psutil
from PyQt6.QtCore import QThread, pyqtSignal

from app.core.config import POLL_INTERVAL_SEC
from app.core.executor import Executor
from app.core.logger import Logger


def _elapsed(since: Optional[datetime]) -> str:
    """Return human-readable elapsed time string."""
    if since is None:
        return "-"
    delta = datetime.now(timezone.utc) - since
    total = int(delta.total_seconds())
    h, rem = divmod(total, 3600)
    m, s   = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


class MonitorThread(QThread):
    """
    Runs in its own thread.  One shot-poll per POLL_INTERVAL_SEC.

    Emits
    -----
    stats_updated(dict)  – snapshot of current resource usage
    """

    stats_updated = pyqtSignal(dict)

    def __init__(self, executor: Executor, parent=None):
        super().__init__(parent)
        self._executor = executor
        self._running  = False
        self._log      = Logger()

    # ── Thread control ───────────────────────────────────────────────────────

    def start_monitoring(self) -> None:
        self._running = True
        self.start()

    def stop_monitoring(self) -> None:
        self._running = False
        self.wait(int(POLL_INTERVAL_SEC * 1000 * 3))

    # ── Main loop ────────────────────────────────────────────────────────────

    def run(self) -> None:
        while self._running:
            data = self._collect()
            if data:
                self.stats_updated.emit(data)
                self._log.log_metrics(data)
                self._log_connections(data.get("connections", []))

            # Check for unexpected exit
            self._executor.poll()

            time.sleep(POLL_INTERVAL_SEC)

    # ── Collection ───────────────────────────────────────────────────────────

    def _collect(self) -> Optional[Dict[str, Any]]:
        pid = self._executor.pid
        if pid is None or not self._executor.is_running():
            return self._idle_stats()

        try:
            proc = psutil.Process(pid)
            cpu  = proc.cpu_percent(interval=None)
            mem  = proc.memory_info()
            status = proc.status()

            # Network I/O counter (process-level on Linux; falls back to system)
            try:
                pio = proc.io_counters()
                sent = pio.read_bytes   # bytes read by process
                recv = pio.write_bytes
            except (AttributeError, psutil.AccessDenied):
                sent = recv = 0

            # Active connections for this PID
            try:
                raw_conns = proc.connections(kind="inet")
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                raw_conns = []

            connections = []
            for c in raw_conns:
                raddr = c.raddr.ip   if c.raddr else ""
                rport = c.raddr.port if c.raddr else 0
                laddr = f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else ""
                connections.append({
                    "laddr":  laddr,
                    "raddr":  raddr,
                    "rport":  rport,
                    "status": c.status,
                })

            return {
                "running":     True,
                "pid":         pid,
                "cpu_pct":     round(cpu, 1),
                "mem_bytes":   mem.rss,
                "mem_mb":      round(mem.rss / 1024 / 1024, 2),
                "status":      status,
                "start_time":  self._executor.start_time,
                "uptime":      _elapsed(self._executor.start_time),
                "net_sent":    sent,
                "net_recv":    recv,
                "connections": connections,
                "conn_count":  len(connections),
            }

        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            return self._idle_stats()
        except Exception:
            return self._idle_stats()

    @staticmethod
    def _idle_stats() -> Dict[str, Any]:
        return {
            "running":     False,
            "pid":         None,
            "cpu_pct":     0.0,
            "mem_bytes":   0,
            "mem_mb":      0.0,
            "status":      "stopped",
            "start_time":  None,
            "uptime":      "-",
            "net_sent":    0,
            "net_recv":    0,
            "connections": [],
            "conn_count":  0,
        }

    def _log_connections(self, conns) -> None:
        for c in conns:
            if c.get("raddr"):
                self._log.log_connection(
                    c["laddr"], c["raddr"], c["rport"], c["status"]
                )
