#!/usr/bin/env bash
# Install the FlashForge Creator 3 profile into OrcaSlicer on macOS.
#
# MERGES Creator 3 into OrcaSlicer's existing FlashForge vendor (keeps the stock
# models) and copies the Creator 3 machine/process/filament presets.
# Requires an admin password once. Restart OrcaSlicer afterwards.
#
# NOTE: this writes inside the OrcaSlicer.app bundle, which invalidates Apple's
# code signature. macOS may then report the app as "damaged". See README for how
# to clear that yourself (it is your decision, not done by this script).
#
# Removal:   ./install_macos.sh --uninstall
# Dry run:   ./install_macos.sh --dry-run

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="/Applications/OrcaSlicer.app"
PROFILES_DIR="$APP/Contents/Resources/profiles"
VENDOR_FILE="$PROFILES_DIR/FlashForge.json"
VENDOR_DIR="$PROFILES_DIR/FlashForge"
STOCK_ORIG="$PROFILES_DIR/FlashForge.json.orig"   # true stock, kept for merges

MODE="install"; DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --uninstall) MODE="uninstall" ;;
        --dry-run)   DRY_RUN=1 ;;
        -h|--help)   sed -n '2,13p' "$0"; exit 0 ;;
        *) echo "unknown arg: $arg" >&2; exit 2 ;;
    esac
done

[[ -d "$APP" ]] || { echo "OrcaSlicer not found at $APP" >&2; exit 1; }

run() { if (( DRY_RUN )); then printf '[dry-run] %s\n' "$*"; else eval "$@"; fi; }

if [[ "$MODE" == "uninstall" ]]; then
    echo "Uninstalling FlashForge Creator 3 profile…"
    [[ -f "$STOCK_ORIG" ]] && run sudo cp -a "$STOCK_ORIG" "$VENDOR_FILE"
    run sudo rm -f "$VENDOR_DIR/machine/FlashForge_Creator3.json" \
                   "$VENDOR_DIR/machine/FlashForge_Creator3_model.json"
    run sudo rm -f "$VENDOR_DIR/process/"*Creator3*.json \
                   "$VENDOR_DIR/filament/"*Creator3*.json
    echo "Done. Restart OrcaSlicer (see README if it reports 'damaged')."
    exit 0
fi

# --- establish the TRUE stock vendor list as FlashForge.json.orig (once) ---
if [[ ! -f "$STOCK_ORIG" ]]; then
    OLDEST_BAK="$(ls -1 "$VENDOR_FILE".bak-* 2>/dev/null | sort | head -1 || true)"
    if [[ -n "$OLDEST_BAK" ]]; then
        echo "Using previous backup as stock base: $(basename "$OLDEST_BAK")"
        run sudo cp -a "$OLDEST_BAK" "$STOCK_ORIG"
    else
        echo "Preserving current FlashForge.json as stock base"
        run sudo cp -a "$VENDOR_FILE" "$STOCK_ORIG"
    fi
fi

echo "Installing FlashForge Creator 3 into: $PROFILES_DIR"
run sudo mkdir -p "$VENDOR_DIR/machine" "$VENDOR_DIR/process" "$VENDOR_DIR/filament"

# --- merge: stock vendor list + Creator 3 entries (dedupe by name) ---
MERGED="$(mktemp)"
python3 - "$STOCK_ORIG" "$HERE/FlashForge.json" "$MERGED" <<'PY'
import json, sys
stock = json.load(open(sys.argv[1]))
addon = json.load(open(sys.argv[2]))
for key in ("machine_model_list", "process_list", "filament_list", "machine_list"):
    have = {e.get("name") for e in stock.get(key, [])}
    for e in addon.get(key, []):
        if e.get("name") not in have:
            stock.setdefault(key, []).append(e); have.add(e.get("name"))
json.dump(stock, open(sys.argv[3], "w"), indent=4, ensure_ascii=False)
print("  merged vendor now lists %d printer models"
      % len(stock.get("machine_model_list", [])))
PY

run sudo cp "$MERGED" "$VENDOR_FILE"; rm -f "$MERGED"
run sudo cp "$HERE/machine/FlashForge_Creator3.json" \
            "$HERE/machine/FlashForge_Creator3_model.json" "$VENDOR_DIR/machine/"
run sudo cp "$HERE/process/"*Creator3*.json "$VENDOR_DIR/process/"
run sudo cp "$HERE/filament/"*Creator3*.json "$VENDOR_DIR/filament/"

echo
echo "Installed (stock FlashForge models kept + Creator 3 added)."
echo "Restart OrcaSlicer, then:"
echo "  1. + Add printer → vendor 'FlashForge' → Creator 3"
echo "  2. Settings → Others → 'Post-processing scripts':"
echo "       python3 $HERE/scripts/gx_converter.py"
echo "  3. See $HERE/README.md for IDEX usage and the 'damaged' note."
