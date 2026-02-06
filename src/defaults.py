from pathlib import Path
from typing import Sequence, Union, Tuple

SEALED_DIR = Path("/usr/local/bin/sealed_src")
SEALED_BIN = Path("/usr/local/bin/sealed")
# SEALED_BIN = SEALED_DIR / "sealed"
BLOCK_FILE = SEALED_DIR / "block.txt"

# Allow running atq for checking at queue
DEFAULT_EXCEPTIONS = [
    SEALED_BIN,
    Path('/usr/bin/atq'),
    (Path('/usr/bin/dnf'),'remove *'),
    (Path('/usr/bin/pacman'),'-Rns *'),
    (Path('/usr/bin/pacman'),'-R -n -s --config /etc/pacman.conf -- *'), # used for yay -Rns
    ]

SubprocessCommand = Sequence[str]
ExceptionType = Union[Path, Tuple[Path, str]]