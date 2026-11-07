"""Convert artwork into a PNG the Billboard Badge can draw.

The badge's decoder (lib/large_png.py) only reads non-interlaced palette or
grayscale PNGs, and the e-paper is 960x672 pixels in white, black and red.
This renders an SVG with Inkscape (or loads a PNG), maps every pixel to
white/black/red with the same rule as _color_kind() in lib/large_png.py, and
writes a small 2-bit palette PNG.

usage:
    python tools/make_epd_png.py <input.svg | input.png> <output.png>

example:
    python tools/make_epd_png.py badge_files/data/graphics/Hello_I_Am_Mod.svg badge_files/data/graphics/Hello_I_Am_Mod.png

Needs Pillow and numpy (pip install pillow numpy), plus Inkscape for SVG input.
"""

import os
import shutil
import struct
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

W, H = 960, 672
WHITE, BLACK, RED = 0, 1, 2  # same codes as lib/large_png.py
PALETTE = [255, 255, 255, 0, 0, 0, 255, 0, 0]  # index == code above
INKSCAPE = [
    shutil.which("inkscape"),
    r"C:\Program Files\Inkscape\bin\inkscape.com",
    r"C:\Program Files\Inkscape\bin\inkscape.exe",
]


def render_svg(svg_path: str, png_path: str) -> None:
    ink = next((p for p in INKSCAPE if p and os.path.exists(p)), None)
    if ink is None:
        sys.exit("Inkscape not found. Export a PNG from your editor and pass that instead.")
    subprocess.run(
        [ink, svg_path, "--export-type=png", f"--export-filename={png_path}",
         "--export-area-page", f"--export-width={W}", f"--export-height={H}",
         "--export-background=#ffffff", "--export-background-opacity=1"],
        check=True, capture_output=True,
    )


def convert(src: str, out: str) -> None:
    tmp = None
    if src.lower().endswith(".svg"):
        fd, tmp = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        render_svg(src, tmp)
        src = tmp
    try:
        im = Image.open(src).convert("RGBA")
    finally:
        if tmp:
            os.remove(tmp)
    if im.size != (W, H):
        print(f"note: resizing {im.size[0]}x{im.size[1]} to {W}x{H}; "
              "for sharp results export at 300 DPI (960x672) instead")
        im = im.resize((W, H), Image.LANCZOS)

    flat = Image.alpha_composite(Image.new("RGBA", im.size, (255, 255, 255, 255)), im)
    rgb = np.asarray(flat.convert("RGB")).astype(np.int16)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    kind = np.full((H, W), WHITE, np.uint8)
    kind[(r >= 128) & (g < 128) & (b < 128)] = RED
    kind[(r < 128) & (g < 128) & (b < 128)] = BLACK

    p = Image.frombytes("P", (W, H), kind.tobytes())
    p.putpalette(PALETTE)
    p.save(out, format="PNG", optimize=True)

    # Check the result the way the badge will read it.
    with open(out, "rb") as f:
        data = f.read()
    _w, _h, depth, color_type, _c, _f, interlace = struct.unpack(">IIBBBBB", data[16:29])
    assert color_type == 3 and interlace == 0 and depth in (1, 2, 4, 8), "unexpected PNG format"
    assert (np.asarray(Image.open(out)) == kind).all(), "round trip mismatch"
    share = [100.0 * (kind == k).sum() / kind.size for k in (WHITE, BLACK, RED)]
    print(f"wrote {out}: {len(data)} bytes, {W}x{H}, {depth}-bit palette "
          f"(white {share[0]:.1f}%, black {share[1]:.1f}%, red {share[2]:.1f}%)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    convert(sys.argv[1], sys.argv[2])
