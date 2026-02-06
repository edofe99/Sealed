import os
from pathlib import Path
import json
from typing import Any


from src.utils import run_cmd, schedule_run_cmd, log, is_block_active
from src.defaults import PERMISSIONS_BACKUP_DIR, FILE_FOLDERS_TO_BLOCK, RESTORE_SCRIPT

def _make_file_folder_read_only(file_folder):
    '''
    Changes permissions of a file / folder so that only root can edit / execute it
    '''
    # create a folder in the sealed install directory where to store a backup for permissions
    # ensure backup directory exists and save permissions
    run_cmd(['mkdir','-p',f"'{PERMISSIONS_BACKUP_DIR}'"])

    # create backup filename
    backup_file = PERMISSIONS_BACKUP_DIR / f"{Path(file_folder).parent.name}_{os.path.basename(file_folder)}.bak"

    # Need to use this command because getfacl -R '{path}' will save the path without "/" in front of it
    # and thus the restore command will not find the path.
    os.system(f'getfacl --absolute-names -R "{file_folder}" > "{backup_file}"')
    
    # folders: readable + traversable
    run_cmd(["find",file_folder,"-type", "d","-exec", "chmod", "555", "{}", "+"])

    # files: readable only
    run_cmd(["find",file_folder,"-type", "f","-exec", "chmod", "444", "{}", "+"])


    # Also make the file immutable to prevent changes
    _make_file_folder_immutable(file_folder)


def _make_file_folder_immutable(file_folder):
    run_cmd(["chattr","-R","+i",file_folder])


def block_file_folder(file_folder_to_block: str | Path | None = None, block_execution: bool = False, schedule_restore : int = None) -> None:
    """
    If file_folder_to_block is provided:
      - convert it into a single-entry JSON-like list and process it
    If file_folder_to_block is None:
      - load FILE_FOLDERS_TO_BLOCK JSON and process all entries
    If schedule_restore is int:
      - after said amount of minutes all blocked files and folders will be restored.
    Each entry:
      - path (absolute)
      - block_execution (bool)
    """

    # ---- normalize input into `data` ----
    if file_folder_to_block is not None:
        p = file_folder_to_block if isinstance(file_folder_to_block, Path) else Path(file_folder_to_block)
        p = p.expanduser().resolve()

        if not p.is_absolute():
            raise RuntimeError(f"path must be absolute: {p}")
        if not p.exists():
            raise RuntimeError(f"path does not exist: {p}")

        data: list[dict[str, Any]] = [
            {
                "path": str(p),
                "block_execution": bool(block_execution),
            }
        ]

    else:
        if not FILE_FOLDERS_TO_BLOCK.is_file():
            log('No file or folders to block.')
            return

        try:
            data = json.loads(FILE_FOLDERS_TO_BLOCK.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in {FILE_FOLDERS_TO_BLOCK}: {e}") from e

        if not isinstance(data, list):
            raise RuntimeError(f"Config must be a JSON list of entries, got {type(data).__name__}")

    for i, entry in enumerate(data, start=1):
        if not isinstance(entry, dict):
            raise RuntimeError(f"Entry #{i} must be an object, got {type(entry).__name__}")

        raw_path = entry.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise RuntimeError(f"Entry #{i} missing/invalid 'path'")

        p = Path(raw_path).expanduser().resolve()
        if not p.is_absolute():
            raise RuntimeError(f"Entry #{i} path must be absolute: {p}")

        exec_block = entry.get("block_execution", False)
        if not isinstance(exec_block, bool):
            raise RuntimeError(f"Entry #{i} 'block_execution' must be boolean")

        # ---- actions ----
        _make_file_folder_immutable(p)

        if exec_block:
            _make_file_folder_read_only(p)

    if schedule_restore:
        schedule_run_cmd([str(RESTORE_SCRIPT)],minutes=schedule_restore)

def add_file_folder(file_folder: Path, block_execution: bool = False) -> None:
    """
    Append a new entry to FILE_FOLDERS_TO_BLOCK JSON:
      {
        "path": "<absolute path>",
        "block_execution": <bool>
      }

    If the JSON file does not exist, it is created.
    If the path already exists, it is not duplicated.
    """

    p = file_folder.expanduser().resolve()

    if not p.is_absolute():
        raise RuntimeError(f"path must be absolute: {p}")
    if not p.exists():
        raise RuntimeError(f"path does not exist: {p}")

    entry = {
        "path": str(p),
        "block_execution": bool(block_execution),
    }

    # ---- load or initialize JSON ----
    if FILE_FOLDERS_TO_BLOCK.exists():
        try:
            data: Any = json.loads(FILE_FOLDERS_TO_BLOCK.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in {FILE_FOLDERS_TO_BLOCK}: {e}") from e

        if not isinstance(data, list):
            raise RuntimeError(
                f"Config must be a JSON list, got {type(data).__name__}"
            )
    else:
        data = []

    # ---- prevent duplicates ----
    for existing in data:
        if isinstance(existing, dict) and existing.get("path") == entry["path"]:
            log(f"[INFO] Path already present in config: {p}")
            return

    # ---- append and write back ----
    data.append(entry)

    FILE_FOLDERS_TO_BLOCK.parent.mkdir(parents=True, exist_ok=True)
    FILE_FOLDERS_TO_BLOCK.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
    )

    # If we are inside a block then activate immediately
    if is_block_active():
        block_file_folder(file_folder, block_execution)

