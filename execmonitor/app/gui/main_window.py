"""
main_window.py – Application shell.

Wires upload → validator → executor → monitor → dashboard / log_viewer.
"""
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow, QMessageBox, QSplitter,
    QStatusBar, QVBoxLayout, QWidget,
)

from app.core.executor  import Executor
from app.core.logger    import Logger
from app.core.monitor   import MonitorThread
from app.core.validator import ValidationError, validate_executable
from app.gui.control_panel import ControlPanel
from app.gui.dashboard     import Dashboard
from app.gui.log_viewer    import LogViewer
from app.gui.upload_panel  import UploadPanel


class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(self):
        super().__init__()
        self._log      = Logger()
        self._executor = Executor(self)
        self._monitor  = MonitorThread(self._executor, self)
        self._exe_path: str = ""

        self._init_window()
        self._build_ui()
        self._connect_signals()
        self._monitor.start_monitoring()

    # ── Window setup ─────────────────────────────────────────────────────────

    def _init_window(self) -> None:
        self.setWindowTitle("ExecMonitor – Executable Activity Monitor")
        self.setMinimumSize(900, 700)
        self.resize(1100, 750)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready.")

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # Top: upload + control (side by side)
        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._upload  = UploadPanel(self)
        self._control = ControlPanel(self)
        top_splitter.addWidget(self._upload)
        top_splitter.addWidget(self._control)
        top_splitter.setSizes([600, 380])
        root.addWidget(top_splitter)

        # Middle: dashboard
        self._dashboard = Dashboard(self)
        root.addWidget(self._dashboard)

        # Bottom: log viewer (collapsible via splitter)
        self._log_viewer = LogViewer(self)
        root.addWidget(self._log_viewer, stretch=1)

    # ── Signal wiring ─────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        # Upload
        self._upload.file_selected.connect(self._on_file_selected)

        # Control buttons
        self._control.start_requested.connect(self._on_start)
        self._control.stop_requested.connect(self._on_stop)

        # Executor life-cycle
        self._executor.started.connect(self._on_proc_started)
        self._executor.stopped.connect(self._on_proc_stopped)
        self._executor.crashed.connect(self._on_proc_crashed)
        self._executor.error.connect(self._on_exec_error)

        # Monitor stats → dashboard + log_viewer
        self._monitor.stats_updated.connect(self._dashboard.update_stats)
        self._monitor.stats_updated.connect(self._on_stats_tick)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_file_selected(self, path: str) -> None:
        self._exe_path = path
        self._control.set_file_loaded(path)
        self.statusBar().showMessage(
            f"Loaded: {os.path.basename(path)}"
        )

    def _on_start(self) -> None:
        if not self._exe_path:
            QMessageBox.warning(self, "No File", "Please upload an executable first.")
            return

        try:
            validated = validate_executable(self._exe_path)
        except ValidationError as exc:
            QMessageBox.critical(self, "Validation Error", str(exc))
            return

        self._executor.start(validated)

    def _on_stop(self) -> None:
        self._executor.stop()

    def _on_proc_started(self, pid: int) -> None:
        self._control.set_running(True)
        self._log.log_event("executable_started",
                            f"PID={pid} exe={os.path.basename(self._exe_path)}")
        self.statusBar().showMessage(f"Running – PID {pid}")
        self._log_viewer.refresh()

    def _on_proc_stopped(self, code: int) -> None:
        self._control.set_running(False)
        self._log.log_event("executable_stopped", f"exit_code={code}")
        self.statusBar().showMessage(f"Stopped (exit code {code})")
        self._log_viewer.refresh()

    def _on_proc_crashed(self, code: int) -> None:
        self._control.set_running(False)
        self._log.log_event("executable_crashed", f"exit_code={code}")
        self.statusBar().showMessage(f"⚠ Process crashed (exit code {code})")
        QMessageBox.warning(
            self, "Process Crashed",
            f"The monitored process exited unexpectedly.\nExit code: {code}"
        )
        self._log_viewer.refresh()

    def _on_exec_error(self, msg: str) -> None:
        QMessageBox.critical(self, "Execution Error", msg)

    _tick_counter = 0

    def _on_stats_tick(self, _data: dict) -> None:
        """Refresh log viewer every 10 ticks (~10 s) to avoid DB thrashing."""
        self._tick_counter += 1
        if self._tick_counter % 10 == 0:
            self._log_viewer.refresh()
        conns = _data.get("conn_count", 0)
        self.statusBar().showMessage(
            f"{'Running' if _data.get('running') else 'Idle'} | "
            f"CPU {_data.get('cpu_pct', 0):.1f}% | "
            f"Mem {_data.get('mem_mb', 0):.1f} MB | "
            f"Connections {conns}"
        )

    # ── Close ─────────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        if self._executor.is_running():
            reply = QMessageBox.question(
                self, "Process Running",
                "A monitored process is still running.\nStop it and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._executor.stop()

        self._monitor.stop_monitoring()
        event.accept()
