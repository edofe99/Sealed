from datetime import datetime, timedelta
from typing import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.core.defaults import MINIMUM_MINUTES_TO_LOCK, USER_LOCK_FILE
from src.core.lock_access import lock_access
from src.core.utils import get_remaining_minutes, is_block_active


class LockAccessTab(QWidget):
    def __init__(
        self,
        settings: dict[str, object],
        save_settings: Callable[[dict[str, object]], None],
    ) -> None:
        super().__init__()

        self._settings = settings
        self._save_settings = save_settings
        self._lock_scheduled = False
        self._last_block_active = False

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)

        self.lock_access_checkbox = QCheckBox("Block user access in:")
        self.lock_access_checkbox.setChecked(bool(settings["lock_access"]))

        self.minutes_input = QSpinBox()
        self.minutes_input.setRange(1, 24 * 60)
        self.minutes_input.setValue(int(settings["lock_access_in_minutes"]))
        self.minutes_input.setSuffix(" minutes")
        self.minutes_input.setAlignment(Qt.AlignCenter)
        self.minutes_input.setStyleSheet("font-size: 22px; padding: 8px;")

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: grey; font-size: 14px;")

        self.lock_button = QPushButton("Block User Access")
        self.lock_button.setStyleSheet("font-size: 20px; padding: 10px 18px;")

        layout.addWidget(self.lock_access_checkbox)
        layout.addWidget(self.minutes_input)
        layout.addWidget(self.status_label)
        layout.addWidget(self.lock_button)

        self.lock_access_checkbox.toggled.connect(self._settings_changed)
        self.minutes_input.valueChanged.connect(self._settings_changed)
        self.lock_button.clicked.connect(self._schedule_lock)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update_ui_state)
        self._timer.start(1000)
        self.update_ui_state()

    def selected_minutes(self) -> int | None:
        if USER_LOCK_FILE.exists() or not self.lock_access_checkbox.isChecked():
            return None
        return self.minutes_input.value()

    def set_block_minutes(self, block_minutes: int) -> None:
        maximum = max(1, block_minutes - MINIMUM_MINUTES_TO_LOCK)
        self.minutes_input.setMaximum(maximum)

    def mark_lock_scheduled(self) -> None:
        self._lock_scheduled = True
        self.update_ui_state()

    def _settings_changed(self) -> None:
        self._settings["lock_access"] = self.lock_access_checkbox.isChecked()
        self._settings["lock_access_in_minutes"] = self.minutes_input.value()
        self._save_settings(self._settings)
        self.update_ui_state()

    def _update_time_label(self) -> None:
        lock_time = datetime.now() + timedelta(minutes=self.minutes_input.value())
        self.status_label.setText(
            f"User will be locked at: {lock_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def update_ui_state(self) -> None:
        checkbox_active = self.lock_access_checkbox.isChecked()
        block_active = is_block_active()
        user_lock_active = USER_LOCK_FILE.exists()

        if self._last_block_active and not block_active:
            self._lock_scheduled = False

        self.setEnabled(not user_lock_active)
        self.minutes_input.setEnabled(checkbox_active and not user_lock_active)
        self.status_label.setVisible(checkbox_active)
        self.lock_button.setVisible(
            block_active and checkbox_active and not user_lock_active
        )
        self.lock_button.setEnabled(
            block_active
            and checkbox_active
            and not user_lock_active
            and not self._lock_scheduled
        )
        self._update_time_label()
        self._last_block_active = block_active

    def _schedule_lock(self) -> None:
        remaining_minutes = get_remaining_minutes()
        delay_minutes = self.minutes_input.value()

        if remaining_minutes is None:
            QMessageBox.warning(self, "Sealed", "There is no active block.")
            self.update_ui_state()
            return

        if delay_minutes >= remaining_minutes:
            QMessageBox.warning(
                self,
                "Sealed",
                "The access lock must start before the current block ends.",
            )
            return

        try:
            lock_access(
                minutes_to_start=delay_minutes,
                minutes_to_end=remaining_minutes - delay_minutes,
            )
        except Exception as error:
            QMessageBox.critical(self, "Sealed", str(error))
            return

        self._lock_scheduled = True
        self.update_ui_state()
