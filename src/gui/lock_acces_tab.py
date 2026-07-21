from datetime import datetime, timedelta
from typing import Callable

from PySide6.QtCore import QDateTime, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.defaults import BLOCK_FILE, MINIMUM_MINUTES_TO_LOCK
from src.core.lock_access import (
    TIME_FORMAT,
    clear_lock_access_schedules,
    get_lock_access_schedules,
    lock_access,
    validate_lock_access_range,
)
from src.core.utils import get_remaining_minutes, is_block_active, time_string_to_minutes
from src.gui.widgets import NoWheelDateTimeEdit, ToggleSwitch, configure_date_time_input


class ScheduleRow(QFrame):
    remove_requested = Signal(object)

    def __init__(
        self,
        start: datetime,
        end: datetime,
        editable: bool,
    ) -> None:
        super().__init__()
        self.editable = editable
        self.setObjectName("scheduleCell")
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(
            "QFrame#scheduleCell {"
            " background-color: palette(window);"
            " border: 1px solid palette(mid);"
            "}"
        )
        self.setMinimumWidth(490)
        self.setMaximumWidth(520)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QGridLayout(self)
        layout.setContentsMargins(12, 8, 12, 10)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(4)

        start_label = QLabel("Lock access")
        end_label = QLabel("Unlock access")
        start_label.setStyleSheet("color: grey; font-size: 12px;")
        end_label.setStyleSheet("color: grey; font-size: 12px;")

        self.start_input = NoWheelDateTimeEdit()
        self.end_input = NoWheelDateTimeEdit()
        for date_input in (self.start_input, self.end_input):
            configure_date_time_input(date_input)
            date_input.setStyleSheet(
                "QDateTimeEdit { font-size: 15px; padding: 6px; }"
            )
            date_input.setFixedSize(205, 40)

        self.start_input.setDateTime(QDateTime(start))
        self.end_input.setDateTime(QDateTime(end))

        layout.addWidget(start_label, 0, 0)
        layout.addWidget(end_label, 0, 1)
        layout.addWidget(self.start_input, 1, 0)
        layout.addWidget(self.end_input, 1, 1)

        if editable:
            remove_button = QPushButton("−")
            remove_button.setToolTip("Remove this schedule")
            remove_button.setFixedSize(34, 34)
            remove_button.setStyleSheet("font-size: 20px;")
            remove_button.clicked.connect(lambda: self.remove_requested.emit(self))
            layout.addWidget(remove_button, 1, 2)
        else:
            for date_input in (self.start_input, self.end_input):
                date_input.setReadOnly(True)
                date_input.setCalendarPopup(False)
                date_input.setButtonSymbols(QAbstractSpinBox.NoButtons)
                date_input.setFocusPolicy(Qt.NoFocus)
            confirmed_label = QLabel("Confirmed")
            confirmed_label.setStyleSheet("color: grey; font-size: 12px;")
            confirmed_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(confirmed_label, 1, 2)

    def times(self) -> tuple[datetime, datetime]:
        start = datetime.strptime(
            self.start_input.dateTime().toString("yyyy-MM-dd HH:mm"),
            TIME_FORMAT,
        )
        end = datetime.strptime(
            self.end_input.dateTime().toString("yyyy-MM-dd HH:mm"),
            TIME_FORMAT,
        )
        return start, end

    def set_bounds(self, earliest: datetime, latest: datetime) -> None:
        if not self.editable or latest <= earliest:
            return
        minimum = QDateTime(earliest)
        maximum = QDateTime(latest)
        self.start_input.setDateTimeRange(minimum, maximum)
        self.end_input.setDateTimeRange(minimum, maximum)


class LockAccessTab(QWidget):
    schedule_changed = Signal()

    def __init__(
        self,
        settings: dict[str, object],
        save_settings: Callable[[dict[str, object]], None],
        get_block_minutes: Callable[[], int],
    ) -> None:
        super().__init__()
        self._settings = settings
        self._save_settings = save_settings
        self._get_block_minutes = get_block_minutes
        self._block_minutes = max(1, get_block_minutes())
        self._draft_rows: list[ScheduleRow] = []
        self._confirmed_rows: list[ScheduleRow] = []
        self._last_block_active = is_block_active()

        if not self._last_block_active:
            clear_lock_access_schedules()

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(24, 18, 24, 18)

        panel = QFrame()
        panel.setObjectName("lockAccessPanel")
        panel.setFrameShape(QFrame.NoFrame)
        panel.setStyleSheet(
            "QFrame#lockAccessPanel { background: transparent; border: none; }"
        )
        panel.setMinimumSize(520, 320)
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(24, 20, 24, 20)
        panel_layout.setSpacing(12)

        title = QLabel("Access blocking")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 17px; font-weight: 600;")

        mode_layout = QHBoxLayout()
        mode_layout.setAlignment(Qt.AlignCenter)
        mode_layout.setSpacing(12)
        self.standard_mode_label = QLabel("Standard")
        self.standard_mode_label.setFixedWidth(90)
        self.standard_mode_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.mode_toggle = ToggleSwitch()
        self.mode_toggle.setAccessibleName("Use multiple scheduled access blocks")
        self.mode_toggle.setToolTip("Switch between standard and scheduled access blocking")
        self.scheduled_mode_label = QLabel("Scheduled")
        self.scheduled_mode_label.setFixedWidth(90)
        self.scheduled_mode_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        mode_layout.addWidget(self.standard_mode_label)
        mode_layout.addWidget(self.mode_toggle)
        mode_layout.addWidget(self.scheduled_mode_label)

        self.views = QStackedWidget()
        self.views.setStyleSheet("QStackedWidget { background: transparent; }")
        self.views.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.standard_view = self._build_standard_view()
        self.scheduled_view = self._build_scheduled_view()
        self.views.addWidget(self.standard_view)
        self.views.addWidget(self.scheduled_view)

        self.lock_button = QPushButton("Block User Access")
        self.lock_button.setStyleSheet("font-size: 18px; padding: 9px 16px;")
        self.lock_button.setFixedWidth(230)

        panel_layout.addWidget(title)
        panel_layout.addLayout(mode_layout)
        panel_layout.addWidget(self.views)
        panel_layout.addWidget(self.lock_button, alignment=Qt.AlignHCenter)
        outer_layout.addWidget(panel)

        selected_mode = (
            "scheduled"
            if settings.get("lock_access_mode") == "scheduled"
            else "standard"
        )
        self.mode_toggle.setChecked(selected_mode == "scheduled")
        self._settings["lock_access_mode"] = selected_mode
        self._save_settings(self._settings)

        self._reload_confirmed_rows()
        self._add_draft_row()

        self.mode_toggle.toggled.connect(self._mode_changed)
        self.lock_access_checkbox.toggled.connect(self._settings_changed)
        self.minutes_input.valueChanged.connect(self._settings_changed)
        self.lock_button.clicked.connect(self._schedule_lock)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update_ui_state)
        self._timer.start(1000)
        self.update_ui_state()

    def _build_standard_view(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)

        self.lock_access_checkbox = QCheckBox("Block user access in:")
        self.lock_access_checkbox.setChecked(bool(self._settings["lock_access"]))
        self.minutes_input = QSpinBox()
        self.minutes_input.setRange(1, 24 * 60)
        self.minutes_input.setValue(int(self._settings["lock_access_in_minutes"]))
        self.minutes_input.setSuffix(" minutes")
        self.minutes_input.setAlignment(Qt.AlignCenter)
        self.minutes_input.setStyleSheet("font-size: 22px; padding: 8px;")
        self.minutes_input.setFixedSize(220, 52)
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: grey; font-size: 14px;")

        layout.addWidget(self.lock_access_checkbox, alignment=Qt.AlignHCenter)
        layout.addWidget(self.minutes_input, alignment=Qt.AlignHCenter)
        layout.addWidget(self.status_label)
        return view

    def _build_scheduled_view(self) -> QWidget:
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.rows_widget = QWidget()
        self.rows_widget.setObjectName("scheduleRows")
        self.rows_widget.setStyleSheet(
            "QWidget#scheduleRows { background: transparent; }"
        )
        self.rows_layout = QVBoxLayout(self.rows_widget)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(8)
        self.rows_layout.setAlignment(Qt.AlignTop)

        self.add_button = QPushButton("+")
        self.add_button.setToolTip("Add another access block")
        self.add_button.setFixedSize(42, 34)
        self.add_button.setStyleSheet("font-size: 20px;")
        self.add_button.clicked.connect(self._add_draft_row)
        self.rows_layout.addWidget(self.add_button, alignment=Qt.AlignHCenter)

        self.schedule_scroll = QScrollArea()
        self.schedule_scroll.setWidgetResizable(True)
        self.schedule_scroll.setFrameShape(QFrame.NoFrame)
        self.schedule_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )
        self.schedule_scroll.viewport().setAutoFillBackground(False)
        self.schedule_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.schedule_scroll.setMinimumHeight(155)
        self.schedule_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.schedule_scroll.setWidget(self.rows_widget)

        self.cutoff_label = QLabel()
        self.cutoff_label.setAlignment(Qt.AlignCenter)
        self.cutoff_label.setStyleSheet("color: grey; font-size: 12px;")

        layout.addWidget(self.schedule_scroll)
        layout.addWidget(self.cutoff_label)
        return view

    def _current_block_end(self, block_minutes: int | None = None) -> datetime:
        if is_block_active():
            return datetime.strptime(
                BLOCK_FILE.read_text(encoding="utf-8").strip(),
                TIME_FORMAT,
            )
        minutes = self._block_minutes if block_minutes is None else block_minutes
        return (datetime.now() + timedelta(minutes=minutes)).replace(
            second=0,
            microsecond=0,
        )

    def _scheduled_cutoff(self, block_minutes: int | None = None) -> datetime:
        return self._current_block_end(block_minutes) - timedelta(
            minutes=MINIMUM_MINUTES_TO_LOCK
        )

    def _default_range(self) -> tuple[datetime, datetime]:
        now = datetime.now().replace(second=0, microsecond=0)
        cutoff = self._scheduled_cutoff()
        intervals = sorted(
            (row.times() for row in self._confirmed_rows + self._draft_rows),
            key=lambda interval: interval[0],
        )

        def find_gap(initial_start: datetime) -> tuple[datetime, datetime] | None:
            candidate_start = initial_start
            for interval_start, interval_end in intervals:
                if interval_end < candidate_start:
                    continue
                gap_end = interval_start - timedelta(minutes=1)
                if candidate_start + timedelta(minutes=1) <= gap_end:
                    return candidate_start, min(
                        candidate_start + timedelta(minutes=10),
                        gap_end,
                    )
                candidate_start = max(
                    candidate_start,
                    interval_end + timedelta(minutes=1),
                )

            if candidate_start + timedelta(minutes=1) <= cutoff:
                return candidate_start, min(
                    candidate_start + timedelta(minutes=10),
                    cutoff,
                )
            return None

        default_range = find_gap(now + timedelta(minutes=10))
        if default_range is None:
            default_range = find_gap(now + timedelta(minutes=1))
        if default_range is not None:
            return default_range
        return now + timedelta(minutes=1), now + timedelta(minutes=2)

    def _add_draft_row(self) -> None:
        start, end = self._default_range()
        row = ScheduleRow(start, end, editable=True)
        row.remove_requested.connect(self._remove_draft_row)
        row.start_input.dateTimeChanged.connect(
            lambda _value: self.schedule_changed.emit()
        )
        row.end_input.dateTimeChanged.connect(
            lambda _value: self.schedule_changed.emit()
        )
        self._draft_rows.append(row)
        self.rows_layout.insertWidget(
            self.rows_layout.count() - 1,
            row,
            alignment=Qt.AlignHCenter,
        )
        self._apply_date_bounds(row)
        self.schedule_changed.emit()

    def _remove_draft_row(self, row: ScheduleRow) -> None:
        if row not in self._draft_rows:
            return
        self._draft_rows.remove(row)
        self.rows_layout.removeWidget(row)
        row.deleteLater()
        self.schedule_changed.emit()

    def _reload_confirmed_rows(self) -> None:
        for row in self._confirmed_rows:
            self.rows_layout.removeWidget(row)
            row.deleteLater()
        self._confirmed_rows.clear()

        insert_at = 0
        for schedule in get_lock_access_schedules():
            row = ScheduleRow(
                datetime.strptime(schedule["start"], TIME_FORMAT),
                datetime.strptime(schedule["end"], TIME_FORMAT),
                editable=False,
            )
            self._confirmed_rows.append(row)
            self.rows_layout.insertWidget(
                insert_at,
                row,
                alignment=Qt.AlignHCenter,
            )
            insert_at += 1

    def _apply_date_bounds(self, row: ScheduleRow) -> None:
        earliest = datetime.now().replace(second=0, microsecond=0) + timedelta(minutes=1)
        row.set_bounds(earliest, self._scheduled_cutoff())

    def _mode_changed(self, scheduled: bool) -> None:
        self._settings["lock_access_mode"] = "scheduled" if scheduled else "standard"
        self._save_settings(self._settings)
        self.update_ui_state()
        self.schedule_changed.emit()

    def _settings_changed(self) -> None:
        self._settings["lock_access"] = self.lock_access_checkbox.isChecked()
        self._settings["lock_access_in_minutes"] = self.minutes_input.value()
        self._save_settings(self._settings)
        self.update_ui_state()
        self.schedule_changed.emit()

    def set_block_minutes(self, block_minutes: int) -> None:
        self._block_minutes = max(1, block_minutes)
        maximum = max(1, self._block_minutes - MINIMUM_MINUTES_TO_LOCK)
        self.minutes_input.setMaximum(maximum)
        for row in self._draft_rows:
            self._apply_date_bounds(row)
        self._update_cutoff_label()

    def has_pending_schedules(self) -> bool:
        if self.mode_toggle.isChecked():
            return bool(self._draft_rows)
        return self.lock_access_checkbox.isChecked()

    def pending_ranges(
        self,
        block_minutes: int | None = None,
    ) -> list[tuple[int, int]]:
        now = datetime.now()
        block_end = self._current_block_end(block_minutes)

        if not self.mode_toggle.isChecked():
            if not self.lock_access_checkbox.isChecked():
                return []
            start_minutes = self.minutes_input.value()
            end_minutes = time_string_to_minutes(block_end.strftime(TIME_FORMAT))
            start = (now + timedelta(minutes=start_minutes)).replace(second=0, microsecond=0)
            validate_lock_access_range(start, block_end)
            latest_start = block_end - timedelta(minutes=MINIMUM_MINUTES_TO_LOCK)
            if start > latest_start:
                raise RuntimeError(
                    f"Lock access must start by {latest_start.strftime(TIME_FORMAT)}."
                )
            return [(start_minutes, end_minutes)]

        cutoff = block_end - timedelta(minutes=MINIMUM_MINUTES_TO_LOCK)
        existing = get_lock_access_schedules()
        pending: list[tuple[int, int]] = []

        for row in self._draft_rows:
            start, end = row.times()
            if end > cutoff or start > cutoff:
                raise RuntimeError(
                    f"Scheduled access blocks must end by {cutoff.strftime(TIME_FORMAT)}."
                )
            validate_lock_access_range(start, end, existing)
            start_minutes = time_string_to_minutes(start.strftime(TIME_FORMAT))
            end_minutes = time_string_to_minutes(end.strftime(TIME_FORMAT))
            pending.append((start_minutes, end_minutes))
            existing.append(
                {
                    "id": "pending",
                    "start": start.strftime(TIME_FORMAT),
                    "end": end.strftime(TIME_FORMAT),
                }
            )

        return pending

    def confirm_ranges(self, ranges: list[tuple[int, int]]) -> None:
        for start_minutes, end_minutes in ranges:
            lock_access(
                start_minutes,
                end_minutes,
                logout_when_lock_starts=bool(
                    self._settings.get("logout_when_lock_access_starts", True)
                ),
            )

        if self.mode_toggle.isChecked() and ranges:
            for row in self._draft_rows:
                self.rows_layout.removeWidget(row)
                row.deleteLater()
            self._draft_rows.clear()
            self._reload_confirmed_rows()
        elif ranges:
            self.lock_access_checkbox.setChecked(False)
            self._reload_confirmed_rows()
        self.update_ui_state()

    def selected_minutes(self) -> int | None:
        """Compatibility helper for callers that still use Standard mode."""
        if self.mode_toggle.isChecked() or not self.lock_access_checkbox.isChecked():
            return None
        return self.minutes_input.value()

    def mark_lock_scheduled(self) -> None:
        self._reload_confirmed_rows()
        self.update_ui_state()

    def _update_standard_label(self) -> None:
        lock_time = datetime.now() + timedelta(minutes=self.minutes_input.value())
        self.status_label.setText(
            f"User will be locked at {lock_time.strftime(TIME_FORMAT)}"
        )

    def _update_cutoff_label(self) -> None:
        cutoff = self._scheduled_cutoff()
        self.cutoff_label.setText(
            f"Latest scheduled time: {cutoff.strftime(TIME_FORMAT)}"
        )

    def update_ui_state(self) -> None:
        block_active = is_block_active()
        if self._last_block_active and not block_active:
            clear_lock_access_schedules()
            self._reload_confirmed_rows()

        if block_active:
            remaining_minutes = get_remaining_minutes()
            if remaining_minutes is not None:
                self.minutes_input.setMaximum(
                    max(1, remaining_minutes - MINIMUM_MINUTES_TO_LOCK)
                )

        scheduled_mode = self.mode_toggle.isChecked()
        self.mode_toggle.setEnabled(not block_active)
        self.views.setCurrentIndex(1 if scheduled_mode else 0)
        self.standard_mode_label.setStyleSheet(
            "font-weight: 600;" if not scheduled_mode else "color: grey;"
        )
        self.scheduled_mode_label.setStyleSheet(
            "font-weight: 600;" if scheduled_mode else "color: grey;"
        )
        self.minutes_input.setEnabled(self.lock_access_checkbox.isChecked())
        self.status_label.setVisible(self.lock_access_checkbox.isChecked())
        self.lock_button.setVisible(block_active)
        self.lock_button.setEnabled(block_active and self.has_pending_schedules())
        self._update_standard_label()
        self._update_cutoff_label()
        self._last_block_active = block_active

    def _schedule_lock(self) -> None:
        remaining_minutes = get_remaining_minutes()
        if remaining_minutes is None:
            QMessageBox.warning(self, "Sealed", "There is no active block.")
            self.update_ui_state()
            return

        try:
            ranges = self.pending_ranges(remaining_minutes)
            self.confirm_ranges(ranges)
        except Exception as error:
            QMessageBox.critical(self, "Sealed", str(error))
