from typing import Iterable, Union
from datetime import datetime, timedelta

import src.utils as utils
import src.leechblock as leechblock
from src.defaults import BLOCK_FILE, ExceptionType, POLICIES_FILE
from src.block_file_folder import block_file_folder

def _block_user_access_to_root(user, minutes, exceptions : Union[ExceptionType, Iterable[ExceptionType], None] = None):
    '''
    Prevent the user to execute commands as root (i.e. sudo)
    '''

    # ----------------- Block user from running commands as root ----------------- #

    utils.add_sudoers_permission(user=user, priority=50, filename='sealed-deny-root',exceptions=None, schedule_removal = minutes)

    # -------------------------- Allow certain commands -------------------------- #

    if exceptions:
        # we give to exceptions an higher priority otherwise they would be overwritten by sealed-deny-root
        utils.add_sudoers_permission(user = user, priority = 90 , filename = 'sealed-extra-exceptions', exceptions = exceptions, schedule_removal = minutes)


def _block_root_access(minutes: int) -> None:
    # These require root -> run via sudo
    block_root_cmd: utils.SubprocessCommand = ["passwd", "-l", "root"]
    restore_root_cmd: utils.SubprocessCommand = ["passwd", "-u", "root"]  # will run as root because we scheduled via sudo at

    utils.schedule_run_cmd(restore_root_cmd, minutes)
    utils.run_cmd(block_root_cmd)


def system_block(block_root = True, exclude_user_from_root = True, minutes = 60, leechblock_blocker = True, exceptions : Union[ExceptionType, Iterable[ExceptionType], None] = None, block_file_folders : bool = False):

    # ------------------------------ Initial checks ------------------------------ #
    user = utils.startup_checks()
    
    if exclude_user_from_root:
        utils.log('Removing user from sudo group')
        _block_user_access_to_root(user, minutes, exceptions)

    if block_root:
        utils.log('Blocking root access using a password')
        _block_root_access(minutes)
    
    # We block the removal of leechblock website blocker, so you can start a website block and not be able to stop it
    if leechblock_blocker:
        utils.log('Installing Firefox Leechblock policy')
        leechblock.check_policy()
        # Schedule the removal of the leechblock policies
        # this is commented because otwewise you would need to restart firefox at every new run
        # for me it's ok to always have leechblock uninstallable
        # utils.schedule_run_cmd(["rm", "-f", "--", str(POLICIES_FILE)], minutes)

    if block_file_folders:
        utils.log('Blocking file folders')
        block_file_folder(schedule_restore=minutes)

    block_end = (datetime.now() + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M")
    utils.log(f'BLOCK ACTIVE UNTIL {block_end}')
    BLOCK_FILE.write_text(block_end + "\n")
