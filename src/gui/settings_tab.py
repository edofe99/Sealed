from typing import Callable

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.utils import is_block_active, uninstall


class RedOutlineButton(QPushButton):
    def paintEvent(self, event) -> None:
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#b00020" if self.isEnabled() else "#9e9e9e"), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        outline = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.drawRoundedRect(outline, 4, 4)


class SettingsTab(QWidget):
    def __init__(
        self,
        settings: dict[str, object],
        save_settings: Callable[[dict[str, object]], None],
    ) -> None:
        super().__init__()

        self._settings = settings
        self._save_settings = save_settings

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignLeft)

        self.leechblock_policy_checkbox = QCheckBox("LeechBlock policy")
        self.leechblock_policy_checkbox.setChecked(
            bool(settings["leechblock_policy"])
        )
        self.leechblock_policy_checkbox.toggled.connect(
            self._save_leechblock_policy
        )
        layout.addWidget(self.leechblock_policy_checkbox)

        self.logout_on_lock_access_checkbox = QCheckBox(
            "Logout when Lock Access start"
        )
        self.logout_on_lock_access_checkbox.setChecked(
            bool(settings.get("logout_when_lock_access_starts", True))
        )
        self.logout_on_lock_access_checkbox.toggled.connect(
            self._save_logout_on_lock_access
        )
        layout.addWidget(self.logout_on_lock_access_checkbox)
        layout.addStretch()

        self.uninstall_button = RedOutlineButton("Uninstall")
        self.uninstall_button.setStyleSheet(
            "QPushButton { font-size: 14px; padding: 4px 10px; color: #b00020; }"
            "QPushButton:disabled { color: #9e9e9e; }"
        )
        self.uninstall_button.clicked.connect(self._confirm_uninstall)
        layout.addWidget(self.uninstall_button)

        self._state_timer = QTimer(self)
        self._state_timer.timeout.connect(self._update_control_states)
        self._state_timer.start(1000)
        self._update_control_states()

    def leechblock_policy_enabled(self) -> bool:
        return self.leechblock_policy_checkbox.isChecked()

    def _save_leechblock_policy(self, checked: bool) -> None:
        self._settings["leechblock_policy"] = checked
        self._save_settings(self._settings)

    def _save_logout_on_lock_access(self, checked: bool) -> None:
        self._settings["logout_when_lock_access_starts"] = checked
        self._save_settings(self._settings)

    def _update_control_states(self) -> None:
        block_active = is_block_active()
        self.leechblock_policy_checkbox.setEnabled(not block_active)
        self.uninstall_button.setEnabled(not block_active)

    def _confirm_uninstall(self) -> None:
        if is_block_active():
            QMessageBox.information(self, "Sealed", "You can't uninstall Sealed while a block is active.")
            self._update_control_states()
            return

        answer = QMessageBox.question(
            self,
            "Uninstall Sealed",
            (
                "Are you sure you want to uninstall Sealed?\n\n"
                "This will remove all installed Sealed files, launchers, icons, "
                "policy rules, and sudoers entries."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            uninstall()
            QMessageBox.information(self, "Sealed", "Sealed has been uninstalled.")
            QApplication.quit()
        except RuntimeError as error:
            if str(error) == "Sealed has been uninstalled.":
                QMessageBox.information(self, "Sealed", str(error))
                QApplication.quit()
                return

            QMessageBox.critical(self, "Sealed", str(error))
        except Exception as error:
            QMessageBox.critical(self, "Sealed", str(error))
