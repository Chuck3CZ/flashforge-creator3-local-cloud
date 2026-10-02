#!/usr/bin/env python3
"""
OrcaSlicer / PrusaSlicer post-processing: converts generated .gcode
into FlashForge .gx (Creator 3 / Dreamer / Adventurer-family) binary format.

Usage as OrcaSlicer post-processing script:
    python3 /path/to/gx_converter.py

OrcaSlicer passes the final .gcode path as argv[1]. The script writes a .gx
file next to it (same basename) and leaves the original .gcode in place for
inspection. If OrcaSlicer is configured to upload only the output file, point
it at the generated .gx.

Header layout (58 bytes, little-endian), as reverse-engineered from stock
FlashPrint 5 output and documented in community tools (Spiritdude Print3D-
FlashForge, slic3r-flashforge-postprocess). Values the printer actually
reads from the header are print_time, filament usage, temperatures, speed,
layer height and extruder-usage flags; the thumbnail is BMP 80x60 24-bit.

Metadata is pulled from the comment block OrcaSlicer / PrusaSlicer emits
at the top/bottom of the file (;TIME:, ;Filament used:, ;Layer height:,
; nozzle_temperature_initial_layer, ; bed_temperature_initial_layer_single
etc.). Missing values fall back to safe defaults.
"""

from __future__ import annotations

import os
import re
import struct
import sys
from pathlib import Path

MAGIC = b"xgcode 1.0\n\0"  # 12 bytes
HEADER_LEN = 58
BMP_OFFSET = 58
GCODE_OFFSET = 14512  # 58 (header) + 14454 (BMP file size)

# BMP 80x60 24bpp, solid dark grey. 80*60*3 = 14400 bytes pixel data,
# padded per 4-byte row (80*3 = 240 is already 4-aligned), + 54-byte BMP
# header = 14454 bytes total.
BMP_WIDTH = 80
BMP_HEIGHT = 60
BMP_PIXEL_BYTES = BMP_WIDTH * BMP_HEIGHT * 3
BMP_FILE_SIZE = 54 + BMP_PIXEL_BYTES


def build_placeholder_bmp(rgb: tuple[int, int, int] = (40, 40, 48)) -> bytes:
    """Minimal 80x60 24-bit BMP, bottom-up, single solid color."""
    b, g, r = rgb[2], rgb[1], rgb[0]
    row = bytes([b, g, r]) * BMP_WIDTH
    pixels = row * BMP_HEIGHT

    bmp_header = struct.pack(
        "<2sIHHI",
        b"BM",
        BMP_FILE_SIZE,
        0,
        0,
        54,
    )
    dib_header = struct.pack(
        "<IiiHHIIiiII",
        40,
        BMP_WIDTH,
        BMP_HEIGHT,
        1,
        24,
        0,
        BMP_PIXEL_BYTES,
        2835,
        2835,
        0,
        0,
    )
    return bmp_header + dib_header + pixels


_METADATA_PATTERNS: dict[str, re.Pattern[str]] = {
    "print_time": re.compile(r";\s*(?:estimated printing time.*?=|TIME:)\s*([^\n]+)", re.I),
    "filament_used_mm": re.compile(r";\s*(?:Filament used|filament used \[mm\])\s*[:=]\s*([^\n]+)", re.I),
    "layer_height": re.compile(r";\s*(?:Layer height|layer_height)\s*[:=]\s*([\d.]+)", re.I),
    "bed_temp": re.compile(r";\s*bed_temperature_initial_layer_single\s*=\s*(\d+)", re.I),
    "nozzle_temp_0": re.compile(r";\s*nozzle_temperature_initial_layer\s*=\s*(\d+)(?:,|\s|$)", re.I),
    "nozzle_temp_1": re.compile(r";\s*nozzle_temperature_initial_layer\s*=\s*\d+\s*,\s*(\d+)", re.I),
    "print_speed": re.compile(r";\s*outer_wall_speed\s*=\s*(\d+)", re.I),
    "shells": re.compile(r";\s*wall_loops\s*=\s*(\d+)", re.I),
}


def _parse_time_to_seconds(text: str) -> int:
    """Accept '1h 23m 45s', '83m', '5025', 'PT1H23M45S' and return seconds."""
    text = text.strip()
    if text.isdigit():
        return int(text)

    total = 0
    for value, unit in re.findall(r"(\d+)\s*([dhms])", text, flags=re.I):
        n = int(value)
        unit = unit.lower()
        if unit == "d":
            total += n * 86400
        elif unit == "h":
            total += n * 3600
        elif unit == "m":
            total += n * 60
        elif unit == "s":
            total += n
    return total or 0


def _parse_filament_mm(text: str) -> tuple[int, int]:
    """Pull up to two filament-length numbers (mm) from a header comment."""
    nums = re.findall(r"[\d.]+", text)
    vals = [int(round(float(n))) for n in nums[:2]]
    while len(vals) < 2:
        vals.append(0)
    return vals[0], vals[1]


def extract_metadata(gcode_text: str) -> dict[str, int]:
    md = {
        "print_time": 0,
        "filament_mm_0": 0,
        "filament_mm_1": 0,
        "layer_height_um": 200,
        "shells": 2,
        "print_speed": 60,
        "bed_temp": 60,
        "nozzle_temp_0": 210,
        "nozzle_temp_1": 210,
    }

    m = _METADATA_PATTERNS["print_time"].search(gcode_text)
    if m:
        md["print_time"] = _parse_time_to_seconds(m.group(1))

    m = _METADATA_PATTERNS["filament_used_mm"].search(gcode_text)
    if m:
        md["filament_mm_0"], md["filament_mm_1"] = _parse_filament_mm(m.group(1))

    m = _METADATA_PATTERNS["layer_height"].search(gcode_text)
    if m:
        md["layer_height_um"] = int(round(float(m.group(1)) * 1000))

    m = _METADATA_PATTERNS["shells"].search(gcode_text)
    if m:
        md["shells"] = int(m.group(1))

    m = _METADATA_PATTERNS["print_speed"].search(gcode_text)
    if m:
        md["print_speed"] = int(m.group(1))

    m = _METADATA_PATTERNS["bed_temp"].search(gcode_text)
    if m:
        md["bed_temp"] = int(m.group(1))

    m = _METADATA_PATTERNS["nozzle_temp_0"].search(gcode_text)
    if m:
        md["nozzle_temp_0"] = int(m.group(1))

    m = _METADATA_PATTERNS["nozzle_temp_1"].search(gcode_text)
    if m:
        md["nozzle_temp_1"] = int(m.group(1))

    return md


def detect_dual(gcode_text: str, md: dict[str, int]) -> bool:
    """A job is dual-material if the gcode toggles between T0 and T1, or
    if OrcaSlicer reported non-zero filament for both extruders."""
    if md.get("filament_mm_1", 0) > 0 and md.get("filament_mm_0", 0) > 0:
        return True
    uses_t0 = re.search(r"^\s*T0\b", gcode_text, flags=re.M) is not None
    uses_t1 = re.search(r"^\s*T1\b", gcode_text, flags=re.M) is not None
    return uses_t0 and uses_t1


def build_header(md: dict[str, int], is_dual: bool) -> bytes:
    """Pack the 58-byte .gx header.

    Layout verified against the HellEvro/FF_Gcode_to_GX reference, which
    the Creator 3 Pro owner validated against FlashPrint 5 output:

        bytes  0..11 : magic "xgcode 1.0\\n\\0"
        bytes 12..15 : zero / unknown
        bytes 16..19 : BMP offset (= 58)
        bytes 20..23 : gcode offset (= 14512)
        bytes 24..27 : gcode offset (duplicate)
        bytes 28..31 : print time, seconds (int32, min 1)
        bytes 32..35 : filament used, right extruder, mm (int32)
        bytes 36..39 : filament used, left extruder, mm (int32)
        bytes 40..41 : multi-extruder type (int16; 0=single, 1=dual)
        bytes 42..43 : layer height, micrometres (int16)
        bytes 44..45 : reserved (int16, 0)
        bytes 46..47 : perimeter shells (int16)
        bytes 48..49 : print speed (int16)
        bytes 50..51 : bed temp (int16)
        bytes 52..53 : nozzle temp, right (int16)
        bytes 54..55 : nozzle temp, left (int16)
        bytes 56..57 : reserved (int16, always 1 per reference)
    """
    multi = 1 if is_dual else 0
    hdr = bytearray(HEADER_LEN)
    hdr[0:12] = MAGIC
    struct.pack_into("<i", hdr, 12, 0)
    struct.pack_into("<i", hdr, 16, BMP_OFFSET)
    struct.pack_into("<i", hdr, 20, GCODE_OFFSET)
    struct.pack_into("<i", hdr, 24, GCODE_OFFSET)
    struct.pack_into("<i", hdr, 28, max(md["print_time"], 1))
    struct.pack_into("<i", hdr, 32, md["filament_mm_0"])
    struct.pack_into("<i", hdr, 36, md["filament_mm_1"] if is_dual else 0)
    struct.pack_into("<h", hdr, 40, multi)
    struct.pack_into("<h", hdr, 42, md["layer_height_um"])
    struct.pack_into("<h", hdr, 44, 0)
    struct.pack_into("<h", hdr, 46, md["shells"])
    struct.pack_into("<h", hdr, 48, md["print_speed"])
    struct.pack_into("<h", hdr, 50, md["bed_temp"])
    struct.pack_into("<h", hdr, 52, md["nozzle_temp_0"])
    struct.pack_into("<h", hdr, 54, md["nozzle_temp_1"] if is_dual else 0)
    struct.pack_into("<h", hdr, 56, 1)
    return bytes(hdr)


# Commands OrcaSlicer emits that stock FlashPrint 5 output never contains.
_DROP_CMDS = re.compile(r"^\s*(M73|M201|M203|M204|M205|G21|M82)\b")
_E_WORD = re.compile(r"(?<=\s)E(-?\d*\.?\d+)")
_G92_E = re.compile(r"^\s*G92\b.*?\bE(-?\d*\.?\d+)")


def normalize_gcode(text: str) -> str:
    """Make OrcaSlicer output look like FlashPrint 5 output.

    - drops M73/M201/M203/M204/M205/G21/M82,
    - folds every `G92 E<v>` into a running offset so E stays one
      monotonically increasing absolute axis (FlashPrint never resets E;
      OrcaSlicer resets it after every wipe),
    - bare `T0`/`T1` -> `M108 T0`/`M108 T1`, `M106 S0` -> `M107`.

    Relative-E files (M83) are returned unchanged apart from the drops.
    """
    relative = re.search(r"(?m)^\s*M83\b", text) is not None
    offset = 0.0      # added to every E word
    last_e = 0.0      # last logical (pre-offset) E position
    out = []
    for line in text.splitlines():
        code = line.split(";", 1)[0]
        if _DROP_CMDS.match(code):
            continue
        if not relative:
            m = _G92_E.match(code)
            if m:
                offset += last_e - float(m.group(1))
                last_e = float(m.group(1))
                continue
            if re.match(r"^\s*G[0-3]\b", code) and _E_WORD.search(code):
                def shift(mm: re.Match) -> str:
                    global_e = float(mm.group(1)) + offset
                    return "E%.5f" % global_e
                last_e = float(_E_WORD.search(code).group(1))
                line = _E_WORD.sub(shift, code, count=1).rstrip() + (
                    " ;" + line.split(";", 1)[1] if ";" in line else "")
        t = re.match(r"^\s*T([01])\s*$", code)
        if t:
            line = "M108 T" + t.group(1)
        elif re.match(r"^\s*M106\s+S0(\.0*)?\s*$", code):
            line = "M107"
        out.append(line)
    return "\n".join(out) + "\n"


def convert(gcode_path: Path, gx_path: Path | None = None, keep_gcode: bool = True) -> Path:
    gcode_bytes = gcode_path.read_bytes()
    try:
        gcode_text = gcode_bytes.decode("utf-8", errors="replace")
    except UnicodeDecodeError:
        gcode_text = gcode_bytes.decode("latin-1", errors="replace")

    if os.environ.get("GX_NORMALIZE", "1") != "0":
        gcode_text = normalize_gcode(gcode_text)
        gcode_bytes = gcode_text.encode("utf-8")

    md = extract_metadata(gcode_text)
    is_dual = detect_dual(gcode_text, md)
    thumbnail = build_placeholder_bmp()
    header = build_header(md, is_dual)

    out = gx_path or gcode_path.with_suffix(".gx")
    with out.open("wb") as f:
        f.write(header)
        f.write(thumbnail)
        f.write(gcode_bytes)

    if not keep_gcode and out != gcode_path:
        gcode_path.unlink(missing_ok=True)

    return out


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: gx_converter.py <input.gcode> [output.gx]", file=sys.stderr)
        return 2

    gcode_path = Path(argv[1])
    if not gcode_path.exists():
        print(f"input not found: {gcode_path}", file=sys.stderr)
        return 1

    gx_path = Path(argv[2]) if len(argv) > 2 else None
    keep = os.environ.get("GX_KEEP_GCODE", "1") != "0"
    out = convert(gcode_path, gx_path, keep_gcode=keep)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
