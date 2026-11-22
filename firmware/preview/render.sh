#!/usr/bin/env bash
set -euo pipefail
firmware=$(cd "$(dirname "$0")/.." && pwd)
smartmatrix="$firmware/.pio/libdeps/teensy41/SmartMatrix/src"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cd "$work"
cc -c "$smartmatrix"/Font_*.c
c++ -O2 -std=c++17 -I"$smartmatrix" -I"$firmware/src" "$firmware/preview/intro.cpp" "$smartmatrix/MatrixFont.cpp" "$smartmatrix/Layer.cpp" ./*.o -o render
./render | ffmpeg -loglevel error -f rawvideo -pixel_format rgb24 -video_size 128x96 -framerate 50/3 -i - \
  -filter_complex '[0:v]split[a][b];[a]palettegen=stats_mode=full[p];[b][p]paletteuse=dither=none' \
  -loop 0 -y "$work/telethon.gif"
cp "$work/telethon.gif" "$firmware/../priv/static/telethon.gif"
