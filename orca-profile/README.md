# OrcaSlicer profile for FlashForge Creator 3

Everything you need to slice for the **FlashForge Creator 3** (and Creator 3
Pro) in **OrcaSlicer** on **macOS or Windows** — profiles, a `.gx`
converter, and IDEX mirror / replica post-processors.

Stock OrcaSlicer has no Creator 3 profile and the official
Orca-Flashforge fork only covers the Adventurer family and AD5X.
This add-on fills that gap without forking OrcaSlicer or writing a
plugin — OrcaSlicer has no plugin API, so vendor extensions are the
right shape here.

> **Works on macOS and Windows the same way.** Profiles are plain JSON
> (OS-agnostic). The post-processing scripts are Python 3 (bundled with
> macOS; on Windows install Python 3.10+ from python.org and tick "Add
> to PATH"). Only the installer differs: `install_macos.sh` for Mac,
> `install_windows.ps1` for Windows.

Credits and layout references:

- [HellEvro/FF_Gcode_to_GX](https://github.com/HellEvro/FF_Gcode_to_GX) —
  validated 58-byte `.gx` header against FlashPrint 5 output on a real
  Creator 3 Pro
- [Official FlashForge Cura Setup PDF](https://en.fss.flashforge.com/10000/software/a42243ba68cb81dc8afd7b7fb3e71dcf.pdf) —
  bed geometry, start/end gcode, nozzle offsets
- IDEX mode semantics confirmed by reverse-engineering the
  `creator3-arm` firmware binary (see "How IDEX actually works" below)

## Contents

1. [What you get](#what-you-get)
2. [Install on macOS](#install-on-macos)
3. [Install on Windows](#install-on-windows)
4. [Add the printer in OrcaSlicer](#add-the-printer-in-orcaslicer)
5. [Wire up the `.gx` converter](#wire-up-the-gx-converter)
6. [Printing on left / right / dual-material](#printing-on-left--right--dual-material)
7. [Mirror and replica (IDEX modes 1 and 2)](#mirror-and-replica-idex-modes-1-and-2)
8. [How IDEX actually works on Creator 3 (RE findings)](#how-idex-actually-works-on-creator-3-re-findings)
9. [What's inside this folder](#whats-inside-this-folder)
10. [Troubleshooting](#troubleshooting)

## What you get

- Printer profile `FlashForge Creator 3` — 300×250×200 mm bed with
  centre-origin coordinates, dual 0.4 mm IDEX nozzles, FlashForge start /
  end / pause G-code with `M118` border info, `M651/M652` chamber LED and
  `G162` Z-home.
- Four filament presets: PLA, PETG, ABS, PVA (soluble support).
- Three process presets: 0.10 mm Fine, 0.20 mm Standard, 0.30 mm Draft.
  Prime tower is on by default (needed for dual-material).
- `gx_converter.py` — turns OrcaSlicer's `.gcode` output into FlashForge
  `.gx` (58-byte header + 80×60 BMP + gcode). Header layout matches
  FlashPrint 5 byte-for-byte; validated against the HellEvro reference.
- `idex_mirror.py` — rewrites single-head gcode into **mirror** or
  **replica** motion for the second head when you don't want to pick
  the mode on the printer's touchscreen.
- Installers that back up any existing FlashForge profiles before they
  overwrite them.

## Install on macOS

Prereqs: OrcaSlicer installed in `/Applications/OrcaSlicer.app`
(download from [SoftFever releases](https://github.com/SoftFever/OrcaSlicer/releases)).

```bash
git clone https://github.com/Chuck3CZ/flashforge-creator3-local-cloud.git
cd flashforge-creator3-local-cloud/orca-profile
./scripts/install_macos.sh
```

The installer asks for `sudo` once (OrcaSlicer's bundled profiles live
inside the `.app`), backs up any existing `FlashForge.json` /
`FlashForge/` with a timestamped suffix, and prints the next steps.

Rerun after each OrcaSlicer update — bundled profiles are replaced on
update. `./scripts/install_macos.sh --uninstall` removes it.

Dry run: `./scripts/install_macos.sh --dry-run`.

## Install on Windows

Prereqs: OrcaSlicer in its default `C:\Program Files\OrcaSlicer\`
(or pass `-OrcaRoot <path>`), and Python 3.10+ from
[python.org](https://www.python.org/downloads/windows/) with "Add to
PATH" ticked.

```powershell
git clone https://github.com/Chuck3CZ/flashforge-creator3-local-cloud.git
cd flashforge-creator3-local-cloud\orca-profile

# One-time: allow this script to run in this session
Set-ExecutionPolicy -Scope Process Bypass

# Elevated PowerShell (Program Files write)
.\scripts\install_windows.ps1
```

Uninstall: `.\scripts\install_windows.ps1 -Uninstall`. Dry run:
`.\scripts\install_windows.ps1 -DryRun`.

## Add the printer in OrcaSlicer

Restart OrcaSlicer, then:

1. **Settings → Printers → + Add printer**
2. Vendor **FlashForge** → **Creator 3** → nozzle **0.4 mm** → **Add**
3. On the first wizard step keep the FlashForge Generic PLA/PETG/ABS
   presets ticked.

The printer shows up in the top-left dropdown as *FlashForge Creator 3
0.4 nozzle*. Pick one of the three process presets (0.10/0.20/0.30 mm).

## Wire up the `.gx` converter

OrcaSlicer exports `.gcode` by default. The Creator 3 wants `.gx` (binary
header + thumbnail + gcode). Add the converter as a post-processing step:

**Settings → Others → Post-processing scripts:**

- **macOS**
  ```
  python3 "/Users/<you>/flashforge-creator3-local-cloud/orca-profile/scripts/gx_converter.py"
  ```
- **Windows**
  ```
  python "C:\Users\<you>\flashforge-creator3-local-cloud\orca-profile\scripts\gx_converter.py"
  ```

OrcaSlicer appends the output `.gcode` path for you; the converter
writes a sibling `.gx` and leaves the `.gcode` behind for inspection.
Set `GX_KEEP_GCODE=0` in your shell to delete the `.gcode` after
conversion.

Upload the `.gx` to the printer however you already do: SD card, your
own [local cloud](https://github.com/Chuck3CZ/flashforge-creator3-local-cloud)
dashboard, or `scp` to the printer.

## Printing on left / right / dual-material

OrcaSlicer indexes extruders from 1. In this profile:

| Orca "Extruder" | Firmware tool | Head |
|---|---|---|
| 1 | T0 | **Right** head |
| 2 | T1 | **Left** head |

### Right head only (print_mode = 0)

- Click the object → **Objects panel → Extruder → 1**.
- Slice as usual. The converter sets the `.gx` header to single-head
  so the printer preheats only T0.

### Left head only (print_mode = 3)

- Object → **Extruder → 2**.
- Same deal; only T1 is preheated.

### Dual material / dual colour (print_mode = 4)

- Top bar **Add filament** → pick a second filament (e.g. black PLA +
  white PLA).
- Assign each object or modifier to filament 1 or 2.
- Prime tower stays on. Default flush volume is 140 mm³; bump to 200+
  for high-contrast transitions (black → white), drop to 80 for same
  material in two colours.

All three modes work out of the box because the firmware simply
replays whatever `T0`/`T1` sequence it receives.

## Mirror and replica (IDEX modes 1 and 2)

The Creator 3 firmware has **no M-code** to switch into mirror or
replica mode (unlike Snapmaker J1's `M605 S2/S3`). You have two paths.

### Path A — pick the mode on the printer (recommended)

1. In OrcaSlicer, slice as a **single-extruder** print on either head.
2. Convert to `.gx` as usual and upload it.
3. On the printer touchscreen, before you tap Print, select
   **Mirror Print** or **Replica Print** on the file menu.

This uses the firmware's own mode machinery (the stock FlashPrint 5
workflow) and does not depend on anything undocumented. It's the one
to try first.

### Path B — bake the mode into the gcode

If you upload via a cloud dashboard that can't reach the mode selector
on the touchscreen, add a second post-processing step **before** the
`.gx` converter runs:

**Settings → Others → Post-processing scripts** (one script per line,
order matters):

```
python3 "/path/to/orca-profile/scripts/idex_mirror.py" --mode mirror
python3 "/path/to/orca-profile/scripts/gx_converter.py"
```

Replica with 150 mm X offset:

```
python3 "/path/to/orca-profile/scripts/idex_mirror.py" --mode replica --offset 150
```

The script interleaves each `G1 X.. Y.. E..` with a twin `G1`
targeting the other head (mirrored across X=0, or offset in replica
mode). The firmware steps both carriages in sequence — slower than the
native touchscreen mode but geometrically correct.

Caveat: this path has not been dyno-tested on a real Creator 3 yet,
only on synthetic gcode. If you try it, open an issue and tell us how
it went so we can tune the T0↔T1 interleave spacing.

## How IDEX actually works on Creator 3 (RE findings)

Disassembling `creator3-arm` (UI software v1.4.8) and `control_run`
(motion controller v4.2.3) answered the main unknown: *how does the
printer decide between left-only / right-only / mirror / replica /
double?*

**The `print_mode` enum** (resolved from the jump table in
`ShowTFCard::getPrintMode()` at `0xf2bb0`):

| value | label on display | how it's generated |
|---|---|---|
| 0 | **Right**   | single-extruder gcode with T0 |
| 1 | **Mirror**  | gcode already contains mirrored motion for the second head |
| 2 | **Replica** | gcode duplicates motion with an X offset |
| 3 | **Left**    | single-extruder gcode with T1 |
| 4 | **Double**  | standard dual-material with toolchanges |

**Where it is NOT:** the motion controller binary has zero
mirror/replica/duplicate/idex strings; there is no `M605` or FlashForge
variant that switches modes. `BuildPrint::getPrintFileParam()` doesn't
read any `print_mode` field from the `.gx` either.

**Where it IS:** `/data/PowerOff` on the printer, written by
`FILESNAMESPACE::CPowerSavingModeFile::setPowerSavingMode(PrintContinueConfig)`.
That's a power-loss recovery state file, not a configuration source.
`PrintMode:` is set by UI selection on the touchscreen before a print
starts, which matches Path A above.

**What the firmware does enforce:** `M118 X<n> Y<n> Z<n> T<n>` at the
top of the gcode. The parser validates X/Y/Z against the 300/250/200
bounds and aborts with `"X axis size exceeding standard"` etc. if the
line is missing or oversized. That's why `machine_start_gcode` begins
with `M118 X150 Y125 Z200 T[initial_extruder]` — not decoration, a
hard requirement.

## What's inside this folder

```
orca-profile/
├── FlashForge.json                              # vendor index
├── machine/
│   ├── FlashForge_Creator3.json                 # printer settings
│   └── FlashForge_Creator3_model.json           # machine_model (vendor list)
├── filament/
│   ├── FlashForge_Generic_PLA_Creator3.json
│   ├── FlashForge_Generic_PETG_Creator3.json
│   ├── FlashForge_Generic_ABS_Creator3.json
│   └── FlashForge_Generic_PVA_Creator3.json
├── process/
│   ├── 0.10mm_Fine_Creator3.json
│   ├── 0.20mm_Standard_Creator3.json
│   └── 0.30mm_Draft_Creator3.json
├── scripts/
│   ├── gx_converter.py                          # .gcode → .gx
│   ├── idex_mirror.py                           # mirror/replica post-processor
│   ├── install_macos.sh
│   └── install_windows.ps1
└── README.md
```

## Troubleshooting

**OrcaSlicer doesn't show FlashForge in the vendor list.**
Did you restart it? Did you run the installer against the right
install root? On Windows pass `-OrcaRoot "D:\OrcaSlicer"` if you
installed to a non-default location.

**Printer rejects the file with "X axis size exceeding standard".**
The `M118 X.. Y.. Z..` line is missing or has larger values than
your bed. Check `machine_start_gcode` in the printer profile hasn't
been overridden.

**`.gx` prints at the wrong temperature or shows weird time estimate.**
The converter extracts time, filament, temps, layer height, shells
and speed from OrcaSlicer's gcode comments. If OrcaSlicer stops
emitting those comments (version change), open the gcode and look for
`;Filament used`, `;TIME:`, `;Layer height:` lines. If they're gone,
upgrade / downgrade OrcaSlicer or file an issue with the gcode
header.

**Dual-material print starts but T1 never fires.**
Prime tower must be enabled (`enable_prime_tower = 1` in the process
profile — default is on). Without it, OrcaSlicer may optimise T1 out
if it never prints anything significant before the model finishes.

**Mirror mode (Path B) crashes or prints garbage.**
Switch to Path A (touchscreen mode selection) and open an issue with
a short sample gcode. The interleave strategy in `idex_mirror.py` is
untested on real hardware.

**macOS says OrcaSlicer "is damaged and can't be opened" after install.**
`install_macos.sh` writes into `OrcaSlicer.app`, which invalidates
Apple's code signature, so Gatekeeper flags the bundle. Clear it with
`xattr -dr com.apple.quarantine /Applications/OrcaSlicer.app` (this
weakens Gatekeeper for that app — your call). Note bundle installs are
also wiped on every OrcaSlicer update; re-run the installer afterwards.

## Verified against FlashPrint 5

The printer / start / end G-code here was cross-checked against stock
**FlashPrint 5** output (`ffslicer 2.4.4`) for a calibration cube on
both heads. Key facts that shaped the profile:

- **Absolute extrusion** (`use_relative_e_distances = 0`, no `G92 E0`
  per layer). FlashForge's own slicer emits monotonically increasing
  `E` values — relative E + a layer-wise `G92 E0` is *wrong* here.
- **Tool numbers are reversed vs. intuition:** right nozzle = `T0`,
  left nozzle = `T1` (matches the `print_mode` table above and the
  reference gcode, where the left-head file heats/waits on `T1`).
- Start sequence uses FlashForge waits `M7 T0` (bed) and `M6 T<n>`
  (active nozzle); no `G28` — the firmware homes itself at print start.
- End sequence `G162 Z` (platform down) + `M652` + `M18`.

## License

MIT, same as the parent repo. FlashForge trademarks and firmware
belong to their respective owners.
