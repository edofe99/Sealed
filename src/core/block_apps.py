import json
from pathlib import Path
import os

from src.core.utils import run_cmd, get_current_user, is_block_active, log, schedule_run_cmd, load_json
from src.core.defaults import APPS_TO_BLOCK, PERMISSIONS_BACKUP_DIR, RESTORE_SCRIPT



def _block_execution(file_folder):
    '''
    Changes permissions of a file / folder so that only root can edit / execute it
    If schedule_restore is int:
      - after said amount of minutes all blocked files and folders will be restored.
    '''
    # create a folder in the sealed install directory where to store a backup for permissions
    # ensure backup directory exists and save permissions
    run_cmd(['mkdir','-p', str(PERMISSIONS_BACKUP_DIR)])

    # create backup filename
    backup_file = PERMISSIONS_BACKUP_DIR / f"{Path(file_folder).parent.name}_{os.path.basename(file_folder)}.bak"

    # Need to use this command because getfacl -R '{path}' will save the path without "/" in front of it
    # and thus the restore command will not find the path.
    run_cmd(["/bin/sh","-c",f'/usr/bin/getfacl --absolute-names -R "{file_folder}" > "{backup_file}"'])
    
    # # folders: readable + traversable
    # run_cmd(["find",str(file_folder),"-type", "d","-exec", "chmod", "555", "{}", "+"])

    # # files: readable only
    # run_cmd(["find",str(file_folder),"-type", "f","-exec", "chmod", "444", "{}", "+"])
    
    # If it is a file then make it executable only by root
    if file_folder.is_file():
        run_cmd(["chown", "root:root", str(file_folder)])
        run_cmd(["chmod", "700", str(file_folder)])

def _kill_app(path_to_exec: str | Path):
    user = get_current_user()
    name = Path(path_to_exec).name
    log(f'Killing {name}...')
    run_cmd(["systemctl",f"--machine={user}@.host","--user","kill","--signal=KILL",f"app-*{name}*",], skip_check=True)


def block_apps(schedule_restore : int = None) -> None:
    # For safety we first schedule file restore, so if any error during blocking file we are able to still restore
    # This will restore EVERYTHING, so safe to run even during a block session
    if schedule_restore:
        schedule_run_cmd([str(RESTORE_SCRIPT)],minutes=schedule_restore)

    _check_json_integrity()
    data = load_json(APPS_TO_BLOCK)
    if data is not None:
        for entry in data:
            path = entry.get("path")
            p = Path(path).expanduser().resolve()
            block_execution = entry.get("block", False)

            if block_execution:
                _kill_app(p)
                _block_execution(p)

def add_app(path_to_executable: str | Path) -> None:
    p = Path(path_to_executable).expanduser().resolve()
    if not p.exists():
        raise RuntimeError(f"executable path does not exist: {p}")
    if not p.is_file():
        raise RuntimeError(f"executable path must be a file: {p}")

    entry = {
        "path": str(p),
        "block": True,
    }
    
    _check_json_integrity()
    data = load_json(APPS_TO_BLOCK)

    # ---- prevent duplicates ----
    for existing in data:
        # If path already exist, skip
        if isinstance(existing, dict) and existing.get("path") == entry["path"]:
            if existing.get("block") != entry["block"]:
                log(f"[INFO] Path already present in config but with different block status: {p}")
                data.remove(existing)
            else:
                log(f"[INFO] Path already present in config: {p}")
                return

    data.append(entry)

    APPS_TO_BLOCK.parent.mkdir(parents=True, exist_ok=True)
    APPS_TO_BLOCK.write_text(json.dumps(data, indent=2) + "\n",encoding="utf-8",)
    log(f"Added {p} to block list.")
    _check_json_integrity()

    if is_block_active():
        log(f"Block session is active, killing and blocking {p}")
        _kill_app(p)
        _block_execution(p)

def remove_app(app_path: Path | str):
    if is_block_active():
        raise RuntimeError(f"Can't remove {app_path} while block session is active.")

    _check_json_integrity()    
    data = load_json(APPS_TO_BLOCK)
    if data is None:
        log(f"[INFO] No apps in block list, skipping removal of {app_path}")
        return
    
    # Rebuild the list without the app to be removed
    data = [entry for entry in data if entry.get("path") != str(app_path)]

    # Save file
    with APPS_TO_BLOCK.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    log(f"Removed {app_path} from block list.")

def _check_json_integrity():
    '''
    This function checks if the APPS_TO_BLOCK JSON file:
    - has duplicates, if so then it removes one copy
    - has paths that no longer exist, if so then it removes them
    - sorts the entries by path
    '''
    data = load_json(APPS_TO_BLOCK)
    if len(data) == 0:
        log("[INFO] List of apps to block is empty, skipping integrity check.")
        return

    log("Starting integrity check for apps to block...")
    seen_paths = set()
    for entry in data:
        path = entry.get("path")
        p = Path(path).expanduser().resolve()

        if not p.exists():
            log(f" -> Path no longer exists, removing it: {p}")
            data.remove(entry)
        
        normalized_path = str(p)
        if normalized_path in seen_paths:
            log(f" -> Duplicate path, removing it: {p}")
            data.remove(entry)
            continue
        
        if not p.is_file():
            log(f" -> Path is not a file, removing it: {p}")
            data.remove(entry)
            continue

        seen_paths.add(normalized_path)

    data.sort(key=lambda entry: entry["path"].casefold())

    APPS_TO_BLOCK.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
    )
    log("Integrity check for apps to block completed.")
