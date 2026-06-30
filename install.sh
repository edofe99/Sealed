#!/usr/bin/env bash
set -Eeuo pipefail

# Re-run as root if needed
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  exec sudo -- "$0" "$@"
fi

SRC_MAIN="./main.py"
DEST_DIR="/usr/local/bin/sealed_src"
DEST_APP="${DEST_DIR}/sealed"

SRC_APP_DIR="./src"

SRC_GUI="./src/gui/gui.py"
DEST_GUI="${DEST_DIR}/sealed-qt"

VENV_DIR="${DEST_DIR}/.venv"

SRC_POLICY="./assets/com.sealed.gui.policy"
POLKIT_ACTIONS_DIR="/usr/share/polkit-1/actions"

SRC_DESKTOP="./assets/sealed.desktop"
DESKTOP_APPLICATIONS_DIR="/usr/share/applications"

SRC_ICON="./assets/sealed.png"
ICON_DEST_DIR="/usr/share/icons/hicolor/512x512/apps"
DEST_ASSETS_DIR="${DEST_DIR}/assets"

# Before starting installation, check that in current folder we have all the files we need
[[ -f "$SRC_MAIN" ]] || { echo "Error: $SRC_MAIN not found."; exit 1; }
# [[ -f "$SRC_RESTORE" ]] || { echo "Error: $SRC_RESTORE not found."; exit 1; }
[[ -d "$SRC_APP_DIR" ]] || { echo "Error: $SRC_APP_DIR directory not found."; exit 1; }
[[ -f "$SRC_POLICY" ]] || { echo "Error: $SRC_POLICY not found."; exit 1; }
[[ -f "$SRC_DESKTOP" ]] || { echo "Error: $SRC_DESKTOP not found."; exit 1; }
[[ -f "$SRC_ICON" ]] || { echo "Error: $SRC_ICON not found."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Error: python3 not found in PATH."; exit 1; }

echo "Installing Sealed..."

echo "Create destination directory /usr/local/bin/sealed_src"
# Delete it if it already exist
# rm -rf -- "${DEST_DIR}"
mkdir -p "$DEST_DIR"

echo "Installing application files"
rm -rf -- "${DEST_DIR}/src"
cp -r "$SRC_APP_DIR" "${DEST_DIR}"
mkdir -p "$DEST_ASSETS_DIR"
install -m 0644 "$SRC_ICON" "${DEST_ASSETS_DIR}/sealed.png"

# Copy main.py (launcher) to destination as "sealed", do the same with the restore script
# we save it as that because it's easier for sudoers file and "at" command just calling "sealed" instead of python sealed.py
echo "Installing scripts"
cp "$SRC_MAIN" "$DEST_APP"
# cp "$SRC_RESTORE" "$DEST_RESTORE"
if [[ -f "$SRC_GUI" ]]; then
  cp "$SRC_GUI" "$DEST_GUI"
fi

echo "Ensuring permissions"
# Make the "sealed" and "restore" files executable
chmod +x "$DEST_APP"
# chmod +x "$DEST_RESTORE"
if [[ -f "$DEST_GUI" ]]; then
  chmod +x "$DEST_GUI"
fi

echo "Creating virtual environment"
# Create virtual environment if missing (this could be omitted, but better if we will use libraries)
rm -rf -- "$VENV_DIR"
if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
  $VENV_DIR/bin/python -m pip install --upgrade pip
  $VENV_DIR/bin/python -m pip install PySide6
fi

echo "Creating launcher shortcut"
# Make a symlink so we can execute it by simply typing "sealed --block" instead of doing "usr/local/bin/..."
ln -sf "$DEST_APP" /usr/local/bin/sealed
if [[ -f "$DEST_GUI" ]]; then
  ln -sf "$DEST_GUI" /usr/local/bin/sealed-qt
fi

echo "Installing Polkit action"
install -D -m 0644 "$SRC_POLICY" "${POLKIT_ACTIONS_DIR}/com.sealed.gui.policy"

echo "Installing desktop launcher"
install -D -m 0644 "$SRC_ICON" "${ICON_DEST_DIR}/sealed.png"
install -D -m 0644 "$SRC_DESKTOP" "${DESKTOP_APPLICATIONS_DIR}/sealed.desktop"
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f -q /usr/share/icons/hicolor || true
fi
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DESKTOP_APPLICATIONS_DIR" || true
fi

echo "First run of Sealed, checking permissions..."
"$DEST_APP" --check-sudoers

echo "✅ Installation complete:
- App:                $DEST_APP
- GUI:                $DEST_GUI
- Venv:               $VENV_DIR
- Modules:            ${DEST_DIR}/src
- Desktop launcher:   ${DESKTOP_APPLICATIONS_DIR}/sealed.desktop
- Icon:               ${ICON_DEST_DIR}/sealed.png"
