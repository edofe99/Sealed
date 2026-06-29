import os
import shutil
import subprocess
from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

def _launch_path() -> Path:
    invoked_path = Path(sys.argv[0])
    if invoked_path.is_absolute():
        return invoked_path

    path_match = shutil.which(sys.argv[0])
    if path_match:
        return Path(path_match)

    return Path(__file__).absolute()


def ensure_running_as_root() -> None:
    if os.geteuid() == 0:
        return

    command = [
        "pkexec",
        str(_launch_path()),
        *sys.argv[1:],
    ]

    try:
        result = subprocess.run(command, check=False)
    except FileNotFoundError:
        _show_elevation_error(
            "Sealed needs administrator privileges, but pkexec was not found."
        )
        sys.exit(1)

    sys.exit(result.returncode)

def _show_elevation_error(message: str) -> None:
    app = QApplication(sys.argv)
    QMessageBox.critical(None, "Sealed", message)
    app.quit()
