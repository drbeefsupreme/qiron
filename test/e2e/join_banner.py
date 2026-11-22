import os
import secrets
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from playwright.sync_api import sync_playwright

from show import show


def rehearse(url, password, panel, playwright, banner):
    guest = playwright.request.new_context(base_url=url)
    booth = playwright.request.new_context(base_url=url, http_credentials={"username": "beef", "password": password})

    def draft():
        return booth.get("/api/panel").json()

    def post(payload):
        return booth.post("/api/operator", headers={"x-qiron": "1"}, data=payload).status

    def stage():
        return guest.get("/api/stage").json()

    def take():
        until = time.monotonic() + 10
        while not draft()["ready"]:
            assert time.monotonic() < until
            time.sleep(0.05)
        assert post({"take": draft()["revision"]}) == 200

    payload = bytes([48]) + banner.encode()
    panel.expect(42, b"")
    assert "join_banner" not in stage() and "join_banner" not in draft()
    assert not any(method == 48 or method == 41 and data[:1] == bytes([48]) for method, data in panel.frames)
    assert os.environ["QYRON_JOIN_PASSWORD"] not in guest.get("/api/stage").text()
    assert guest.get("/api/panel").status == 401
    assert post({"mode": "intro"}) == 200
    widgets = "join intro sd chart crow beef peter santa ticker line1 line2 line3 line4 line5 lineF".split()
    assert post({"widgets": widgets}) == 200
    panel.expect(41, payload)
    assert draft()["join_banner"] == banner and "join_banner" not in stage()
    take()
    assert stage()["join_banner"] == banner
    assert stage()["widgets"] == widgets
    assert "join_banner" not in guest.get("/api/me").json()
    time.sleep(0.7)
    assert panel.frames.count((41, payload)) == 1
    panel.detach()
    until = time.monotonic() + 10
    while draft()["status"] != "disconnected":
        assert time.monotonic() < until
        time.sleep(0.05)
    start = len(panel.frames)
    panel.attach()
    panel.expect(42, b"", start)
    assert (41, payload) in panel.frames[start:panel.frames.index((42, b""), start)]
    assert post({"widgets": ["intro"]}) == 200
    assert "join_banner" not in draft() and stage()["join_banner"] == banner
    take()
    assert "join_banner" not in stage()
    assert panel.frames[start:].count((41, payload)) == 1
    assert os.environ["QYRON_JOIN_PASSWORD"].encode() not in (panel.device.parent / "show.etf").read_bytes()


if __name__ == "__main__":
    pw = "mIx-" + secrets.token_hex(8)
    net = "demo-π"
    prefix = "TRADE BLOOD FUTURES ON YOUR PHONE: "
    suffix = f"   WI-FI: {net}   PASSWORD: {pw}"
    url = "chyron.local:4000/"
    url += "a" * (240 - len((prefix + url + suffix).encode()))
    with patch.dict(os.environ, QYRON_JOIN_URL=url, QYRON_JOIN_SSID=net, QYRON_JOIN_PASSWORD=pw):
        with show() as (server, password, panel), sync_playwright() as playwright:
            rehearse(server, password, panel, playwright, prefix + url + suffix)
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, QYRON_JOIN_URL=url + "x", MIX_ENV="dev", SHOW_FILE=tmp + "/show")
            failed = subprocess.run(["mix", "run", "--no-halt"], env=env, cwd=Path(__file__).resolve().parents[2],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
            assert failed.returncode != 0 and b"at most 240 bytes" in failed.stdout
            assert pw.encode() not in failed.stdout and net.encode() not in failed.stdout
    print("Join banner HTTP/USB rehearsal passed.")
