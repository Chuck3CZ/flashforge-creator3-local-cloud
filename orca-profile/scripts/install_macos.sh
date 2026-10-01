#!/usr/bin/env bash
# Install the FlashForge Creator 3 profile into OrcaSlicer on macOS.
#
# This copies the profile into OrcaSlicer's bundled system profiles folder
# (requires an admin password once) and backs up anything that was there
# before. OrcaSlicer must be restarted after install.
#
# Removal:
#   ./install_macos.sh --uninstall
#
# Dry run (print what would happen):
#   ./install_macos.sh --dry-run

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="/Applications/OrcaSlicer.app"
PROFILES_DIR="$APP/Contents/Resources/profiles"
VENDOR_FILE="$PROFILES_DIR/FlashForge.json"
VENDOR_DIR="$PROFILES_DIR/FlashForge"
BACKUP_SUFFIX=".bak-$(date +%Y%m%d-%H%M%S)"

MODE="install"
DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --uninstall) MODE="uninstall" ;;
        --dry-run)   DRY_RUN=1 ;;
        -h|--help)
            sed -n '2,15p' "$0"
            exit 0 ;;
        *) echo "unknown arg: $arg" >&2; exit 2 ;;
    esac
done

if [[ ! -d "$APP" ]]; then
    echo "OrcaSlicer not found at $APP" >&2
    echo "Install it from https://github.com/SoftFever/OrcaSlicer/releases first." >&2
    exit 1
fi

run() {
    if (( DRY_RUN )); then
        printf '[dry-run] %s\n' "$*"
    else
        eval "$@"
    fi
}

if [[ "$MODE" == "uninstall" ]]; then
    echo "Uninstalling FlashForge Creator 3 profile from OrcaSlicer…"
    run sudo rm -f "$VENDOR_FILE"
    run sudo rm -rf "$VENDOR_DIR"
    echo "Done. Restart OrcaSlicer."
    exit 0
fi

echo "Installing FlashForge Creator 3 profile into:"
echo "  $PROFILES_DIR"
echo

if [[ -f "$VENDOR_FILE" ]]; then
    echo "Backing up existing FlashForge.json → FlashForge.json${BACKUP_SUFFIX}"
    run sudo cp -a "$VENDOR_FILE" "${VENDOR_FILE}${BACKUP_SUFFIX}"
fi
if [[ -d "$VENDOR_DIR" ]]; then
    echo "Backing up existing FlashForge/ → FlashForge${BACKUP_SUFFIX}"
    run sudo cp -a "$VENDOR_DIR" "${VENDOR_DIR}${BACKUP_SUFFIX}"
fi

run sudo mkdir -p "$VENDOR_DIR/machine" "$VENDOR_DIR/process" "$VENDOR_DIR/filament"
run sudo cp "$HERE/FlashForge.json" "$VENDOR_FILE"
run sudo cp "$HERE/machine/"*.json "$VENDOR_DIR/machine/"
run sudo cp "$HERE/process/"*.json "$VENDOR_DIR/process/"
run sudo cp "$HERE/filament/"*.json "$VENDOR_DIR/filament/"

echo
echo "Installed. Restart OrcaSlicer, then:"
echo "  1. Settings → Printers → + Add → vendor 'FlashForge' → Creator 3"
echo "  2. Settings → Others → set 'Post-processing scripts' to:"
echo "       python3 $HERE/scripts/gx_converter.py"
echo "     (Orca passes the output .gcode path as the last argument.)"
echo "  3. Read $HERE/README.md for IDEX (left/right/mirror) usage."
