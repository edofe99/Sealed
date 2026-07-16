from typing import Iterable, Union
from datetime import datetime, timedelta

from src.core.block_file_folder import block_file_folder
from src.core.block_apps import block_apps
from src.core.defaults import BLOCK_FILE, ExceptionType
import src.core.utils as utils
from src.core.lock_access import lock_access
import src.website_blocker.leechblock as leechblock

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
    # First we schedule enabling root access with password
    utils.schedule_run_cmd(["passwd", "-u", "root"], minutes)
    # Then we remove root access with passowrd
    utils.run_cmd(["passwd", "-l", "root"])


def system_block(block_root = True,
                 minutes = 60,
                 leechblock_blocker = True,
                 exceptions : Union[ExceptionType, Iterable[ExceptionType], None] = None,
                 block_file_folders : bool = True,
                 block_applications : bool = True,
                 lock_access_minutes : int = None) -> None:

    # ------------------------------ Initial checks ------------------------------ #
    user = utils.startup_checks()

    if block_root:
        utils.log(f'Revoking root commands execution for {utils.get_current_user()}')
        _block_user_access_to_root(user, minutes, exceptions)
        
        utils.log('Blocking root access')
        _block_root_access(minutes)
        
        block_end = (datetime.now() + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M")
        BLOCK_FILE.write_text(block_end + "\n")

        utils.send_notification(f"BLOCK ACTIVE UNTIL {block_end}")
        utils.send_notification("BLOCK ENDED", minutes)
        utils.log(f'BLOCK ACTIVE UNTIL {block_end}')

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
    
    if block_applications:
        utils.log('Blocking apps')
        block_apps(schedule_restore=minutes)

    if  lock_access_minutes is not None:
        utils.log(f'Locking user access in {lock_access_minutes} minutes')
        lock_access(
            minutes_to_start=lock_access_minutes,
            minutes_to_end=minutes,
        )