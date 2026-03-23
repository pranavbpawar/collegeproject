"""
upload_panel.py – File picker widget.

Emits file_selected(str) when the user chooses a valid path.
"""
import os
import shutil

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from app.core.config import UPLOAD_DIR


class UploadPanel(QGroupBox):
    """
    Lets the user browse for an executable and copies it into UPLOAD_DIR.

    Signals
    -------
    file_selected(path: str)   – emitted after successful copy
    """

    file_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("Executable Upload", parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        info = QLabel(
            "Select an executable (.exe, .bin, ELF, or any binary).\n"
            "The file will be copied to the application's secure upload directory."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #a6adc8; font-size: 12px;")
        layout.addWidget(info)

        row = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setReadOnly(True)
        self._path_edit.setPlaceholderText("No file selected…")
        row.addWidget(self._path_edit, stretch=1)

        self._btn_browse = QPushButton("Browse…")
        self._btn_browse.setFixedWidth(90)
        self._btn_browse.clicked.connect(self._on_browse)
        row.addWidget(self._btn_browse)

        layout.addLayout(row)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

    # ── Slots ────────────────────────────────────────────────────────────────

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Executable",
            os.path.expanduser("~"),
            "Executables (*.exe *.bin *.sh *.AppImage *);;All Files (*)",
        )
        if not path:
            return
        self._import_file(path)

    def _import_file(self, src: str) -> None:
        filename = os.path.basename(src)
        dst = os.path.join(UPLOAD_DIR, filename)

        try:
            shutil.copy2(src, dst)
        except Exception as exc:
            self._set_status(f"❌ Copy failed: {exc}", error=True)
            return

        self._path_edit.setText(dst)
        self._set_status(
            f"✅ Uploaded: {filename}  →  {UPLOAD_DIR}", error=False
        )
        self.file_selected.emit(dst)

    def _set_status(self, msg: str, error: bool = False) -> None:
        color = "#f38ba8" if error else "#a6e3a1"
        self._status_label.setStyleSheet(f"color: {color}; font-size: 12px;")
        self._status_label.setText(msg)

    # ── Public ───────────────────────────────────────────────────────────────

    def current_path(self) -> str:
        return self._path_edit.text()
