import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHeaderView,
    QHBoxLayout,
    QAbstractItemView,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.core.block_file_folder import add_file_folder
from src.core.defaults import FILE_FOLDERS_TO_BLOCK
from src.core.utils import is_block_active


ORIGINAL_PATH_ROLE = Qt.UserRole
PENDING_CUSTOM_PATH_ROLE = Qt.UserRole + 1


class PathTableWidget(QTableWidget):
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if (
            event.key() in {Qt.Key_Return, Qt.Key_Enter}
            and self.currentColumn() == 1
            and self.state() != QAbstractItemView.State.EditingState
        ):
            item = self.currentItem()
            if item is not None and item.flags() & Qt.ItemIsEditable:
                self.editItem(item)
                event.accept()
                return

        super().keyPressEvent(event)


class FileFoldersTab(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self._entries: list[dict[str, Any]] = []
        self._delete_buttons: list[QToolButton] = []
        self._block_execution_checkboxes: list[QCheckBox] = []
        self._last_block_active: bool | None = None
        self._loading = False

        layout = QVBoxLayout(self)

        self.table = PathTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Delete", "Path", "Block Execution"])
        self.table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.ResizeToContents,
        )
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            2,
            QHeaderView.ResizeToContents,
        )
        self.table.horizontalHeader().setSectionsClickable(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked)
        self.table.setFocusPolicy(Qt.StrongFocus)
        self.table.setAlternatingRowColors(True)
        self.table.itemChanged.connect(self._save_path_change)

        layout.addWidget(self.table)

        buttons_layout = QHBoxLayout()
        self.add_file_button = QPushButton("Add file")
        self.add_file_button.clicked.connect(self._add_file)
        buttons_layout.addWidget(self.add_file_button)

        self.add_folder_button = QPushButton("Add folder")
        self.add_folder_button.clicked.connect(self._add_folder)
        buttons_layout.addWidget(self.add_folder_button)

        self.add_custom_path_button = QPushButton("Add custom path")
        self.add_custom_path_button.clicked.connect(self._add_custom_path)
        buttons_layout.addWidget(self.add_custom_path_button)
        layout.addLayout(buttons_layout)

        self.load_entries()

        self._state_timer = QTimer(self)
        self._state_timer.timeout.connect(self._update_control_states)
        self._state_timer.start(1000)

    def load_entries(self) -> None:
        self._loading = True

        try:
            data = json.loads(FILE_FOLDERS_TO_BLOCK.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            data = []

        if not isinstance(data, list):
            data = []

        self._entries = self._sort_entries(
            [entry for entry in data if isinstance(entry, dict)]
        )
        self._delete_buttons = []
        self._block_execution_checkboxes = []

        self.table.setRowCount(0)
        for row, entry in enumerate(self._entries):
            self.table.insertRow(row)
            self._add_table_row(row, entry)

        self._loading = False
        self._update_control_states()

    def _sort_entries(self, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(entries, key=lambda entry: bool(entry.get("block_execution")))

    def _add_table_row(
        self,
        row: int,
        entry: dict[str, Any],
        pending_custom_path: bool = False,
    ) -> QTableWidgetItem:
        delete_button = QToolButton()
        delete_button.setText("X")
        delete_button.setAutoRaise(True)
        delete_button.setCursor(Qt.PointingHandCursor)
        delete_button.setStyleSheet(
            "QToolButton { color: #b00020; border: none; padding: 2px 6px; }"
            "QToolButton:disabled { color: grey; }"
        )
        delete_button.setToolTip("Delete")
        delete_button.clicked.connect(
            lambda _checked=False, button=delete_button: self._delete_button_row(button)
        )
        delete_cell = QWidget()
        delete_layout = QHBoxLayout(delete_cell)
        delete_layout.addWidget(delete_button)
        delete_layout.setAlignment(Qt.AlignCenter)
        delete_layout.setContentsMargins(0, 0, 0, 0)

        path = str(entry.get("path", ""))
        path_item = QTableWidgetItem(path)
        path_item.setData(ORIGINAL_PATH_ROLE, path)
        path_item.setData(PENDING_CUSTOM_PATH_ROLE, pending_custom_path)
        path_item.setFlags(
            self._path_item_flags(force_editable=pending_custom_path)
        )

        block_execution_checkbox = QCheckBox()
        block_execution_checkbox.setChecked(bool(entry.get("block_execution")))
        block_execution_checkbox.toggled.connect(
            lambda checked, checkbox=block_execution_checkbox: (
                self._save_checkbox_widget_change(checkbox, checked)
            )
        )
        checkbox_cell = QWidget()
        checkbox_layout = QHBoxLayout(checkbox_cell)
        checkbox_layout.addWidget(block_execution_checkbox)
        checkbox_layout.setAlignment(Qt.AlignCenter)
        checkbox_layout.setContentsMargins(0, 0, 0, 0)

        self.table.setCellWidget(row, 0, delete_cell)
        self.table.setItem(row, 1, path_item)
        self.table.setCellWidget(row, 2, checkbox_cell)
        self._delete_buttons.insert(row, delete_button)
        self._block_execution_checkboxes.insert(row, block_execution_checkbox)
        return path_item

    def _path_item_flags(
        self,
        block_active: bool | None = None,
        force_editable: bool = False,
    ) -> Qt.ItemFlag:
        if block_active is None:
            block_active = is_block_active()

        flags = Qt.ItemIsEnabled
        if force_editable or not block_active:
            flags |= Qt.ItemIsEditable

        return flags

    def _save_checkbox_widget_change(
        self,
        checkbox: QCheckBox,
        checked: bool,
    ) -> None:
        try:
            row = self._block_execution_checkboxes.index(checkbox)
        except ValueError:
            return

        self._save_checkbox_change(row, checked)

    def _save_checkbox_change(self, row: int, checked: bool) -> None:
        if self._loading:
            return

        if row >= len(self._entries):
            return

        block_active = is_block_active()
        entry = self._entries[row]
        current_block_execution = bool(entry.get("block_execution"))

        if block_active:
            if current_block_execution and not checked:
                self._block_execution_checkboxes[row].setChecked(True)
                return

            if checked and not current_block_execution:
                add_file_folder(
                    file_folder=Path(str(entry.get("path", ""))),
                    block_execution=True,
                )
                self.load_entries()
                return

        self._entries[row]["block_execution"] = checked
        self._write_entries()
        self.load_entries()

    def _write_entries(self) -> None:
        self._entries = self._sort_entries(self._entries)
        FILE_FOLDERS_TO_BLOCK.parent.mkdir(parents=True, exist_ok=True)
        FILE_FOLDERS_TO_BLOCK.write_text(
            json.dumps(self._entries, indent=2) + "\n",
            encoding="utf-8",
        )

    def _delete_button_row(self, button: QToolButton) -> None:
        try:
            row = self._delete_buttons.index(button)
        except ValueError:
            return

        self._delete_row(row)

    def _delete_row(self, row: int) -> None:
        if row >= len(self._entries):
            self._remove_unsaved_row(row)
            return

        del self._entries[row]
        self._write_entries()
        self.load_entries()

    def _remove_unsaved_row(self, row: int) -> None:
        if row < 0 or row >= self.table.rowCount():
            return

        self.table.removeRow(row)
        if row < len(self._delete_buttons):
            del self._delete_buttons[row]
        if row < len(self._block_execution_checkboxes):
            del self._block_execution_checkboxes[row]
        self._update_control_states()

    def _update_control_states(self) -> None:
        block_active = is_block_active()
        block_state_changed = (
            self._last_block_active is None
            or self._last_block_active != block_active
        )

        self.add_file_button.setEnabled(True)
        self.add_folder_button.setEnabled(True)
        self.add_custom_path_button.setEnabled(True)

        for button in self._delete_buttons:
            button.setEnabled(not block_active)

        if block_state_changed:
            was_loading = self._loading
            self._loading = True
            try:
                for row in range(self.table.rowCount()):
                    path_item = self.table.item(row, 1)
                    if path_item is not None:
                        path_item.setFlags(
                            self._path_item_flags(
                                block_active,
                                force_editable=self._is_pending_custom_path(row),
                            )
                        )
            finally:
                self._loading = was_loading

        for row, checkbox in enumerate(self._block_execution_checkboxes):
            if row >= len(self._entries) or self._is_pending_custom_path(row):
                checkbox.setEnabled(False)
                continue

            checkbox.setEnabled(
                not block_active or not self._entries[row].get("block_execution")
            )

        self._last_block_active = block_active

    def _is_pending_custom_path(self, row: int) -> bool:
        path_item = self.table.item(row, 1)
        return bool(
            path_item is not None
            and path_item.data(PENDING_CUSTOM_PATH_ROLE)
        )

    def _validate_path(self, path_text: str) -> Path:
        path = Path(path_text).expanduser().resolve()

        if not path.is_absolute():
            raise RuntimeError(f"path must be absolute: {path}")
        if not path.exists():
            raise RuntimeError(f"path does not exist: {path}")

        return path

    def _set_path_item_text(self, item: QTableWidgetItem, path: str) -> None:
        was_loading = self._loading
        self._loading = True
        item.setText(path)
        self._loading = was_loading

    def _set_saved_path_item(self, item: QTableWidgetItem, path: str) -> None:
        was_loading = self._loading
        self._loading = True
        item.setData(ORIGINAL_PATH_ROLE, path)
        item.setData(PENDING_CUSTOM_PATH_ROLE, False)
        item.setText(path)
        self._loading = was_loading

    def _save_path_change(self, item: QTableWidgetItem) -> None:
        if self._loading or item.column() != 1:
            return

        row = item.row()
        path_text = item.text().strip()
        original_path = str(item.data(ORIGINAL_PATH_ROLE) or "")
        pending_custom_path = bool(item.data(PENDING_CUSTOM_PATH_ROLE))

        if is_block_active() and not pending_custom_path:
            self._set_path_item_text(item, original_path)
            self._update_control_states()
            return

        if not path_text:
            if pending_custom_path:
                self._remove_unsaved_row(row)
                return

            QMessageBox.warning(self, "Sealed", "Path cannot be empty.")
            self._set_path_item_text(item, original_path)
            return

        try:
            path = self._validate_path(path_text)
        except Exception as error:
            QMessageBox.critical(self, "Sealed", str(error))
            if not pending_custom_path:
                self._set_path_item_text(item, original_path)
            self.table.editItem(item)
            return

        normalized_path = str(path)
        if pending_custom_path:
            try:
                add_file_folder(path)
            except Exception as error:
                QMessageBox.critical(self, "Sealed", str(error))
                self.table.editItem(item)
                return

            self.load_entries()
            self._write_entries()
            return

        if normalized_path == original_path:
            self._set_path_item_text(item, normalized_path)
            return

        if row >= len(self._entries):
            return

        if any(
            index != row and entry.get("path") == normalized_path
            for index, entry in enumerate(self._entries)
        ):
            QMessageBox.warning(self, "Sealed", "Path is already in the list.")
            self._set_path_item_text(item, original_path)
            return

        self._entries[row]["path"] = normalized_path
        self._write_entries()
        self._set_saved_path_item(item, normalized_path)

    def _add_selected_path(self, selected_path: str) -> None:
        if not selected_path:
            return

        try:
            add_file_folder(Path(selected_path))
        except Exception as error:
            QMessageBox.critical(self, "Sealed", str(error))
            return

        self.load_entries()
        self._write_entries()

    def _add_file(self) -> None:
        selected_path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Choose File",
            "",
            "All files (*)",
        )
        self._add_selected_path(selected_path)

    def _add_folder(self) -> None:
        selected_path = QFileDialog.getExistingDirectory(self, "Choose Folder")
        self._add_selected_path(selected_path)

    def _add_custom_path(self) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)

        self._loading = True
        path_item = self._add_table_row(
            row,
            {"path": "", "block_execution": False},
            pending_custom_path=True,
        )
        self._loading = False
        self._update_control_states()
        self.table.editItem(path_item)
