"""
control_panel.py – Start / Stop execution control buttons.
"""
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)


class ControlPanel(QGroupBox):
    """
    Provides ▶ Start and ■ Stop buttons.

    Signals
    -------
    start_requested()
    stop_requested()
    """

    start_requested = pyqtSignal()
    stop_requested  = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Execution Control", parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self._exe_label = QLabel("No executable loaded.")
        self._exe_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        layout.addWidget(self._exe_label)

        btn_row = QHBoxLayout()

        self._btn_start = QPushButton("▶  Start")
        self._btn_start.setObjectName("btnStart")
        self._btn_start.setEnabled(False)
        self._btn_start.setMinimumHeight(38)
        self._btn_start.clicked.connect(self.start_requested)

        self._btn_stop = QPushButton("■  Stop")
        self._btn_stop.setObjectName("btnStop")
        self._btn_stop.setEnabled(False)
        self._btn_stop.setMinimumHeight(38)
        self._btn_stop.clicked.connect(self.stop_requested)

        btn_row.addWidget(self._btn_start)
        btn_row.addWidget(self._btn_stop)
        layout.addLayout(btn_row)

    # ── State helpers ─────────────────────────────────────────────────────────

    def set_file_loaded(self, path: str) -> None:
        """Call when a valid executable has been selected."""
        import os
        self._exe_label.setText(f"Loaded: {os.path.basename(path)}")
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)

    def set_running(self, running: bool) -> None:
        """Update button states based on running state."""
        self._btn_start.setEnabled(not running)
        self._btn_stop.setEnabled(running)
