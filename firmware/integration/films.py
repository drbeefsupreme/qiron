from bisect import bisect_right
from pathlib import Path
import sys
import subprocess
import tempfile

from PIL import Image, ImageSequence

firmware = Path(__file__).resolve().parents[1]
build = firmware / ".pio/build/teensy41/films"
library = firmware / ".pio/libdeps/teensy41/AnimatedGIF/src"
with tempfile.TemporaryDirectory() as directory:
    renderer = Path(directory) / "render"
    smartmatrix = firmware / ".pio/libdeps/teensy41/SmartMatrix/src"
    subprocess.run(["cc", "-O2", "-c", *sorted(smartmatrix.glob("Font_*.c"))], cwd=directory, check=True)
    subprocess.run(["c++", "-O2", "-std=c++17", "-D__LINUX__", "-DreadFLASH=readMem", "-I", firmware / "src",
                    "-I", library, "-I", build, "-I", smartmatrix, firmware / "integration/films.cpp",
                    library / "AnimatedGIF.cpp", smartmatrix / "MatrixFont.cpp", smartmatrix / "Layer.cpp",
                    *sorted(Path(directory).glob("*.o")), "-o", renderer], check=True)
    def draw(ids, times, melt=0, hue=0):
        return subprocess.check_output([renderer, ids, str(melt), str(hue), *map(str, times)])

    names = ["telethon.gif", "dr-crow.gif", "dr-beef.gif", "peter-thiel.gif", "santa.gif"]
    for id, filename in enumerate(names, 2):
        duration = 24000 if id == 2 else 10000
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
        rgb = draw(str(id), samples)
        size = 128 * 96 * 3
        assert len(rgb) == size * len(samples)
        for i, ms in enumerate(samples):
            frame = bisect_right(starts, ms % elapsed) - 1
            assert rgb[i*size:(i+1)*size] == frames[frame], (filename, ms)
        print(f"{filename}: {len(frames)} frames, {elapsed} ms, all pixels matched")

    stack = "0,3,4,5,6"
    base = Image.new("RGB", (128,96), (14,22,38))
    for filename in names[1:]:
        with Image.open(firmware.parent / "priv/static" / filename) as image:
            portrait = image.convert("RGBA")
            base.paste(portrait,(16,0),portrait)
    assert draw(stack,[0]) == base.tobytes()
    assert draw("3,4",[0]) != draw("4,3",[0])
    assert draw("3,8,1",[0]) == draw("1",[0])
    assert draw("0,8,3",[0]) != draw("0,3,8",[0])
    assert draw("8,2",[0]) == draw("2",[0])
    text = draw("8",[500])
    post = draw("8",[500],100,0)
    original = Image.frombytes("RGB",(128,96),text)
    dripping = Image.frombytes("RGB",(128,96),post)
    assert original.getbbox() and dripping.getbbox()[3] > original.getbbox()[3]
    for x in range(128):
        old = [y for y in range(96) if original.getpixel((x,y)) != (0,0,0)]
        new = [y for y in range(96) if dripping.getpixel((x,y)) != (0,0,0)]
        if new:
            delta = new[0] - old[0]
            assert delta >= 0 and new == [y+delta for y in old if y+delta < 96]
    assert draw("8",[500],0,100) != text
    assert draw(stack,[500],100,90) != draw(stack,[500],100,0)
    def image(ids, ms):
        return Image.frombytes("RGB",(128,96),draw(ids,[ms]))
    a, b = image("7",0), image("7",40)
    assert a.getbbox() and a.getbbox()[1] >= 88
    assert a.crop((0,88,127,96)).tobytes() == b.crop((1,88,128,96)).tobytes()
    assert image("1,7",0).crop((0,0,128,88)).tobytes() == image("1",0).crop((0,0,128,88)).tobytes()
    print("Verified transparent portrait stacks, text order, chart, ticker motion, whole-frame melt and hue")
    if "--bench" in sys.argv:
        for ids, melt, hue in [("3",0,0),("0,1,2,3,4,5,6,7,8,9,10,11,12,13",100,100)]:
            print(ids, draw(ids,["bench"],melt,hue).decode().strip())
