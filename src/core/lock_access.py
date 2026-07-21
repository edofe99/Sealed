import json
import os
import pwd
import shlex
from datetime import datetime, timedelta
from uuid import uuid4

from src.core.defaults import (
    BLOCK_FILE,
    ICON_PATH,
    LOCK_ACCESS_SCHEDULES_FILE,
    MINIMUM_MINUTES_TO_LOCK,
)
from src.core.utils import get_current_user, log, schedule_run_cmd

TIME_FORMAT = "%Y-%m-%d %H:%M"


def get_lock_access_schedules() -> list[dict[str, str]]:
    """Return confirmed lock intervals from the current Sealed session."""
    try:
        data = json.loads(LOCK_ACCESS_SCHEDULES_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []

    if not isinstance(data, list):
        return []

    schedules: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        schedule_id = item.get("id")
        start = item.get("start")
        end = item.get("end")
        if not all(isinstance(value, str) for value in (schedule_id, start, end)):
            continue
        try:
            datetime.strptime(start, TIME_FORMAT)
            datetime.strptime(end, TIME_FORMAT)
        except ValueError:
            continue
        schedules.append({"id": schedule_id, "start": start, "end": end})

    return schedules


def clear_lock_access_schedules() -> None:
    """Remove schedule state after the main Sealed session has ended."""
    LOCK_ACCESS_SCHEDULES_FILE.unlink(missing_ok=True)


def _ranges_overlap_or_touch(
    start: datetime,
    end: datetime,
    other_start: datetime,
    other_end: datetime,
) -> bool:
    return start <= other_end and end >= other_start


def validate_lock_access_range(
    start: datetime,
    end: datetime,
    existing_schedules: list[dict[str, str]] | None = None,
) -> None:
    if start >= end:
        raise RuntimeError("Lock access start time must be before its end time.")

    schedules = (
        get_lock_access_schedules()
        if existing_schedules is None
        else existing_schedules
    )
    for schedule in schedules:
        other_start = datetime.strptime(schedule["start"], TIME_FORMAT)
        other_end = datetime.strptime(schedule["end"], TIME_FORMAT)
        if _ranges_overlap_or_touch(start, end, other_start, other_end):
            raise RuntimeError("Lock access schedules cannot overlap or touch.")


def _save_schedule(start: datetime, end: datetime) -> None:
    schedules = get_lock_access_schedules()
    schedules.append(
        {
            "id": uuid4().hex,
            "start": start.strftime(TIME_FORMAT),
            "end": end.strftime(TIME_FORMAT),
        }
    )
    LOCK_ACCESS_SCHEDULES_FILE.write_text(
        json.dumps(schedules, indent=2) + "\n",
        encoding="utf-8",
    )


def schedule_logout(
    minutes: int,
    minutes_to_end: int,
    logout: bool = True,
) -> None:
    user = get_current_user()
    uid = pwd.getpwnam(user).pw_uid
    now = datetime.now()
    lock_epoch = int((now + timedelta(minutes=minutes)).timestamp())
    end_epoch = int((now + timedelta(minutes=minutes_to_end)).timestamp())

    if logout:
        session_command = [
            "sudo",
            "--user",
            user,
            "--",
            "env",
            f"XDG_RUNTIME_DIR=/run/user/{uid}",
            f"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{uid}/bus",
            "qdbus6",
            "org.kde.Shutdown",
            "/Shutdown",
            "logout",
        ]
        action = "logged out"
        log_action = "logout"
    else:
        session_command = [
            "/usr/bin/bash",
            "-c",
            'session_id=$(/usr/bin/loginctl show-user "$1" --property=Display --value); '
            '[[ -n "$session_id" ]] || exit 1; '
            'exec /usr/bin/loginctl lock-session "$session_id"',
            "_",
            user,
        ]
        action = "locked"
        log_action = "lock"

    schedule_run_cmd(
        [
            "/usr/bin/bash",
            "-c",
            '(( $(/usr/bin/date +%s) < $1 )); exec "${@:2}"',
            "_",
            str(end_epoch),
            *session_command,
        ],
        minutes=minutes,
    )

    log(f"Scheduled session {log_action} in {minutes} minutes for user {user}")

    if minutes > 5:
        _send_lock_notification(
            f"Your session will be {action} in 5 minutes.",
            minutes=minutes - 5,
            valid_until_epoch=lock_epoch,
        )
    if minutes > 1:
        _send_lock_notification(
            f"Your session will be {action} in 1 minute.",
            minutes=minutes - 1,
            valid_until_epoch=lock_epoch,
        )


def _send_lock_notification(
    message: str,
    minutes: int,
    valid_until_epoch: int,
) -> None:
    """Send a warning only while its block and interval are still relevant."""
    user = get_current_user()
    uid = int(os.environ.get("SUDO_UID") or pwd.getpwnam(user).pw_uid)

    notify_params = [
        "/usr/bin/bash",
        "-c",
        '[[ -e "$1" ]] || exit 0; (( $(/usr/bin/date +%s) < $2 )) || exit 0; exec "${@:3}"',
        "_",
        str(BLOCK_FILE),
        str(valid_until_epoch),
        "runuser",
        "-u",
        user,
        "--",
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

    if minutes > 0:
        schedule_run_cmd(notify_params, minutes=minutes, print_log=False)


def lock_access(
    minutes_to_start: int,
    minutes_to_end: int,
    logout_when_lock_starts: bool = True,
) -> None:
    if minutes_to_start <= 0 or minutes_to_end <= 0:
        raise RuntimeError("Lock access times must be in the future.")
    if minutes_to_start >= minutes_to_end:
        raise RuntimeError("Lock access start time must be before its end time.")

    try:
        block_end = datetime.strptime(
            BLOCK_FILE.read_text(encoding="utf-8").strip(),
            TIME_FORMAT,
        )
    except (FileNotFoundError, OSError, ValueError) as error:
        raise RuntimeError("There is no active Sealed block.") from error

    now = datetime.now()
    start = now + timedelta(minutes=minutes_to_start)
    end = now + timedelta(minutes=minutes_to_end)
    normalized_start = start.replace(second=0, microsecond=0)
    normalized_end = end.replace(second=0, microsecond=0)
    latest_start = block_end - timedelta(minutes=MINIMUM_MINUTES_TO_LOCK)

    if normalized_end > block_end:
        raise RuntimeError("Lock access end time must be within the Sealed block.")
    if normalized_start > latest_start:
        raise RuntimeError(
            f"Lock access must start at least {MINIMUM_MINUTES_TO_LOCK} "
            "minutes before the Sealed block ends."
        )

    validate_lock_access_range(normalized_start, normalized_end)

    user = get_current_user()
    interval_end_epoch = int(end.timestamp())
    latest_lock_epoch = int(latest_start.timestamp()) + 59

    log(f"Scheduling user account to be unlocked in {minutes_to_end} minutes")
    schedule_run_cmd(["usermod", "-U", user], minutes=minutes_to_end)

    log(f"Scheduling user account to be locked in {minutes_to_start} minutes")
    schedule_run_cmd(
        [
            "/usr/bin/bash",
            "-c",
            f'''
block_file={shlex.quote(str(BLOCK_FILE))}
user={shlex.quote(user)}
interval_end_epoch={interval_end_epoch}
latest_lock_epoch={latest_lock_epoch}

if [[ ! -f "$block_file" ]]; then
    exit 0
fi

current_epoch=$(/usr/bin/date +%s)
if (( current_epoch < interval_end_epoch && current_epoch <= latest_lock_epoch )); then
    /usr/bin/usermod -L "$user"
fi
'''.strip(),
        ],
        minutes=minutes_to_start,
    )

    schedule_logout(
        minutes_to_start,
        minutes_to_end,
        logout=logout_when_lock_starts,
    )
    _save_schedule(normalized_start, normalized_end)

    minutes_until_block_end = max(
        1,
        int((block_end - now).total_seconds() / 60) + 1,
    )
    schedule_run_cmd(
        ["rm", "-f", str(LOCK_ACCESS_SCHEDULES_FILE)],
        minutes=minutes_until_block_end,
        print_log=False,
    )
