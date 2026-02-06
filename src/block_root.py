from typing import Iterable, Union
from datetime import datetime, timedelta

import src.utils as utils
# from src.website_blocker import leechblock
from src.defaults import BLOCK_FILE, ExceptionType


def _block_user_access_to_root(user, minutes, exceptions : Union[ExceptionType, Iterable[ExceptionType], None] = None):
    '''
    Prevent the user to execute commands as root (i.e. sudo)
    '''

    # ----------------- Block user from running commands as root ----------------- #

    utils.add_sudoers_permission(user=user, priority=50, filename='sealed-deny-root',exceptions=None, schedule_removal = minutes)

    # -------------------------- Allow certain commands -------------------------- #

    if exceptions:
        utils.add_sudoers_permission(user = user, priority = 90 , filename = 'sealed-extra-exceptions', exceptions = exceptions, schedule_removal = minutes)


def _block_root_access(minutes: int) -> None:
    # These require root -> run via sudo
    block_root_cmd: utils.SubprocessCommand = ["passwd", "-l", "root"]
    restore_root_cmd: utils.SubprocessCommand = ["passwd", "-u", "root"]  # will run as root because we scheduled via sudo at

    utils.schedule_run_cmd(restore_root_cmd, minutes)
    utils.run_cmd(block_root_cmd)


def is_block_active():
    try:
        # .strip() removes any accidental newlines or spaces
        time_str = BLOCK_FILE.read_text().strip()

        # 2. Convert the string to a datetime object
        file_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M")

        # 3. Compare with the current time
        now = datetime.now()

        if file_time <= now:
            utils.run_cmd(['rm',str(BLOCK_FILE)])
            return False
        elif file_time > now:
            return True
        
    except FileNotFoundError, ValueError:
        utils.log("Block file not found")
        return False


def system_block(block_root = True, exclude_user_from_root = True, minutes = 60, leechblock_blocker = True, exceptions : Union[ExceptionType, Iterable[ExceptionType], None] = None):

    # ------------------------------ Initial checks ------------------------------ #
    user = utils.startup_checks()
    
    if exclude_user_from_root:
        utils.log(exceptions)
        _block_user_access_to_root(user, minutes, exceptions)

    if block_root:
        _block_root_access(minutes)
    
    # if leechblock_blocker:
    #     leechblock.check_policy()

    BLOCK_FILE.write_text((datetime.now() + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M") + "\n")