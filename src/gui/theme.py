from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication


def apply_theme(app: QApplication) -> None:
    family = (
        "DejaVu Sans"
        if "DejaVu Sans" in QFontDatabase.families()
        else "Noto Sans"
    )
    app.setFont(QFont(family, 10))
