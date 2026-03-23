"""
NEF Agent GUI — Work Tracker Widget
Clock-in/clock-out panel with session history and hours summary.
"""

import logging

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QGroupBox,
    QMessageBox, QTextEdit
)

from gui import api_client

logger = logging.getLogger(__name__)

_STYLE = """
    QGroupBox {
        color: #94a3b8;
        font-size: 12px;
        font-weight: bold;
        border: 1px solid #334155;
        border-radius: 8px;
        margin-top: 8px;
        padding-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 3px;
    }
    QPushButton#clock_in_btn {
        background: #22c55e;
        color: #0f2217;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-size: 14px;
        font-weight: bold;
    }
    QPushButton#clock_in_btn:hover { background: #16a34a; }
    QPushButton#clock_out_btn {
        background: #ef4444;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-size: 14px;
        font-weight: bold;
    }
    QPushButton#clock_out_btn:hover { background: #dc2626; }
    QPushButton:disabled {
        background: #334155;
        color: #64748b;
    }
    QLabel#stat_value {
        color: #7dd3fc;
        font-size: 22px;
        font-weight: bold;
    }
    QLabel#stat_label {
        color: #94a3b8;
        font-size: 11px;
    }
    QTableWidget {
        background: #1e2336;
        color: #e0e6f0;
        gridline-color: #334155;
        border: none;
        border-radius: 4px;
    }
    QHeaderView::section {
        background: #1a1f2e;
        color: #94a3b8;
        padding: 6px;
        border: none;
        font-size: 12px;
    }
    QTableWidget::item { padding: 6px; }
    QTableWidget::item:selected { background: #334155; }
"""


class _AsyncWorker(QThread):
    done    = pyqtSignal(object)
    failed  = pyqtSignal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn   = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            self.done.emit(self._fn(*self._args, **self._kwargs))
        except Exception as e:
            self.failed.emit(str(e))


class WorkTrackerWidget(QWidget):
    """
    Clock-in / clock-out panel with session history and weekly summary.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(_STYLE)
        self._worker = None
        self._build_ui()
        self._refresh()

        # Auto-refresh every 60 seconds
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(60_000)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # ── Header ─────────────────────────────────────────────────────────────
        title = QLabel("⏱️ Work Hours Tracker")
        title.setFont(QFont("Inter", 15, QFont.Weight.Bold))
        title.setStyleSheet("color: #e0e6f0;")
        layout.addWidget(title)

        # ── Summary stats ──────────────────────────────────────────────────────
        stats_row = QHBoxLayout()

        self.today_val  = self._stat_block("Today", "—")
        self.week_val   = self._stat_block("This Week", "—")
        self.status_val = self._stat_block("Status", "—")
        stats_row.addWidget(self.today_val[0])
        stats_row.addWidget(self.week_val[0])
        stats_row.addWidget(self.status_val[0])
        layout.addLayout(stats_row)

        # ── Clock controls ─────────────────────────────────────────────────────
        ctrl_box = QGroupBox("Clock Controls")
        ctrl_layout = QHBoxLayout(ctrl_box)

        self.clock_in_btn = QPushButton("🟢  Clock In")
        self.clock_in_btn.setObjectName("clock_in_btn")
        self.clock_in_btn.setMinimumHeight(44)
        self.clock_in_btn.clicked.connect(self._do_clock_in)
        ctrl_layout.addWidget(self.clock_in_btn)

        self.clock_out_btn = QPushButton("🔴  Clock Out")
        self.clock_out_btn.setObjectName("clock_out_btn")
        self.clock_out_btn.setMinimumHeight(44)
        self.clock_out_btn.clicked.connect(self._do_clock_out)
        ctrl_layout.addWidget(self.clock_out_btn)

        layout.addWidget(ctrl_box)

        # ── Session history table ──────────────────────────────────────────────
        hist_box = QGroupBox("Session History")
        hist_layout = QVBoxLayout(hist_box)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Date", "Clock In", "Clock Out", "Duration"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        hist_layout.addWidget(self.table)

        layout.addWidget(hist_box, stretch=1)

    def _stat_block(self, label_text: str, value_text: str):
        """Return (QFrame, value_label) for a stat card."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: #1e2336;
                border-radius: 8px;
                border: 1px solid #334155;
            }
        """)
        v = QVBoxLayout(frame)
        v.setContentsMargins(14, 12, 14, 12)
        val_lbl = QLabel(value_text)
        val_lbl.setObjectName("stat_value")
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(label_text)
        lbl.setObjectName("stat_label")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(val_lbl)
        v.addWidget(lbl)
        return frame, val_lbl

    # ── Actions ────────────────────────────────────────────────────────────────

    def _do_clock_in(self):
        self.clock_in_btn.setEnabled(False)
        self.clock_in_btn.setText("Clocking in…")
        self._worker = _AsyncWorker(api_client.clock_in)
        self._worker.done.connect(lambda r: self._on_clock_result(r, "in"))
        self._worker.failed.connect(self._on_clock_fail)
        self._worker.start()

    def _do_clock_out(self):
        self.clock_out_btn.setEnabled(False)
        self.clock_out_btn.setText("Clocking out…")
        self._worker = _AsyncWorker(api_client.clock_out)
        self._worker.done.connect(lambda r: self._on_clock_result(r, "out"))
        self._worker.failed.connect(self._on_clock_fail)
        self._worker.start()

    def _on_clock_result(self, result: dict, action: str):
        self._reset_buttons()
        QMessageBox.information(self, "Work Session", result.get("message", "Done."))
        self._refresh()

    def _on_clock_fail(self, error: str):
        self._reset_buttons()
        QMessageBox.warning(self, "Clock Error", error)

    def _reset_buttons(self):
        self.clock_in_btn.setEnabled(True)
        self.clock_in_btn.setText("🟢  Clock In")
        self.clock_out_btn.setEnabled(True)
        self.clock_out_btn.setText("🔴  Clock Out")

    # ── Data refresh ───────────────────────────────────────────────────────────

    def _refresh(self):
        self._refresh_summary()
        self._refresh_sessions()

    def _refresh_summary(self):
        worker = _AsyncWorker(api_client.my_summary)
        worker.done.connect(self._update_summary)
        worker.start()

    def _update_summary(self, data: dict):
        self.today_val[1].setText(data.get("today_human", "—"))
        self.week_val[1].setText(data.get("week_human", "—"))
        open_n = int(data.get("open_sessions", 0))
        if open_n:
            self.status_val[1].setText("🟢 Active")
            self.status_val[1].setStyleSheet("color: #22c55e; font-size: 16px; font-weight: bold;")
        else:
            self.status_val[1].setText("⚫ Idle")
            self.status_val[1].setStyleSheet("color: #94a3b8; font-size: 16px; font-weight: bold;")

    def _refresh_sessions(self):
        worker = _AsyncWorker(api_client.my_sessions, 20)
        worker.done.connect(self._populate_table)
        worker.start()

    def _populate_table(self, sessions: list):
        self.table.setRowCount(0)
        for s in sessions:
            row = self.table.rowCount()
            self.table.insertRow(row)
            # Parse date from clock_in ISO string
            ci = s.get("clock_in", "")
            date_str = ci[:10] if ci else "—"
            time_in  = ci[11:16] if len(ci) > 16 else ci
            co = s.get("clock_out") or ""
            time_out = co[11:16] if len(co) > 16 else ("In progress" if not co else co)
            duration = s.get("duration_human", "In progress")

            for col, val in enumerate([date_str, time_in, time_out, duration]):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if val == "In progress":
                    item.setForeground(QColor("#22c55e"))
                self.table.setItem(row, col, item)
