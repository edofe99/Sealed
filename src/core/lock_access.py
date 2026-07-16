import pwd
import shlex

from src.core.defaults import BLOCK_FILE, MINIMUM_MINUTES_TO_LOCK, USER_LOCK_FILE
from src.core.utils import get_current_user, log, schedule_run_cmd, send_notification, run_cmd

def _get_current_account_expiry(user: str) -> str:
    '''
    We lock user access by setting the account expiry date to a date in the past.
    This function returns the current account expiry date for the given user.
    i.e. the value to be restored after the lock period is over.
    '''
    proc = run_cmd(["sudo", "getent", "shadow", user])
    shadow_line = proc.stdout.strip().splitlines()[0]
    fields = shadow_line.split(":")

    if len(fields) < 8:
        raise RuntimeError(f"Unable to read account expiry for {user}")

    return fields[7] or "-1"

def schedule_logout(minutes: int) -> None:
    user = get_current_user()
    uid = pwd.getpwnam(user).pw_uid

    schedule_run_cmd([
        "sudo","--user", user,
        "--","env",f"XDG_RUNTIME_DIR=/run/user/{uid}",
        f"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{uid}/bus",
        "qdbus6","org.kde.Shutdown","/Shutdown","logout"],
        minutes=minutes)

    log(f"Scheduled logout in {minutes} minutes for user {user}")

    if minutes > 5:
        send_notification("You will be logged out in 5 minutes.", minutes=minutes-5)
    if minutes > 1:
        send_notification("You will be logged out in 1 minute.", minutes=minutes-1)


def lock_access(minutes_to_start: int, minutes_to_end: int) -> None:
    
    if USER_LOCK_FILE.exists():
        raise RuntimeError("User access lock is already scheduled or active.")
    
    if minutes_to_start >= minutes_to_end - MINIMUM_MINUTES_TO_LOCK:
        raise RuntimeError(f"Can't schedule user access lock. The lock must start at least {MINIMUM_MINUTES_TO_LOCK} minutes before the block ends.")
    if minutes_to_start < 0 or minutes_to_end <= 0:
        raise RuntimeError("Cannot schedule user access using a negative or expired delay.")

    user = get_current_user()
    previous_expiry = _get_current_account_expiry(user)

    log(f'Scheduling user account to be unlocked in {minutes_to_end} minutes')
    schedule_run_cmd(["chage", "-E", previous_expiry, user],minutes=minutes_to_end)

    log(f'Scheduling user account to be locked in {minutes_to_start} minutes')
    """
    We need to schedule the lock at least MINIMUM_MINUTES_TO_LOCK before the block ends, so we subtract that from minutes_to_start
    This is to avoid a race condition where the computer might be suspended/turned before scheduled account lock and scheduled restore are meant to be run, 
    because in this case they would be run at the same time once your computer is resumed.
    """
    schedule_run_cmd([
        "/usr/bin/bash",
        "-c",
        f'''
block_file={shlex.quote(str(BLOCK_FILE))}
user={shlex.quote(user)}
minimum_minutes_to_lock={MINIMUM_MINUTES_TO_LOCK}

if [[ ! -f "$block_file" ]]; then
    exit 0
fi

if ! IFS= read -r block_end < "$block_file"; then
    exit 0
fi

if ! block_end_epoch=$(/usr/bin/date --date="$block_end" +%s 2>/dev/null); then
    exit 0
fi

current_epoch=$(/usr/bin/date +%s)
latest_lock_epoch=$((block_end_epoch - minimum_minutes_to_lock * 60))

if (( current_epoch < latest_lock_epoch )); then
    /usr/bin/chage -E 1970-01-02 "$user"
fi
'''.strip(),
    ], minutes=minutes_to_start)
    
    run_cmd(['touch', str(USER_LOCK_FILE)])
    schedule_run_cmd(['rm', str(USER_LOCK_FILE)],minutes=minutes_to_end)
    schedule_logout(minutes_to_start)
