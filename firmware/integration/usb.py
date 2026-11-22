import os
from pathlib import Path
import signal
import struct
import subprocess
import tempfile
import tty

import serial
from simple_rpc import Interface

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
    port = os.ttyname(slave)
    with tempfile.TemporaryFile() as events:
        device = subprocess.Popen([binary], stdin=master, stdout=master, stderr=events)
        try:
            with Interface(port, wait=0) as legacy:
                assert len(legacy.device["methods"]) == 37
                assert legacy.device["size_t"] == "I"
                legacy.scrollingLayerF_start(TEXT, -1)
                legacy.scrollingLayer4_speed(200)
                legacy.setBrightness(16)
                legacy.gifH()
            with serial.Serial(port, timeout=2) as usb:
                command = frame(0, struct.pack("<i", -1) + TEXT)
                for i in range(0, len(command), 83):
                    usb.write(command[i:i+83])
                assert usb.read(2) == bytes([254, 0])
                for invalid in [frame(2, bytes(32772)), frame(1, bytes(5)), frame(200, b""), frame(6, b"")]:
                    usb.write(invalid)
                    assert usb.read(2) == bytes([254, 1])
                usb.write(frame(36, b"") + frame(6, bytes([255])) + frame(12, bytes([32])))
                assert usb.read(6) == bytes([254, 0]) * 3
        finally:
            os.close(slave)
            os.close(master)
            device.terminate()
            device.wait(timeout=2)
        events.seek(0)
        assert events.read().splitlines() == [b"start 5 -1 " + TEXT, b"speed 3 200", b"brightness 16", b"effect 35", b"live 0 -1 " + TEXT, b"liveEffect 36", b"speed 0 255", b"brightness 32"]
print("Legacy Python client and framed USB protocol passed over a pseudo-terminal")
