"""Step 1: read the e-paper panel's OTP calibration block. Nothing is drawn.

    mpremote connect COM12 resume run tools/epd_fast_probe.py

`resume` matters: without it mpremote soft-resets MicroPython first, and
importing lib.epd again after a soft reset re-creates the LVGL display on top
of the one the badge app made, which hard-resets the badge. With it, this
reuses the badge app's display.

Needs lib/epd_fast.py on the badge. Prints which panel is attached and the
register values the fast refresh will use, next to what the stock driver sends.
Afterwards restart the badge app with:  mpremote connect COM12 reset
"""

import asyncio as aio
import sys
import time

if "lib.epd" not in sys.modules:
    raise SystemExit("run this with `mpremote connect COM12 resume run ...` while the badge app is up")
aio.new_event_loop()  # drop the interrupted badge app's tasks

print("probe: importing lib.epd_fast")
time.sleep_ms(50)
from lib.epd_fast import fast

print("probe: imported")
time.sleep_ms(50)
fast.verbose = True


async def main():
    ok = await fast.probe()
    print("probe ok:", ok)
    for key, value in fast.info().items():
        print("%-14s %s" % (key, value))


aio.run(main())
