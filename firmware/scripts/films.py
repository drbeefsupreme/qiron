from pathlib import Path
import struct

Import("env")


def frames(data):
    width, height, flags = struct.unpack_from("<HHB", data, 6)
    pos = 13 + (3 << ((flags & 7) + 1) if flags & 128 else 0)
    header = data[:pos]
    control = b""
    while data[pos] != 0x3b:
        start = pos
        kind = data[pos]
        if kind == 0x21:
            pos += 2
        elif kind == 0x2c:
            x, y, w, h, flags = struct.unpack_from("<4HB", data, pos + 1)
            if (x, y, w, h) != (0, 0, width, height):
                raise ValueError("Film must contain independent full-canvas frames")
            pos += 11 + (3 << ((flags & 7) + 1) if flags & 128 else 0)
        else:
            raise ValueError("Unknown GIF block")
        while data[pos]:
            pos += 1 + data[pos]
        pos += 1
        if kind == 0x2c:
            yield header + control + data[start:pos] + b";", struct.unpack_from("<H", control, 4)[0] * 10
            control = b""
        elif data[start+1] == 0xf9:
            control = data[start:pos]


assets = Path(env.subst("$PROJECT_DIR")).parent / "priv/static"
output = Path(env.subst("$BUILD_DIR")) / "films"
output.mkdir(parents=True, exist_ok=True)
lines = ["#pragma once"]
for name, file, width in [("intro", "telethon.gif", 128), ("crow", "dr-crow.gif", 96),
                          ("beef", "dr-beef.gif", 96), ("peter", "peter-thiel.gif", 96),
                          ("santa", "santa.gif", 96)]:
    gif = (assets / file).read_bytes()
    if gif[:3] != b"GIF" or gif[6:10] != bytes([width, 0, 96, 0]):
        raise ValueError(f"Expected {width}x96 GIF for {file}")
    packed = bytearray()
    table = []
    elapsed = 0
    for frame, delay in frames(gif):
        elapsed += delay
        table.append(f"{{{len(packed)},{len(frame)},{elapsed}}}")
        packed.extend(frame)
    lines.append(f"const uint8_t {name}Bytes[] PROGMEM = {{")
    for offset in range(0, len(packed), 32):
        lines.append(",".join(map(str, packed[offset:offset + 32])) + ",")
    lines.extend(["};", f"const films::Frame {name}Frames[] PROGMEM = {{", ",".join(table), "};"])
    lines.append(f"constexpr films::Film {name}Film{{{name}Bytes,{name}Frames,{len(table)},{width},{elapsed}}};")
lines.append("const films::Film filmsByLayer[] = {introFilm,crowFilm,beefFilm,peterFilm,santaFilm};")
header = output / "film_assets.h"
source = "\n".join(lines)
if not header.exists() or header.read_text() != source:
    header.write_text(source)
env.Append(CPPPATH=[str(output)])

photo_file = assets.parents[1] / "art/splice-photos.rgb565"
photos = photo_file.read_bytes()
if len(photos) != 2 * 128 * 96 * 2:
    raise ValueError("Expected two 128x96 little-endian RGB565 splice frames")
rows = ["#pragma once", "const uint16_t splicePhotos[] PROGMEM = {"]
for offset in range(0, len(photos), 64):
    rows.append(",".join(map(str, struct.unpack_from("<32H", photos, offset))) + ",")
rows.append("};")
header = output / "splice_assets.h"
source = "\n".join(rows)
if not header.exists() or header.read_text() != source:
    header.write_text(source)
