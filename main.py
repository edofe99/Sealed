#!/usr/local/bin/sealed_src/.venv/bin/python
from __future__ import annotations

import sys
import os
from typing import Iterable, Optional, Sequence, Union

from src.block_root import system_block
from src.defaults import BLOCK_FILE, ExceptionType
from src.utils import startup_checks, format_exceptions_args, log
from src.argparse import parse_args

# Check if the script is being run with superuser privileges
if os.geteuid() != 0:
    print("This script requires elevated permissions. Please run it with sudo.")
    sys.exit(1)

def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    if args.check_sudoers:
        user = startup_checks()
        log(f'Sudoers permissions set for {user}')

    if args.remaining:
        try:
            print(BLOCK_FILE.read_text(encoding="utf-8"), end="")
        except FileNotFoundError:
            print(f"block file not found: {BLOCK_FILE}", file=sys.stderr)
            return 1
        except OSError as e:
            print(f"failed to read block file {BLOCK_FILE}: {e}", file=sys.stderr)
            return 1
        return 0

    exceptions: Union[ExceptionType, Iterable[ExceptionType], None] = None
    if args.exception:
        exceptions = format_exceptions_args(args.exception)

    if args.block:
        system_block(minutes=args.block,exceptions=exceptions)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
