"""
main.py – ExecMonitor application entry point.
"""
import os
import sys


def _load_stylesheet(app) -> None:
    """Load the QSS dark-mode stylesheet."""
    qss_path = os.path.join(os.path.dirname(__file__), "app", "resources", "styles.qss")
    if os.path.isfile(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())


def main() -> None:
    # Must be imported after sys.path is set up
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QFont
    from app.gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("ExecMonitor")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("ExecMonitor")

    # Set default font
    font = QFont("Inter", 10)
    font.setFamily("Inter")
    app.setFont(font)

    _load_stylesheet(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
