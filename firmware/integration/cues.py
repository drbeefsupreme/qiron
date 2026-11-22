from io import BytesIO
from pathlib import Path
import struct
import subprocess
import tempfile

from PIL import Image

firmware = Path(__file__).resolve().parents[1]
repo = firmware.parent
width, height = 128, 96
size = width * height * 3


def normal(green):
    return bytes(channel for y in range(height) for x in range(width) for channel in (x, green, y))


photos = []
packed = (repo / "art/splice-photos.rgb565").read_bytes()
for index, name in enumerate(["jfk", "911"]):
    data = bytearray()
    with Image.open(repo / f"priv/static/splice-{name}.png") as image:
        original = image.convert("RGB").tobytes()
    for i in range(width * height):
        color = struct.unpack_from("<H", packed, 2*(index*width*height + i))[0]
        red, green, blue = color>>11, (color>>5)&63, color&31
        data.extend((red*8+red//4, green*4+green//16, blue*8+blue//4))
        assert abs(data[-3]-original[3*i]) <= 8 and abs(data[-2]-original[3*i+1]) <= 4 and abs(data[-1]-original[3*i+2]) <= 8
    photos.append(bytes(data))
assert photos[0] != photos[1]

with tempfile.TemporaryDirectory() as work:
    renderer = Path(work) / "cues"
    subprocess.run(["c++","-O2","-std=c++17","-I",firmware / "src","-I",firmware / ".pio/build/teensy41/films",
                    firmware / "integration/cues.cpp","-o",renderer],check=True)

    def run(commands):
        stream = BytesIO(subprocess.check_output([renderer], input=commands.encode()))
        presented = []
        while flag := stream.read(1):
            if flag == b"\0":
                presented.append(None)
            else:
                assert flag == b"\1"
                frame = stream.read(size)
                assert len(frame) == size
                presented.append(frame)
        return presented

    result = run("""
splice 100 5
tick 5099
splice 5099 5
tick 5100
take 5101 40
tick 5134
tick 10100
splice 10101 0
tick 10133
tick 20000
""")
    assert result == [None, photos[0], normal(40), None, photos[1], normal(40), None]
    result = run("""
splice 0 5
tick 55000
tick 65500
tick 65533
tick 69999
tick 70000
tick 70033
splice 70534 60
tick 130533
tick 130534
tick 130567
splice 130568 0
splice 130568 5
tick 135568
""")
    assert result == [photos[0], normal(17), None, None, photos[1], normal(17), None, photos[0], normal(17), photos[0]]
    assert run("splice 0 5\ntick 5000\ntick 5033\nsplice 5100 60\ntick 65099\ntick 65100\ntick 65133\nsplice 65200 5\ntick 70200") == [
        photos[0], normal(17), None, photos[0], normal(17), photos[0]]
    assert run("splice 0 5\ntick 5025\ntick 5058\ntick 9999\ntick 10000") == [
        photos[0], normal(17), None, photos[1]]
    assert run("splice 4294967200 5\ntick 4903\ntick 4904\ntick 4937\n") == [None, photos[0], normal(17)]
    for kind in (1, 2):
        result = run(f"burst 0 {kind} 72\ntick 2000\ntick 9999\ntick 10000\ntick 10033\n")
        assert result[0] != normal(17) and result[1] is not None and result[2:] == [normal(17),None]
    result = run("""
splice 0 5
burst 1000 1 123
tick 3000
tick 5000
tick 5033
take 6000 29
burst 6500 2 1234
tick 8500
tick 10000
splice 10001 0
tick 10033
tick 16500
tick 16533
""")
    assert result[1] == photos[0] and result[2] == run("burst 1000 1 123\ntick 5033")[0]
    assert result[3] == run("take 0 29\nburst 0 1 123\ntick 5000")[1]
    assert result[4] == run("take 0 29\nburst 0 2 1234\ntick 2000")[1]
    assert result[5] == photos[1] and result[6] == run("take 0 29\nburst 6500 2 1234\ntick 10033")[1]
    assert result[7:] == [normal(29),None]
print("Cue playback matched both photos, all timing boundaries, retrigger, TAKE, expiry and static-frame restoration")
