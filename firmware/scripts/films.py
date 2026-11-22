from pathlib import Path

Import("env")

assets = Path(env.subst("$PROJECT_DIR")).parent / "priv/static"
output = Path(env.subst("$BUILD_DIR")) / "films"
output.mkdir(parents=True, exist_ok=True)
lines = ["#pragma once"]
for name, file, width, duration in [("crow", "dr-crow.gif", 96, 10000),
                                    ("beef", "dr-beef.gif", 96, 10000),
                                    ("intro", "telethon.gif", 128, 24000)]:
    gif = (assets / file).read_bytes()
    if gif[:3] != b"GIF" or gif[6:10] != bytes([width, 0, 96, 0]):
        raise ValueError(f"Expected {width}x96 GIF for {file}")
    lines.append(f"const uint8_t {name}Bytes[] PROGMEM = {{")
    for offset in range(0, len(gif), 32):
        lines.append(",".join(map(str, gif[offset:offset + 32])) + ",")
    lines.append("};")
    lines.append(f"constexpr films::Film {name}Film{{{name}Bytes, sizeof({name}Bytes), {duration}, {(128-width)//2}}};")
header = output / "film_assets.h"
source = "\n".join(lines)
if not header.exists() or header.read_text() != source:
    header.write_text(source)
env.Append(CPPPATH=[str(output)])
