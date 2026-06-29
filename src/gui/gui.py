#!/usr/local/bin/sealed_src/.venv/bin/python 
import sys
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow

from src.gui.check_root import ensure_running_as_root

QCoreApplication.setApplicationName("Sealed")
QCoreApplication.setOrganizationName("Sealed")
QGuiApplication.setDesktopFileName("sealed")


def main() -> int:
    ensure_running_as_root()

    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setWindowTitle("Sealed")
    window.setCentralWidget(QLabel("Hello from PySide6"))
    window.resize(500, 300)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
