import os
import shlex
import subprocess
import shutil
from typing import Optional, Iterable, Union
from pathlib import Path
from datetime import datetime, timedelta

from src.defaults import SubprocessCommand, ExceptionType, SEALED_BIN, DEFAULT_EXCEPTIONS


def log(*message : str):
    date_prefix = f"[{(datetime.now()).isoformat(timespec='seconds')}]"
    print(date_prefix,*message)


def get_current_user() -> str:

    user = (
        os.environ.get("SUDO_USER")
        or os.environ.get("USER")
        or os.environ.get("LOGNAME")
    )

    if not user or user == "root":
        raise RuntimeError("Unable to determine invoking non-root user")

    return user


def run_cmd(command: SubprocessCommand, stdin_text: Optional[str] = None) -> subprocess.CompletedProcess[str]:
    """
    Run a command without a shell.
    - command is argv (e.g. ["ls", "-l"]).
    - stdin_text is the input to the command, if provided, is written to the process STDIN (like: echo "$stdin_text" | cmd).
    Returns CompletedProcess with .stdout/.stderr as strings.
    """
    ### Debug
    
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

    if proc.returncode != 0:
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

    log("Command has been scheduled for:",(datetime.now() + timedelta(minutes=minutes)).isoformat(timespec="seconds"))

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
    add_sudoers_permission(user, "90", "sealed", DEFAULT_EXCEPTIONS.append(SEALED_BIN))
    
    return user


