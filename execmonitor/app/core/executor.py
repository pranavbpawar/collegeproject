"""
executor.py – Launch, stop, and query the monitored process.

Emits Qt signals so the GUI can react to lifecycle changes without polling.
"""
import os
import shutil
import subprocess
import platform
from datetime import datetime, timezone
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal


class Executor(QObject):
    """
    Wraps subprocess.Popen and provides Start / Stop semantics.

    Signals
    -------
    started(pid: int)
    stopped(exit_code: int)
    crashed(exit_code: int)
    error(message: str)
    """

    started  = pyqtSignal(int)        # PID
    stopped  = pyqtSignal(int)        # exit code
    crashed  = pyqtSignal(int)        # exit code when unexpected
    error    = pyqtSignal(str)        # error description

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proc: Optional[subprocess.Popen] = None
        self._exe_path: Optional[str] = None
        self._start_time: Optional[datetime] = None

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def pid(self) -> Optional[int]:
        return self._proc.pid if self._proc else None

    @property
    def start_time(self) -> Optional[datetime]:
        return self._start_time

    @property
    def exe_path(self) -> Optional[str]:
        return self._exe_path

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def start(self, path: str) -> bool:
        """Launch *path* as a subprocess.  Returns True on success."""
        if self.is_running():
            self.error.emit("A process is already running. Stop it first.")
            return False

        self._exe_path = path
        try:
            kwargs = dict(
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=(platform.system() != "Windows"),
            )
            self._proc = subprocess.Popen([path], **kwargs)
            self._start_time = datetime.now(timezone.utc)
            self.started.emit(self._proc.pid)
            return True
        except Exception as exc:
            self._proc = None
            self._start_time = None
            self.error.emit(f"Failed to start process: {exc}")
            return False

    def stop(self) -> bool:
        """Terminate the running subprocess.  Returns True if a process was stopped."""
        if not self.is_running():
            return False

        try:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait()
            code = self._proc.returncode
        except Exception:
            code = -1
        finally:
            self._proc = None
            self._start_time = None

        self.stopped.emit(code)
        return True

    def poll(self) -> Optional[int]:
        """
        Non-blocking status check.  If the process has exited unexpectedly
        emits `crashed` and cleans up.  Returns exit code or None if running.
        """
        if self._proc is None:
            return None
        code = self._proc.poll()
        if code is not None:
            self._proc = None
            self._start_time = None
            self.crashed.emit(code)
        return code

    def is_running(self) -> bool:
        """True if the subprocess is alive right now."""
        if self._proc is None:
            return False
        return self._proc.poll() is None
