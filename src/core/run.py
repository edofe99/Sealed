import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence, Union, Iterable

from src.core.block_root import system_block
from src.core.defaults import BLOCK_FILE, ExceptionType, MINIMUM_MINUTES_TO_LOCK
from src.core.utils import get_remaining_minutes, startup_checks, format_exceptions_args, log, is_block_active, uninstall
from src.core.block_file_folder import add_file_folder
from src.core.block_apps import add_app
from src.core.lock_access import lock_access

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
            "  sealed --block 10 --exception \"/usr/bin/timeshift\" --exception \"/usr/bin/dnf remove *\"\n"
            "  sealed --block 60 --lock-access 10\n"
            "  sealed --lock-access 10\n"
            "  sealed --remaining\n"
            "  sealed --check-sudoers\n"
            "  sealed --add-file-folder /abs/path/to/thing\n"
            "  sealed --add-app /usr/bin/firefox\n"
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
        "--lock-access",
        type=int,
        metavar="MINUTES",
        help="Lock access to user account in MINUTES (positive integer, lower than block duration).\n" \
        "User will be logged out in MINUTES and will not be able to log back in for the duration of the block.\n" \
        "Can be used in conjuction with --block or alone when a block is already active.",
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

    # -------------------------- FILE / FODLER BLOCKING -------------------------- #
    p.add_argument(
        "--add-file-folder",
        metavar="PATH",
        type=Path,
        help="Add path to a file or folder. When the block will start the file/folder will be read-only and immutable for the user.",
    )

    # -------------------------------- APP BLOCKER ------------------------------- #
    p.add_argument(
        "--add-app",
        metavar="PATH",
        type=Path,
        help="Add path to an executable file. When the block will start any process will be killed and the executable will be blocked.",
    )
    
    # --------------------------------- UNINSTALL -------------------------------- #
    p.add_argument(
        "--uninstall",
        action="store_true",
        help="Completely uninstall Sealed, leaving nothing behind.",
    )

    args = p.parse_args(argv)
    argv = sys.argv[1:] if argv is None else list(argv)

    # ---------------------------------------------------------------------------- #
    #                                  ARGS CHECKS                                 #
    # ---------------------------------------------------------------------------- #
    
    # --check-sudoers alone
    if args.check_sudoers:
        if len(argv) != 1:
            p.error("--check-sudoers can only be run alone")

        return args
    
    # --uninstall alone
    if args.uninstall:
        if len(argv) != 1:
            p.error("--uninstall can only be run alone")
        
        if is_block_active():
            raise RuntimeError("You can't do this inside a Sealed session.")

        return args

    # --remaining alone
    if args.remaining:
        if len(argv) != 1:
            p.error("--remaining can only be run alone")
        return args

    # --exception requires --block
    if args.exception and args.block is None:
        p.error("--exception requires --block")

    # --lock-access requires --block or active block
    if args.lock_access and args.block is None:
        
        if not is_block_active():
            p.error("--lock-access can be run alone only when a block is active")
        
        # Check if --lock-access is lower than remaining block time if a block is already active
        if is_block_active():
            if args.lock_access >= get_remaining_minutes() - MINIMUM_MINUTES_TO_LOCK:
                p.error(f"--lock-access must be at least {MINIMUM_MINUTES_TO_LOCK} minutes before the block end")
            return args

    # --lock-access must be lower than --block
    if args.lock_access and args.block and args.lock_access >= args.block - MINIMUM_MINUTES_TO_LOCK:
        p.error(f"--lock-access must be at least {MINIMUM_MINUTES_TO_LOCK} minutes before --block")
    
    # --block-files-folders requires --block
    # if args.block_files_folders and args.block is None:
    #     p.error("--block-files-folders requires --block")

    # --add-file-folder alone
    if args.add_file_folder:
        used_flags = [arg for arg in argv if arg.startswith("--")]
        if len(used_flags) != 1:
            p.error("--add_file_folder can only be run alone")
        return args

    # --add-app alone
    if args.add_app:
        used_flags = [arg for arg in argv if arg.startswith("--")]
        if len(used_flags) != 1:
            p.error("--add-app can only be run alone")
        return args

    # must have --block if we got here
    if args.block is None:
        p.error("Missing parameters. Use --block, --remaining, --check-sudoers, or --add-file-folder.")

    if args.block <= 0:
        p.error("--block MINUTES must be a positive integer.")

    if is_block_active() and args.block is not None:
        raise RuntimeError("You are already inside a sealed session")
    
    return args


def run(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    if args.check_sudoers:
        user = startup_checks()
        log(f'Sudoers permissions set for {user}')
        return 0
    
    if args.uninstall:
        uninstall()
        
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
        system_block(minutes=args.block,exceptions=exceptions,lock_access_minutes=args.lock_access)
        return 0

    if args.lock_access and not args.block:
        remaining_minutes = get_remaining_minutes()
        lock_access(
            minutes_to_start=args.lock_access,
            minutes_to_end=remaining_minutes,
        )
        return 0

    if args.add_file_folder:
        add_file_folder(args.add_file_folder)
        return 0
    
    if args.add_app:
        add_app(args.add_app)
        return 0
