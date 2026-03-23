"""
dashboard.py – Live stats dashboard widget.

Updated by MonitorThread via stats_updated(dict) signal.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QGroupBox, QLabel, QSizePolicy,
    QSplitter, QVBoxLayout, QWidget,
)


def _make_pair(title: str) -> tuple[QLabel, QLabel]:
    """Return a (label_title, label_value) pair."""
    lbl = QLabel(title)
    lbl.setObjectName("statLabel")
    val = QLabel("—")
    val.setObjectName("statValue")
    return lbl, val


class _StatCard(QFrame):
    """A small card showing one metric."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "QFrame { background:#181825; border:1px solid #313244;"
            "border-radius:8px; padding:8px; }"
        )
        layout = QVBoxLayout(self)
        layout.setSpacing(2)

        self._title = QLabel(title)
        self._title.setObjectName("statLabel")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._value = QLabel("—")
        self._value.setObjectName("statValue")
        self._value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value.setStyleSheet("font-size:18px; font-weight:bold;")

        layout.addWidget(self._title)
        layout.addWidget(self._value)

    def set_value(self, text: str) -> None:
        self._value.setText(text)


class Dashboard(QGroupBox):
    """
    Grid of stat cards that reflect the latest MonitorThread snapshot.
    """

    def __init__(self, parent=None):
        super().__init__("Live Dashboard", parent)
        self._build_ui()

    def _build_ui(self) -> None:
        grid = QGridLayout(self)
        grid.setSpacing(10)

        self._status_card  = _StatCard("Status")
        self._pid_card     = _StatCard("PID")
        self._cpu_card     = _StatCard("CPU")
        self._mem_card     = _StatCard("Memory")
        self._uptime_card  = _StatCard("Uptime")
        self._conns_card   = _StatCard("Connections")
        self._sent_card    = _StatCard("Bytes Read")
        self._recv_card    = _StatCard("Bytes Written")

        cards = [
            self._status_card, self._pid_card,
            self._cpu_card,    self._mem_card,
            self._uptime_card, self._conns_card,
            self._sent_card,   self._recv_card,
        ]

        for i, card in enumerate(cards):
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            grid.addWidget(card, i // 4, i % 4)

        # Network connections section header
        self._net_label = QLabel("Active Network Connections: none")
        self._net_label.setStyleSheet("color: #a6adc8; font-size: 12px; padding: 4px;")
        self._net_label.setWordWrap(True)
        grid.addWidget(self._net_label, 2, 0, 1, 4)

    # ── Public update slot ────────────────────────────────────────────────────

    def update_stats(self, data: dict) -> None:
        running = data.get("running", False)

        status_text = "● Running" if running else "● Stopped"
        self._status_card.set_value(status_text)
        self._status_card._value.setStyleSheet(
            "font-size:16px; font-weight:bold; color:" +
            ("#a6e3a1;" if running else "#f38ba8;")
        )

        self._pid_card.set_value(str(data.get("pid") or "—"))
        self._cpu_card.set_value(f"{data.get('cpu_pct', 0.0):.1f}%")
        self._mem_card.set_value(f"{data.get('mem_mb', 0.0):.1f} MB")
        self._uptime_card.set_value(data.get("uptime", "—"))
        self._conns_card.set_value(str(data.get("conn_count", 0)))

        sent = data.get("net_sent", 0)
        recv = data.get("net_recv", 0)
        self._sent_card.set_value(self._fmt_bytes(sent))
        self._recv_card.set_value(self._fmt_bytes(recv))

        # Connection detail line
        conns = data.get("connections", [])
        if conns:
            lines = [
                f"{c['raddr']}:{c['rport']} ({c['status']})"
                for c in conns[:6] if c.get("raddr")
            ]
            self._net_label.setText("Active Connections: " + " | ".join(lines))
        else:
            self._net_label.setText("Active Network Connections: none")

    @staticmethod
    def _fmt_bytes(n: int) -> str:
        if n < 1024:
            return f"{n} B"
        elif n < 1024 ** 2:
            return f"{n/1024:.1f} KB"
        else:
            return f"{n/1024**2:.1f} MB"
