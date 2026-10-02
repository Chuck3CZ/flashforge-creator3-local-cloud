#!/usr/bin/env bash
# Install the FlashForge Creator 3 profile into OrcaSlicer on macOS.
#
# OrcaSlicer loads system presets from its per-user cache
#   ~/Library/Application Support/OrcaSlicer/system/
# and only refreshes that cache from the app bundle when the bundled vendor
# version is newer. Installing into the cache therefore:
#   - is what OrcaSlicer actually reads (bundle edits are ignored),
#   - needs no admin password,
#   - does not touch OrcaSlicer.app, so macOS never reports it as "damaged".
#
# Launch OrcaSlicer once before installing (so the cache exists), and re-run
# this script after every OrcaSlicer update (an update rewrites the cache).
#
# Removal:   ./install_macos.sh --uninstall
# Dry run:   ./install_macos.sh --dry-run

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYS="$HOME/Library/Application Support/OrcaSlicer/system"
VENDOR_FILE="$SYS/FlashForge.json"     # macOS FS is case-insensitive (Flashforge.json)
VENDOR_DIR="$SYS/FlashForge"

MODE="install"; DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --uninstall) MODE="uninstall" ;;
        --dry-run)   DRY_RUN=1 ;;
        -h|--help)   sed -n '2,17p' "$0"; exit 0 ;;
        *) echo "unknown arg: $arg" >&2; exit 2 ;;
    esac
done

if [[ ! -f "$VENDOR_FILE" ]]; then
    echo "OrcaSlicer system cache not found: $VENDOR_FILE" >&2
    echo "Launch OrcaSlicer once, quit it (Cmd+Q), then run this again." >&2
    exit 1
fi

if pgrep -x OrcaSlicer >/dev/null; then
    echo "OrcaSlicer is running – quit it with Cmd+Q first, then re-run." >&2
    exit 1
fi

run() { if (( DRY_RUN )); then printf '[dry-run] %s\n' "$*"; else eval "$@"; fi; }

# Rewrite the vendor index: drop any old Creator 3 entries, add the current
# ones when installing.
update_vendor() {
    local add="$1"
    (( DRY_RUN )) && { echo "[dry-run] update vendor index (add=$add)"; return; }
    python3 - "$VENDOR_FILE" "$HERE/FlashForge.json" "$add" <<'PY'
import json, sys
vendor_path, addon_path, add = sys.argv[1], sys.argv[2], sys.argv[3] == "1"
v = json.load(open(vendor_path))
a = json.load(open(addon_path))
def is_c3(e):
    n = e.get("name", "")
    return "Creator 3" in n or "Creator3" in n
for key in ("machine_model_list", "process_list", "filament_list", "machine_list"):
    lst = [e for e in v.get(key, []) if not is_c3(e)]
    if add:
        have = {e["name"] for e in lst}
        lst += [e for e in a.get(key, []) if e["name"] not in have]
    v[key] = lst
json.dump(v, open(vendor_path, "w"), indent=4, ensure_ascii=False)
print("  vendor now lists %d printer models" % len(v["machine_model_list"]))
PY
}

if [[ "$MODE" == "uninstall" ]]; then
    echo "Uninstalling FlashForge Creator 3 profile from the OrcaSlicer cache…"
    update_vendor 0
    run rm -f "\"$VENDOR_DIR/machine/FlashForge_Creator3.json\"" \
              "\"$VENDOR_DIR/machine/FlashForge_Creator3_model.json\""
    run rm -f "\"$VENDOR_DIR/process/\"*Creator3*.json" "\"$VENDOR_DIR/filament/\"*Creator3*.json"
    echo "Done. Start OrcaSlicer."
    exit 0
fi

echo "Installing FlashForge Creator 3 into: $SYS"
run mkdir -p "\"$VENDOR_DIR/machine\"" "\"$VENDOR_DIR/process\"" "\"$VENDOR_DIR/filament\""
run cp "\"$HERE/machine/FlashForge_Creator3.json\"" "\"$HERE/machine/FlashForge_Creator3_model.json\"" "\"$VENDOR_DIR/machine/\""
run cp "\"$HERE/process/\"*Creator3*.json" "\"$VENDOR_DIR/process/\""
run cp "\"$HERE/filament/\"*Creator3*.json" "\"$VENDOR_DIR/filament/\""
update_vendor 1

# Wire the .gx converter into the Creator 3 process presets (absolute path,
# system python so it works when OrcaSlicer is launched from the Dock).
PP_CMD="/usr/bin/python3 \"$HERE/scripts/gx_converter.py\""
if (( DRY_RUN )); then
    echo "[dry-run] set post_process = $PP_CMD"
else
    python3 - "$PP_CMD" "$VENDOR_DIR/process/"*Creator3*.json <<'PY'
import json, sys
cmd, files = sys.argv[1], sys.argv[2:]
for f in files:
    d = json.load(open(f))
    d["post_process"] = [cmd]
    json.dump(d, open(f, "w"), indent=4, ensure_ascii=False)
print("  post_process set on %d process presets" % len(files))
PY
fi

echo
echo "Installed. Start OrcaSlicer, then:"
echo "  1. Printer selector → FlashForge Creator 3 0.4 nozzle"
echo "     (if missing: Add/Remove Printers → Flashforge → Creator 3)"
echo "  2. Slicing then saves a .gx directly (the converter is wired in"
echo "     automatically as the post-processing script)."
echo "  3. Right-click the model → Set Extruder: 1 = right (T0), 2 = left (T1)."
