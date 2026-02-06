#!/usr/local/bin/sealed_src/.venv/bin/python
from __future__ import annotations
import argparse
import sys
import os
from pathlib import Path
from typing import Iterable, Optional, Sequence, Union

from src.block_root import system_block, is_block_active
from src.defaults import BLOCK_FILE
from src.utils import startup_checks, log

# Check if the script is being run with superuser privileges
if os.geteuid() != 0:
    print("This script requires elevated permissions. Please run it with sudo.")
    sys.exit(1)

def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="sealed", add_help=True)

    p.add_argument("--block", type=int, metavar="MINUTES")
    p.add_argument("--exceptions", nargs="+", metavar="PATH")
    p.add_argument("--remaining", action="store_true")
    p.add_argument("--check-sudoers", action="store_true")

    args = p.parse_args(argv)

    # --remaining is standalone
    if args.remaining or args.check_sudoers:
        if args.block is not None or args.exceptions:
            p.error(f"{" ".join(sys.argv)} cannot be combined with --block/--exceptions")
        return args

    # Otherwise must provide --block
    if args.block is None:
        p.error("Missing parameters.")

    elif args.block <= 0:
        p.error("--block MINUTES must be a positive integer.")
    
    elif args.block > 0 and is_block_active():
        raise RuntimeError("You are already inside a sealed session")
        
    # --exceptions allowed only with --block (already ensured)
    return args


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

    exceptions: Union[Path, Iterable[Path], None] = None
    if args.exceptions:
        exceptions = [Path(p) for p in args.exceptions]

    if args.block:
        system_block(minutes=args.block,exceptions=exceptions)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
