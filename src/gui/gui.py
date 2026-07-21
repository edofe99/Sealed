#!/usr/local/bin/sealed_src/.venv/bin/python 
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys
from PySide6.QtCore import QCoreApplication, QDateTime, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.block_root import system_block
from src.core.defaults import BLOCK_FILE, SEALED_DIR, SETTINGS_FILE
from src.core.utils import is_block_active, startup_checks, time_string_to_minutes
from src.gui.apps import ApplicationsTab
from src.gui.check_root import ensure_running_as_root
from src.gui.file_folders_tab import FileFoldersTab
from src.gui.lock_acces_tab import LockAccessTab
from src.gui.settings_tab import SettingsTab
from src.gui.theme import apply_theme
from src.gui.widgets import NoWheelDateTimeEdit, ToggleSwitch, configure_date_time_input

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
    "block_time_mode": "minutes",
    "lock_access": False,
    "lock_access_in_minutes": 60,
    "lock_access_mode": "standard",
    "logout_when_lock_access_starts": True,
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
    sealed_block_layout.setContentsMargins(36, 24, 36, 24)

    block_panel = QFrame()
    block_panel.setFrameShape(QFrame.StyledPanel)
    block_panel.setMaximumWidth(390)
    block_panel_layout = QVBoxLayout(block_panel)
    block_panel_layout.setContentsMargins(32, 26, 32, 26)
    block_panel_layout.setSpacing(14)

    title_label = QLabel("When should the block end?")
    title_label.setAlignment(Qt.AlignCenter)
    title_label.setStyleSheet("font-size: 17px; font-weight: 600;")

    settings = load_settings()
    save_settings(settings)

    minutes_input = QSpinBox()
    minutes_input.setRange(1, 24 * 60)
    minutes_input.setValue(int(settings["block_duration"]))
    minutes_input.setSuffix(" minutes")
    minutes_input.setAlignment(Qt.AlignCenter)
    minutes_input.setStyleSheet("font-size: 22px; padding: 8px;")
    minutes_input.setFixedSize(280, 52)
    settings["block_duration"] = minutes_input.value()

    mode_layout = QHBoxLayout()
    mode_layout.setAlignment(Qt.AlignCenter)
    mode_layout.setSpacing(12)

    minutes_mode_label = QLabel("Minutes")
    minutes_mode_label.setFixedWidth(62)
    minutes_mode_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    mode_layout.addWidget(minutes_mode_label)

    time_mode_toggle = ToggleSwitch()
    time_mode_toggle.setAccessibleName("Use an end date instead of minutes")
    time_mode_toggle.setToolTip("Switch between a duration and an exact end date")
    selected_mode = "date" if settings["block_time_mode"] == "date" else "minutes"
    time_mode_toggle.setChecked(selected_mode == "date")
    mode_layout.addWidget(time_mode_toggle)

    date_mode_label = QLabel("Date")
    date_mode_label.setFixedWidth(62)
    date_mode_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    mode_layout.addWidget(date_mode_label)

    date_input = NoWheelDateTimeEdit()
    configure_date_time_input(date_input)
    date_input.setDateTime(QDateTime.currentDateTime().addSecs(60 * 60))
    date_input.setFixedSize(280, 52)

    time_input_stack = QStackedWidget()
    time_input_stack.setFixedSize(280, 52)
    time_input_stack.addWidget(minutes_input)
    time_input_stack.addWidget(date_input)

    settings["block_time_mode"] = selected_mode
    save_settings(settings)

    def selected_block_minutes() -> int:
        if not time_mode_toggle.isChecked():
            return minutes_input.value()

        return time_string_to_minutes(
            date_input.dateTime().toString("yyyy-MM-dd HH:mm")
        )

    lock_access_tab = LockAccessTab(
        settings,
        save_settings,
        get_block_minutes=selected_block_minutes,
    )
    settings_tab = SettingsTab(settings, save_settings)
    lock_access_tab.set_block_minutes(selected_block_minutes())

    status_label = QLabel()
    status_label.setAlignment(Qt.AlignCenter)
    status_label.setStyleSheet("color: grey; font-size: 14px;")
    status_label.setMinimumHeight(22)

    start_button = QPushButton("Start Block")
    start_button.setStyleSheet("font-size: 20px; padding: 10px 18px;")
    start_button.setFixedWidth(220)

    scheduled_lock_label = QLabel("Scheduled access block")
    scheduled_lock_label.setAlignment(Qt.AlignCenter)
    scheduled_lock_label.setStyleSheet("color: #c85f72; font-size: 14px;")

    def update_end_time_label() -> None:
        if time_mode_toggle.isChecked():
            end_time = date_input.dateTime().toString("yyyy-MM-dd HH:mm")
            status_label.setText(f"Block End: {end_time}")
            return

        end_time = datetime.now() + timedelta(minutes=selected_block_minutes())
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
        date_mode = time_mode_toggle.isChecked()

        time_mode_toggle.setEnabled(not block_active)
        time_input_stack.setCurrentIndex(1 if date_mode else 0)
        minutes_input.setEnabled(not block_active)
        date_input.setEnabled(not block_active)
        minutes_mode_label.setStyleSheet(
            "font-weight: 600;" if not date_mode else "color: grey;"
        )
        date_mode_label.setStyleSheet(
            "font-weight: 600;" if date_mode else "color: grey;"
        )

        valid_time = True
        if not block_active:
            try:
                block_minutes = selected_block_minutes()
            except (RuntimeError, ValueError):
                valid_time = False
                status_label.setText("Block date must be in the future.")
            else:
                lock_access_tab.set_block_minutes(block_minutes)
                update_end_time_label()

        start_button.setEnabled(not block_active and valid_time)
        scheduled_lock_label.setVisible(
            lock_access_tab.has_pending_schedules() and not block_active
        )

        if block_active:
            update_remaining_time_label()

    def start_block() -> None:
        try:
            block_minutes = selected_block_minutes()
        except (RuntimeError, ValueError) as error:
            QMessageBox.warning(window, "Sealed", str(error))
            update_ui_state()
            return

        try:
            pending_access_ranges = lock_access_tab.pending_ranges(block_minutes)
        except Exception as error:
            QMessageBox.warning(window, "Sealed", str(error))
            return

        start_button.setEnabled(False)

        try:
            system_block(
                minutes=block_minutes,
                leechblock_blocker=settings_tab.leechblock_policy_enabled(),
                lock_access_minutes=None,
            )
            lock_access_tab.confirm_ranges(pending_access_ranges)
        except Exception as error:
            QMessageBox.critical(window, "Sealed", str(error))

        update_ui_state()

    def save_block_duration(value: int) -> None:
        settings["block_duration"] = value
        save_settings(settings)

    def save_block_time_mode(date_mode: bool) -> None:
        settings["block_time_mode"] = "date" if date_mode else "minutes"
        save_settings(settings)
        update_ui_state()

    timer = QTimer(window)
    timer.timeout.connect(update_ui_state)
    timer.start(1000)
    minutes_input.valueChanged.connect(update_ui_state)
    minutes_input.valueChanged.connect(save_block_duration)
    date_input.dateTimeChanged.connect(update_ui_state)
    time_mode_toggle.toggled.connect(save_block_time_mode)
    lock_access_tab.schedule_changed.connect(update_ui_state)
    start_button.clicked.connect(start_block)
    update_ui_state()

    block_panel_layout.addWidget(title_label)
    block_panel_layout.addLayout(mode_layout)
    block_panel_layout.addWidget(time_input_stack, alignment=Qt.AlignHCenter)
    block_panel_layout.addWidget(status_label)
    block_panel_layout.addSpacing(2)
    block_panel_layout.addWidget(start_button, alignment=Qt.AlignHCenter)
    block_panel_layout.addWidget(scheduled_lock_label)

    sealed_block_layout.addStretch()
    sealed_block_layout.addWidget(block_panel, alignment=Qt.AlignCenter)
    sealed_block_layout.addStretch()

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
