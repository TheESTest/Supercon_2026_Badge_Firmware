"""Step 2: one fast, partial refresh of a small test box. Watch the badge.

    mpremote connect COM12 resume run tools/epd_fast_test.py

`resume` matters: without it mpremote soft-resets MicroPython first, and
importing lib.epd again after a soft reset re-creates the LVGL display on top
of the one the badge app made, which hard-resets the badge.

Needs lib/epd_fast.py on the badge. It:

  1. draws the Hello I Am Mod nametag with a normal refresh (about 40 s), then
  2. fast-refreshes only a 56x72 box in the gap between "Austin" and the QR
     code, drawing a bordered letter F in it (a few seconds).

If it works, the F is upright and reads normally, and nothing else on the
screen changes during step 2. A mirrored or upside-down F means the bit or line
order is wrong. The box was picked so that even a mirrored or flipped mapping
would land on white space. Restart the badge app afterwards with:
mpremote connect COM12 reset
"""

import asyncio as aio
import sys
import time

import framebuf

if "lib.epd" not in sys.modules:
    raise SystemExit("run this with `mpremote connect COM12 resume run ...` while the badge app is up")
aio.new_event_loop()  # drop the interrupted badge app's tasks

from lib.epd import display
from lib.epd_fast import fast

NAMETAG = "/data/graphics/Hello_I_Am_Mod.png"
WINDOW = (480, 300, 535, 371)  # x0, y0, x1, y1: right-half bytes 0-6, rows symmetric about the middle


async def wait_normal_update():
    await aio.sleep_ms(200)
    while display._framebuffer_ready.is_set() or not display.is_done_updating():
        await aio.sleep_ms(100)


async def main():
    task = aio.create_task(display.run())

    print("== 1. nametag, normal refresh")
    t0 = time.ticks_ms()
    display.clear()
    display.draw_png(NAMETAG)
    display.update()
    await wait_normal_update()
    print("== 1. done in %d ms" % time.ticks_diff(time.ticks_ms(), t0))

    print("== 2. fast partial refresh of", WINDOW)
    x0, y0, x1, y1 = WINDOW
    w, h = x1 - x0 + 1, y1 - y0 + 1
    fb = display.black
    fb.fill_rect(x0, y0, w, h, 0)
    display.red.fill_rect(x0, y0, w, h, 0)
    fb.rect(x0, y0, w, h, 1)
    fb.rect(x0 + 1, y0 + 1, w - 2, h - 2, 1)
    fb.fill_rect(x0 + 12, y0 + 10, 8, h - 20, 1)  # stem, on the left
    fb.fill_rect(x0 + 12, y0 + 10, w - 24, 8, 1)  # top bar
    fb.fill_rect(x0 + 12, y0 + 30, w - 34, 8, 1)  # middle bar, shorter
    ok = await fast.refresh(WINDOW, keep_awake=False)
    print("== 2. ok:", ok)
    print("panel:", fast.info().get("panel"))
    task.cancel()


aio.run(main())
