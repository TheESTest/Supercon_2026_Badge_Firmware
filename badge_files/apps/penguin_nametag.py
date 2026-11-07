"""Penguin Nametag: the Hello I Am Mod nametag, with the EST penguin waddling
next to your name.

The first picture is a normal refresh. After that the penguin moves with fast,
partial refreshes from lib/epd_fast.py. In "delta" mode (the default) each move
is one pass of a change-only table over the strip between "Austin" and the QR
code: only pixels that change colour get any voltage, so the rest of the
screen, red included, is never touched. Every CLEAN_EVERY moves a normal
refresh restores the film; RUN_MINUTES can make the penguin rest.

The frames come from tools/make_penguin_frames.py. They are decoded once when
the app opens, so a move only copies a few kilobytes into the framebuffer.

On the badge:
    User A          pause / resume (or start again after a rest)
    User B          normal refresh now (clears any ghosting)
    Menu + / -      back to the app menu
"""

import asyncio as aio
import gc
import json
import sys
import time

import micropython

from apps.base_app import BaseApp
from lib.button import UserA, UserB
from lib.epd import display
from lib.epd_fast import delta_lut, fast
from lib.large_png import show_png
from lib.led_bar import leds

_NAMETAG = "/data/graphics/Hello_I_Am_Mod.png"
_FRAMES = "/data/graphics/penguin"

FAST_MODE = "delta"
""""delta": change-only table, one pass per move. "hold": the official table, FAST_PULLS passes."""
DELTA_FRAMES = 20
"""Frames of drive per move in delta mode, about 15 ms each over the strip. 20 is
the shortest table; raise it (26, 32, ...) if the penguin comes out grey or leaves a trail."""
WHITE_PUSH = 6
"""Delta mode: frames (of DELTA_FRAMES per pass) of push towards white for pixels
that stay white, so the background stays clean and old poses fade out."""
RED_PUSH = 20
"""Delta mode: frames of the reduced positive rail (VDHR, which holds red up
without bringing black up) for the red pixels on the strip's lines, your name and
the QR code, so they are held red on every pass instead of sitting at 0 V and
fading. Pixels that stay black are sent as white-to-black, so they get a full
drive to black every pass and do not share this table."""
WINDOW_WRITES = True
"""Delta mode: the controller scans only the strip's lines (224-555), never the
red bands, and only those lines (full width, 80 KB) are sent on each move."""
FAST_PULLS = 2
"""Refresh passes per move in hold mode. 3 is what the official driver uses."""
REFRESH_ROWS = "frame"
"""Hold mode only: the controller's refresh window. "frame" scans only the lines
that change in each move, "strip" the penguin's whole strip, None the whole panel.
Delta mode always scans the whole strip, so every move gets the same drive."""
PAUSE_MS = 0
"""Rest between moves, on top of the fast refresh itself."""
CLEAN_EVERY = 1000
"""Normal refresh (about 40 s) after this many moves. 0 turns it off."""
RUN_MINUTES = 0
"""Rest after this long, with a normal refresh. 0 animates forever."""


@micropython.viper
def _pack_stage(packed, fb, c0: int, nb: int, y0: int, h: int):
    """Copy the stage out of a full framebuffer into a packed nb x h buffer."""
    d = ptr8(packed)
    s = ptr8(fb)
    r = 0
    while r < h:
        f = (y0 + r) * 120 + c0
        p = r * nb
        i = 0
        while i < nb:
            d[p + i] = s[f + i]
            i += 1
        r += 1


@micropython.viper
def _unpack_stage(fb, packed, c0: int, nb: int, y0: int, h: int):
    """Copy a packed nb x h stage image into a full framebuffer."""
    d = ptr8(fb)
    s = ptr8(packed)
    r = 0
    while r < h:
        f = (y0 + r) * 120 + c0
        p = r * nb
        i = 0
        while i < nb:
            d[f + i] = s[p + i]
            i += 1
        r += 1


class PenguinNametagApp(BaseApp):
    def __init__(self, name: str | None = None) -> None:
        super().__init__(name or "Penguin Nametag")
        self.sleep_ms = 2
        self.anim = None
        self.frames = None  # packed stage images, one per frame
        self.windows = None  # box that changes when moving to frame i
        self.old = None  # full-screen copy of what the panel shows, for delta mode
        self.lut = None  # the delta table
        self.frame = 0
        self.fast_count = 0
        self.paused = False
        self.resting = False
        self.started_ms = 0
        self.next_ms = 0
        self.waiting_normal = False

    async def arun(self):
        try:
            await self._step()
        except Exception as ex:
            print(f"{self.name} hit an exception {ex}")
            sys.print_exception(ex)
            self.resting = True
            await fast.close()
        await aio.sleep_ms(self.sleep_ms)

    def _load(self):
        """Decode every frame once and work out what changes between them."""
        with open(_FRAMES + "/anim.json") as f:
            a = json.load(f)
        x, y, w, h = a["x"], a["y"], a["w"], a["h"]
        c0 = x >> 3
        nb = ((x + w - 1) >> 3) - c0 + 1
        a["c0"], a["nb"] = c0, nb
        black = bytearray(len(display._framebuffer_black))
        red = bytearray(len(black))
        frames = []
        for i in range(a["frames"]):
            show_png(f"{_FRAMES}/f{i:02d}.png", black, red, y, x)
            packed = bytearray(nb * h)
            _pack_stage(packed, black, c0, nb, y, h)
            frames.append(packed)
        del black, red
        windows = []
        n = len(frames)
        for i in range(n):
            prev, cur = frames[i - 1], frames[i]
            first = last = -1
            for r in range(h):
                if prev[r * nb:(r + 1) * nb] != cur[r * nb:(r + 1) * nb]:
                    if first < 0:
                        first = r
                    last = r
            windows.append(None if first < 0 else (x, y + first, x + w - 1, y + last))
        # The "old" plane for the move into frame i: the previous frame with the
        # pixels that stay black cleared, so they go out as white-to-black (full
        # drive) and table 3 is left to the red hold pixels.
        olds = [bytes(p & ~c & 0xFF for p, c in zip(frames[i - 1], frames[i])) for i in range(n)]
        self.anim, self.frames, self.windows, self.olds = a, frames, windows, olds
        gc.collect()

    def _show(self, i: int, fb=None):
        a = self.anim
        _unpack_stage(display._framebuffer_black if fb is None else fb, self.frames[i],
                      a["c0"], a["nb"], a["y"], a["h"])

    def _show_packed(self, packed, fb):
        a = self.anim
        _unpack_stage(fb, packed, a["c0"], a["nb"], a["y"], a["h"])

    def _normal_refresh(self):
        display.update()
        self.waiting_normal = True

    def _start(self):
        self.frame = 0
        self.fast_count = 0
        self.paused = False
        self.resting = False
        self.started_ms = time.ticks_ms()

    async def _step(self):
        if self.launched:
            await fast.close()
            leds.fill((0, 1, 1))
            if self.frames is None:
                self._load()
                self.old = bytearray(len(display._framebuffer_black))
                self.lut = delta_lut(DELTA_FRAMES, WHITE_PUSH, 0, RED_PUSH)
            # The session only has to close for the cleaning refresh.
            fast.max_images = 1_000_000
            fast.window_writes = WINDOW_WRITES
            self._start()
            display.clear()
            display.draw_png(_NAMETAG)
            self._show(0)
            # The "old" plane is the previous frame with pixels that stay black
            # cleared (see _load). Outside the penguin nothing changes, so it is
            # all clear: black there (your name, the QR code) goes out as
            # white-to-black and gets a full drive to black on every pass.
            self.old[:] = bytes(len(self.old))
            self._normal_refresh()
            leds.fill((0, 1, 0))
            return

        if UserA.pressed():
            if self.resting:
                print("Penguin: starting again")
                self.resting = False
                self.started_ms = time.ticks_ms()
            else:
                self.paused = not self.paused
                print("Penguin paused" if self.paused else "Penguin resumed")
        if UserB.pressed() and not self.waiting_normal:
            await fast.close()
            self.fast_count = 0
            self._normal_refresh()

        if self.waiting_normal:
            if display._framebuffer_ready.is_set() or not display.is_done_updating():
                return
            self.waiting_normal = False
            self.next_ms = time.ticks_add(time.ticks_ms(), PAUSE_MS)
            return
        if self.paused or self.resting:
            return
        if time.ticks_diff(time.ticks_ms(), self.next_ms) < 0:
            return

        if RUN_MINUTES and time.ticks_diff(time.ticks_ms(), self.started_ms) > RUN_MINUTES * 60_000:
            print("Penguin: resting. Press User A to start again.")
            self.resting = True
            await fast.close()
            self.fast_count = 0
            self._normal_refresh()
            return

        prev = self.frame
        self.frame = (prev + 1) % len(self.frames)
        self._show(self.frame)
        window = self.windows[self.frame]
        if window is None:
            return
        if CLEAN_EVERY and self.fast_count >= CLEAN_EVERY:
            await fast.close()
            self.fast_count = 0
            self._normal_refresh()
            return
        a = self.anim
        strip = (a["y"], a["y"] + a["h"] - 1)
        if FAST_MODE == "delta":
            # The panel shows frame prev; the planes carry (prev & ~new, new) over the stage.
            self._show_packed(self.olds[self.frame], self.old)
            stage = (a["x"], a["y"], a["x"] + a["w"] - 1, a["y"] + a["h"] - 1)
            ok = await fast.refresh(stage, pulls=1, refresh_rows=strip, old=self.old, lut=self.lut,
                                    scan_rows=strip, hold=display._framebuffer_red)
        else:
            if REFRESH_ROWS == "frame":
                rows = (window[1], window[3])
            elif REFRESH_ROWS == "strip":
                rows = strip
            else:
                rows = None
            ok = await fast.refresh(window, pulls=FAST_PULLS, refresh_rows=rows)
        if not ok:
            print("Penguin: fast refresh failed, stopping the animation")
            self.resting = True
            self._normal_refresh()
            return
        self.fast_count += 1
        self.next_ms = time.ticks_add(time.ticks_ms(), PAUSE_MS)
