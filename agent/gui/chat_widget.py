"""
NEF Agent GUI — Chat Widget
Secure chat interface for employee ↔ manager/HR communication with file sharing.
"""

import logging
import os
import tempfile
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QCursor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QLineEdit,
    QSplitter, QFrame, QFileDialog, QMessageBox, QScrollArea
)

from gui import api_client

logger = logging.getLogger(__name__)

_STYLE = """
    QWidget { background: #0f1117; }
    QListWidget {
        background: #1a1f2e;
        color: #e0e6f0;
        border: 1px solid #334155;
        border-radius: 6px;
        font-size: 13px;
    }
    QListWidget::item { padding: 10px 8px; border-bottom: 1px solid #1e2336; }
    QListWidget::item:selected { background: #334155; border-radius: 4px; }
    QListWidget::item:hover { background: #253050; }
    QScrollArea { border: none; background: transparent; }
    QTextEdit#msg_input {
        background: #1e2336;
        color: #e0e6f0;
        border: 1.5px solid #334155;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 14px;
    }
    QTextEdit#msg_input:focus { border: 1.5px solid #7dd3fc; }
    QPushButton#send_btn {
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
            stop:0 #3b82f6, stop:1 #6366f1);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 13px;
        font-weight: bold;
    }
    QPushButton#send_btn:hover { background: #2563eb; }
    QPushButton#attach_btn {
        background: #1e2336;
        color: #7dd3fc;
        border: 1.5px solid #334155;
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 18px;
    }
    QPushButton#attach_btn:hover { background: #253050; border-color: #7dd3fc; }
    QPushButton#send_btn:disabled, QPushButton#attach_btn:disabled {
        background: #334155; color: #64748b;
    }
    QLabel#conv_header {
        color: #e0e6f0;
        font-size: 15px;
        font-weight: bold;
        padding: 8px 12px;
    }
    QLabel#empty_state {
        color: #475569;
        font-size: 14px;
    }
"""


class _WorkerThread(QThread):
    done   = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            self.done.emit(self._fn(*self._args, **self._kwargs))
        except Exception as e:
            msg = str(e)
            if hasattr(e, "response") and e.response is not None:
                try:
                    msg = e.response.json().get("detail", msg)
                except Exception:
                    pass
            self.failed.emit(msg)


class MessageBubble(QFrame):
    """A single styled message bubble in the chat view."""

    def __init__(self, msg: dict, employee_id: str, parent=None):
        super().__init__(parent)
        self._msg         = msg
        self._employee_id = employee_id
        self._build()

    def _build(self):
        is_mine = self._msg.get("sender_id") == self._employee_id
        msg_type = self._msg.get("message_type", "text")

        # Outer alignment layout
        outer = QHBoxLayout(self)
        outer.setContentsMargins(6, 2, 6, 2)

        bubble = QFrame()
        bubble.setMaximumWidth(480)
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(12, 8, 12, 8)
        bubble_layout.setSpacing(4)

        if msg_type == "file":
            file_name  = self._msg.get("file_name", "attachment")
            file_size  = self._msg.get("file_size_human", "")
            file_id    = self._msg.get("file_id", "")

            icon_lbl = QLabel(f"📎  {file_name}")
            icon_lbl.setStyleSheet("color: #7dd3fc; font-size: 13px; font-weight: bold;")
            icon_lbl.setWordWrap(True)
            bubble_layout.addWidget(icon_lbl)

            size_lbl = QLabel(file_size)
            size_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
            bubble_layout.addWidget(size_lbl)

            dl_btn = QPushButton("⬇  Download")
            dl_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #38bdf8;
                    border: none;
                    font-size: 12px;
                    text-align: left;
                    padding: 0;
                }
                QPushButton:hover { color: #7dd3fc; text-decoration: underline; }
            """)
            dl_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            dl_btn.clicked.connect(lambda: self._download(file_id))
            bubble_layout.addWidget(dl_btn)

        else:
            content = self._msg.get("content") or ""
            txt = QLabel(content)
            txt.setWordWrap(True)
            txt.setStyleSheet("color: #e0e6f0; font-size: 13px;")
            txt.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            bubble_layout.addWidget(txt)

        ts = (self._msg.get("created_at") or "")
        time_str = ts[11:16] if len(ts) > 16 else ts
        time_lbl = QLabel(time_str)
        time_lbl.setStyleSheet("color: #64748b; font-size: 10px;")
        time_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        bubble_layout.addWidget(time_lbl)

        if is_mine:
            bubble.setStyleSheet("""
                QFrame {
                    background: #1e3a5f;
                    border-radius: 14px 2px 14px 14px;
                    border: 1px solid #2563eb;
                }
            """)
            outer.addStretch()
            outer.addWidget(bubble)
        else:
            bubble.setStyleSheet("""
                QFrame {
                    background: #1e2336;
                    border-radius: 2px 14px 14px 14px;
                    border: 1px solid #334155;
                }
            """)
            outer.addWidget(bubble)
            outer.addStretch()

    def _download(self, file_id: str):
        from gui import api_client
        emp_id = api_client.get_employee_id()
        if not emp_id:
            QMessageBox.warning(self, "Error", "Not authenticated.")
            return

        try:
            token_resp = api_client.get_download_token(file_id)
            token      = token_resp["download_token"]
            file_name  = token_resp.get("file_name", f"file_{file_id}")
        except Exception as e:
            QMessageBox.warning(self, "Download Failed", str(e))
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save File",
            str(Path.home() / "Downloads" / file_name),
        )
        if not save_path:
            return

        try:
            api_client.download_file(file_id, emp_id, token, save_path)
            QMessageBox.information(self, "Download Complete", f"File saved to:\n{save_path}")
        except Exception as e:
            QMessageBox.warning(self, "Download Failed", str(e))


class ChatWidget(QWidget):
    """
    Chat panel: conversation list (left) + message view with input (right).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(_STYLE)
        self._current_conv  = None
        self._workers       = []
        self._pending_file  = None   # path of file selected but not yet sent
        self._build_ui()
        self._load_conversations()

        # Auto-refresh messages every 15 seconds
        self._msg_timer = QTimer(self)
        self._msg_timer.timeout.connect(self._refresh_messages)
        self._msg_timer.start(15_000)

    # ── UI Construction ────────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background: #334155; }")

        # ── Left: conversation list ────────────────────────────────────────────
        left = QFrame()
        left.setMaximumWidth(260)
        left.setMinimumWidth(200)
        left.setStyleSheet("QFrame { background: #1a1f2e; border-right: 1px solid #334155; }")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        conv_title = QLabel("  💬 Conversations")
        conv_title.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: bold; padding: 12px 8px 8px 8px;")
        left_layout.addWidget(conv_title)

        self.conv_list = QListWidget()
        self.conv_list.itemClicked.connect(self._on_conv_selected)
        left_layout.addWidget(self.conv_list)

        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #64748b;
                border: none; font-size: 11px; padding: 6px;
            }
            QPushButton:hover { color: #94a3b8; }
        """)
        refresh_btn.clicked.connect(self._load_conversations)
        left_layout.addWidget(refresh_btn)

        splitter.addWidget(left)

        # ── Right: message view + input ────────────────────────────────────────
        right = QFrame()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Header
        self.conv_header = QLabel("Select a conversation")
        self.conv_header.setObjectName("conv_header")
        self.conv_header.setStyleSheet("""
            QLabel { background: #1a1f2e; border-bottom: 1px solid #334155;
                     color: #e0e6f0; font-size: 15px; font-weight: bold;
                     padding: 12px 16px; }
        """)
        right_layout.addWidget(self.conv_header)

        # Messages scroll area
        self.msg_area = QScrollArea()
        self.msg_area.setWidgetResizable(True)
        self.msg_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.msg_area.setStyleSheet("QScrollArea { background: #0f1117; border: none; }")

        self.msg_container = QWidget()
        self.msg_container.setStyleSheet("QWidget { background: #0f1117; }")
        self.msg_layout = QVBoxLayout(self.msg_container)
        self.msg_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.msg_layout.setSpacing(4)
        self.msg_layout.setContentsMargins(8, 8, 8, 8)

        self._empty_label = QLabel("Select a conversation to start chatting.")
        self._empty_label.setObjectName("empty_state")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.msg_layout.addWidget(self._empty_label)

        self.msg_area.setWidget(self.msg_container)
        right_layout.addWidget(self.msg_area, stretch=1)

        # File preview banner
        self.file_banner = QFrame()
        self.file_banner.setVisible(False)
        self.file_banner.setStyleSheet("""
            QFrame { background: #1e2336; border-top: 1px solid #334155; padding: 4px 12px; }
        """)
        _fb_layout = QHBoxLayout(self.file_banner)
        _fb_layout.setContentsMargins(0, 0, 0, 0)
        self.file_banner_label = QLabel()
        self.file_banner_label.setStyleSheet("color: #7dd3fc; font-size: 12px;")
        _clear_btn = QPushButton("✕")
        _clear_btn.setFixedSize(20, 20)
        _clear_btn.setStyleSheet("QPushButton { background: transparent; color: #94a3b8; border: none; }")
        _clear_btn.clicked.connect(self._clear_attachment)
        _fb_layout.addWidget(self.file_banner_label)
        _fb_layout.addStretch()
        _fb_layout.addWidget(_clear_btn)
        right_layout.addWidget(self.file_banner)

        # Input row
        input_frame = QFrame()
        input_frame.setStyleSheet("QFrame { background: #0f1117; border-top: 1px solid #334155; }")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(12, 10, 12, 10)
        input_layout.setSpacing(8)

        self.attach_btn = QPushButton("📎")
        self.attach_btn.setObjectName("attach_btn")
        self.attach_btn.setFixedSize(44, 44)
        self.attach_btn.setToolTip("Attach a file")
        self.attach_btn.clicked.connect(self._pick_file)
        input_layout.addWidget(self.attach_btn)

        self.msg_input = QTextEdit()
        self.msg_input.setObjectName("msg_input")
        self.msg_input.setPlaceholderText("Type a message… (Ctrl+Enter to send)")
        self.msg_input.setMaximumHeight(90)
        self.msg_input.setMinimumHeight(44)
        input_layout.addWidget(self.msg_input, stretch=1)

        self.send_btn = QPushButton("Send ➤")
        self.send_btn.setObjectName("send_btn")
        self.send_btn.setFixedHeight(44)
        self.send_btn.clicked.connect(self._send_message)
        input_layout.addWidget(self.send_btn)

        right_layout.addWidget(input_frame)
        splitter.addWidget(right)
        splitter.setSizes([220, 550])

        layout.addWidget(splitter)

    # ── Conversations ──────────────────────────────────────────────────────────

    def _load_conversations(self):
        w = _WorkerThread(api_client.list_conversations)
        w.done.connect(self._populate_conv_list)
        w.failed.connect(lambda e: logger.warning(f"Conv load failed: {e}"))
        w.start()
        self._workers.append(w)

    def _populate_conv_list(self, convs: list):
        self.conv_list.clear()
        for c in convs:
            staff_name = c.get("staff_name") or c.get("staff_user_id", "Staff")
            label = f"📋 {staff_name}\n  {c.get('staff_role', 'manager').title()}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, c)
            self.conv_list.addItem(item)

    def _on_conv_selected(self, item: QListWidgetItem):
        conv = item.data(Qt.ItemDataRole.UserRole)
        self._current_conv = conv
        staff_name = conv.get("staff_name") or "Staff"
        self.conv_header.setText(f"💬 Chat with {staff_name}")
        self._load_messages()

    # ── Messages ───────────────────────────────────────────────────────────────

    def _refresh_messages(self):
        if self._current_conv:
            self._load_messages(scroll_bottom=False)

    def _load_messages(self, scroll_bottom: bool = True):
        if not self._current_conv:
            return
        conv_id = self._current_conv["id"]
        w = _WorkerThread(api_client.get_messages, conv_id)
        w.done.connect(lambda msgs: self._render_messages(msgs, scroll_bottom))
        w.failed.connect(lambda e: logger.warning(f"Messages load failed: {e}"))
        w.start()
        self._workers.append(w)

    def _render_messages(self, messages: list, scroll_bottom: bool = True):
        # Clear existing messages
        while self.msg_layout.count():
            item = self.msg_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not messages:
            empty = QLabel("No messages yet. Say hello! 👋")
            empty.setObjectName("empty_state")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.msg_layout.addWidget(empty)
        else:
            emp_id = api_client.get_employee_id() or ""
            for msg in messages:
                bubble = MessageBubble(msg, emp_id)
                self.msg_layout.addWidget(bubble)

        if scroll_bottom:
            QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        sb = self.msg_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ── Sending ────────────────────────────────────────────────────────────────

    def _send_message(self):
        if not self._current_conv:
            QMessageBox.information(self, "Chat", "Please select a conversation first.")
            return

        conv_id = self._current_conv["id"]

        # File send
        if self._pending_file:
            file_path = self._pending_file
            self._clear_attachment()
            self.send_btn.setEnabled(False)
            self.attach_btn.setEnabled(False)
            self.send_btn.setText("Uploading…")
            w = _WorkerThread(api_client.upload_file, conv_id, file_path)
            w.done.connect(lambda r: self._on_send_done())
            w.failed.connect(self._on_send_fail)
            w.start()
            self._workers.append(w)
            return

        # Text send
        content = self.msg_input.toPlainText().strip()
        if not content:
            return

        self.msg_input.clear()
        self.send_btn.setEnabled(False)
        self.send_btn.setText("Sending…")

        w = _WorkerThread(api_client.send_message, conv_id, content)
        w.done.connect(lambda r: self._on_send_done())
        w.failed.connect(self._on_send_fail)
        w.start()
        self._workers.append(w)

    def _on_send_done(self):
        self.send_btn.setEnabled(True)
        self.attach_btn.setEnabled(True)
        self.send_btn.setText("Send ➤")
        self._load_messages()

    def _on_send_fail(self, error: str):
        self.send_btn.setEnabled(True)
        self.attach_btn.setEnabled(True)
        self.send_btn.setText("Send ➤")
        QMessageBox.warning(self, "Send Failed", error)

    # ── File Attachment ────────────────────────────────────────────────────────

    def _pick_file(self):
        ALLOWED = "Documents (*.pdf *.doc *.docx *.xls *.xlsx *.txt *.csv);;" \
                  "Images (*.png *.jpg *.jpeg *.gif *.webp);;" \
                  "All Files (*)"
        path, _ = QFileDialog.getOpenFileName(self, "Attach File", str(Path.home()), ALLOWED)
        if path:
            size_bytes = Path(path).stat().st_size
            size_mb = size_bytes / (1024 * 1024)
            if size_mb > 20:
                QMessageBox.warning(self, "File Too Large", f"Maximum file size is 20 MB.\nSelected file: {size_mb:.1f} MB")
                return
            self._pending_file = path
            fname = Path(path).name
            fsize = f"{size_bytes / 1024:.1f} KB" if size_bytes < 1024**2 else f"{size_mb:.1f} MB"
            self.file_banner_label.setText(f"📎  {fname}  ({fsize})")
            self.file_banner.setVisible(True)

    def _clear_attachment(self):
        self._pending_file = None
        self.file_banner.setVisible(False)
        self.file_banner_label.setText("")
