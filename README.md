# Supercon 2026 "Billboard Badge": stock firmware and files

A complete backup of the badge as it shipped, pulled over USB on 2026-11-06. Edit the copy in `badge_files/`. Everything in `firmware_backup/` gets you back to stock.

## What's in this folder

| Path | What it is |
|---|---|
| `badge_files/` | Your working copy of the badge's filesystem: all of its Python code and images. It started as an exact copy (80 files, each SHA-256 checked against the badge). **This is what you edit.** See [Your changes](#your-changes). |
| `tools/make_epd_png.py` | Converts an SVG or PNG into the 960×672 white/black/red palette PNG the badge can draw. |
| `firmware_backup/full_flash_8MB.bin` | The entire 8 MB flash: bootloader, partition table, MicroPython, filesystem and NVS. Writing it back restores the badge exactly. |
| `firmware_backup/bootloader.bin`<br>`firmware_backup/partition-table.bin`<br>`firmware_backup/micropython.bin` | The firmware split into the usual ESP-IDF pieces. |
| `firmware_backup/vfs_filesystem.bin` | Raw LittleFS image of the stock filesystem. |
| `firmware_backup/partitions.csv` | The partition table. |
| `firmware_backup/stock_files.sha256` | Checksums of the 80 stock files, for seeing what you've changed. |
| `firmware_backup/SHA256SUMS` | Checksums of the `.bin` files. |
| `device_info.txt` | What the badge reported: chip, MicroPython build, partitions, file list, built-in modules. |

As of 2026-11-06 the source for this firmware build hasn't been published, so `micropython.bin` is the only copy of it. Keep it safe.

**Not in the GitHub repository** (kept on the PC only): `firmware_backup/` and `device_info.txt`, which are a backup of one particular badge, MAC address included; the gallery images in `badge_files/data/gallery/`, which are Hackaday's artwork and are in the [official repository](https://github.com/Hack-a-Day/2026-Billboard_Badge); and `badge_files/data/app_list` and `data/user_apps.py`, which the badge regenerates at every boot.

## Hardware and firmware

- **MCU:** ESP32-S3 (QFN56, rev v0.2), 8 MB flash, 8 MB octal PSRAM, native USB.
- **Firmware:** custom MicroPython 1.24.1 build named "Billboard Badge", compiled 2026-11-04 with ESP-IDF v5.2.3. LVGL is built in (`import lvgl`). The modules frozen into the firmware are only the standard MicroPython ones, so all badge-specific code is in `badge_files/`.
- **Display:** 9.69" Pervasive Displays e-paper, 960×672, black/white/red ([lib/epd.py](badge_files/lib/epd.py)).
- **LEDs:** 8 RGB LEDs ([lib/led_bar.py](badge_files/lib/led_bar.py)).
- **Buttons:** Menu −, Menu +, User A, User B, Boot ([lib/button.py](badge_files/lib/button.py)). Menu + and Menu − are swapped on the silkscreen.
- **SAO ports:** 3, on I2C SDA 17 / SCL 18 ([lib/sao.py](badge_files/lib/sao.py)).
- **Supply voltage sense:** USB or battery, ADC on GPIO14 ([lib/board.py](badge_files/lib/board.py)).

| Region | Offset | Size | Contents |
|---|---|---|---|
| bootloader | 0x0 | 19.6 KB | ESP-IDF second-stage bootloader |
| partition table | 0x8000 | 3 KB | |
| nvs | 0x9000 | 24 KB | ESP-IDF key/value storage |
| phy_init | 0xF000 | 4 KB | RF calibration |
| factory | 0x10000 | 3 MB | MicroPython (2.8 MB used) |
| vfs | 0x310000 | 4.9 MB | LittleFS filesystem (about half used) |

## How the badge software works

- [main.py](badge_files/main.py) adds one to a boot counter in `data/panel_config.json`. On first boot it shows the splash screen. It then runs four asyncio tasks: buttons, display, LEDs, and the app switcher.
- [lib/app_switcher.py](badge_files/lib/app_switcher.py) imports every `.py` file in `apps/` and creates each `BaseApp` subclass it finds. The stock apps are Workshops, Sat Talks and Sun Talks (all from `schedule.py`), Gallery, and Nametag.
- **On the badge:** Menu +/− picks an app (shown on the LED bar) and User A/B launches it. Pressing Menu +/− inside an app returns to the menu.
- `data/user_apps.py` and `data/app_list` are regenerated at every boot. Don't edit them.

**To add an app:**
1. Copy [apps/template.py](badge_files/apps/template.py) to `apps/myapp.py`.
2. Rename the class and set `self.name`.
3. Put your code in `run()`, which is called every `sleep_ms` milliseconds.

`self.launched` is `True` on the first call after the app is opened, so draw your screen there.

**Drawing:** call `display.clear()`, then `display.draw_png(path, row, col)`, then `display.update()`. PNGs must be non-interlaced and either palette or grayscale ([lib/large_png.py](badge_files/lib/large_png.py)); a normal RGBA export raises `ValueError`. [tools/make_epd_png.py](tools/make_epd_png.py) converts images for you. For text, use LVGL; [apps/nametag.py](badge_files/apps/nametag.py) shows how.

**Your nametag:** the two name labels in [apps/nametag.py](badge_files/apps/nametag.py#L52) (lines 52 and 57) are empty strings. Put your name in them.

## Your changes

| File | Where it lives | What it is |
|---|---|---|
| `apps/hello_i_am_mod.py` | badge + PC | New app, **Hello I Am Mod**, that shows your nametag full screen. |
| `data/graphics/Hello_I_Am_Mod.png` | badge + PC | Your nametag as a 960×672 white/black/red palette PNG (4.7 KB): name and QR code in black, moved apart to leave the middle free for the penguin. |
| `data/graphics/Hello_I_Am_Mod.svg` | PC only | Inkscape source for the PNG. The badge can't use SVG files. |
| `lib/epd_fast.py` | badge + PC | Fast, partial e-paper refreshes (see below). |
| `apps/penguin_nametag.py` | badge + PC | New app, **Penguin Nametag**: your nametag with the EST penguin waddling next to your name. |
| `data/graphics/penguin/` | badge + PC | The 12 penguin frames and `anim.json` (stage position and size). |

The stock apps are unchanged. On the badge, press Menu + or Menu − until the bright LED is the right one, then press User A or User B: **Hello I Am Mod** is the 5th lit LED and **Penguin Nametag** the 7th, next to the one dark LED.

In Penguin Nametag, User A pauses and resumes, and User B runs a normal refresh to clear any ghosting. The settings at the top of [apps/penguin_nametag.py](badge_files/apps/penguin_nametag.py):

| Setting | Default | What it does |
|---|---|---|
| `FAST_MODE` | `"delta"` | `"delta"`: change-only table, one pass per move. `"hold"`: the official table, `FAST_PULLS` passes. |
| `DELTA_FRAMES` | 20 | Frames of drive per move in delta mode (about 15 ms each with window writes). 20 is the shortest table; raise it if the penguin comes out grey or leaves a trail. |
| `WHITE_PUSH` | 6 | Delta mode: frames (of 20 per pass) of push towards white for pixels that stay white, so the background stays clean and old poses fade out. Pixels that stay black (your name, the QR code, the penguin's body) are sent as white→black, so they get a full drive to black on every pass and do not fade. |
| `RED_PUSH` | 20 | Delta mode: frames of the reduced positive rail (VDHR) for red pixels on the scanned lines, which go out as "hold" (`hold=` the red framebuffer). It keeps red there from fading; with the black design there is no red on those lines, so it does nothing. |
| `WINDOW_WRITES` | `True` | Delta mode: the controller scans only the strip's lines (224–555), so the red bands are never driven, and only those lines are sent on each move, across the full width (80 KB). |
| `FAST_PULLS` | 2 | Hold mode only: refresh passes per move. |
| `REFRESH_ROWS` | `"frame"` | Hold mode only: which lines the controller scans. |
| `PAUSE_MS` | 0 | Extra rest between moves. |
| `CLEAN_EVERY` | 1000 | A normal refresh (about 40 s) after this many moves, about every 6 minutes. |
| `RUN_MINUTES` | 0 | Rest after this long; User A starts it again. 0 animates forever. |

## Fast and partial refresh (experimental)

A normal refresh runs the panel's own waveform and takes about 40 s. [lib/epd_fast.py](badge_files/lib/epd_fast.py) is a MicroPython port of the fast mode in the official C++ driver ([firmware/esp32s3-itc97](https://github.com/Hack-a-Day/2026-Billboard_Badge/tree/main/firmware/esp32s3-itc97) in the Hackaday repo) for this badge's E2969JS0B1 panel:

- It reads the panel's calibration block from its OTP once, and takes the update registers and the booster ramp from it.
- It writes the short waveform (`lutb_base` from `data/rendered_luts.py`, identical to the C++ driver's) to register `0xB0` and runs each refresh three times, because this panel runs every pass for a fixed ~1.1 s.
- It keeps the controller up between frames (at most 20 frames, closed after 10 s idle and before any normal update).
- **Partial refresh:** each pixel's two bits pick a waveform table, and in this waveform the "both bits set" table never applies a voltage. Pixels outside the window are sent that way, so only the window changes. The red bands, your name and the QR code are never driven.

- **Change-only mode** (after phthallo/supercon's delta refresh): `refresh(window, old=previous_framebuffer, lut=delta_lut(n))`. The red plane carries the previous frame, so each pixel picks its table as (old, new): stays white, white→black, black→white, stays black. `delta_lut(n)` drives only the two changing tables, for all n frames, so one pass does a move. Pixels that keep their colour would sit at ground, which slowly lets black and red relax and fade, so the penguin app sends pixels that stay black as white→black (their old bit cleared), gives pixels that stay white a short push (`delta_lut(n, white_push)`, as phthallo does), and holds red on the scanned lines with `hold=` and `delta_lut(..., hold_push=n)` (the reduced positive rail, VDHR). With `window_writes` and `scan_rows`, the controller scans and is written only on those lines, across their full width. Narrowing the data window in x as well does not work on this panel: the controller keeps writing full 60-byte rows, so the window's data wraps across them and shows up as several squashed copies.
- **Speed:** the plane data goes over the hardware SPI bus at 20 MHz, a session starts with Pervasive Displays' short waits for this controller family (0.26 s instead of 2.8 s), and `refresh_rows=(first, last)` narrows the refresh window (register `0x90`).

How the timing works, measured on this badge (`tools/epd_fast_timing.py`, `tools/epd_fast_bench.py` and the penguin):

| What | Measured |
|---|---|
| One pass | the table's frame count × the frame time. The official table is 40 frames, of which only 20 drive; the shortest possible table is 20 frames (10 groups of at least 2). |
| Frame time | about 43 µs per display line scanned: 29 ms for the whole panel, 24 ms down to line 555. Narrowing the refresh window (`0x90`) only moves the end of the scan; narrowing the data window (`0x13`, which window writes do) also moves the start, so the penguin's strip (332 lines) scans at about 15 ms a frame. The oscillator register (`0x03`) makes no difference. |
| Penguin move, delta mode, 20 frames, window writes | about 0.4 s (0.3 s pass, 70 ms of image data) |
| Penguin move, hold mode, 2 passes | about 1.8 s |
| Session start | 0.26 s with the short waits |
| Normal refresh | about 40 s |

Fast refreshes are black and white only (keep red out of the window), and only a normal refresh fully restores the film, so do one now and then.

Usage from asyncio code: draw into the framebuffer as usual, then `await fast.refresh((x0, y0, x1, y1))` with `from lib.epd_fast import fast`.

PC-side tools, all run with `mpremote connect COM12 resume run ...`:

| Tool | What it does |
|---|---|
| [tools/epd_fast_probe.py](tools/epd_fast_probe.py) | Reads the panel's OTP and prints the values next to the stock driver's. Draws nothing. |
| [tools/epd_fast_test.py](tools/epd_fast_test.py) | Normal refresh of your nametag, then one fast refresh of a small box with an F in it. |
| [tools/epd_fast_bench.py](tools/epd_fast_bench.py) | Times the bit-banged bus against hardware SPI, and full against narrowed refresh windows, on the same box (ends on an H). |
| [tools/epd_fast_timing.py](tools/epd_fast_timing.py) | Times passes for different table lengths and windows with tables that drive nothing, so the screen does not change. |
| [tools/run_app.py](tools/run_app.py) | Opens one app (Penguin Nametag by default) without the buttons. Add `--no-follow`. |
| [tools/make_penguin_frames.py](tools/make_penguin_frames.py) | Rebuilds the penguin frames from the logo SVG (PC only). [tools/penguin_preview.gif](tools/penguin_preview.gif) previews them. |

**Always use `resume` for scripts that import `lib.epd`.** Without it, mpremote soft-resets MicroPython first, `lib/epd.py` then sets LVGL up a second time, and the badge hard-resets.

The stock `lib/epd.py` uses register values meant for the other panel variant (E2969JS084). This panel's OTP has a different RAM pointer, refresh window and booster ramp, and the stock driver never sends DCTL, which the official C++ driver does. The stock driver still works; the different RAM pointer is probably why it has to bit-reverse its image data on this panel.

After editing the SVG, regenerate the PNG and upload it:

```powershell
python tools/make_epd_png.py badge_files/data/graphics/Hello_I_Am_Mod.svg badge_files/data/graphics/Hello_I_Am_Mod.png
mpremote connect COM12 cp badge_files/data/graphics/Hello_I_Am_Mod.png :data/graphics/Hello_I_Am_Mod.png + reset
```

## Working with the badge

On this PC the badge is **COM12** when MicroPython is running and **COM13** in bootloader mode. `mpremote` is installed with pip, and `esptool` comes from PlatformIO. Both are on your PATH.

```powershell
# Upload one changed file, then reboot so the app reloads
mpremote connect COM12 cp badge_files/apps/nametag.py :apps/nametag.py + reset

# Upload whole folders; files already identical on the badge are skipped
mpremote connect COM12 cp -r badge_files/apps badge_files/lib : + reset

# Watch the console (prints, tracebacks). Ctrl-C stops the app, Ctrl-D restarts it, Ctrl-] exits
mpremote connect COM12 repl

# Run a script from the PC without saving it to the badge
mpremote connect COM12 run test.py
```

```bash
# Git Bash: list the stock files you've changed (files you've added aren't listed)
cd badge_files && sha256sum -c --quiet ../firmware_backup/stock_files.sha256
```

Transfers run at only about 3 KB/s, so upload just what you've changed. The gallery images alone are 2.2 MB.

## Bootloader mode and restoring

To enter the bootloader, hold **BOOT**, press and release **RESET** (or power-cycle the badge), then let go of BOOT. The badge appears as a new COM port with USB ID 303A:1001.

Don't use `machine.bootloader()` from the REPL. On this badge it leaves the USB hung until you do a hardware reset.

```powershell
# Restore everything exactly as shipped: firmware, files and NVS
esptool --chip esp32s3 --port COM13 write_flash 0x0 firmware_backup/full_flash_8MB.bin

# Reinstall only the stock firmware and keep your files
esptool --chip esp32s3 --port COM13 write_flash 0x0 firmware_backup/bootloader.bin 0x8000 firmware_backup/partition-table.bin 0x10000 firmware_backup/micropython.bin

# Put back only the stock files (replaces the whole filesystem)
esptool --chip esp32s3 --port COM13 write_flash 0x310000 firmware_backup/vfs_filesystem.bin
```

When it finishes, `esptool` resets the badge back into its app.

## Bugs in the stock code

- **[main.py:48](badge_files/main.py#L48):** on the 42nd boot it draws `never-epd.png`, but the file is named `never_epd.png`. That boot crashes before the app starts and leaves the badge at the REPL. The next boot is normal. To fix it, change the `-` to `_`.
- **[lib/sao.py:32-36](badge_files/lib/sao.py#L32-L36):** `set_address()` ignores its argument (`self.address = 0`). It also uses `machine.I2CTarget`, which this MicroPython build doesn't have. Nothing calls it yet, but any SAO code that does will fail.
