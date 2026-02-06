#!/usr/bin/env bash
#set -Eeuo pipefail

# Re-run as root if needed
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  exec sudo -- "$0" "$@"
fi

SRC_MAIN="./main.py"
SRC_RESTORE="./restore.py"
SRC_APP_DIR="./src"
SRC_ASSETS_DIR="./assets"
DEST_DIR="/usr/local/bin/sealed_src"
DEST_APP="${DEST_DIR}/sealed"
DEST_RESTORE="${DEST_DIR}/restore"
VENV_DIR="${DEST_DIR}/.venv"


# Sanity checks
[[ -f "$SRC_MAIN" ]] || { echo "Error: $SRC_MAIN not found."; exit 1; }
[[ -f "$SRC_RESTORE" ]] || { echo "Error: $SRC_RESTORE not found."; exit 1; }
[[ -d "$SRC_APP_DIR" ]] || { echo "Error: $SRC_APP_DIR directory not found."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Error: python3 not found in PATH."; exit 1; }

# Create destination directory
# rm -rf "$DEST_DIR"
mkdir -p "$DEST_DIR"

# Move main.py to destination as "sealed"
cp "$SRC_MAIN" "$DEST_APP"
cp "$SRC_RESTORE" "$DEST_RESTORE"

# Create virtual environment if missing
rm -rf $VENV_DIR
if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi

# Upgrade pip and install ttkbootstrap
# "$VENV_DIR/bin/pip" install --upgrade pip
# "$VENV_DIR/bin/pip" install ttkbootstrap

# Make the "sealed" file executable
chmod +x "$DEST_APP"

# Make the desktop file executable
chmod +x "$SRC_ASSETS_DIR/sealed.desktop"
cp "$SRC_ASSETS_DIR/sealed.desktop" /usr/share/applications/sealed.desktop
cp "$SRC_ASSETS_DIR/sealed.png" "$DEST_DIR/sealed.png"

# Move app_functions into destination
# Remove existing target to ensure a clean move
rm -rf "$SRC_APP_DIR"
cp -r "$SRC_APP_DIR" "${DEST_DIR}"

# Make a symlink so we can execute it
ln -sf "$DEST_APP" /usr/local/bin/sealed

"$DEST_APP" --check-sudoers

echo "Installation complete:
- App:                $DEST_APP
- Restore script:     $DEST_RESTORE
- Venv:               $VENV_DIR
- Modules:            ${DEST_DIR}/app_functions"