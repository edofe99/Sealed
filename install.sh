#!/usr/bin/env bash
set -Eeuo pipefail

# Re-run as root if needed
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  exec sudo -- "$0" "$@"
fi

SRC_MAIN="./main.py"
SRC_RESTORE="./restore.py"
SRC_APP_DIR="./src"
DEST_DIR="/usr/local/bin/sealed_src"
DEST_APP="${DEST_DIR}/sealed"
DEST_RESTORE="${DEST_DIR}/restore"
VENV_DIR="${DEST_DIR}/.venv"

# Before starting installation, check that in current folder we have all the files we need
[[ -f "$SRC_MAIN" ]] || { echo "Error: $SRC_MAIN not found."; exit 1; }
[[ -f "$SRC_RESTORE" ]] || { echo "Error: $SRC_RESTORE not found."; exit 1; }
[[ -d "$SRC_APP_DIR" ]] || { echo "Error: $SRC_APP_DIR directory not found."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Error: python3 not found in PATH."; exit 1; }

# Create destination directory "/usr/local/bin/sealed_src"
# Delete it if it already exist
# rm -rf -- "${DEST_DIR}"
mkdir -p "$DEST_DIR"

# Move "src" into the sealed_src folder
rm -rf -- "${DEST_DIR}/src"
cp -r "$SRC_APP_DIR" "${DEST_DIR}"

# Copy main.py (launcher) to destination as "sealed", do the same with the restore script
# we save it as that because it's easier for sudoers file and "at" command just calling "sealed" instead of python sealed.py
cp "$SRC_MAIN" "$DEST_APP"
cp "$SRC_RESTORE" "$DEST_RESTORE"

# Make the "sealed" and "restore" files executable
chmod +x "$DEST_APP"
chmod +x "$DEST_RESTORE"

# Create virtual environment if missing (this could be omitted, but better if we will use libraries)
rm -rf -- "$VENV_DIR"
if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi

# Make a symlink so we can execute it by simply typing "sealed --block" instead of doing "usr/local/bin/..."
ln -sf "$DEST_APP" /usr/local/bin/sealed

"$DEST_APP" --check-sudoers

echo "Installation complete:
- App:                $DEST_APP
- Restore script:     $DEST_RESTORE
- Venv:               $VENV_DIR
- Modules:            ${DEST_DIR}/src"