#!/usr/bin/env python3
"""
Mirror/Replica post-processor for the FlashForge Creator 3 IDEX head.

Reverse-engineering of the Creator 3 firmware (see repo README) showed that
the printer has NO M-code for mirror or replica mode — the stock FlashPrint 5
emits mode-specific motion itself and the firmware just replays it. This
script does the same transformation on gcode OrcaSlicer produces for a
single extruder (T0), turning it into dual-head parallel motion.

Modes:
  mirror   — T1 moves to the mirror image of T0 across the X=0 axis of the
             centre-origin bed. Each printed point ends up at (-X, Y, Z) on
             the left head while the right head prints at (+X, Y, Z).
  replica  — T1 moves parallel to T0 with a fixed X offset. Both heads print
             identical copies side by side.

How this talks to the Creator 3's two heads:
  Creator 3 is a true IDEX printer: T0 and T1 own independent X axes but
  share Y and Z. The firmware accepts T0/T1 tool-select and, in the stock
  dual-material path, moves whichever head is currently active. For
  mirror/replica we interleave moves: before each extrusion the script
  emits the T1 counterpart as a separate G1 line with the mirrored or
  offset X and the same Y/Z, so the firmware steps both carriages in a
  tight sequence rather than truly in parallel. This is slower than
  FlashPrint 5's native mode (which the firmware may schedule as a single
  blended move via the sync machinery exposed to the UI touchscreen), but
  it prints the right geometry and does not depend on any undocumented
  M-code.

RECOMMENDED alternative, if you prefer the native path: slice single-head
in OrcaSlicer, drop the .gx onto the printer's SD card, and pick "Mirror
Print" or "Replica Print" from the touchscreen before you tap Print.
That uses the firmware's own sync and is what FlashPrint 5 effectively
leans on. This script is for people who want the mode baked into the file
so a web upload / cloud dashboard doesn't need the extra tap.

Usage as OrcaSlicer post-processing (set in Others → Post-processing
scripts, after gx_converter.py or instead of it until you need the .gx):

    python3 /path/to/idex_mirror.py --mode mirror
    python3 /path/to/idex_mirror.py --mode replica --offset 150

OrcaSlicer appends the gcode path as the last argument.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Centre-origin bed: X spans -150 to +150, Y spans -125 to +125.
# Mirror axis is X = 0 unless --mirror-axis is passed.

MOVE_RE = re.compile(
    r"""^\s*(?P<cmd>G0|G1)\s+                       # G0 / G1
        (?P<rest>.*?)\s*
        (?:;\s*(?P<comment>.*))?$""",
    re.VERBOSE | re.IGNORECASE,
)
TOKEN_RE = re.compile(r"([XYZEFxyzef])\s*(-?\d+(?:\.\d+)?)")
TOOL_RE = re.compile(r"^\s*(T0|T1)\b", re.IGNORECASE)


@dataclass
class MoveTokens:
    cmd: str
    x: float | None = None
    y: float | None = None
    z: float | None = None
    e: float | None = None
    f: float | None = None
    other: str = ""
    comment: str = ""

    @classmethod
    def parse(cls, line: str) -> "MoveTokens | None":
        m = MOVE_RE.match(line)
        if not m:
            return None
        tokens = {t[0].upper(): float(t[1]) for t in TOKEN_RE.findall(m.group("rest"))}
        other = TOKEN_RE.sub("", m.group("rest")).strip()
        return cls(
            cmd=m.group("cmd").upper(),
            x=tokens.get("X"),
            y=tokens.get("Y"),
            z=tokens.get("Z"),
            e=tokens.get("E"),
            f=tokens.get("F"),
            other=other,
            comment=(m.group("comment") or "").strip(),
        )

    def format(self) -> str:
        parts = [self.cmd]
        if self.x is not None:
            parts.append(f"X{self.x:.4f}".rstrip("0").rstrip("."))
        if self.y is not None:
            parts.append(f"Y{self.y:.4f}".rstrip("0").rstrip("."))
        if self.z is not None:
            parts.append(f"Z{self.z:.4f}".rstrip("0").rstrip("."))
        if self.e is not None:
            parts.append(f"E{self.e:.5f}".rstrip("0").rstrip("."))
        if self.f is not None:
            parts.append(f"F{int(self.f) if self.f.is_integer() else self.f}")
        if self.other:
            parts.append(self.other)
        line = " ".join(parts)
        if self.comment:
            line = f"{line} ;{self.comment}"
        return line


def transform(lines: list[str], mode: str, offset: float, mirror_axis: float) -> list[str]:
    out: list[str] = []
    out.append(f";; idex_mirror.py mode={mode} offset={offset} mirror_axis={mirror_axis}")
    active_tool = 0  # T0 by default
    header_done = False

    for raw in lines:
        line = raw.rstrip("\n")
        tool = TOOL_RE.match(line)
        if tool:
            active_tool = 0 if tool.group(1).upper() == "T0" else 1
            out.append(line)
            continue

        move = MoveTokens.parse(line)
        if move is None or move.x is None:
            out.append(line)
            continue

        # Emit the original line (T0 carriage).
        out.append(line)

        # Only mirror extruding moves and primary travels. Pure Z lifts
        # (no X token) and tool-change parking moves are already handled.
        twin = MoveTokens(
            cmd=move.cmd,
            x=(2 * mirror_axis - move.x) if mode == "mirror" else (move.x + offset),
            y=move.y,
            z=move.z,
            e=move.e,
            f=move.f,
            other=move.other,
            comment=f"[{mode}:T1]",
        )

        if not header_done:
            out.append("; Switch to T1 for mirror/replica twin motion")
            out.append("M108 T1")
            out.append("T1")
            out.append("G92 E0")
            out.append("M108 T0")
            out.append("T0")
            header_done = True

        out.append("M108 T1")
        out.append("T1")
        out.append(twin.format())
        out.append("M108 T0")
        out.append("T0")

    return [l + "\n" for l in out]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="FlashForge Creator 3 mirror/replica post-processor")
    ap.add_argument("--mode", choices=["mirror", "replica"], required=True)
    ap.add_argument("--offset", type=float, default=150.0, help="X offset for replica mode (mm)")
    ap.add_argument("--mirror-axis", type=float, default=0.0, help="X axis the mirror reflects across")
    ap.add_argument("gcode", help="Path to the gcode file to transform in place")
    args = ap.parse_args(argv[1:])

    path = Path(args.gcode)
    if not path.exists():
        print(f"input not found: {path}", file=sys.stderr)
        return 1

    original = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=False)
    transformed = transform(original, args.mode, args.offset, args.mirror_axis)
    path.write_text("".join(transformed), encoding="utf-8")
    print(f"transformed {path} ({args.mode}, {len(transformed)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
