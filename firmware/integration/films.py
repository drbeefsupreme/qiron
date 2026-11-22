from bisect import bisect_right
from pathlib import Path
import subprocess
import tempfile

from PIL import Image, ImageSequence

firmware = Path(__file__).resolve().parents[1]
build = firmware / ".pio/build/teensy41/films"
library = firmware / ".pio/libdeps/teensy41/AnimatedGIF/src"
with tempfile.TemporaryDirectory() as directory:
    renderer = Path(directory) / "render"
    subprocess.run(["c++", "-std=c++17", "-D__LINUX__", "-DreadFLASH=readMem", "-I", firmware / "src",
                    "-I", library, "-I", build, firmware / "integration/films.cpp",
                    library / "AnimatedGIF.cpp", "-o", renderer], check=True)
    for name, filename, duration in [("crow", "dr-crow.gif", 10000), ("beef", "dr-beef.gif", 10000),
                                     ("intro", "telethon.gif", 24000)]:
        frames = []
        starts = []
        elapsed = 0
        with Image.open(firmware.parent / f"priv/static/{filename}") as image:
            for frame in ImageSequence.Iterator(image):
                panel = Image.new("RGB", (128, 96))
                portrait = frame.convert("RGBA")
                panel.paste(portrait, ((128 - frame.width) // 2, 0), portrait)
                frames.append(panel.tobytes())
                starts.append(elapsed)
                elapsed += frame.info["duration"]
        assert elapsed == duration
        samples = sorted(set(starts + [start - 1 for start in starts[1:]] + [duration-1, duration, duration+7231, duration*3+5299]))
        rgb = subprocess.check_output([renderer, name, *map(str, samples)])
        size = 128 * 96 * 3
        assert len(rgb) == size * len(samples)
        for i, ms in enumerate(samples):
            frame = bisect_right(starts, ms % elapsed) - 1
            assert rgb[i*size:(i+1)*size] == frames[frame], (name, ms)
        print(f"{name}: {len(frames)} frames, {elapsed} ms, all pixels matched")
