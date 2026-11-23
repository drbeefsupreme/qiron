from bisect import bisect_right
from pathlib import Path
import sys
import os
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

    names = ["telethon.gif", "dr-crow.gif", "dr-beef.gif", "peter-thiel.gif", "santa.gif", "solid-snake.gif"]
    for id, filename in zip([2,3,4,5,6,18], names):
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

    stack = "0,3,4,5,6,18"
    base = Image.new("RGB", (128,96), (14,22,38))
    for filename in names[1:]:
        with Image.open(firmware.parent / "priv/static" / filename) as image:
            portrait = image.convert("RGBA")
            base.paste(portrait,(16,0),portrait)
    assert draw(stack,[0]) == base.tobytes()
    with Image.open(firmware.parent / "priv/static/solid-snake.gif") as source:
        snake = source.convert("RGBA")
        assert snake.size == (96,96) and snake.getchannel("A").getextrema() == (0,255)
        for below in ["0,8","3,8"]:
            base = Image.frombytes("RGB",(128,96),draw(below,[0]))
            base.paste(snake,(16,0),snake)
            assert draw(below+",18",[0]) == base.tobytes()
    assert draw("18,8",[0]) != draw("8,18",[0])
    assert draw("3,4",[0]) != draw("4,3",[0])
    graph = Image.frombytes("RGB",(128,96),draw("1",[0]))
    expected = Image.frombytes("RGB",(128,96),draw("3,8",[0]))
    expected.paste(graph,(0,0),graph.convert("L").point(lambda x: 255 if x else 0))
    assert expected.tobytes() == draw("3,8,1",[0]) and expected.tobytes() != graph.tobytes()
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
    chart = image("1",0)
    banner = image("1,14",0)
    assert banner.crop((0,9,128,96)).tobytes() == chart.crop((0,9,128,96)).tobytes()
    assert {color for _, color in banner.crop((0,0,128,9)).getcolors()} == {(8,13,28),(255,240,168)}
    assert image("14,1",0).tobytes() == banner.tobytes()
    assert image("14",0).crop((1,0,128,9)).tobytes() == image("14",50).crop((0,0,127,9)).tobytes()
    assert image("14",0).tobytes() == image("14",50*(13*5+18)).tobytes()
    assert chart.getbbox() == (3,29,125,74)
    price = image("15",0)
    assert price.getbbox()[0] >= 3 and price.getbbox()[3] < 23
    assert (254,68,85) in {color for _,color in price.crop((0,0,128,9)).getcolors()}
    assert (248,239,201) in {color for _,color in price.crop((0,10,128,23)).getcolors()}
    interest = image("16",0)
    assert interest.crop((0,88,128,96)).tobytes() == image("7",0).crop((0,88,128,96)).tobytes()
    for long_c, short_c, long_label, short_label in [(5000000,250000000,"50K","2.5M"),
        (0,18446744073709551615,"0","184.4Q"), (99999,101,"999.99","1.01"),
        (99999999,100000000000,"999.9K","1B")]:
        frame = subprocess.check_output([renderer,"16","0","0","0"],env={**os.environ,
            "RENDER_LONG_CENTS":str(long_c),"RENDER_SHORT_CENTS":str(short_c)})
        labels = draw("16",["reference","LONG "+long_label,"SHORT "+short_label])
        assert frame[:128*88*3] == labels
    phone = "TELETHON CALL-IN"
    band = (0,87,128,96)
    call = image("17",0)
    ref = Image.frombytes("RGB",(128,96),draw("17",["caption",phone]))
    first = (0,87,len(phone)*5+18,96)
    assert call.crop(first).tobytes() == ref.crop(first).tobytes()
    custom = "ON AIR ~"
    output = subprocess.check_output([renderer,"17","0","0","0"],env={**os.environ,"RENDER_CALLIN":custom})
    custom_ref = draw("17",["caption",custom])
    strip = (0,87,len(custom)*5+18,96)
    assert Image.frombytes("RGB",(128,96),output).crop(strip).tobytes() == Image.frombytes("RGB",(128,96),custom_ref).crop(strip).tobytes()
    assert call.crop((1,87,128,96)).tobytes() == image("17",50).crop((0,87,127,96)).tobytes()
    assert call.tobytes() == image("17",50*(len(phone)*5+18)).tobytes()
    for ticker in ("7","16"):
        assert image("3,"+ticker+",17",0).crop(band).tobytes() == call.crop(band).tobytes()
        assert image("3,17,"+ticker,0).crop(band).tobytes() == image(ticker,0).crop(band).tobytes()
    assert image("3,17",0).crop((0,0,128,87)).tobytes() == image("3",0).crop((0,0,128,87)).tobytes()
    dense = ",".join(map(str,range(19)))
    assert image(dense,600).crop((0,0,128,9)).tobytes() == image("14,15,18",600).crop((0,0,128,9)).tobytes()
    print("Verified portrait stacks, text order, chart, ticker, join banner clipping and wrap, melt and hue")
    def check_fade(events, start=0):
        script = []
        expected = bytearray()
        for elapsed, cmd, values in events:
            now = (start + elapsed) & 0xffffffff
            if cmd == "s":
                script.append(f"s {now} {values[0]} {values[1]}")
            else:
                script.append(f"r {now}")
                expected.append(values is not None)
                if values is not None:
                    expected.extend(draw("8",[now],*values))
        actual = subprocess.check_output([renderer,"8","0","0","fade"],input="\n".join(script).encode())
        assert actual == expected

    moves = [
        (0,"r",None), (0,"s",(100,0)), (0,"r",(0,0)), (3750,"r",(25,0)),
        (7500,"s",(100,80)), (7500,"r",(50,0)), (11250,"r",(75,20)),
        (11250,"s",(0,80)), (11250,"r",(75,20)), (15000,"r",(56.25,40)),
        (15000,"s",(0,80)), (18750,"r",(37.5,60)), (22500,"r",(18.75,80)),
        (26250,"r",(0,80)), (27000,"s",(0,0)), (34500,"r",(0,40)),
        (42000,"r",(0,0)), (42033,"r",None)]
    check_fade(moves)
    check_fade(moves, 0xffffe000)
    print("Verified independent 15-second melt and hue ramps, continuous retargeting, idle restoration and clock wrap")
    if "--bench" in sys.argv:
        for ids, melt, hue in [("3",0,0),("0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18",100,100)]:
            print(ids, draw(ids,["bench"],melt,hue).decode().strip())
