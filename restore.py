#!/usr/local/bin/sealed_src/.venv/bin/python
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import argparse

from src.defaults import FILE_FOLDERS_TO_BLOCK, PERMISSIONS_BACKUP_DIR
from src.utils import run_cmd, log


def remove_immutability() -> None:
    if not FILE_FOLDERS_TO_BLOCK.is_file():
        raise RuntimeError(f"Config file not found: {FILE_FOLDERS_TO_BLOCK}")

    try:
        data: Any = json.loads(FILE_FOLDERS_TO_BLOCK.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in {FILE_FOLDERS_TO_BLOCK}: {e}") from e

    if not isinstance(data, list):
        raise RuntimeError(f"Config must be a JSON list, got {type(data).__name__}")

    for i, entry in enumerate(data, start=1):
        try:
            raw_path = entry.get("path")
            if not isinstance(raw_path, str) or not raw_path.strip():
                raise RuntimeError(f"Entry #{i} missing/invalid 'path'")

            p = Path(raw_path).expanduser().resolve()
            if not p.is_absolute():
                raise RuntimeError(f"Entry #{i} path must be absolute: {p}")
            if not p.exists():
                raise RuntimeError(f"Entry #{i} path does not exist: {p}")

            run_cmd(["/usr/bin/chattr", "-R", "-i", str(p)])

        except Exception as e:
            log(f"[WARN] Skipping entry #{i}: {e}")
            continue

def restore_acl_backups() -> None:
    if not PERMISSIONS_BACKUP_DIR.is_dir():
        raise RuntimeError(f"Backup directory not found: {PERMISSIONS_BACKUP_DIR}")

    for bak in PERMISSIONS_BACKUP_DIR.iterdir():
        try:
            if not bak.exists():
                continue
            if not bak.is_file():
                continue
            if bak.stat().st_size == 0:
                continue

            run_cmd(["/bin/sh","-c",f"/usr/bin/setfacl --restore={bak} && rm -f -- {bak}"])

        except Exception as e:
            log(f"[WARN] Failed to schedule restore of ACL from {bak}: {e}")
            continue


def main() -> None:
    p = argparse.ArgumentParser(
        prog="sealed-unblock",
        description="Restore permissions and/or remove immutability for paths managed by Sealed",
    )

    p.add_argument(
        "--restore-immutability",
        action="store_true",
        help="Remove immutable flag (-i) recursively from all paths in FILE_FOLDERS_TO_BLOCK",
    )

    p.add_argument(
        "--restore-permissions",
        action="store_true",
        help="Restore ACLs from PERMISSIONS_BACKUP_DIR and delete backups if successful",
    )

    args = p.parse_args()

    if not args.restore_immutability and not args.restore_permissions:
        p.error("At least one of --restore-immutability or --restore-permissions must be specified")

    if args.restore_immutability:
        remove_immutability()

    if args.restore_permissions:
        restore_acl_backups()


if __name__ == "__main__":
    remove_immutability()
    restore_acl_backups()