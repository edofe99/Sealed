from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication, QStyleFactory


SYSTEM_QT_PLUGIN_DIR = Path("/usr/lib/qt6/plugins")
PREFERRED_STYLE = "Breeze"


def apply_theme(app: QApplication) -> None:
    _add_system_qt_plugins()
    _apply_preferred_style(app)


def _add_system_qt_plugins() -> None:
    if SYSTEM_QT_PLUGIN_DIR.is_dir():
        QCoreApplication.addLibraryPath(str(SYSTEM_QT_PLUGIN_DIR))


def _apply_preferred_style(app: QApplication) -> None:
    available_styles = {
        style.casefold(): style for style in QStyleFactory.keys()
    }
    preferred_style = available_styles.get(PREFERRED_STYLE.casefold())
    if preferred_style:
        app.setStyle(preferred_style)
