import contextlib
import os
import pty
import secrets
import select
import signal
import socket
import struct
import subprocess
import tempfile
import threading
import time
import tty
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


class Panel:
    def __init__(self, device):
        self.device = device
        self.thread = None
        self.frames = []
        self.changed = threading.Condition()
        self.stopped = threading.Event()

    def attach(self):
        self.fd, self.slave = pty.openpty()
        tty.setraw(self.slave)
        self.device.symlink_to(os.ttyname(self.slave))
        self.stopped.clear()
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def detach(self):
        if self.thread is None:
            return
        self.device.unlink()
        self.stopped.set()
        self.thread.join()
        os.close(self.fd)
        os.close(self.slave)
        self.thread = None

    def run(self):
        buffer = bytearray()
        while not self.stopped.is_set():
            if not select.select([self.fd], [], [], 0.1)[0]:
                continue
            buffer.extend(os.read(self.fd, 65536))
            while len(buffer) >= 4:
                prefix, method, length = struct.unpack_from("<BBH", buffer)
                if prefix != 254:
                    raise ValueError(f"Unexpected command prefix {prefix}")
                if len(buffer) < length + 4:
                    break
                payload = bytes(buffer[4 : 4 + length])
                del buffer[: 4 + length]
                os.write(self.fd, b"\xfe")
                time.sleep(0.002)
                os.write(self.fd, b"\x00")
                with self.changed:
                    self.frames.append((method, payload))
                    self.changed.notify_all()

    def expect(self, method, payload, after=0):
        with self.changed:
            assert self.changed.wait_for(
                lambda: (method, payload) in self.frames[after:], timeout=10
            ), f"Missing method {method} with {len(payload)} payload bytes"


@contextlib.contextmanager
def show():
    with tempfile.TemporaryDirectory() as directory:
        panel = Panel(Path(directory) / "tty")
        panel.attach()
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        password = secrets.token_hex(16)
        env = dict(os.environ, MIX_ENV="dev", QYRON_DEVICE=str(panel.device),
                   PORT=str(port), SHOW_FILE=f"{directory}/show.etf",
                   OPERATOR_PASSWORD=password)
        server = subprocess.Popen(["mix", "run", "--no-halt"], env=env,
                                  cwd=Path(__file__).resolve().parents[2],
                                  start_new_session=True)
        try:
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                if server.poll() is not None:
                    raise RuntimeError("Qiron exited during startup")
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                        break
                except ConnectionRefusedError:
                    time.sleep(0.1)
            else:
                raise TimeoutError("Qiron did not listen")
            yield f"http://127.0.0.1:{port}", password, panel
        finally:
            if server.poll() is None:
                os.killpg(server.pid, signal.SIGTERM)
                server.wait(timeout=15)
            panel.detach()


def rehearse(browser, url, password, panel):
    booth = browser.new_context(http_credentials={"username": "beef", "password": password})
    operator = booth.new_page()
    operator.goto(url + "/operator")
    operator.get_by_role("button", name="Hold drift").click()
    expect(operator.locator("#marketmeta")).to_contain_text("Drift held")

    def set_price(value):
        operator.locator("#price").fill(value)
        operator.get_by_role("button", name="Set price").click()
        expect(operator.locator("#mark")).to_have_text(value + ".00")

    set_price("100")
    audience = [browser.new_page(viewport={"width": 390, "height": 844}) for _ in range(2)]
    for phone, side in zip(audience, ("up", "down")):
        phone.goto(url)
        expect(phone.locator("#balance")).to_have_text("50,000.00")
        if side == "up":
            phone.locator("#leverage").press("End")
            expect(phone.locator("#multiplier")).to_have_text("50×")
        phone.locator("#" + side).click()
        expect(phone.locator("#side")).to_contain_text(side.upper())
    set_price("110")
    stage = browser.new_page()
    stage.goto(url + "/stage")
    expect(stage.locator("#l2")).to_contain_text("UP  1    DOWN  1", use_inner_text=False)
    panel.expect(0, struct.pack("<i", -1) + b"CROW BLOOD  110.00")
    for phone, value in zip(audience, ("300,000.00", "45,000.00")):
        expect(phone.locator("#balance")).to_have_text(value)
        phone.locator("#close").click()
        expect(phone.locator("#side")).to_contain_text("NONE")
        phone.reload()
        expect(phone.locator("#balance")).to_have_text(value)

    long = audience[0]
    long.locator("#leverage").press("End")
    long.locator("#up").click()
    expect(long.locator("#side")).to_contain_text("50×")
    set_price("107")
    expect(long.locator("#balance")).to_have_text("0.00")
    long.reload()
    expect(long.locator("#cooldown")).to_contain_text("Liquidated")
    expect(long.locator("#claim")).to_be_disabled()
    expect(long.locator("#down")).to_be_disabled()
    assert long.request.post(url + "/api/refill", headers={"x-qiron": "1"}, data={}).status == 409

    cue = "Q" + "ab" * 16383
    layer = operator.locator("#layer4")
    layer.fill(cue)
    layer.locator("xpath=ancestor::form").get_by_role("button", name="Save", exact=True).click()
    panel.expect(3, struct.pack("<i", -1) + cue.encode())
    expect(stage.locator("#l4")).to_have_text(cue)
    expect(stage.locator("#mark")).to_be_in_viewport()
    start = len(panel.frames)
    layer.fill("")
    layer.locator("xpath=ancestor::form").get_by_role("button", name="Save", exact=True).click()
    panel.expect(3, struct.pack("<i", -1) + b"BLOOD", start)
    expect(stage.locator("#l4")).to_have_text("BLOOD")
    for field, button, value, method in [
        ("#speed6", "Set speed", 85, 11), ("#brightness", "Set brightness", 73, 12)
    ]:
        control = operator.locator(field)
        start = len(panel.frames)
        control.fill(str(value))
        control.locator("xpath=ancestor::form").get_by_role("button", name=button).click()
        panel.expect(method, bytes([value]), start)
    public = audience[0].request
    assert public.get(url + "/api/panel").status == 401
    assert public.post(url + "/api/operator", headers={"x-qiron": "1"},
                       data={"action": "gifJ"}).status == 401
    assert booth.request.post(url + "/api/operator", data={"action": "gifJ"}).status == 403
    assert booth.request.post(url + "/api/operator", headers={"x-qiron": "1"},
                              data={"layer": 6, "text": cue + "x"}).status == 422
    start = len(panel.frames)
    operator.locator("#action").select_option("nextGif")
    operator.locator("#run-action").click()
    panel.expect(21, b"", start)

    panel.detach()
    expect(operator.locator("#panel-status")).to_have_text("USB disconnected", timeout=10000)
    operator.locator("#run-action").click()
    expect(operator.locator("#error")).to_contain_text("disconnected")
    offline = operator.locator("#layer6")
    offline.fill(cue)
    offline.locator("xpath=ancestor::form").get_by_role("button", name="Save", exact=True).click()
    expect(operator.locator("#receipt")).to_contain_text("Layer 6 saved")
    reconnected = len(panel.frames)
    panel.attach()
    panel.expect(5, struct.pack("<i", -1) + cue.encode(), reconnected)
    expect(operator.locator("#panel-status")).to_have_text("USB connected")
    assert (21, b"") not in panel.frames[reconnected:]


if __name__ == "__main__":
    with show() as (url, password, panel), sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=os.getenv("CHROMIUM"))
        rehearse(browser, url, password, panel)
        browser.close()
    print("Browser rehearsal passed with two phones, booth, stage and USB simulator.")
