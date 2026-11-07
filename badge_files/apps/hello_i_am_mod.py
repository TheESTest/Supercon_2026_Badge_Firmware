"""Hello I Am Mod: custom nametag, drawn full screen from a single PNG.

Edit the artwork in data/graphics/Hello_I_Am_Mod.svg, then export it as a
960x672, non-interlaced, palette (white/black/red) PNG to the path below.
"""

from apps.base_app import BaseApp
from lib.epd import display
from lib.led_bar import leds

_IMAGE = "/data/graphics/Hello_I_Am_Mod.png"


class HelloIAmModApp(BaseApp):
    def __init__(self, name: str | None = None) -> None:
        super().__init__(name or "Hello I Am Mod")

    def run(self):
        if self.launched:
            leds.fill((0, 1, 1))
            display.clear()
            display.draw_png(_IMAGE)
            display.update()
            leds.fill((0, 1, 0))
