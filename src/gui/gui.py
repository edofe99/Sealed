#!/usr/local/bin/sealed_src/.venv/bin/python 
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys
from PySide6.QtCore import QCoreApplication, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import (
    QApplication,
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
from src.core.defaults import BLOCK_FILE, SEALED_DIR, SETTINGS_FILE
from src.core.utils import is_block_active, startup_checks
from src.gui.apps import ApplicationsTab
from src.gui.check_root import ensure_running_as_root
from src.gui.file_folders_tab import FileFoldersTab
from src.gui.lock_acces_tab import LockAccessTab
from src.gui.settings_tab import SettingsTab
from src.gui.theme import apply_theme

QCoreApplication.setApplicationName("Sealed")
QCoreApplication.setOrganizationName("Sealed")
QGuiApplication.setDesktopFileName("sealed")
APP_ICON_PATHS = (
    SEALED_DIR / "assets" / "sealed.png",
    Path(__file__).resolve().parents[2] / "assets" / "sealed.png",
    Path("/usr/share/icons/hicolor/512x512/apps/sealed.png"),
)
DEFAULT_SETTINGS = {
    "leechblock_policy": True,
    "block_duration": 60,
    "lock_access": False,
    "lock_access_in_minutes": 60,
}


def app_icon() -> QIcon:
    themed_icon = QIcon.fromTheme("sealed")
    if not themed_icon.isNull():
        return themed_icon

    for icon_path in APP_ICON_PATHS:
        if icon_path.is_file():
            return QIcon(str(icon_path))

    return QIcon()


def load_settings() -> dict[str, object]:
    try:
        # start with DEFAULT_SETTINGS, then overwrite with values from loaded_settings
        return DEFAULT_SETTINGS | json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict[str, object]) -> None:
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ensure_running_as_root()

    app = QApplication(sys.argv)
    apply_theme(app)
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
    lock_access_tab = LockAccessTab(settings, save_settings)
    settings_tab = SettingsTab(settings, save_settings)

    minutes_input = QSpinBox()
    minutes_input.setRange(1, 24 * 60)
    minutes_input.setValue(int(settings["block_duration"]))
    minutes_input.setSuffix(" minutes")
    minutes_input.setAlignment(Qt.AlignCenter)
    minutes_input.setStyleSheet("font-size: 22px; padding: 8px;")
    settings["block_duration"] = minutes_input.value()
    save_settings(settings)
    lock_access_tab.set_block_minutes(minutes_input.value())

    status_label = QLabel()
    status_label.setAlignment(Qt.AlignCenter)
    status_label.setStyleSheet("color: grey; font-size: 14px;")

    start_button = QPushButton("Start Block")
    start_button.setStyleSheet("font-size: 20px; padding: 10px 18px;")

    scheduled_lock_label = QLabel("Scheduled lock user access")
    scheduled_lock_label.setAlignment(Qt.AlignCenter)
    scheduled_lock_label.setStyleSheet("color: #c85f72; font-size: 14px;")

    def update_end_time_label() -> None:
        end_time = datetime.now() + timedelta(minutes=minutes_input.value())
        status_label.setText(
            f"Block End: {end_time.strftime('%Y-%m-%d %H:%M')}"
        )

    def update_remaining_time_label() -> None:
        block_end_text = BLOCK_FILE.read_text(encoding="utf-8").strip()
        block_end = datetime.strptime(block_end_text, "%Y-%m-%d %H:%M")
        remaining = max(block_end - datetime.now(), timedelta())
        total_seconds = int(remaining.total_seconds())
        total_minutes = (total_seconds + 59) // 60
        hours, minutes = divmod(total_minutes, 60)

        status_label.setText(f"Remaining: {hours:02d}:{minutes:02d}")

    def update_ui_state() -> None:
        block_active = is_block_active()

        minutes_input.setEnabled(not block_active)
        start_button.setEnabled(not block_active)
        scheduled_lock_label.setVisible(
            lock_access_tab.lock_access_checkbox.isChecked() and not block_active
        )

        if not block_active:
            update_end_time_label()
        else:
            update_remaining_time_label()

    def start_block() -> None:
        lock_access_minutes = lock_access_tab.selected_minutes()
        if (
            lock_access_minutes is not None
            and lock_access_minutes >= minutes_input.value()
        ):
            QMessageBox.warning(
                window,
                "Sealed",
                "The access lock must start before the block ends.",
            )
            return

        start_button.setEnabled(False)

        try:
            system_block(
                minutes=minutes_input.value(),
                leechblock_blocker=settings_tab.leechblock_policy_enabled(),
                lock_access_minutes=lock_access_minutes,
            )
        except Exception as error:
            QMessageBox.critical(window, "Sealed", str(error))
        else:
            if lock_access_minutes is not None:
                lock_access_tab.mark_lock_scheduled()

        update_ui_state()

    def save_block_duration(value: int) -> None:
        settings["block_duration"] = value
        save_settings(settings)

    timer = QTimer(window)
    timer.timeout.connect(update_ui_state)
    timer.start(1000)
    minutes_input.valueChanged.connect(update_ui_state)
    minutes_input.valueChanged.connect(save_block_duration)
    minutes_input.valueChanged.connect(lock_access_tab.set_block_minutes)
    lock_access_tab.lock_access_checkbox.toggled.connect(update_ui_state)
    start_button.clicked.connect(start_block)
    update_ui_state()

    sealed_block_layout.addWidget(minutes_input)
    sealed_block_layout.addWidget(status_label)
    sealed_block_layout.addWidget(start_button)
    sealed_block_layout.addWidget(scheduled_lock_label)

    tabs.addTab(sealed_block_tab, "Sealed Block")
    tabs.addTab(lock_access_tab, "Lock Access")
    tabs.addTab(ApplicationsTab(), "Applications")
    tabs.addTab(FileFoldersTab(), "Files and Folders")
    tabs.addTab(settings_tab, "Settings")

    window.setCentralWidget(tabs)
    window.resize(650, 420)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
