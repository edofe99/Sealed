import configparser
import json
import os
from pathlib import Path
import pwd
import shlex
import shutil

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QIcon, QShowEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QHeaderView,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.core.block_apps import add_app, is_sealed_executable, remove_app
from src.core.defaults import APPS_TO_BLOCK
from src.core.utils import get_current_user, is_block_active, load_json

PENDING_CUSTOM_PATH_ROLE = Qt.UserRole


def installed_applications() -> list[tuple[str, str, str, QIcon]]:
    try:
        home = Path(pwd.getpwnam(get_current_user()).pw_dir)
    except Exception:
        home = Path.home()

    data_dirs = [home / ".local/share"]
    data_dirs.extend(
        Path(path)
        for path in os.environ.get(
            "XDG_DATA_DIRS", "/usr/local/share:/usr/share"
        ).split(":")
        if path
    )
    data_dirs.extend(
        [
            home / ".local/share/flatpak/exports/share",
            Path("/var/lib/flatpak/exports/share"),
            Path("/var/lib/snapd/desktop"),
        ]
    )

    icon_paths = {}
    for data_dir in dict.fromkeys(data_dirs):
        for icon_dir in (data_dir / "icons", data_dir / "pixmaps"):
            for icon_file in icon_dir.rglob("*"):
                if icon_file.suffix.lower() not in {".png", ".svg", ".xpm"}:
                    continue
                icon_paths.setdefault(icon_file.name, str(icon_file))
                icon_paths.setdefault(icon_file.stem, str(icon_file))

    applications = []
    seen = set()
    for data_dir in data_dirs:
        for desktop_file in (data_dir / "applications").glob("*.desktop"):
            if "sealed" in desktop_file.stem.lower():
                continue

            config = configparser.ConfigParser(interpolation=None, strict=False)
            config.optionxform = str
            try:
                config.read(desktop_file, encoding="utf-8")
                entry = config["Desktop Entry"]
            except (OSError, UnicodeError, configparser.Error, KeyError):
                continue

            if (
                entry.get("Type") != "Application"
                or entry.get("Hidden", "").lower() == "true"
                or entry.get("NoDisplay", "").lower() == "true"
            ):
                continue

            try:
                command = entry.get("TryExec") or shlex.split(entry["Exec"])[0]
            except (KeyError, ValueError, IndexError):
                continue

            executable = (
                str(Path(command).expanduser().resolve())
                if Path(command).is_absolute()
                else shutil.which(command)
            )
            if not executable or not Path(executable).is_file():
                continue
            if is_sealed_executable(executable):
                continue

            name = entry.get("Name", desktop_file.stem)
            if (name, executable) in seen:
                continue
            seen.add((name, executable))

            icon_name = entry.get("Icon", "")
            icon_path = (
                icon_name
                if Path(icon_name).is_absolute() and Path(icon_name).is_file()
                else icon_paths.get(icon_name, "")
            )
            icon = (
                QIcon(icon_path)
                if icon_path
                else QIcon.fromTheme(icon_name)
            )
            applications.append((name, executable, icon_path, icon))

    return sorted(applications, key=lambda application: application[0].casefold())


class ApplicationPicker(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Applications")
        self.resize(520, 600)

        layout = QVBoxLayout(self)
        self.app_list = QListWidget()
        self.app_list.setIconSize(QSize(32, 32))
        layout.addWidget(self.app_list)

        for name, executable, icon_path, icon in installed_applications():
            item = QListWidgetItem(icon, name)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, executable)
            item.setData(Qt.UserRole + 1, icon_path)
            item.setToolTip(executable)
            self.app_list.addItem(item)

        submit_button = QPushButton("Submit")
        submit_button.clicked.connect(self._submit)
        layout.addWidget(submit_button)

    def _submit(self) -> None:
        errors = []
        for row in range(self.app_list.count()):
            item = self.app_list.item(row)
            if item.checkState() != Qt.Checked:
                continue
            try:
                add_app(
                    item.data(Qt.UserRole),
                    item.text(),
                    item.data(Qt.UserRole + 1),
                )
            except Exception as error:
                errors.append(f"{item.text()}: {error}")

        if errors:
            QMessageBox.critical(self, "Sealed", "\n".join(errors))
            return

        self.accept()


class ApplicationsTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._loading = False
        self._entries = []
        self._delete_buttons = []
        self._block_checkboxes = []

        layout = QVBoxLayout(self)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(
            ["Delete", "Application", "Block Execution"]
        )
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
        self.table.setIconSize(QSize(24, 24))
        self.table.setAlternatingRowColors(True)
        self.table.itemChanged.connect(self._save_custom_path)

        layout.addWidget(self.table)

        buttons_layout = QHBoxLayout()
        self.add_custom_path_button = QPushButton("Add custom path")
        self.add_custom_path_button.clicked.connect(self._add_custom_path)
        buttons_layout.addWidget(self.add_custom_path_button)

        self.add_application_button = QPushButton("Add application")
        self.add_application_button.clicked.connect(self._add_applications)
        buttons_layout.addWidget(self.add_application_button)
        layout.addLayout(buttons_layout)

        self.load_entries()

        self._state_timer = QTimer(self)
        self._state_timer.timeout.connect(self._update_control_states)
        self._state_timer.start(1000)

    def load_entries(self) -> None:
        self._loading = True
        data = load_json(APPS_TO_BLOCK)
        entries = sorted(
            (entry for entry in data if isinstance(entry, dict)),
            key=lambda entry: str(
                entry.get("name") or entry.get("path", "")
            ).casefold(),
        )
        self._entries = entries
        self._delete_buttons = []
        self._block_checkboxes = []
        self.table.setRowCount(len(entries))

        for row, entry in enumerate(entries):
            delete_button = QToolButton()
            delete_button.setText("X")
            delete_button.setAutoRaise(True)
            delete_button.setCursor(Qt.PointingHandCursor)
            delete_button.setStyleSheet(
                "QToolButton { color: #b00020; border: none; padding: 2px 6px; }"
                "QToolButton:disabled { color: grey; }"
            )
            delete_button.setToolTip("Delete")
            path = str(entry.get("path", ""))
            delete_button.clicked.connect(
                lambda _checked=False, app_path=path: self._remove_app(app_path)
            )
            delete_cell = QWidget()
            delete_layout = QHBoxLayout(delete_cell)
            delete_layout.addWidget(delete_button)
            delete_layout.setAlignment(Qt.AlignCenter)
            delete_layout.setContentsMargins(0, 0, 0, 0)

            path_item = QTableWidgetItem(str(entry.get("name") or path))
            path_item.setIcon(QIcon(str(entry.get("icon", ""))))
            path_item.setToolTip(path)
            path_item.setFlags(Qt.ItemIsEnabled)
            path_item.setData(PENDING_CUSTOM_PATH_ROLE, False)

            block_checkbox = QCheckBox()
            block_checkbox.setChecked(bool(entry.get("block", False)))
            block_checkbox.toggled.connect(
                lambda checked, app_path=path, checkbox=block_checkbox: (
                    self._update_block(app_path, checked, checkbox)
                )
            )
            checkbox_cell = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_cell)
            checkbox_layout.addWidget(block_checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)

            self.table.setCellWidget(row, 0, delete_cell)
            self.table.setItem(row, 1, path_item)
            self.table.setCellWidget(row, 2, checkbox_cell)
            self._delete_buttons.append(delete_button)
            self._block_checkboxes.append(block_checkbox)

        self._loading = False
        self._update_control_states()

    def _add_custom_path(self) -> None:
        self._loading = True
        row = self.table.rowCount()
        self.table.insertRow(row)

        delete_button = QToolButton()
        delete_button.setText("X")
        delete_button.setAutoRaise(True)
        delete_button.setCursor(Qt.PointingHandCursor)
        delete_button.setStyleSheet(
            "QToolButton { color: #b00020; border: none; padding: 2px 6px; }"
            "QToolButton:disabled { color: grey; }"
        )
        delete_button.setToolTip("Delete")
        delete_button.setEnabled(not is_block_active())
        delete_cell = QWidget()
        delete_layout = QHBoxLayout(delete_cell)
        delete_layout.addWidget(delete_button)
        delete_layout.setAlignment(Qt.AlignCenter)
        delete_layout.setContentsMargins(0, 0, 0, 0)

        path_item = QTableWidgetItem("")
        path_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable)
        path_item.setData(PENDING_CUSTOM_PATH_ROLE, True)
        delete_button.clicked.connect(
            lambda _checked=False, item=path_item: self.table.removeRow(item.row())
        )

        block_checkbox = QCheckBox()
        block_checkbox.setEnabled(False)
        checkbox_cell = QWidget()
        checkbox_layout = QHBoxLayout(checkbox_cell)
        checkbox_layout.addWidget(block_checkbox)
        checkbox_layout.setAlignment(Qt.AlignCenter)
        checkbox_layout.setContentsMargins(0, 0, 0, 0)

        self.table.setCellWidget(row, 0, delete_cell)
        self.table.setItem(row, 1, path_item)
        self.table.setCellWidget(row, 2, checkbox_cell)
        self._loading = False
        self.table.editItem(path_item)

    def _add_applications(self) -> None:
        if ApplicationPicker(self).exec() == QDialog.Accepted:
            self.load_entries()

    def _save_custom_path(self, item: QTableWidgetItem) -> None:
        if self._loading or not item.data(PENDING_CUSTOM_PATH_ROLE):
            return

        path = item.text().strip()
        if not path:
            self.table.removeRow(item.row())
            return

        try:
            add_app(path)
            self.load_entries()
        except Exception as error:
            QMessageBox.critical(self, "Sealed", str(error))
            self.table.editItem(item)

    def _update_block(
        self,
        app_path: str,
        block: bool,
        checkbox: QCheckBox,
    ) -> None:
        data = load_json(APPS_TO_BLOCK)
        selected_entry = None
        for entry in data:
            if isinstance(entry, dict) and entry.get("path") == app_path:
                selected_entry = entry
                entry["block"] = block

        if selected_entry is None:
            return

        if is_block_active():
            if not block:
                checkbox.blockSignals(True)
                checkbox.setChecked(True)
                checkbox.blockSignals(False)
                return

            try:
                add_app(
                    app_path,
                    selected_entry.get("name"),
                    selected_entry.get("icon"),
                )
            except Exception as error:
                QMessageBox.critical(self, "Sealed", str(error))
            self.load_entries()
            return

        APPS_TO_BLOCK.write_text(
            json.dumps(data, indent=2) + "\n",
            encoding="utf-8",
        )

    def _update_control_states(self) -> None:
        block_active = is_block_active()

        for button in self._delete_buttons:
            button.setEnabled(not block_active)

        for row, checkbox in enumerate(self._block_checkboxes):
            checkbox.setEnabled(
                not block_active or not self._entries[row].get("block", False)
            )

    def _remove_app(self, app_path: str) -> None:
        try:
            remove_app(app_path)
            self.load_entries()
        except Exception as error:
            QMessageBox.critical(self, "Sealed", str(error))

    def showEvent(self, event: QShowEvent) -> None:
        self.load_entries()
        super().showEvent(event)
