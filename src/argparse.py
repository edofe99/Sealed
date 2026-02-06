import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence, Union, Iterable

from src.block_root import system_block
from src.defaults import BLOCK_FILE, ExceptionType
from src.utils import startup_checks, format_exceptions_args, log, is_block_active
from src.block_file_folder import add_file_folder

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
            "  sealed --remaining\n"
            "  sealed --check-sudoers\n"
            "  sealed --add-file-folder /abs/path/to/thing\n"
            "  sealed --add-file-folder /abs/path/to/thing --no-exec\n"
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

    # -------------------------- FILE / FODLER BLOCKING -------------------------- #
    p.add_argument(
        "--block-files-folders",
        action="store_true",
        help="Block files and folder during the next session.",
    )

    p.add_argument(
        "--add-file-folder",
        metavar="PATH",
        type=Path,
        help="Add an absolute file/folder path to FILE_FOLDERS_TO_BLOCK.",
    )

    p.add_argument(
        "--no-exec",
        action="store_true",
        help="When used with --add-file-folder, makes the file owned by root and non-executable during the block.",
    )

    args = p.parse_args(argv)

    # ---------------------------------------------------------------------------- #
    #                                  ARGS CHECKS                                 #
    # ---------------------------------------------------------------------------- #
    
    # --check-sudoers alone
    if args.check_sudoers:
        if args.block is not None or args.exception or args.remaining or args.block_files_folders or args.add_file_folder or args.no_exec:
            p.error("--check-sudoers can only be run alone")
        return args

    # --remaining alone
    if args.remaining:
        if args.block is not None or args.exception or args.block_files_folders or args.add_file_folder or args.no_exec:
            p.error("--remaining can only be run alone")
        return args

    # --no-exec requires --add-file-folder
    if args.no_exec and args.add_file_folder is None:
        p.error("--no-exec can't be run alone (requires --add-file-folder)")

    # --add-file-folder mode (only allowed with optional --no-exec)
    if args.add_file_folder is not None:
        if args.block is not None or args.exception or args.block_files_folders:
            p.error("--add-file-folder can only be used with optional --no-exec (no other flags)")
        args.add_file_folder = args.add_file_folder.expanduser().resolve()
        if not args.add_file_folder.is_absolute():
            p.error(f"--add-file-folder must be an absolute path: {args.add_file_folder}")
        return args

    # --exception requires --block
    if args.exception and args.block is None:
        p.error("--exception requires --block")

    # --block-files-folders requires --block
    if args.block_files_folders and args.block is None:
        p.error("--block-files-folders requires --block")

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
        system_block(minutes=args.block,exceptions=exceptions,block_file_folders=args.block_files_folders)
        return 0

    if args.add_file_folder:
        add_file_folder(args.add_file_folder, args.no_exec)
        return 0


