# Qiron

The Too Late Show audience calls the price of Dr. Crow’s unborn child’s blood. Give the audience the root URL and put `/stage` on the venue screen. Doctor Beef Supreme runs the show from `/operator`.

## Run a rehearsal

Install Elixir 1.18 or later on Erlang/OTP 27 or later. From this checkout, run the following in zsh.

```sh
mix deps.get
read -rs 'OPERATOR_PASSWORD?Booth password (12 or more characters): '
export OPERATOR_PASSWORD
mix run --no-halt
```

The password prompt above uses zsh. In Bash use `read -rs -p 'Booth password: ' OPERATOR_PASSWORD`. Open `http://localhost:4000` on the server. On a phone connected to the same Wi-Fi, use the server’s LAN address and port 4000. Sign into the booth with username `beef` and the password you set.

1. Open the audience page in two browsers. Call up on one and down on the other.
2. In the booth, hold the drift and set the price. Both phones update their balances. The stage shows the mark and the up/down counts.
3. Enter a cue in one of the five stage layer fields and save it. Clear the field and save again to resume its automatic feed.

## Game rules

Each browser gets a private seat cookie for seven days and 1,000 fictional credits. A tap opens a position at the server’s current mark. A 1% move pays or costs one credit on a 100-credit position. The stake is the smaller of 100 credits and the current balance. Losses stop at the stake. A position closes when its stake is exhausted. Switching direction settles the old position and opens the new one at the same mark. Closing banks the result. Repeating the same call keeps the original entry price.

The mark starts at 100.00 and drifts by up to 0.5% every two seconds within a range of 1.00 to 10,000.00. The booth can hold the drift, move the mark by 5%, or set it directly. The audience sees its position and credits. The stage carries the shared price.

## Run on a show server

Run one application instance behind an HTTPS reverse proxy at the root of a show subdomain. Set `PORT`, `OPERATOR_PASSWORD`, `COOKIE_SECURE=true`, and `SHOW_FILE` to an absolute path on a persistent volume. Serve the app and its API on the same origin. The booth stays locked until you configure a password of at least 12 characters.

```sh
MIX_ENV=prod mix deps.get --only prod
MIX_ENV=prod mix release
_build/prod/rel/qiron/bin/qiron start
```

The market process serializes trades and operator commands. It writes price, seats, and layer overrides to a single snapshot before acknowledging changes. Restarting restores that show. Point `SHOW_FILE` at a fresh path to rehearse a separate show. The default path is `data/show.etf`.

## Run the booth on the Raspberry Pi 4

Run the Elixir application on the Pi that has the Teensy plugged into USB. The same application serves the audience, booth and stage. For a show URL, point the HTTPS reverse proxy at that Pi. The server needs Linux, Python 3 and permission to open the USB serial device. Raspberry Pi OS usually grants serial access through the `dialout` group. Restart the login session after changing groups.

The controller opens `/dev/ttyACM0`. To select a stable device name, set `QYRON_DEVICE` to the Teensy symlink under `/dev/serial/by-id/` before starting the app. Run only one controller on the port. Stop Qiron before connecting the old TUI or flashing over USB.

In `/operator`, the USB status shows the panel connection. The six layers have independent text and speed controls. The first five normally carry the show feed. Saving an empty field restores that feed for its layer. The sixth field drives the feature layer. Text accepts up to 32,767 UTF-8 bytes per layer. The panel uses its existing bitmap fonts. The booth also controls brightness, CAW, DOPAMINE, clearing, backgrounds, blinking, shapes, pixels, and GIF playback. Choose a cue and press **Run**.

Text, speed and brightness settings survive a disconnect and a show restart. The controller resends them when the panel reconnects. One-shot effects require a live connection. If a cue times out, check the panel before repeating it. The device may have acted before its reply was lost. The audience and browser stage work while the panel is unplugged.

## Build the Teensy 4.1 firmware

Use PlatformIO Core and Git on a build host. From the repo root run:

```sh
pio run -d firmware
```

The image is `firmware/.pio/build/teensy41/firmware.hex`. On a machine with the Teensy attached, use `pio run -d firmware -t upload` with the Teensy loader tools installed. Press the board’s program button if the loader asks. The target preserves USB Serial + HID, SmartLED Shield V5, the 128 × 96 HUB75 layout and C-shaped stacking. The firmware build pins SmartMatrix and applies the long-text changes automatically.

Keep the show’s GIFs on the Teensy microSD card. Use one directory per preset under `/gifs/`: `koyaanisqatsi`, `obama`, `flag`, `drugs`, `joker`, `spooky`, `subgenius`, `transparent`, `aj`, `blue`, and `hank`. Boot defaults to the Joker directory. Rehearse panel orientation, scroll speed, GIF colors and brightness on the actual rig.

## USB interface

Legacy clients can discover and call the original 37 simpleRPC methods in their original order. The Pi controller uses framed commands on that same port. Flash the new image before starting the new controller. Each framed request begins with `FE` (hex), a one-byte method index, and a little-endian unsigned 16-bit payload length. The Pi waits for `FE 00` (accepted) or `FE 01` (invalid) before sending the next request.

| Method index | Operation | Payload |
| --- | --- | --- |
| 0–5 | Start text on 1, 2, 3, 4, 5, F | Signed 32-bit little-endian repeat count, then text bytes without a NUL. The booth uses −1 for continuous scrolling. |
| 6–11 | Set scroll speed on the corresponding layer | One byte |
| 12 | Set brightness | One byte |
| 13–36 | Effects and GIF actions in legacy order | Empty |

`GET /api/stage` remains public and returns the mark, change, drift hold flag, position counts, and five ordered layer records. The booth reads the authenticated `GET /api/panel` for device status, six layer settings, brightness and action names.

## Verification

Run `mix test` for the market integration check. On Linux, the browser rehearsal starts its own server with a temporary snapshot and booth password, opens independent audience seats and attaches a simulated Teensy over a pseudo-terminal. Install the test-only browser dependency in a virtual environment:

```sh
python3 -m venv /tmp/qiron-browser
/tmp/qiron-browser/bin/pip install playwright
/tmp/qiron-browser/bin/python -m playwright install chromium
/tmp/qiron-browser/bin/python test/e2e/show.py
```

Set `CHROMIUM` to use an already-installed Chrome or Chromium executable. The test operates the booth, verifies two opposite positions against the same mark, and checks the serial bytes for a full-size cue.

For the firmware protocol integration test, install a C++17 compiler and run the following from the repo root. The test connects the original Python simpleRPC client and a framed client to a host build of the firmware parser through a pseudo-terminal. It checks discovery, calls, maximum-size text, invalid frames, and recovery.

```sh
/tmp/qiron-browser/bin/pip install -r firmware/integration/requirements.txt
/tmp/qiron-browser/bin/python firmware/integration/usb.py
```
