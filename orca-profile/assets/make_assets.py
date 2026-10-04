#!/usr/bin/env python3
"""Generate the OrcaSlicer artwork for the FlashForge Creator 3 profile.

Outputs (next to this script):
  FlashForge Creator 3_cover.png               printer picture in "Add printer"
  flashforge_creator3_buildplate_model.stl     3D bed shown under the plate
  flashforge_creator3_buildplate_texture.png   bed texture (grid + labels)

All artwork is original (drawn here), not FlashForge product photos.
Rasterising uses macOS Quick Look (`qlmanage`, WebKit – full SVG incl.
gradients and text) and ImageMagick (`magick`) for resizing. OrcaSlicer's
own SVG loader (nanosvg) cannot draw <text>, hence PNG textures.
"""
import math
import os
import struct
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
W, D = 300.0, 250.0            # printable area, centred on 0,0


# ---------------------------------------------------------------- bed model
def rounded_rect(x0, y0, x1, y1, r, seg=6):
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0),
                       (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def plate_outline():
    """Plate a bit larger than the print area with a front grip tab."""
    m = 6.0
    body = rounded_rect(-W / 2 - m, -D / 2 - m, W / 2 + m, D / 2 + m, 8)
    # insert a front tab (centre front, y < -D/2-m) into the bottom edge
    tab_w, tab_d = 90.0, 10.0
    y0 = -D / 2 - m
    out = []
    for p in body:
        out.append(p)
    # body starts at bottom-right corner going counter-clockwise; the bottom
    # edge is between the last point and the first one. Append tab there.
    out += [(-tab_w / 2, y0), (-tab_w / 2 + 6, y0 - tab_d),
            (tab_w / 2 - 6, y0 - tab_d), (tab_w / 2, y0)]
    return out


def triangulate_fan(poly):
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    return [((cx, cy), poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly))]


def write_stl(path, outline, z0=-3.0, z1=0.0):
    tris = []
    for c, a, b in triangulate_fan(outline):
        tris.append(((c[0], c[1], z1), (a[0], a[1], z1), (b[0], b[1], z1)))   # top
        tris.append(((c[0], c[1], z0), (b[0], b[1], z0), (a[0], a[1], z0)))   # bottom
    n = len(outline)
    for i in range(n):
        a, b = outline[i], outline[(i + 1) % n]
        tris.append(((a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1)))
        tris.append(((a[0], a[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)))
    with open(path, "wb") as f:
        f.write(b"FlashForge Creator 3 build plate".ljust(80, b"\0"))
        f.write(struct.pack("<I", len(tris)))
        for t in tris:
            (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
            ux, uy, uz = bx - ax, by - ay, bz - az
            vx, vy, vz = cx - ax, cy - ay, cz - az
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            f.write(struct.pack("<3f", nx / ln, ny / ln, nz / ln))
            for v in t:
                f.write(struct.pack("<3f", *v))
            f.write(b"\0\0")


# ---------------------------------------------------------------- texture
def texture_svg():
    s = 10  # 10 px per mm -> 3000 x 2500
    w, h = int(W * s), int(D * s)
    g = []
    for i in range(0, int(W) + 1, 10):
        x = i * s
        major = i % 50 == 0
        g.append('<line x1="%d" y1="0" x2="%d" y2="%d" stroke="#%s" stroke-width="%d"/>'
                 % (x, x, h, "a9bccf" if major else "d6e0ea", 5 if major else 2))
    for j in range(0, int(D) + 1, 10):
        y = j * s
        major = j % 50 == 0
        g.append('<line x1="0" y1="%d" x2="%d" y2="%d" stroke="#%s" stroke-width="%d"/>'
                 % (y, w, y, "a9bccf" if major else "d6e0ea", 5 if major else 2))
    cx, cy = w // 2, h // 2
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">
  <rect width="{w}" height="{h}" fill="#e8eef4"/>
  {''.join(g)}
  <line x1="{cx-80}" y1="{cy}" x2="{cx+80}" y2="{cy}" stroke="#5d7a96" stroke-width="6"/>
  <line x1="{cx}" y1="{cy-80}" x2="{cx}" y2="{cy+80}" stroke="#5d7a96" stroke-width="6"/>
  <text x="{cx}" y="{h-150}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif"
        font-size="150" font-weight="700" fill="#5d7a96" opacity="0.55">FLASHFORGE CREATOR 3</text>
  <text x="{cx}" y="{h-40}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif"
        font-size="80" fill="#5d7a96" opacity="0.55">IDEX · 300 × 250 × 200 mm</text>
  <text x="60" y="140" font-family="Helvetica, Arial, sans-serif" font-size="90" font-weight="700"
        fill="#e07b2a" opacity="0.7">◀ L · Extruder 1</text>
  <text x="{w-60}" y="140" text-anchor="end" font-family="Helvetica, Arial, sans-serif"
        font-size="90" font-weight="700" fill="#2e9e4f" opacity="0.7">Extruder 2 · R ▶</text>
</svg>
'''


# ---------------------------------------------------------------- cover art
COVER_SVG = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240" width="480" height="480">
  <defs>
    <linearGradient id="body" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#4a4f57"/><stop offset="1" stop-color="#25282d"/>
    </linearGradient>
    <linearGradient id="glass" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#3b4a5c" stop-opacity="0.95"/>
      <stop offset="1" stop-color="#1a2230" stop-opacity="0.95"/>
    </linearGradient>
    <linearGradient id="plate" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#4f8fe0"/><stop offset="1" stop-color="#2d63b0"/>
    </linearGradient>
  </defs>
  <ellipse cx="120" cy="222" rx="92" ry="8" fill="#000" opacity="0.18"/>
  <!-- cabinet -->
  <rect x="30" y="18" width="180" height="200" rx="10" fill="url(#body)"/>
  <rect x="30" y="18" width="180" height="200" rx="10" fill="none" stroke="#6b717a" stroke-width="1.5"/>
  <!-- top panel with touchscreen -->
  <rect x="38" y="26" width="164" height="36" rx="5" fill="#1d2025"/>
  <rect x="96" y="31" width="48" height="26" rx="2" fill="#0e1a2b" stroke="#3d6fb3" stroke-width="1"/>
  <rect x="100" y="35" width="16" height="11" fill="#3a3f48"/>
  <rect x="120" y="36" width="20" height="3" fill="#8fb6e8"/>
  <rect x="120" y="42" width="14" height="3" fill="#8fb6e8" opacity="0.7"/>
  <rect x="100" y="49" width="40" height="5" rx="1" fill="#2f6fd6"/>
  <text x="46" y="48" font-family="Helvetica, Arial, sans-serif" font-size="8" font-weight="700" fill="#cfd5dd">FLASHFORGE</text>
  <!-- door glass -->
  <rect x="40" y="68" width="160" height="140" rx="5" fill="url(#glass)" stroke="#11151b" stroke-width="2"/>
  <!-- gantry + two IDEX heads -->
  <rect x="46" y="88" width="148" height="7" rx="2" fill="#8c939d"/>
  <rect x="62" y="80" width="26" height="30" rx="3" fill="#d9dde3"/>
  <rect x="66" y="84" width="18" height="8" rx="1" fill="#e07b2a"/>
  <polygon points="72,110 78,110 75,117" fill="#c9a24a"/>
  <rect x="152" y="80" width="26" height="30" rx="3" fill="#d9dde3"/>
  <rect x="156" y="84" width="18" height="8" rx="1" fill="#2e9e4f"/>
  <polygon points="162,110 168,110 165,117" fill="#c9a24a"/>
  <!-- build plate in perspective -->
  <polygon points="58,168 182,168 196,188 44,188" fill="url(#plate)"/>
  <polygon points="44,188 196,188 196,192 44,192" fill="#1f4c8c"/>
  <rect x="96" y="132" width="20" height="36" fill="#7ac36a" opacity="0.95"/>
  <rect x="124" y="140" width="20" height="28" fill="#f2f2f2" opacity="0.95"/>
  <!-- glass highlight + handle -->
  <polygon points="48,72 92,72 58,204 44,204" fill="#fff" opacity="0.06"/>
  <rect x="192" y="120" width="4" height="40" rx="2" fill="#9aa1ab"/>
</svg>
'''


def rasterize(svg_text, name, size, out_path, flatten=None):
    """SVG -> PNG via Quick Look, then exact resize with ImageMagick."""
    import tempfile
    tmp = tempfile.mkdtemp()
    svg = os.path.join(tmp, name + ".svg")
    with open(svg, "w") as f:
        f.write(svg_text)
    subprocess.check_call(["qlmanage", "-t", "-s", str(max(size) * 2), "-o", tmp, svg],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    side = max(size) * 2
    crop_w, crop_h = side * size[0] // max(size), side * size[1] // max(size)
    # Quick Look letterboxes non-square SVGs into a square: crop back
    cmd = ["magick", os.path.join(tmp, name + ".svg.png"), "-gravity", "center",
           "-crop", "%dx%d+0+0" % (crop_w, crop_h), "+repage"]
    if flatten:
        cmd += ["-background", flatten, "-flatten"]
    else:  # Quick Look renders on white: make the outer background transparent
        cmd += ["-alpha", "set", "-fuzz", "4%", "-fill", "none",
                "-draw", "color 0,0 floodfill"]
    cmd += ["-resize", "%dx%d!" % size, "PNG32:" + out_path]
    subprocess.check_call(cmd)


def main():
    write_stl(os.path.join(HERE, "flashforge_creator3_buildplate_model.stl"), plate_outline())
    rasterize(texture_svg(), "texture", (2400, 2000),
              os.path.join(HERE, "flashforge_creator3_buildplate_texture.png"), flatten="#e8eef4")
    rasterize(COVER_SVG, "cover", (240, 240),
              os.path.join(HERE, "FlashForge Creator 3_cover.png"))
    print("assets written to", HERE)


if __name__ == "__main__":
    main()
