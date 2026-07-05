from pathlib import Path
from typing import Sequence, Union, Tuple

SEALED_DIR = Path("/usr/local/bin/sealed_src")
SEALED_BIN = Path("/usr/local/bin/sealed")
ICON_PATH = SEALED_DIR / "assets" / "sealed.png"
RESTORE_SCRIPT = SEALED_DIR / 'src/core/restore_file_folder.py'
# SEALED_BIN = SEALED_DIR / "sealed"
BLOCK_FILE = SEALED_DIR / "block.txt"
FILE_FOLDERS_TO_BLOCK = SEALED_DIR / "file_folders.json"
APPS_TO_BLOCK = SEALED_DIR / "apps.json"

PERMISSIONS_BACKUP_DIR = SEALED_DIR / 'permissions_backup'

# Leechblock
POLICIES_PATH = Path('/etc/firefox/policies/')
POLICIES_FILE = POLICIES_PATH / 'policies.json'


# Allow running atq for checking at queue
DEFAULT_EXCEPTIONS = [
    SEALED_BIN,
    Path('/usr/bin/atq'),
    # (Path('/usr/bin/dnf'),'remove *'),
    (Path('/usr/bin/pacman'),'-Rns *'),
    (Path('/usr/bin/pacman'),'-R -n -s --config /etc/pacman.conf -- *'), # used for yay -Rns
    ]

SubprocessCommand = Sequence[str]
ExceptionType = Union[Path, Tuple[Path, str]]
