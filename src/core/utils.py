from email import utils
import os
import pwd
import shlex
import subprocess
import shutil
from typing import Optional, Iterable, Union, List
from pathlib import Path
from datetime import datetime, timedelta
import json

from src.core.defaults import (
    SubprocessCommand,
    ExceptionType,
    DEFAULT_EXCEPTIONS,
    BLOCK_FILE,
    SEALED_DIR,
    SEALED_BIN,
    ICON_PATH
)


def log(*message : str):
    date_prefix = f"[{(datetime.now()).isoformat(timespec='seconds')}]"
    print(date_prefix,*message)


def load_json(path: str | Path) -> list:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []

def get_current_user() -> str:

    user = os.environ.get("SUDO_USER")
    if user and user != "root":
        return user

    # This part is needed for the GUI app root instance to be able to determine the user 
    pkexec_uid = os.environ.get("PKEXEC_UID")
    if pkexec_uid:
        try:
            return pwd.getpwuid(int(pkexec_uid)).pw_name
        except (KeyError, ValueError):
            pass

    user = os.environ.get("USER") or os.environ.get("LOGNAME")

    if not user or user == "root":
        raise RuntimeError("Unable to determine invoking non-root user")

    return user


def run_cmd(command: SubprocessCommand, stdin_text: Optional[str] = None, skip_check = False, print_log = True) -> subprocess.CompletedProcess[str]:
    """
    Run a command without a shell.
    - command is argv (e.g. ["ls", "-l"]).
    - stdin_text is the input to the command, if provided, is written to the process STDIN (like: echo "$stdin_text" | cmd).
    Returns CompletedProcess with .stdout/.stderr as strings.
    """
    ### Debug
    if print_log:
        if stdin_text is not None:
            log('Running command:', shlex.join(command), f"< {stdin_text}")
        else:
            log('Running command:', shlex.join(command))
    ### 

    proc = subprocess.run(
        args=list(command),
        input=stdin_text,
        text=True,
        capture_output=True,

    )

    if proc.returncode != 0 and not skip_check:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"Command failed: {command}")

    return proc


def schedule_run_cmd(command_to_schedule: SubprocessCommand, minutes: int) -> subprocess.CompletedProcess[str]:
    """
    Schedule a command to run in <minutes> using `at` by sending a small script to at's stdin.
    IMPORTANT: at job must be created as root if the scheduled command needs root.
    """
    # Convert argv -> a safely quoted command line for a shell script
    scheduled_line = shlex.join(command_to_schedule)

    job_script = (
        "#!/bin/sh\n"
        "set -eu\n"
        f"{scheduled_line}\n"
    )

    # Create the at job AS ROOT so it will run as root
    schedule_cmd: SubprocessCommand = ["at", "now", "+", str(minutes), "minutes"]

    log("The following command has been scheduled for:",(datetime.now() + timedelta(minutes=minutes)).isoformat(timespec="seconds"))

    return run_cmd(schedule_cmd, stdin_text=job_script)



def add_sudoers_permission(user : str, priority : str, filename : str, exceptions : Union[ExceptionType, Iterable[ExceptionType], None], schedule_removal : int = False):
    '''
    Makes a sudoers.d file with following options:
    - exceptions : Path, Iterable[Path] -> creates a sudoers.d file that allows to run the given paths to binaries without root privilege
    - exceptions : None -> creates a sudoers.d file that prevent the user to run any command as root
    - exceptiosn -> Instead of Path you can pass Union[Path, str] where strings are commands, i.e. you can add exception for [Path('/usr/bin/pacman'), "-Rns *"]
    - schedule_deletion -> if you pass an integer then the permission file will be deleted after that amount of minutes
    '''

    sudoers_permissions_filename = f"{priority}-{user}-{filename}"
    sudoers_permissions_filepath = str(Path("/etc/sudoers.d") / sudoers_permissions_filename)

    lines: list[str] = []
    if exceptions:
        if not isinstance(exceptions, (list, tuple, set)):
            exceptions = [exceptions]

        # de-duplicate
        exceptions = list(dict.fromkeys(exceptions))

        for exc in exceptions:
            # case 1: Path only → allow binary with any args
            if isinstance(exc, Path):
                if not exc.is_absolute():
                    raise RuntimeError(f"{exc} is not absolute")

                lines.append(
                    f"{user} ALL=(root) NOPASSWD: {exc}"
                )

            # case 2: (Path, args)
            elif isinstance(exc, tuple) and len(exc) == 2:
                binary, args = exc

                if not isinstance(binary, Path):
                    raise RuntimeError(f"{binary} is not a Path")

                if not binary.is_absolute():
                    raise RuntimeError(f"{binary} is not absolute")

                if not isinstance(args, str) or not args.strip():
                    raise RuntimeError("Command arguments must be a non-empty string")

                lines.append(
                    f"{user} ALL=(root) NOPASSWD: {binary} {args}"
                )

            else:
                raise RuntimeError(f"Invalid sudoers exception: {exc}")
    
    # If there are no exceptions then make a sudoers.d file that prevents user from running commands as sudo
    if not exceptions:
        lines.append(f"{user} ALL=(ALL) !ALL\n")

    if len(lines) == 0:
        log('No exceptions to add')
        return
    
    run_cmd(
        ["tee", sudoers_permissions_filepath],
        stdin_text="\n".join(lines) + "\n",
    )

    run_cmd(["chmod", "440", sudoers_permissions_filepath])
    run_cmd(["visudo", "-cf", sudoers_permissions_filepath])

    if schedule_removal:
        schedule_run_cmd(["rm", "-f", sudoers_permissions_filepath],minutes=schedule_removal)    

def startup_checks() -> str: 
    """
    Check if dependencies are ok and the sudoers file is ok
    """
    # Check script is being run as root
    if os.geteuid() != 0:
        raise PermissionError("You must run this script as root (e.g., with sudo).")

    # Check at is active, if not the run_cmd will stop the code
    run_cmd(["systemctl", "is-active", "--quiet", "atd"])
    
    # Check that we are able to get current user 
    user = get_current_user()
    
    # Check that notify-send is installed
    if not shutil.which("notify-send"):
        raise RuntimeError("'notify-send' not found (install libnotify).")
    
    # ---------------- Check sudoers exceptions for sealed exissts --------------- #
    
    # Add Sealed binary exception and default ones
    add_sudoers_permission(user, "90", "sealed-default-exceptions", exceptions = DEFAULT_EXCEPTIONS)
    
    return user

def format_exceptions_args(input: Union[str, List[str]]):
    '''
    We need to turn a string into a proper exception type
    --exceptions "/usr/bin/pacman" -> exceptions = [Path("/usr/bin/pacman")]
    --exceptions "/usr/bin/pacman -Rns -- *" -> exceptions = [(Path("/usr/bin/pacman"), "-Rns -- *")]
    '''
    exceptions = []
    for raw in input:
        raw = raw.strip()
        # split only on FIRST space
        if " " in raw:
            bin_part, arg_part = raw.split(" ", 1)
            bin_path = Path(bin_part)
            if not bin_path.is_absolute():
                raise RuntimeError(f"{bin_path} is not an absolute path")

            if not arg_part.strip():
                exceptions.append(bin_path)
            else:
                exceptions.append((bin_path, arg_part.strip()))
        else:
            bin_path = Path(raw)
            if not bin_path.is_absolute():
                raise RuntimeError(f"{bin_path} is not an absolute path")

            exceptions.append(bin_path)

    return exceptions

def is_block_active():
    try:
        # .strip() removes any accidental newlines or spaces
        time_str = BLOCK_FILE.read_text().strip()

        # 2. Convert the string to a datetime object
        file_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M")

        # 3. Compare with the current time
        now = datetime.now()

        if file_time <= now:
            run_cmd(['rm',str(BLOCK_FILE)])
            return False
        elif file_time > now:
            return True
        
    except (FileNotFoundError, ValueError):
        # log("Block file not found")
        return False

def uninstall():
    log('Starting Sealed uninstall')
    # This function will delete EVERYTHING
    if os.geteuid() != 0:
        raise PermissionError("You must run this script as root (e.g., with sudo).")

    sudoers_dir = Path("/etc/sudoers.d")
    if sudoers_dir.is_dir():
        for sudoers_file in sudoers_dir.iterdir():
            if sudoers_file.is_file() and "sealed" in sudoers_file.name.lower():
                run_cmd(["rm", "-rf", "--", str(sudoers_file)])

    for path in (
        SEALED_DIR,
        SEALED_BIN,
        Path("/usr/local/bin/sealed-qt"),
        Path("/usr/share/applications/sealed.desktop"),
        Path("/usr/share/icons/hicolor/512x512/apps/sealed.png"),
        Path("/usr/share/polkit-1/actions/com.sealed.gui.policy"),
    ):
        run_cmd(["rm", "-rf", "--", str(path)])
    
    log('Sealed has been completely uninstalled, no leftovers files.')
    raise RuntimeError("Sealed has been uninstalled.")


def send_notification(message : str = None, minutes : int = None):
    user = get_current_user()
    uid = int(os.environ.get("SUDO_UID") or pwd.getpwnam(user).pw_uid)

    notify_params = [
        "runuser", "-u", user, "--",
        "env",
        f"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{uid}/bus",
        f"XDG_RUNTIME_DIR=/run/user/{uid}",
        f"DISPLAY={os.environ.get('DISPLAY', ':0')}",
        "notify-send",
        "--urgency=normal",
        "--app-name=Sealed",
        f"--icon={ICON_PATH}",
        "--expire-time=10000",
        "--transient",
        "Sealed",
        message,
    ]

    if minutes is not None and minutes > 0:
        schedule_run_cmd(notify_params, minutes=minutes)
    else:
        run_cmd(notify_params, skip_check=True)

def get_remaining_minutes() -> Optional[int]:
    """
    Returns the remaining minutes of the block if active, otherwise None.
    """
    try:
        time_str = BLOCK_FILE.read_text().strip()
        file_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        now = datetime.now()

        if file_time > now:
            remaining_time = (file_time - now).total_seconds() / 60
            return int(remaining_time)
        else:
            run_cmd(['rm', str(BLOCK_FILE)])
            return None
    except (FileNotFoundError, ValueError):
        return None