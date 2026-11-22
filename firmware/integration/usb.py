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
        finally:
            os.close(slave)
            os.close(master)
            device.terminate()
            device.wait(timeout=2)
        events.seek(0)
        assert events.read().splitlines() == [
            b"start 0 -1 " + TEXT, b"effect 36", b"speed 0 255", b"brightness 32"
        ]
print("Framed USB protocol passed over a pseudo-terminal")
