import os
import select
import struct
import subprocess
import sys
import time
from pathlib import Path


def read_bytes(stream, size):
    end = time.monotonic() + 3
    result = bytearray()
    while len(result) < size:
        if not select.select([stream], [], [], max(0, end - time.monotonic()))[0]:
            raise SystemExit("Timed out waiting for the Teensy. Check the firmware and USB cable.")
        chunk = os.read(stream.fileno(), size - len(result))
        if not chunk:
            raise SystemExit("USB bridge closed. Check the device path, permissions and other controllers.")
        result.extend(chunk)
    return bytes(result)


device = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("QYRON_DEVICE", "/dev/ttyACM0")
bridge = Path(__file__).resolve().parents[2] / "priv" / "serial.py"
with subprocess.Popen([sys.executable, bridge, device], stdin=subprocess.PIPE, stdout=subprocess.PIPE) as usb:
    try:
        if read_bytes(usb.stdout, 1) != b"R":
            raise SystemExit("USB bridge did not open the device.")
        for method, payload in [(40, bytes([0])), (41, bytes([12, 64])), (41, bytes([6, 0])),
                                (41, bytes([0]) + struct.pack("<i", -1) + b"QYRON PI TEST"), (42, b"")]:
            usb.stdin.write(struct.pack("<BBH", 254, method, len(payload)) + payload)
            usb.stdin.flush()
            if read_bytes(usb.stdout, 2) != bytes([254, 0]):
                raise SystemExit(f"Teensy rejected command {method}.")
    finally:
        usb.stdin.close()
    print("Teensy acknowledged the prepared cue and TAKE. Look for QYRON PI TEST on the middle row.")
