import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer
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


class FileFoldersTab(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self._entries: list[dict[str, Any]] = []
        self._delete_buttons: list[QToolButton] = []
        self._block_execution_checkboxes: list[QCheckBox] = []
        self._loading = False

        layout = QVBoxLayout(self)

        self.table = QTableWidget(0, 3)
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
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)

        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self._add_file_folder)
        layout.addWidget(self.add_button)

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

        self._entries = [entry for entry in data if isinstance(entry, dict)]
        self._delete_buttons = []
        self._block_execution_checkboxes = []

        self.table.setRowCount(len(self._entries))
        for row, entry in enumerate(self._entries):
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
                lambda _checked=False, row=row: self._delete_row(row)
            )
            delete_cell = QWidget()
            delete_layout = QHBoxLayout(delete_cell)
            delete_layout.addWidget(delete_button)
            delete_layout.setAlignment(Qt.AlignCenter)
            delete_layout.setContentsMargins(0, 0, 0, 0)

            path_item = QTableWidgetItem(str(entry.get("path", "")))
            path_item.setFlags(Qt.ItemIsEnabled)

            block_execution_checkbox = QCheckBox()
            block_execution_checkbox.setChecked(bool(entry.get("block_execution")))
            block_execution_checkbox.toggled.connect(
                lambda checked, row=row: self._save_checkbox_change(row, checked)
            )
            checkbox_cell = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_cell)
            checkbox_layout.addWidget(block_execution_checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)

            self.table.setCellWidget(row, 0, delete_cell)
            self.table.setItem(row, 1, path_item)
            self.table.setCellWidget(row, 2, checkbox_cell)
            self._delete_buttons.append(delete_button)
            self._block_execution_checkboxes.append(block_execution_checkbox)

        self._loading = False
        self._update_control_states()

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
        FILE_FOLDERS_TO_BLOCK.write_text(
            json.dumps(self._entries, indent=2) + "\n",
            encoding="utf-8",
        )
        self._update_control_states()

    def _delete_row(self, row: int) -> None:
        if row >= len(self._entries):
            return

        del self._entries[row]
        FILE_FOLDERS_TO_BLOCK.write_text(
            json.dumps(self._entries, indent=2) + "\n",
            encoding="utf-8",
        )
        self.load_entries()

    def _update_control_states(self) -> None:
        block_active = is_block_active()

        for button in self._delete_buttons:
            button.setEnabled(not block_active)

        for row, checkbox in enumerate(self._block_execution_checkboxes):
            if row >= len(self._entries):
                continue

            checkbox.setEnabled(
                not block_active or not self._entries[row].get("block_execution")
            )

    def _add_file_folder(self) -> None:
        dialog = QFileDialog(self, "Choose File or Folder")
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setOption(QFileDialog.ShowDirsOnly, False)

        if not dialog.exec():
            return

        selected_paths = dialog.selectedFiles()
        if not selected_paths:
            return

        try:
            add_file_folder(Path(selected_paths[0]))
        except Exception as error:
            QMessageBox.critical(self, "Sealed", str(error))
            return

        self.load_entries()
