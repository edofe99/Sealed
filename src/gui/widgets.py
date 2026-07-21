from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QCalendarWidget, QCheckBox, QDateTimeEdit


class ToggleSwitch(QCheckBox):
    """Compact neutral two-state switch."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(52, 28)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)

    def hitButton(self, position) -> bool:
        return self.rect().contains(position)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        track_color = self.palette().mid().color()
        knob_color = self.palette().base().color()
        if not self.isEnabled():
            track_color.setAlpha(100)
            knob_color.setAlpha(150)

        painter.setPen(Qt.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(
            QRectF(1, 4, self.width() - 2, self.height() - 8),
            3,
            3,
        )
        knob_size = 18
        knob_x = self.width() - knob_size - 5 if self.isChecked() else 5
        painter.setBrush(knob_color)
        painter.drawRoundedRect(
            QRectF(knob_x, 5, knob_size, knob_size),
            2,
            2,
        )


class NoWheelDateTimeEdit(QDateTimeEdit):
    """Date-time field that cannot be changed accidentally with the wheel."""

    def wheelEvent(self, event) -> None:
        event.ignore()


def configure_date_time_input(date_input: QDateTimeEdit) -> None:
    date_input.setDisplayFormat("yyyy-MM-dd HH:mm")
    date_input.setCalendarPopup(True)
    date_input.setAlignment(Qt.AlignCenter)
    date_input.setStyleSheet(
        "QDateTimeEdit { font-size: 22px; padding: 8px; }"
    )

    calendar = date_input.calendarWidget()
    calendar.setMinimumSize(280, 210)
    calendar.setGridVisible(False)
    calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
    calendar.setHorizontalHeaderFormat(QCalendarWidget.ShortDayNames)
    calendar.setStyleSheet(
        """
        QCalendarWidget QWidget#qt_calendar_navigationbar {
            background-color: palette(button);
            border-bottom: 1px solid palette(mid);
            padding: 4px;
        }
        QCalendarWidget QToolButton {
            background: transparent;
            border: none;
            border-radius: 5px;
            color: palette(button-text);
            font-weight: 600;
            min-height: 28px;
            padding: 3px 8px;
        }
        QCalendarWidget QToolButton:hover {
            background: palette(midlight);
        }
        QCalendarWidget QSpinBox {
            background: palette(base);
            border: 1px solid palette(mid);
            border-radius: 4px;
            padding: 3px;
        }
        QCalendarWidget QAbstractItemView {
            background: palette(base);
            border: none;
            outline: none;
            selection-background-color: palette(highlight);
            selection-color: palette(highlighted-text);
            padding: 6px;
        }
        QCalendarWidget QMenu {
            background: palette(base);
        }
        """
    )
