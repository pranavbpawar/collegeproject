"""
NEF Agent GUI — Main Application Window
Tabbed window: Chat | Work Tracker | Status
Shown after successful employee login.
"""

import logging

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QFrame, QStatusBar,
    QSizePolicy
)

from gui.chat_widget        import ChatWidget
from gui.work_tracker_widget import WorkTrackerWidget
from gui import api_client

logger = logging.getLogger(__name__)

_MAIN_STYLE = """
    QMainWindow { background: #0f1117; }
    QTabWidget::pane {
        border: none;
        background: #0f1117;
    }
    QTabWidget::tab-bar { alignment: left; }
    QTabBar::tab {
        background: #1a1f2e;
        color: #94a3b8;
        border: none;
        padding: 10px 24px;
        font-size: 13px;
        font-weight: bold;
    }
    QTabBar::tab:selected {
        background: #0f1117;
        color: #7dd3fc;
        border-bottom: 2px solid #3b82f6;
    }
    QTabBar::tab:hover { background: #253050; color: #e0e6f0; }
    QStatusBar {
        background: #1a1f2e;
        color: #64748b;
        font-size: 11px;
        border-top: 1px solid #334155;
    }
    QLabel#header_name {
        color: #e0e6f0;
        font-size: 14px;
        font-weight: bold;
    }
    QLabel#header_role { color: #94a3b8; font-size: 12px; }
    QPushButton#logout_btn {
        background: transparent;
        color: #94a3b8;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 6px 14px;
        font-size: 12px;
    }
    QPushButton#logout_btn:hover { color: #f87171; border-color: #f87171; }
"""


class MainWindow(QMainWindow):
    """
    Main application window for the TBAPS employee client.
    Tabs: Chat | Work Tracker | Status
    """

    def __init__(self, user_data: dict, parent=None):
        super().__init__(parent)
        self._user_data = user_data
        self._build_ui()

    def _build_ui(self):
        self.setWindowTitle("TBAPS — Employee Client")
        self.setMinimumSize(900, 620)
        self.setStyleSheet(_MAIN_STYLE)

        central = QWidget()
        central.setStyleSheet("background: #0f1117;")
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(central)

        # ── Top header bar ─────────────────────────────────────────────────────
        header = QFrame()
        header.setFixedHeight(52)
        header.setStyleSheet("""
            QFrame {
                background: #1a1f2e;
                border-bottom: 1px solid #334155;
            }
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 0, 16, 0)

        brand = QLabel("🛡️ TBAPS")
        brand.setStyleSheet("color: #7dd3fc; font-size: 15px; font-weight: bold;")
        h_layout.addWidget(brand)
        h_layout.addSpacing(16)

        # Divider
        div = QFrame()
        div.setFixedWidth(1)
        div.setFixedHeight(24)
        div.setStyleSheet("background: #334155;")
        h_layout.addWidget(div)
        h_layout.addSpacing(16)

        name_lbl = QLabel(f"👤 {self._user_data.get('name', 'Employee')}")
        name_lbl.setObjectName("header_name")
        h_layout.addWidget(name_lbl)

        dept = self._user_data.get("department", "")
        if dept:
            dept_lbl = QLabel(f"  ·  {dept}")
            dept_lbl.setObjectName("header_role")
            h_layout.addWidget(dept_lbl)

        h_layout.addStretch()

        self._conn_lbl = QLabel("⬤ Connected")
        self._conn_lbl.setStyleSheet("color: #22c55e; font-size: 12px;")
        h_layout.addWidget(self._conn_lbl)
        h_layout.addSpacing(12)

        logout_btn = QPushButton("Sign Out")
        logout_btn.setObjectName("logout_btn")
        logout_btn.clicked.connect(self._logout)
        h_layout.addWidget(logout_btn)

        root_layout.addWidget(header)

        # ── Tab widget ─────────────────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        root_layout.addWidget(self.tabs, stretch=1)

        # Chat tab
        self._chat_widget = ChatWidget()
        self.tabs.addTab(self._chat_widget, "💬  Chat")

        # Work Tracker tab
        self._work_widget = WorkTrackerWidget()
        self.tabs.addTab(self._work_widget, "⏱️  Work Tracker")

        # Status tab
        status_tab = self._build_status_tab()
        self.tabs.addTab(status_tab, "📡  Status")

        # ── Status bar ─────────────────────────────────────────────────────────
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _build_status_tab(self) -> QWidget:
        """Simple agent status / info panel."""
        w = QWidget()
        w.setStyleSheet("background: #0f1117;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Agent Status")
        title.setFont(QFont("Inter", 15, QFont.Weight.Bold))
        title.setStyleSheet("color: #e0e6f0;")
        layout.addWidget(title)

        info = {
            "Employee ID":  self._user_data.get("employee_id", "—"),
            "Email":        self._user_data.get("email", "—"),
            "Department":   self._user_data.get("department", "—"),
            "Role":         self._user_data.get("role", "—"),
            "Server":       api_client._server_url or "—",
        }
        for k, v in info.items():
            row = QHBoxLayout()
            key_lbl = QLabel(f"{k}:")
            key_lbl.setStyleSheet("color: #64748b; font-size: 13px;")
            key_lbl.setFixedWidth(120)
            val_lbl = QLabel(str(v))
            val_lbl.setStyleSheet("color: #e0e6f0; font-size: 13px;")
            val_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            row.addWidget(key_lbl)
            row.addWidget(val_lbl)
            row.addStretch()
            layout.addLayout(row)

        layout.addStretch()

        note = QLabel(
            "The NEF monitoring agent runs in the background.\n"
            "All activity data is securely transmitted to your employer's TBAPS server.\n"
            "Contact your IT admin for privacy policy details."
        )
        note.setStyleSheet("color: #475569; font-size: 11px;")
        note.setWordWrap(True)
        layout.addWidget(note)

        return w

    def _logout(self):
        api_client.logout()
        self.close()
        # Re-launch login window — handled by the calling code in main.py


def launch_gui(server_url: str):
    """
    Entry point: show login, then main window.
    Called by ``python main.py --gui``.
    """
    import sys
    from PyQt6.QtWidgets import QApplication
    from gui.login_window import LoginWindow

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Inter", 10))

    api_client.configure(server_url)

    def _show_main(user_data: dict):
        w = MainWindow(user_data)
        w.show()
        app._main_window = w   # prevent GC

    login = LoginWindow(server_url)
    login.login_success.connect(_show_main)

    if login.exec() != QMainWindow.DialogCode.Accepted:
        # User closed login dialog without completing — exit
        sys.exit(0)

    sys.exit(app.exec())
