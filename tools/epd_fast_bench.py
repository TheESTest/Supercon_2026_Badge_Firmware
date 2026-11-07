"""Speed test for lib/epd_fast.py on the F test box next to "Austin".

    mpremote connect COM12 resume run tools/epd_fast_bench.py

Four fast refreshes of the box, each in its own session, printing how long the
plane transfer and each refresh pass take:

  1. L  bit-banged bus, full refresh window,              1 pass
  2. F  hardware SPI,   full refresh window,              1 pass
  3. E  hardware SPI,   refresh window = the box's lines, 1 pass
  4. H  hardware SPI,   refresh window = the penguin's strip (lines 224-555), 3 passes

The box should end up showing an H. Any other letter says which step did not
land on the panel. Restart the badge app afterwards: mpremote connect COM12 reset
"""

import asyncio as aio
import sys

if "lib.epd" not in sys.modules:
    raise SystemExit("run this with `mpremote connect COM12 resume run ...` while the badge app is up")
aio.new_event_loop()  # drop the interrupted badge app's tasks

from lib.epd import display
from lib.epd_fast import fast

BOX = (480, 300, 535, 371)
STRIP_ROWS = (224, 555)


def letter(ch):
    x0, y0, x1, y1 = BOX
    w, h = x1 - x0 + 1, y1 - y0 + 1
    k = display.black
    k.fill_rect(x0, y0, w, h, 0)
    display.red.fill_rect(x0, y0, w, h, 0)
    k.rect(x0, y0, w, h, 1)
    k.rect(x0 + 1, y0 + 1, w - 2, h - 2, 1)
    left, top, bottom = x0 + 12, y0 + 10, y0 + h - 18
    k.fill_rect(left, top, 8, h - 20, 1)  # left stem, every letter
    if ch in "FE":
        k.fill_rect(left, top, 32, 8, 1)  # top bar
        k.fill_rect(left, y0 + 30, 22, 8, 1)  # middle bar
    if ch in "LE":
        k.fill_rect(left, bottom, 32, 8, 1)  # bottom bar
    if ch == "H":
        k.fill_rect(left + 24, top, 8, h - 20, 1)  # right stem
        k.fill_rect(left, y0 + 32, 32, 8, 1)  # crossbar


async def run(label, ch, hw, pulls, rows):
    fast.hw_spi = hw
    letter(ch)
    ok = await fast.refresh(BOX, keep_awake=False, pulls=pulls, refresh_rows=rows)
    r = fast.last
    print("== %s: ok=%s, planes %d ms, passes %s ms, total %d ms"
          % (label, ok, r.get("planes_ms", -1), r.get("pass_ms"), r.get("total_ms", -1)))


async def main():
    # Nothing runs the normal display task here; if the badge app was stopped in
    # the middle of a normal update its flags would never clear.
    display._framebuffer_ready.clear()
    display._display_updated.set()
    if not await fast.probe():
        print("probe failed:", fast.info())
        return
    await run("1. L  bit-banged bus, full window, 1 pass  ", "L", False, 1, None)
    await run("2. F  hardware SPI,   full window, 1 pass  ", "F", True, 1, None)
    await run("3. E  hardware SPI,   box lines,   1 pass  ", "E", True, 1, (BOX[1], BOX[3]))
    await run("4. H  hardware SPI,   strip lines, 3 passes", "H", True, 3, STRIP_ROWS)


aio.run(main())
