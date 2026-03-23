"""
NEF Agent GUI — Login Window
Beautiful, secure employee login window for the TBAPS client app.
"""

import logging
from typing import Callable

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette, QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QSizePolicy, QApplication, QMessageBox
)

from gui import api_client

logger = logging.getLogger(__name__)


class _LoginWorker(QThread):
    """Runs login in background thread to keep UI responsive."""
    success = pyqtSignal(dict)
    failure = pyqtSignal(str)

    def __init__(self, email: str, password: str):
        super().__init__()
        self.email    = email
        self.password = password

    def run(self):
        try:
            result = api_client.login(self.email, self.password)
            self.success.emit(result)
        except Exception as e:
            err = str(e)
            if hasattr(e, "response") and e.response is not None:
                try:
                    detail = e.response.json().get("detail", err)
                    err = detail
                except Exception:
                    pass
            self.failure.emit(err)


class LoginWindow(QDialog):
    """
    Secure, styled login dialog for employee authentication.
    Emits login_success(dict) on successful login.
    """
    login_success = pyqtSignal(dict)

    def __init__(self, server_url: str, parent=None):
        super().__init__(parent)
        api_client.configure(server_url)
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        self.setWindowTitle("TBAPS — Employee Login")
        self.setFixedSize(440, 520)
        self.setModal(True)

        # ── Dark theme palette ─────────────────────────────────────────────────
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#0f1117"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#e0e6f0"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        self.setStyleSheet("""
            QDialog {
                background: #0f1117;
            }
            QLabel#title {
                color: #7dd3fc;
                font-size: 22px;
                font-weight: bold;
            }
            QLabel#subtitle {
                color: #94a3b8;
                font-size: 13px;
            }
            QLabel#field_label {
                color: #cbd5e1;
                font-size: 13px;
                margin-bottom: 2px;
            }
            QLineEdit {
                background: #1e2336;
                color: #e0e6f0;
                border: 1.5px solid #334155;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1.5px solid #7dd3fc;
            }
            QPushButton#login_btn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #6366f1);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton#login_btn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2563eb, stop:1 #4f46e5);
            }
            QPushButton#login_btn:disabled {
                background: #334155;
                color: #64748b;
            }
            QLabel#error_label {
                color: #f87171;
                font-size: 12px;
            }
            QLabel#status_label {
                color: #94a3b8;
                font-size: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(18)

        # ── Logo / branding ────────────────────────────────────────────────────
        logo_label = QLabel("🛡️ TBAPS")
        logo_label.setObjectName("title")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo_label)

        subtitle = QLabel("Employee Secure Access Portal")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(10)

        # ── Email ──────────────────────────────────────────────────────────────
        email_lbl = QLabel("Work Email")
        email_lbl.setObjectName("field_label")
        layout.addWidget(email_lbl)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("you@company.com")
        self.email_input.setObjectName("email_field")
        layout.addWidget(self.email_input)

        # ── Password ───────────────────────────────────────────────────────────
        pw_lbl = QLabel("App Password")
        pw_lbl.setObjectName("field_label")
        layout.addWidget(pw_lbl)

        self.pw_input = QLineEdit()
        self.pw_input.setPlaceholderText("••••••••")
        self.pw_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.pw_input)

        # ── Error label ────────────────────────────────────────────────────────
        self.error_label = QLabel("")
        self.error_label.setObjectName("error_label")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        # ── Login button ───────────────────────────────────────────────────────
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setObjectName("login_btn")
        self.login_btn.setMinimumHeight(46)
        self.login_btn.clicked.connect(self._do_login)
        layout.addWidget(self.login_btn)

        # ── Allow Enter key ────────────────────────────────────────────────────
        self.pw_input.returnPressed.connect(self._do_login)
        self.email_input.returnPressed.connect(self.pw_input.setFocus)

        # ── Status bar ─────────────────────────────────────────────────────────
        self.status_label = QLabel("Contact your IT admin if you need your password reset.")
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

    def _do_login(self):
        email    = self.email_input.text().strip()
        password = self.pw_input.text()

        if not email or not password:
            self.error_label.setText("Please enter your email and password.")
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("Signing in…")
        self.error_label.setText("")
        self.status_label.setText("Connecting to server…")

        self._worker = _LoginWorker(email, password)
        self._worker.success.connect(self._on_login_success)
        self._worker.failure.connect(self._on_login_failure)
        self._worker.start()

    def _on_login_success(self, data: dict):
        self.login_btn.setText("Sign In")
        self.login_btn.setEnabled(True)
        self.status_label.setText("")
        self.login_success.emit(data)
        self.accept()

    def _on_login_failure(self, error: str):
        self.login_btn.setText("Sign In")
        self.login_btn.setEnabled(True)
        self.error_label.setText(f"❌ {error}")
        self.status_label.setText("")
        self.pw_input.clear()
        self.pw_input.setFocus()
