"""Time refresh passes without drawing anything.

    mpremote connect COM12 resume run tools/epd_fast_timing.py

Each line is one session with one pass. The planes hold every pixel and the
test tables drive nothing, so the screen does not change. Shows how long a pass
takes for a given table length and refresh window, whether the short start-up
waits still latch a table (a pass that fell back to the panel's own waveform
would take ~34 s), and whether writing the oscillator register (0x03) changes
the frame time. Restart the badge app afterwards: mpremote connect COM12 reset
"""

import asyncio as aio
import sys

if "lib.epd" not in sys.modules:
    raise SystemExit("run this with `mpremote connect COM12 resume run ...` while the badge app is up")
aio.new_event_loop()  # drop the interrupted badge app's tasks

from lib.epd import display
from lib.epd_fast import fast, ground_lut

STRIP = (224, 555)  # the penguin's lines


async def one(label, lut, quick, osc, rows, frames):
    fast.quick = quick
    fast.osc = osc
    ok = await fast.refresh(None, keep_awake=False, pulls=1, refresh_rows=rows, lut=lut)
    r = fast.last
    passes = r.get("pass_ms") or [0]
    per_frame = "%.1f ms/frame" % (passes[0] / frames) if frames else ""
    print("== %-44s ok=%s  pass %5d ms  %-14s  start-up %4d ms"
          % (label, ok, passes[0], per_frame, r.get("open_ms", 0) + r.get("refresh_ms", 0) - sum(passes)))


async def main():
    # Nothing runs the normal display task here; clear its flags in case the
    # badge app was stopped in the middle of a normal update.
    display._framebuffer_ready.clear()
    display._display_updated.set()
    fast.log = False
    if not await fast.probe():
        print("probe failed:", fast.info())
        return
    await one("official table, official waits, strip", None, False, None, STRIP, 40)
    await one("ground 20 f, quick waits, strip", ground_lut(20), True, None, STRIP, 20)
    await one("ground 40 f, quick waits, strip", ground_lut(40), True, None, STRIP, 40)
    await one("ground 20 f, quick waits, strip, 0x03 = 11", ground_lut(20), True, 0x11, STRIP, 20)
    await one("ground 20 f, quick waits, whole panel", ground_lut(20), True, None, None, 20)
    fast.quick, fast.osc = True, None


aio.run(main())
