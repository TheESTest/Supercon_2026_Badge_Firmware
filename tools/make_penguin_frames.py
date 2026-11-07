"""Build the penguin animation for the Penguin Nametag app.

Poses the penguin logo at each keyframe inside a small stage next to your name
on the nametag, and writes:

    badge_files/data/graphics/penguin/fNN.png    one white/black/red palette
                                                 PNG per frame, stage-sized
    badge_files/data/graphics/penguin/anim.json  stage position, frame count,
                                                 and the box each frame changes
    tools/penguin_preview.gif                    the whole nametag, animated,
                                                 for checking on the PC (the
                                                 badge moves slower than this)

usage:
    python tools/make_penguin_frames.py [logo.svg | logo.png]

Change STAGE, SPRITE_H and KEYFRAMES below to change where and how it moves.
Needs Pillow and numpy, plus cairosvg or Inkscape for SVG input
(pip install pillow numpy cairosvg).
"""

import glob
import io
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NAMETAG = os.path.join(ROOT, "badge_files", "data", "graphics", "Hello_I_Am_Mod.png")
OUT_DIR = os.path.join(ROOT, "badge_files", "data", "graphics", "penguin")
PREVIEW = os.path.join(HERE, "penguin_preview.gif")
LOGO = (r"C:\Users\austi\Desktop\Elation Sports Technologies\EST Logo Designs"
        r"\Blue Penguin Vectorized Larger Eye 30 Aug 2020 Square Black.svg")

W, H = 960, 672
WHITE, BLACK, RED = 0, 1, 2  # same codes as lib/large_png.py
PALETTE = [255, 255, 255, 0, 0, 0, 255, 0, 0]  # index == code above

# The stage is the white strip between "Austin" (ends at x=455) and the QR
# code (starts at x=572), inside the white band (rows 221-557). Keep x and
# width multiples of 8, and y and height multiples of 4, so refresh windows
# line up with the panel's byte columns and 4-line rows.
STAGE = (456, 224, 112, 332)  # x, y, width, height
SPRITE_H = 120  # penguin height in pixels
SUPERSAMPLE = 4

# (center x, center y) inside the stage, tilt in degrees (+ leans right), and
# whether the penguin faces left, toward your name.
KEYFRAMES = [
    (53, 261, -8, False),  # waddle up the strip
    (59, 213, 8, False),
    (53, 166, -8, False),
    (59, 118, 8, False),
    (56, 71, 0, False),  # reach the top
    (56, 71, 0, True),  # turn to look at your name
    (54, 71, 6, True),
    (56, 135, 0, True),  # hop back down
    (56, 198, -6, True),
    (56, 261, 0, True),
    (56, 261, 0, False),  # turn back
    (56, 231, 0, False),  # little bounce
]

INKSCAPE = [
    shutil.which("inkscape"),
    r"C:\Program Files\Inkscape\bin\inkscape.com",
    r"C:\Program Files\Inkscape\bin\inkscape.exe",
]


def render_svg(path: str, height: int) -> Image.Image:
    try:
        import cairosvg

        return Image.open(io.BytesIO(cairosvg.svg2png(url=path, output_height=height)))
    except ImportError:
        pass
    ink = next((p for p in INKSCAPE if p and os.path.exists(p)), None)
    if ink is None:
        sys.exit("Install cairosvg (pip install cairosvg) or Inkscape, or pass a PNG instead.")
    fd, tmp = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        subprocess.run([ink, path, "--export-type=png", f"--export-filename={tmp}",
                        f"--export-height={height}"], check=True, capture_output=True)
        return Image.open(tmp).copy()
    finally:
        os.remove(tmp)


def load_logo(path: str, height: int) -> Image.Image:
    """The logo cropped to its ink and scaled to `height` pixels tall."""
    if path.lower().endswith(".svg"):
        im = render_svg(path, height * 2)
    else:
        im = Image.open(path)
    im = im.convert("RGBA")
    a = np.asarray(im)
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    ink = (a[..., 3] >= 128) & (lum < 128)
    ys, xs = np.nonzero(ink)
    im = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    width = round(im.width * height / im.height)
    return im.resize((width, height), Image.LANCZOS)


def pose(logo_hi: Image.Image, tilt: float, face_left: bool) -> np.ndarray:
    """Boolean ink mask of the logo, mirrored and tilted, at sprite size."""
    im = ImageOps.mirror(logo_hi) if face_left else logo_hi
    if tilt:
        im = im.rotate(-tilt, resample=Image.BICUBIC, expand=True)
    im = im.resize((max(1, round(im.width / SUPERSAMPLE)), max(1, round(im.height / SUPERSAMPLE))),
                   Image.LANCZOS)
    a = np.asarray(im).astype(np.int32)
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    return (a[..., 3] >= 128) & (lum < 128)


def to_kinds(rgb: np.ndarray) -> np.ndarray:
    """Same rule as _color_kind() in lib/large_png.py."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    kind = np.full(rgb.shape[:2], WHITE, np.uint8)
    kind[(r >= 128) & (g < 128) & (b < 128)] = RED
    kind[(r < 128) & (g < 128) & (b < 128)] = BLACK
    return kind


def palette_image(kind: np.ndarray) -> Image.Image:
    p = Image.frombytes("P", (kind.shape[1], kind.shape[0]), kind.astype(np.uint8).tobytes())
    p.putpalette(PALETTE)
    return p


def save_badge_png(kind: np.ndarray, path: str) -> int:
    palette_image(kind).save(path, format="PNG", optimize=True)
    with open(path, "rb") as f:
        data = f.read()
    _w, _h, depth, color_type, _c, _f, interlace = struct.unpack(">IIBBBBB", data[16:29])
    assert color_type == 3 and interlace == 0 and depth in (1, 2, 4, 8), "unexpected PNG format"
    back = to_kinds(np.asarray(Image.open(path).convert("RGB")).astype(np.int16))
    assert (back == kind).all(), "round trip mismatch"
    return len(data)


def align(x0: int, y0: int, x1: int, y1: int) -> list:
    """Grow a box out to 8 px columns and 4-line rows."""
    return [x0 // 8 * 8, y0 // 4 * 4, x1 // 8 * 8 + 7, y1 // 4 * 4 + 3]


def main() -> None:
    logo_path = sys.argv[1] if len(sys.argv) > 1 else LOGO
    sx, sy, sw, sh = STAGE
    assert sx % 8 == 0 and sw % 8 == 0 and sy % 4 == 0 and sh % 4 == 0, "misaligned STAGE"

    tag = to_kinds(np.asarray(Image.open(NAMETAG).convert("RGB")).astype(np.int16))
    stage_bg = tag[sy:sy + sh, sx:sx + sw].copy()
    if (stage_bg != WHITE).any():
        print("note: the stage overlaps the nametag artwork; the frames keep it as it is")

    logo_hi = load_logo(logo_path, SPRITE_H * SUPERSAMPLE)
    frames = []
    for i, (cx, cy, tilt, face_left) in enumerate(KEYFRAMES):
        ink = pose(logo_hi, tilt, face_left)
        h, w = ink.shape
        x0, y0 = round(cx - w / 2), round(cy - h / 2)
        if x0 < 0 or y0 < 0 or x0 + w > sw or y0 + h > sh:
            sys.exit(f"keyframe {i} ({w}x{h} at {x0},{y0}) doesn't fit the {sw}x{sh} stage")
        frame = stage_bg.copy()
        frame[y0:y0 + h, x0:x0 + w][ink] = BLACK
        frames.append(frame)

    # The box each frame changes, compared with the frame before it (looping)
    windows = []
    for i, frame in enumerate(frames):
        ys, xs = np.nonzero(frame != frames[i - 1])
        if len(xs) == 0:
            windows.append(None)
            continue
        windows.append(align(sx + int(xs.min()), sy + int(ys.min()),
                             sx + int(xs.max()), sy + int(ys.max())))

    os.makedirs(OUT_DIR, exist_ok=True)
    for old in glob.glob(os.path.join(OUT_DIR, "f*.png")):
        os.remove(old)
    sizes = [save_badge_png(f, os.path.join(OUT_DIR, f"f{i:02d}.png")) for i, f in enumerate(frames)]
    with open(os.path.join(OUT_DIR, "anim.json"), "w") as f:
        json.dump({"x": sx, "y": sy, "w": sw, "h": sh, "frames": len(frames), "windows": windows},
                  f, separators=(",", ":"))

    # Preview of the whole nametag
    pictures = []
    for frame in frames:
        full = tag.copy()
        full[sy:sy + sh, sx:sx + sw] = frame
        pictures.append(palette_image(full))
    pictures[0].save(PREVIEW, save_all=True, append_images=pictures[1:], duration=700, loop=0)

    print(f"wrote {len(frames)} frames to {OUT_DIR} ({sum(sizes)} bytes in all) and anim.json")
    for i, win in enumerate(windows):
        size = "no change" if win is None else f"{win[2] - win[0] + 1}x{win[3] - win[1] + 1} at {win[0]},{win[1]}"
        print(f"  f{i:02d}: {sizes[i]} bytes, refresh box {size}")
    print(f"preview: {PREVIEW}")


if __name__ == "__main__":
    main()
