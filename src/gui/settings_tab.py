from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton, QVBoxLayout, QWidget

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
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignBottom)

        self.uninstall_button = RedOutlineButton("Uninstall")
        self.uninstall_button.setStyleSheet(
            "font-size: 14px; padding: 4px 10px; color: #b00020;"
        )
        self.uninstall_button.clicked.connect(self._confirm_uninstall)
        layout.addWidget(self.uninstall_button)

        self._state_timer = QTimer(self)
        self._state_timer.timeout.connect(self._update_control_states)
        self._state_timer.start(1000)
        self._update_control_states()

    def _update_control_states(self) -> None:
        self.uninstall_button.setEnabled(not is_block_active())

    def _confirm_uninstall(self) -> None:
        if is_block_active():
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
