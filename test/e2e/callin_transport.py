import os
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from playwright.sync_api import sync_playwright

from show import show


def rehearse(url, password, device, playwright, banner):
    operator = playwright.request.new_context(base_url=url, http_credentials={"username": "beef", "password": password})
    public = playwright.request.new_context(base_url=url)

    def stage():
        return public.get("/api/stage").json()

    def draft():
        return operator.get("/api/panel").json()

    def post(data):
        assert operator.post("/api/operator", data=data, headers={"x-qiron": "1"}).ok

    def take():
        until = time.monotonic() + 10
        while not (scene := draft())["ready"]:
            assert time.monotonic() < until
            time.sleep(0.05)
        post({"take": scene["revision"]})

    field = bytes([50]) + banner.encode("ascii")
    device.expect(42, b"")
    assert "callin_banner" not in stage() and "callin_banner" not in draft()
    assert not any(method == 41 and payload.startswith(bytes([50])) for method, payload in device.frames)
    post({"widgets": ["callin"]})
    device.expect(41, field)
    assert draft()["callin_banner"] == banner and "callin_banner" not in stage()
    take()
    assert stage()["callin_banner"] == banner
    device.detach()
    until = time.monotonic() + 10
    while draft()["status"] != "disconnected":
        assert time.monotonic() < until
        time.sleep(0.05)
    after = len(device.frames)
    device.attach()
    device.expect(42, b"", after)
    assert (41, field) in device.frames[after:device.frames.index((42, b""), after)]
    post({"widgets": []})
    assert "callin_banner" not in draft() and stage()["callin_banner"] == banner
    take()
    assert "callin_banner" not in stage()
    assert device.frames.count((41, field)) == 2
    assert banner.encode() not in (device.device.parent / "show.etf").read_bytes()


if __name__ == "__main__":
    for number, expected in [("   ", "TELETHON CALL-IN"), (" 555-0100 ", "CALL 555-0100"), ("A" * 115, "CALL " + "A" * 115)]:
        with patch.dict(os.environ, QYRON_CALLIN_NUMBER=number):
            with show() as (url, password, device), sync_playwright() as playwright:
                rehearse(url, password, device, playwright, expected)
    for invalid in ["555-0100" + "X" * 108, "555-0100\nCall", "é555-0100"]:
        with tempfile.TemporaryDirectory() as directory:
            env = dict(os.environ, QYRON_CALLIN_NUMBER=invalid, MIX_ENV="dev", SHOW_FILE=directory + "/show")
            result = subprocess.run(["mix", "run", "--no-halt"], env=env, cwd=Path(__file__).resolve().parents[2],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
            assert result.returncode != 0 and b"printable ASCII" in result.stdout and b"555-0100" not in result.stdout
    print("Call-in banner HTTP/USB rehearsal passed.")
