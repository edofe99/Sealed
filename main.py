#!/usr/local/bin/sealed_src/.venv/bin/python
from __future__ import annotations

import sys
import os


from src.argparse import run

# Check if the script is being run with superuser privileges
if os.geteuid() != 0:
    print("This script requires elevated permissions. Please run it with sudo.")
    sys.exit(1)


if __name__ == "__main__":
    raise SystemExit(run())
