import argparse
import sys

from src.block_root import is_block_active
from typing import Optional, Sequence

def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:

    p = argparse.ArgumentParser(prog="sealed", add_help=True)


    p = argparse.ArgumentParser(
        prog="sealed",
        description=(
            "Sealed temporarily restricts privileged actions by tightening sudo access.\n"
            "Use --block to start a sealed session, optionally with allowlisted commands."
        ),
        epilog=(
            "Examples:\n"
            "  sealed --block 10\n"
            "  sealed --block 10 --exception \"/usr/bin/pacman -Rns -- *\"\n"
            "  sealed --block 10 --exception \"/usr/bin/timeshift --list\" --exception \"/usr/bin/dnf remove *\"\n"
            "  sealed --remaining\n"
            "  sealed --check-sudoers\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter,  # keeps newlines in description/epilog
        add_help=True,
    )

    p.add_argument(
        "--block",
        type=int,
        metavar="MINUTES",
        help="Start a sealed session for MINUTES (positive integer).",
    )


    p.add_argument(
        "--exception",
        action="append",
        metavar="EXC",
        help=(
            "Allowlist one command during the sealed session.\n"
            "Format:\n"
            "  \"/abs/path/to/bin\"                (allow any args)\n"
            "  \"/abs/path/to/bin <args...>\"      (allow only that arg pattern)\n"
            "Repeat --exception to add multiple entries."
        ),
    )

    p.add_argument(
        "--remaining",
        action="store_true",
        help="Print the end time of the block and exit.",
    )

    p.add_argument(
        "--check-sudoers",
        action="store_true",
        help="Ensure that Sealed can be run by user as root even when a block is active.",
    )

    args = p.parse_args(argv)

    # ---------------------------------------------------------------------------- #
    #                                  ARGS CHECKS                                 #
    # ---------------------------------------------------------------------------- #
    
    # --remaining is standalone
    if args.remaining or args.check_sudoers:
        if args.block is not None or args.exception:
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
