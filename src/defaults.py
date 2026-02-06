from pathlib import Path
from typing import Sequence

SEALED_DIR = Path("/usr/local/bin/sealed_src")
SEALED_BIN = Path("/usr/local/bin/sealed")
# SEALED_BIN = SEALED_DIR / "sealed"
BLOCK_FILE = SEALED_DIR / "block.txt"

SubprocessCommand = Sequence[str]
