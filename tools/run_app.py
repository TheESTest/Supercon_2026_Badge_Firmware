"""Start the badge's main loop with one app already open, without the buttons.

    mpremote connect COM12 resume run --no-follow tools/run_app.py

Opens the app named APP below. `resume` keeps the badge app's modules (a soft
reset would make lib/epd.py set LVGL up twice, which hard-resets the badge);
`--no-follow` lets mpremote exit while the loop keeps running on the badge.
To pick up newly uploaded apps, reset the badge first: mpremote connect COM12 reset
"""

import asyncio as aio
import sys

APP = "Penguin Nametag"

if "lib.app_switcher" not in sys.modules:
    raise SystemExit("run this with `mpremote connect COM12 resume run ...` while the badge app is up")
aio.new_event_loop()  # drop the interrupted badge app's tasks

from lib.app_switcher import switcher
from lib.button import scan as button_scan
from lib.epd import display
from lib.led_bar import leds

names = [app.name for app in switcher.apps]
if APP not in names:
    raise SystemExit("no app named %r, the badge has: %s" % (APP, ", ".join(names)))
idx = names.index(APP)
switcher.selection_idx = switcher.active_idx = idx
switcher.selecting_mode = False
switcher.apps[idx].launched = True
leds.clear_sequence()
leds.fill((0, 0, 0))
leds.write()


async def main():
    aio.create_task(button_scan())
    aio.create_task(display.run())
    aio.create_task(leds.update())
    await switcher.arun()


print("running", APP)
aio.run(main())
