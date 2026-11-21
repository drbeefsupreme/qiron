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
3. Enter a cue in one of the five layer fields and save it. Clear the field and save again to resume its automatic feed.

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

## Connect a Chyron reader

Poll `GET /api/stage` from the display host. The browser preview uses a 1.5-second interval. Each response contains the mark, change since the prior mark update, drift hold flag, up/down counts and five ordered layers. Each layer has an integer `id`, rendered `text`, and an `override` string. Layers 1 through 3 represent the horizontal rows. Layers 4 and 5 represent the side columns.

The physical bridge is a later step. The existing controller sends text to the Teensy through `scrollingLayerN_start(text_bytes, -1)`. A bridge can compare layer text between snapshots and send only changed lines. Layer orientation and scrolling speed need a rehearsal on the panel. [Existing Qyron controller](https://github.com/drbeefsupreme/qyron-tui/blob/master/py_rpc/python/connect.py)

## Iterate

Run `mix test` to check scoring, settlement, liquidation, and restore. Edit the HTML, CSS, and JavaScript in `priv/static` and refresh the browser during development. Restart the Mix process after editing Elixir. The specimen illustration uses Canvas 2D. The market API can also drive WebGL shaders from the browser.
