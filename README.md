# Qiron

The Too Late Show audience calls the price of Dr. Crow’s unborn child’s blood. Give the audience the root URL. Open `/stage` for an optional browser monitor or projector feed. The physical QYRON runs directly from the Pi with the stage tab closed. Doctor Beef Supreme runs the show from `/operator`.

## Run a rehearsal

Install Elixir 1.18 or later on Erlang/OTP 27 or later. From this checkout, run the following in zsh.

```sh
mix deps.get
read -rs 'OPERATOR_PASSWORD?Booth password (12 or more characters): '
export OPERATOR_PASSWORD
mix run --no-halt
```

The password prompt above uses zsh. In Bash use `read -rs -p 'Booth password: ' OPERATOR_PASSWORD`. Open `http://localhost:4000` on the server. On a phone connected to the same Wi-Fi, use the server’s LAN address and port 4000. Sign into the booth with username `beef` and the password you set.

1. Open `/operator` and `/stage` in separate windows. In the booth, select **Introduction**. The stage keeps its current picture while the booth prepares the telethon loop.
2. Press the red **Take live** button or **Alt+Enter** anywhere in the booth, including a text field. The button and shortcut are active once a changed draft is ready. With USB disconnected you can take the draft to the browser stage for a laptop rehearsal.
3. Prepare **GIF**, choose a folder or enter a full SD path such as `/gifs/joker/hotline.gif`, and type the five scrolls. You can also set their speeds, brightness and an optional feature line or effect. Take the cue when you want those changes on air. The browser stage shows the overlay text and identifies the SD selection. The Teensy plays the SD file.
4. Prepare and take **Blood Futures**. Hold the drift and set the mark to 100. Open two audience seats in separate browser profiles and call opposite directions at 1×. Set the mark to 110. The stage shows the price, candles, one bull and one bear. The seats show 55,000 and 45,000 PISS COIN.

The booth also has two one-click portrait takes, **Dr. Crow** and **Dr. Beef Supreme**. Each plays a ten-second idle loop. To return to a show cue, select its mode and take it live.

The 24-second Introduction places Crow, Beef, Peter Thiel and Santa against the poster’s ochre jungle and falling petals. The CAW-IN and Santa Tracker sequences return to an ensemble Christmas Telethon title. The Teensy plays the intro and the two booth portraits directly from flash. The browser stage uses the same GIFs. To regenerate the intro from its source art, run `python3 art/telethon.py` with Pillow installed before building the firmware.

## Game rules

Each seat starts with 50,000 PISS COIN. Each position uses the full seat balance at the chosen leverage (1× through 50×, default 1×). At 10×, a 1% move in your direction earns 10% of the entry balance. Each Long or Short button shows the liquidation price for that call. “Outside range” means the mark cannot reach the threshold under the show’s price limits. An open position keeps its entry and leverage until closed or flipped. Switching sides settles the old position first. A balance of zero closes the position and starts a five-minute cooldown. The seat can then claim another 50,000 PISS COIN. The cooldown and balances survive server restarts. When upgrading an old snapshot, the server settles open positions at the saved mark under the old rules and converts each old credit into 50 PISS COIN.

The mark starts at 100.00 and moves every two seconds within a range of 1.00 to 10,000.00. In the operator booth, Volatility sets the largest random move per tick, from ±0% to ±5%. The default is ±0.5%. The setting applies on the next unheld tick and survives a restart. The booth can hold the drift, move the mark by 5%, or set it directly. The audience sees its position and PISS COIN balance. The stage carries the shared price.

## Run on a show server

Run one application instance behind an HTTPS reverse proxy at the root of a show subdomain. Set `PORT`, `OPERATOR_PASSWORD`, `COOKIE_SECURE=true`, and `SHOW_FILE` to an absolute path on a persistent volume. Serve the app and its API on the same origin. The booth stays locked until you configure a password of at least 12 characters.

```sh
MIX_ENV=prod mix deps.get --only prod
MIX_ENV=prod mix release
_build/prod/rel/qiron/bin/qiron start
```

The market process serializes trades and operator commands. It writes the market, seats, candles, on-air display, prepared draft and draft revision to a single snapshot. Restarting restores that show. Point `SHOW_FILE` at a fresh path to rehearse a separate show. The default path is `data/show.etf`.

## Run the booth on the Raspberry Pi 4

Run the Elixir application on the Pi that has the Teensy plugged into USB. The same application serves the audience, booth and stage. For a show URL, point the HTTPS reverse proxy at that Pi. The server needs Linux, Python 3 and permission to open the USB serial device. Raspberry Pi OS usually grants serial access through the `dialout` group. Restart the login session after changing groups.

The controller opens `/dev/ttyACM0`. To select a stable device name, set `QYRON_DEVICE` to the Teensy symlink under `/dev/serial/by-id/` before starting the app. Run only one controller on the port. Stop the running controller before flashing over USB.

## How the booth stages a cue

The Pi owns the show state. `Qiron.Display` holds the mode, brightness and GIF settings, including the five scrolling layers and feature layer F. Each layer accepts up to 32,767 UTF-8 bytes. `Qiron.Market` keeps two display records in the show snapshot, one on air and one for the next take. It also aggregates the last four minutes of ten-second OHLC bars. Trading and the operator’s mark controls stay live in every display mode.

Editing the booth increments the draft revision. `Qiron.Panel` sends the settings to a staging buffer on the Teensy while the current mode continues running. A newer revision supersedes the previous preload. For a specific SD filename, the Teensy opens the file and decodes its first frame before reporting ready. A bad file path leaves the live cue running and the booth shows the error. Selecting an empty or missing folder allows a text-only scene.

**Take live** or **Alt+Enter** activates the prepared revision. The Teensy applies the staged mode, text, speeds, brightness and queued effect together, and the Pi publishes the new on-air scene after the Teensy acknowledges. In Blood Futures mode the Pi sends price, open-position counts and candle updates as they change. The Teensy draws the candle bodies and wicks directly into the 128 × 96 background layer.

A disconnected booth can take a scene to the browser stage. When USB returns, the controller restores the saved on-air settings, then prepares any different draft. One-shot effects run only on a connected take and are never replayed during recovery. If the connection drops in the middle of a take, check the booth’s on-air status after it reconnects.

## Build the Teensy 4.1 firmware

Use PlatformIO Core and Git on a build host. From the repo root run:

```sh
pio run -d firmware
```

The image is `firmware/.pio/build/teensy41/firmware.hex`. On a machine with the Teensy attached, use `pio run -d firmware -t upload` with the Teensy loader tools installed. Press the board’s program button if the loader asks. The target preserves USB Serial + HID, SmartLED Shield V5, the 128 × 96 HUB75 layout and C-shaped stacking. The firmware build pins SmartMatrix and applies the long-text changes automatically.

Keep the show’s GIFs on the Teensy microSD card. Use one directory per preset under `/gifs/`: `koyaanisqatsi`, `obama`, `flag`, `drugs`, `joker`, `spooky`, `subgenius`, `transparent`, `aj`, `blue`, and `hank`. Boot defaults to the Joker directory. Rehearse panel orientation, scroll speed, GIF colors and brightness on the actual rig.

## USB interface

The Pi and Teensy use one framed binary protocol over USB serial. Flash the new image before starting the new controller. Each framed request begins with `FE` (hex), a one-byte method index, and a little-endian unsigned 16-bit payload length. The Pi waits for `FE 00` (accepted) or `FE 01` (invalid) before sending the next request.

| Method index | Operation | Payload |
| --- | --- | --- |
| 0–5 | Start text on 1, 2, 3, 4, 5, F | Signed 32-bit little-endian repeat count, then text bytes without a NUL. The booth uses −1 for continuous scrolling. |
| 6–11 | Set scroll speed on the corresponding layer | One byte |
| 12 | Set brightness | One byte |
| 13–36 | Demo, shapes, pixels, backgrounds, blink, GIF controls and presets, clear loops | Empty |
| 37 | Activate mode directly | One byte: 0 = GIF, 1 = Blood Futures, 2 = Introduction, 3 = Dr. Crow, 4 = Dr. Beef Supreme |
| 38 | Update Blood Futures | Little-endian uint32 mark in cents, bulls, bears, then 1–24 OHLC tuples in cents, oldest first |
| 39 | Loop a specific SD GIF | Full path under the selected `/gifs/` folder, up to 240 bytes |
| 40 | Begin a new staged scene | Mode byte |
| 41 | Preload a field | One-byte field method followed by its normal payload |
| 42 | Take the prepared scene | Empty |

`GET /api/stage` exposes the on-air display, current mark, open counts and candles. The authenticated `GET /api/panel` exposes the draft, its revision, the on-air mode and preload status. A booth edit posts to `/api/operator`; a take posts `{"take": revision}` to that endpoint. A stale revision returns HTTP 409.

## Verification

Run `mix test` for the market, snapshot and display integration checks. On Linux, the browser rehearsal starts its own server with a temporary snapshot and booth password, opens independent audience seats and attaches a simulated Teensy over a pseudo-terminal. Install the test-only browser dependency in a virtual environment:

```sh
python3 -m venv /tmp/qiron-browser
/tmp/qiron-browser/bin/pip install playwright
/tmp/qiron-browser/bin/python -m playwright install chromium
/tmp/qiron-browser/bin/python test/e2e/show.py
```

Set `CHROMIUM` to use an already-installed Chrome or Chromium executable. The test operates the booth, verifies two opposite positions against the same mark, and checks that a full-size cue stays off air until Alt+Enter. It also checks missing-file rejection, offline takes and USB reconnect.

Run the firmware parser integration check on Linux with Python 3 and a C++17 compiler. It sends fragmented and maximum-size cues over a pseudo-terminal, checks accepted and rejected replies, and verifies that unframed input has no effect.

```sh
python3 firmware/integration/usb.py
```

After building the firmware, run `python3 firmware/integration/films.py` with Pillow installed. This exercises the firmware GIF decoder and compares its 128 × 96 output against the source animations through each loop boundary.

## First physical test

Start the rehearsal in a fresh checkout on the Pi connected to the Teensy. Quit the old controller and stop its service if it normally launches automatically. Leave the show microSD card in the Teensy. Download the matching Teensy 4.1 HEX and flash it from the Pi with PJRC’s command-line loader. Tap the board’s Program button once when the loader is waiting.

```sh
teensy_loader_cli --mcu=TEENSY41 -w -v ~/qyron-teensy41.hex
ls -l /dev/serial/by-id/
python3 firmware/integration/panel.py /dev/ttyACM0
```

Substitute the Teensy’s actual device path in the last command. Run this check with the booth stopped. It uses only Python 3, sets brightness to 64 out of 255, sets the middle row speed to zero and displays **QYRON PI TEST**. Five acknowledgments cover the prepared cue and take. Seeing those words on the board also tests the display output. Starting the booth restores its saved settings.

For the physical rehearsal, follow the four booth steps above with **USB connected**. Watch the LEDs while typing a cue. They should keep the current scene until you see **Draft preloaded on panel** and press **Alt+Enter** or **Take live**. Check the exact GIF and all five scroll orientations, the bull/bear counts and candle movement, and a full 24-second Introduction cycle.
