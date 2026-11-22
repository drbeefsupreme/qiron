import os
from pathlib import Path
import signal
import struct
import subprocess
import tempfile
import tty

ROOT = Path(__file__).resolve().parents[1]
TEXT = b"abcdefg" * 4681
assert len(TEXT) == 32767


def frame(method, payload):
    return struct.pack("<BBH", 254, method, len(payload)) + payload


signal.alarm(30)
with tempfile.TemporaryDirectory() as work:
    binary = Path(work) / "device"
    subprocess.run(["c++", "-std=c++17", "-Isrc", "src/protocol.cpp", "integration/device.cpp", "-o", binary], cwd=ROOT, check=True)
    master, slave = os.openpty()
    tty.setraw(slave)
    with tempfile.TemporaryFile() as events:
        device = subprocess.Popen([binary], stdin=master, stdout=master, stderr=events)
        try:
            with os.fdopen(os.dup(slave), "r+b", buffering=0) as usb:
                usb.write(bytes([255, 13, 35, 36]))
                command = frame(0, struct.pack("<i", -1) + TEXT)
                for i in range(0, len(command), 83):
                    usb.write(command[i:i+83])
                assert usb.read(1) + usb.read(1) == bytes([254, 0])
                for invalid in [frame(2, bytes(32772)), frame(1, bytes(5)), frame(200, b""), frame(6, b"")]:
                    usb.write(invalid)
                    assert usb.read(1) + usb.read(1) == bytes([254, 1])
                usb.write(frame(36, b"") + frame(6, bytes([255])) + frame(12, bytes([32])))
                assert bytes(usb.read(1)[0] for _ in range(6)) == bytes([254, 0]) * 3
                def send(method, data, accepted=True):
                    usb.write(frame(method, data))
                    assert usb.read(1) + usb.read(1) == bytes([254, 0 if accepted else 1])

                chart = struct.pack("<7I", 12300, 92, 4, 10100, 12500, 9900, 12300)
                for mode in (0, 1, 2, 3, 4):
                    send(37, bytes([mode]))
                send(37, bytes([5]), False)
                for mode in (3, 4):
                    send(40, bytes([mode]))
                    send(41, bytes([12, 100]))
                    send(42, b"")
                send(38, chart)
                send(38, chart[:-1], False)
                send(38, struct.pack("<7I", 10000, 0, 0, 10000, 9000, 8500, 9200), False)
                send(39, b"/gifs/../caw.gif", False)
                send(39, b"/gifs/joker/missing.gif", False)
                send(40, bytes([0]))
                send(41, bytes([39]) + b"/gifs/joker/missing.gif", False)
                send(42, b"", False)
                send(40, bytes([0]))
                send(41, bytes([0]) + struct.pack("<i", -1) + TEXT)
                send(40, bytes([1]))
                send(42, b"", False)
                send(40, bytes([1]))
                send(41, bytes([38]) + chart)
                send(38, struct.pack("<7I", 10400, 1, 4, 10100, 11000, 10000, 10400))
                send(42, b"")
                send(42, b"", False)
                send(40, bytes([0]))
                for field in [bytes([12,90]), bytes([25]), bytes([39]) + b"/gifs/joker/caw.gif",
                              bytes([22]), bytes([17]), bytes([6,42]), bytes([0]) + struct.pack("<i", -1) + b"SHOW"]:
                    send(41, field)
                send(42, b"")
                for fields in ([22, 26], [26, 21], [26, 21]):
                    send(40, bytes([0]))
                    for field in fields:
                        send(41, bytes([field]))
                    send(42, b"")
                send(44, bytes([0,0,14]), False)
                send(48, b"X"*240)
                send(48, "é📺".encode())
                for bad in [b"", b"X"*241, b"A\0B", b"\xc0\x80", b"\xed\xa0\x80", b"\xf4\x90\x80\x80", b"\xe2\x82"]:
                    send(48, bad, False)
                send(40, bytes([0]))
                send(41, bytes([48]) + b"SAMPLE", False)
                send(40, bytes([1]))
                send(41, bytes([44,0,0,1,14]))
                send(41, bytes([38]) + chart)
                send(41, bytes([48]) + b"SAMPLE")
                send(42, b"")
                quotes = struct.pack("<6I", 0, 5, 48, 7816, 255, 4294967295)
                send(43, quotes)
                send(43, quotes[:-1], False)
                send(43, quotes + b"x", False)
                send(44, bytes([0, 100, *range(15)]))
                for layout in ([0], [0, 0, 15], [0, 0, 5, 5], [101, 0], [0, 101],
                               [0, 0, *range(16)]):
                    send(44, bytes(layout), False)
                send(45, bytes([101, 0]), False)
                send(45, bytes([0, 101]), False)
                send(45, bytes([0]), False)
                for layout, field in [([8], [39, *b"/gifs/joker/caw.gif"]), ([0], [38, *chart]),
                                      ([9], [0, *bytes(5)]), ([9], [8, 42]), ([3], [43, *quotes]),
                                      ([0], [45, 1, 2]), ([0], [44, 3, 4])]:
                    send(40, bytes([1]))
                    send(41, bytes([44, 0, 0, *layout]))
                    send(41, bytes(field), False)
                    send(42, b"", False)
                for widget in (1, 7, 14):
                    send(40, bytes([0]))
                    send(41, bytes([44, 0, 0, widget]))
                    send(42, b"", False)
                send(40, bytes([1]))
                send(41, bytes([44, 0, 100]))
                send(42, b"")
                send(40, bytes([4]))
                send(41, bytes([44, 10, 20, 0, 5, 6, 9, 1, 7]))
                send(41, bytes([39]) + b"/gifs/joker/caw.gif")
                send(41, bytes([38]) + chart)
                send(41, bytes([43]) + quotes)
                send(41, bytes([7, 42]))
                send(41, bytes([1]) + struct.pack("<i", -1) + b"SCROLL")
                send(43, bytes(24))
                send(45, bytes([100, 0]))
                for command, payload in [(46, bytes([2,1])), (46, bytes([3,0,0,0,0])), (47, b""), (47, bytes([1]))]:
                    send(command, payload, False)
                send(46, struct.pack("<BI",1,0x87654321))
                send(47, bytes([60]))
                send(46, struct.pack("<BI",2,0))
                send(47, bytes([5]))
                send(47, bytes([0]))
                send(42, b"")
                for method, payload in [(46, struct.pack("<BI",2,18)), (47, bytes([5]))]:
                    send(40, bytes([0]))
                    send(41, bytes([method]) + payload, False)
                    send(42, b"", False)
        finally:
            os.close(slave)
            os.close(master)
            device.terminate()
            device.wait(timeout=2)
        events.seek(0)
        assert events.read().splitlines() == [
            b"start 0 -1 " + TEXT, b"effect 36", b"speed 0 255", b"brightness 32",
            b"mode 0", b"mode 1", b"mode 2", b"mode 3", b"mode 4",
            b"beginTake", b"mode 3", b"brightness 100", b"endTake",
            b"beginTake", b"mode 4", b"brightness 100", b"endTake", b"chart 12300 92 4 1 12300",
            b"chart 10400 1 4 1 10400", b"beginTake", b"mode 1", b"chart 12300 92 4 1 12300", b"endTake",
            b"prepare preset 0", b"beginTake", b"mode 0", b"source 0 /gifs/joker/caw.gif 1",
            b"speed 0 42", b"start 0 -1 SHOW", b"effect 17", b"brightness 90", b"endTake",
            b"beginTake", b"mode 0", b"source 1  1", b"endTake",
            b"prepare preset 1", b"beginTake", b"mode 0", b"source 1  0", b"effect 21", b"endTake",
            b"prepare preset 1", b"beginTake", b"mode 0", b"source 1  0", b"effect 21", b"endTake",
            b"join 240", b"join 2", b"beginTake", b"mode 1", b"stack 0 0 1 14", b"chart 12300 92 4 1 12300", b"join 6", b"endTake",
            b"quotes 0 5 48 7816 255 4294967295", b"stack 0 100 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14",
            b"beginTake", b"mode 1", b"stack 0 100", b"endTake",
            b"quotes 0 0 0 0 0 0", b"fx 100 0", b"burst 1 2271560481", b"splice 60", b"burst 2 0", b"splice 5", b"splice 0", b"beginTake", b"mode 4",
            b"stack 10 20 0 5 6 9 1 7", b"source -1 /gifs/joker/caw.gif 0",
            b"chart 12300 92 4 1 12300", b"quotes 0 5 48 7816 255 4294967295",
            b"speed 1 42", b"start 1 -1 SCROLL", b"endTake"
        ]
print("Framed USB protocol passed over a pseudo-terminal")
