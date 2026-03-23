"""
log_viewer.py – Scrollable event log table widget.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGroupBox, QHBoxLayout, QHeaderView, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from app.core.logger import Logger


class LogViewer(QGroupBox):
    """
    Displays the most recent events from the SQLite logger.
    Refreshed externally (e.g. on each stats_updated signal).
    """

    def __init__(self, parent=None):
        super().__init__("Event Log", parent)
        self._log = Logger()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # Toolbar
        tb = QHBoxLayout()
        self._btn_refresh = QPushButton("↻  Refresh")
        self._btn_refresh.setFixedWidth(100)
        self._btn_refresh.clicked.connect(self.refresh)

        self._btn_clear = QPushButton("🗑  Clear")
        self._btn_clear.setFixedWidth(90)
        self._btn_clear.clicked.connect(self._clear_log)

        tb.addWidget(self._btn_refresh)
        tb.addWidget(self._btn_clear)
        tb.addStretch()
        layout.addLayout(tb)

        # Table
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Timestamp (UTC)", "Event", "Detail"])
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        rows = self._log.fetch_events(limit=100)
        self._table.setRowCount(0)
        for row in rows:
            r = self._table.rowCount()
            self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(str(row["ts"])))
            self._table.setItem(r, 1, QTableWidgetItem(str(row["event_type"])))
            self._table.setItem(r, 2, QTableWidgetItem(str(row["detail"] or "")))

        # Auto-scroll to newest (top, since ORDER BY DESC)
        if self._table.rowCount():
            self._table.scrollToTop()

    def _clear_log(self) -> None:
        self._table.setRowCount(0)
