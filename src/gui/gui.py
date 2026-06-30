#!/usr/local/bin/sealed_src/.venv/bin/python 
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys
from PySide6.QtCore import QCoreApplication, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QGroupBox,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.block_root import system_block
from src.core.defaults import BLOCK_FILE, SEALED_DIR
from src.core.utils import is_block_active, startup_checks
from src.gui.check_root import ensure_running_as_root
from src.gui.file_folders_tab import FileFoldersTab

QCoreApplication.setApplicationName("Sealed")
QCoreApplication.setOrganizationName("Sealed")
QGuiApplication.setDesktopFileName("sealed")

SETTINGS_FILE = SEALED_DIR / "settings.json"
APP_ICON_PATHS = (
    SEALED_DIR / "assets" / "sealed.png",
    Path(__file__).resolve().parents[2] / "assets" / "sealed.png",
    Path("/usr/share/icons/hicolor/512x512/apps/sealed.png"),
)
DEFAULT_SETTINGS = {
    "block_files_folders": False,
    "leechblock_policy": True,
}


def app_icon() -> QIcon:
    themed_icon = QIcon.fromTheme("sealed")
    if not themed_icon.isNull():
        return themed_icon

    for icon_path in APP_ICON_PATHS:
        if icon_path.is_file():
            return QIcon(str(icon_path))

    return QIcon()


def load_settings() -> dict[str, bool]:
    try:
        settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_SETTINGS.copy()

    return {
        "block_files_folders": bool(
            settings.get(
                "block_files_folders",
                DEFAULT_SETTINGS["block_files_folders"],
            )
        ),
        "leechblock_policy": bool(
            settings.get("leechblock_policy", DEFAULT_SETTINGS["leechblock_policy"])
        ),
    }


def save_settings(settings: dict[str, bool]) -> None:
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ensure_running_as_root()

    app = QApplication(sys.argv)
    icon = app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)

    try:
        startup_checks()
    except Exception as error:
        QMessageBox.critical(None, "Sealed", str(error))
        return 1

    window = QMainWindow()
    window.setWindowTitle("Sealed")
    if not icon.isNull():
        window.setWindowIcon(icon)

    tabs = QTabWidget()

    sealed_block_tab = QWidget()
    sealed_block_layout = QVBoxLayout(sealed_block_tab)
    sealed_block_layout.setAlignment(Qt.AlignCenter)
    sealed_block_layout.setSpacing(12)

    settings = load_settings()
    save_settings(settings)

    settings_group = QGroupBox("Block Settings")
    settings_layout = QVBoxLayout(settings_group)

    block_files_folders_checkbox = QCheckBox("Block Files && Folders")
    block_files_folders_checkbox.setChecked(settings["block_files_folders"])

    leechblock_policy_checkbox = QCheckBox("LeechBlock policy")
    leechblock_policy_checkbox.setChecked(settings["leechblock_policy"])

    settings_layout.addWidget(block_files_folders_checkbox)
    settings_layout.addWidget(leechblock_policy_checkbox)

    minutes_input = QSpinBox()
    minutes_input.setRange(1, 24 * 60)
    minutes_input.setValue(60)
    minutes_input.setSuffix(" minutes")
    minutes_input.setAlignment(Qt.AlignCenter)
    minutes_input.setStyleSheet("font-size: 22px; padding: 8px;")

    status_label = QLabel()
    status_label.setAlignment(Qt.AlignCenter)
    status_label.setStyleSheet("color: grey; font-size: 14px;")

    start_button = QPushButton("Start Block")
    start_button.setStyleSheet("font-size: 20px; padding: 10px 18px;")

    def update_end_time_label() -> None:
        end_time = datetime.now() + timedelta(minutes=minutes_input.value())
        status_label.setText(
            f"Block End: {end_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def update_remaining_time_label() -> None:
        block_end_text = BLOCK_FILE.read_text(encoding="utf-8").strip()
        block_end = datetime.strptime(block_end_text, "%Y-%m-%d %H:%M")
        remaining = max(block_end - datetime.now(), timedelta())
        total_seconds = int(remaining.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        status_label.setText(
            f"Remaining: {hours:02d}:{minutes:02d}:{seconds:02d}"
        )

    def update_ui_state() -> None:
        block_active = is_block_active()

        settings_group.setEnabled(not block_active)
        minutes_input.setEnabled(not block_active)
        start_button.setEnabled(not block_active)

        if not block_active:
            update_end_time_label()
        else:
            update_remaining_time_label()

    def start_block() -> None:
        start_button.setEnabled(False)

        try:
            system_block(
                minutes=minutes_input.value(),
                leechblock_blocker=leechblock_policy_checkbox.isChecked(),
                block_file_folders=block_files_folders_checkbox.isChecked(),
            )
        except Exception as error:
            QMessageBox.critical(window, "Sealed", str(error))

        update_ui_state()

    def save_current_settings() -> None:
        save_settings(
            {
                "block_files_folders": block_files_folders_checkbox.isChecked(),
                "leechblock_policy": leechblock_policy_checkbox.isChecked(),
            }
        )

    timer = QTimer(window)
    timer.timeout.connect(update_ui_state)
    timer.start(1000)
    minutes_input.valueChanged.connect(update_ui_state)
    block_files_folders_checkbox.toggled.connect(save_current_settings)
    leechblock_policy_checkbox.toggled.connect(save_current_settings)
    start_button.clicked.connect(start_block)
    update_ui_state()

    sealed_block_layout.addWidget(settings_group)
    sealed_block_layout.addWidget(minutes_input)
    sealed_block_layout.addWidget(status_label)
    sealed_block_layout.addWidget(start_button)

    tabs.addTab(sealed_block_tab, "Sealed Block")
    tabs.addTab(FileFoldersTab(), "Files and Folders")

    window.setCentralWidget(tabs)
    window.resize(650, 420)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
