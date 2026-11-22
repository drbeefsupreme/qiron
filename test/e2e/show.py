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
                rejected = method == 41 and payload == b"\x27/gifs/joker/missing.gif"
                os.write(self.fd, bytes([int(rejected)]))
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
        password = secrets.token_hex(2)[:3]
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

    stage = browser.new_page()
    stage.goto(url + "/stage")
    expect(stage.locator("#stage-gif")).to_be_visible()
    request = booth.request

    def panel_state():
        return request.get(url + "/api/panel").json()

    def post(payload):
        return request.post(url + "/api/operator", headers={"x-qiron": "1"}, data=payload)

    def take(mode, online=True, keyboard=False):
        start = len(panel.frames)
        if keyboard:
            operator.locator("#layer4").focus()
            operator.keyboard.press("Alt+Enter")
        else:
            operator.locator("#take-live").click()
        expect(stage.locator("#stage-" + mode)).to_be_visible()
        if online:
            panel.expect(42, b"", start)
        assert request.get(url + "/api/stage").json()["mode"] == mode

    operator.locator("#volatility").press("End")
    expect(operator.locator("#volatility-label")).to_have_text("±5.00%")
    expect(operator.locator("#volatility")).to_be_enabled()
    assert panel_state()["volatility_bps"] == 500
    expect(operator.locator("#marketmeta")).to_contain_text("Drift held")

    set_price("100")
    start = len(panel.frames)
    operator.locator("#mode-blood").click()
    panel.expect(40, bytes([1]), start)
    expect(stage.locator("#stage-gif")).to_be_visible()
    assert (42, b"") not in panel.frames[start:]
    take("blood")
    audience = [browser.new_page(viewport={"width": 390, "height": 844}) for _ in range(2)]
    for phone, side in zip(audience, ("up", "down")):
        phone.goto(url)
        expect(phone.locator("#balance")).to_have_text("50,000.00")
        if side == "up":
            phone.locator("#leverage").press("End")
            expect(phone.locator("#multiplier")).to_have_text("50×")
            expect(phone.locator("#up-liq")).to_have_text("98.00")
            expect(phone.locator("#down-liq")).to_have_text("102.00")
        phone.locator("#" + side).click()
        expect(phone.locator("#side")).to_contain_text("Long" if side == "up" else "Short")
    set_price("110")
    expect(stage.locator("#bulls")).to_have_text("1")
    expect(stage.locator("#bears")).to_have_text("1")
    expect(stage.locator("#mark")).to_have_text("110.00")
    chart = request.get(url + "/api/stage").json()["candles"]
    assert chart[-1]["close"] == 11000
    with panel.changed:
        assert panel.changed.wait_for(lambda: any(
            method == 38 and data[:12] == struct.pack("<III", 11000, 1, 1)
            and len(data) >= 28 and struct.unpack("<I", data[-4:])[0] == 11000
            for method, data in panel.frames[start:]), timeout=10)
    for phone, value in zip(audience, ("300,000.00", "45,000.00")):
        expect(phone.locator("#balance")).to_have_text(value)
        phone.locator("#close").click()
        expect(phone.locator("#side")).to_contain_text("Flat")
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
    start = len(panel.frames)
    operator.locator("#mode-gif").click()
    operator.locator("#layer4").fill(cue)
    operator.locator("#speed4").fill("85")
    operator.locator("#brightness").fill("73")
    path = "/gifs/joker/hotline.gif"
    operator.locator("#gif-file").fill(path)
    panel.expect(41, bytes([3]) + struct.pack("<i", -1) + cue.encode(), start)
    panel.expect(41, bytes([9, 85]), start)
    panel.expect(41, bytes([12, 73]), start)
    panel.expect(41, bytes([39]) + path.encode(), start)
    expect(stage.locator("#stage-blood")).to_be_visible()
    expect(operator.locator("#take-live")).to_be_enabled()
    assert (42, b"") not in panel.frames[start:]
    assert post({"take": panel_state()["revision"] - 1}).status == 409
    take("gif", keyboard=True)
    expect(stage.locator("#l4")).to_have_text(cue)
    expect(stage.locator("#stage-file")).to_contain_text("hotline.gif")

    start = len(panel.frames)
    operator.locator("#gif-file").fill("/gifs/joker/missing.gif")
    panel.expect(41, bytes([39]) + b"/gifs/joker/missing.gif", start)
    expect(operator.locator("#take-live")).to_be_disabled()
    operator.keyboard.press("Alt+Enter")
    assert request.get(url + "/api/stage").json()["gif"]["file"] == path
    assert (42, b"") not in panel.frames[start:]
    operator.locator("#gif-file").fill(path)
    operator.locator("#mode-intro").click()
    panel.expect(40, bytes([2]), start)
    take("intro")
    expect(stage.locator("#stage-canvas")).to_be_visible()
    assert stage.locator("#stage-canvas").evaluate("canvas => [canvas.width, canvas.height]") == [128, 96]
    for mode, mode_id in [("crow", 3), ("beef", 4)]:
        start = len(panel.frames)
        operator.locator("#take-" + mode).click()
        panel.expect(40, bytes([mode_id]), start)
        panel.expect(42, b"", start)
        expect(stage.locator("#stage-" + mode)).to_be_visible()
        assert request.get(url + "/api/stage").json()["mode"] == mode
    public = audience[0].request
    assert public.get(url + "/api/panel").status == 401
    assert public.post(url + "/api/operator", headers={"x-qiron": "1"},
                       data={"action": "gifJ"}).status == 401
    assert booth.request.post(url + "/api/operator", data={"action": "gifJ"}).status == 403
    operator.locator("#mode-gif").click()
    expect(operator.locator("#layer4")).to_have_value(cue)
    assert booth.request.post(url + "/api/operator", headers={"x-qiron": "1"},
                              data={"layer": 6, "text": cue + "x"}).status == 422
    operator.locator("#action").select_option("hitShapes")
    start = len(panel.frames)
    expect(operator.locator("#take-live")).to_be_enabled()
    take("gif")
    panel.expect(41, bytes([16]))
    assert (16, b"") not in panel.frames[start:]

    panel.detach()
    expect(operator.locator("#panel-status")).to_contain_text("disconnected", ignore_case=True, timeout=10000)
    operator.locator("#mode-intro").click()
    take("intro", online=False)
    reconnected = len(panel.frames)
    panel.attach()
    panel.expect(40, bytes([2]), reconnected)
    panel.expect(42, b"", reconnected)
    expect(operator.locator("#panel-status")).to_contain_text("connected", ignore_case=True)
    assert (41, bytes([16])) not in panel.frames[reconnected:]

    operator.locator("#mode-gif").click()
    operator.locator("#gif-source").select_option("beef")
    operator.locator("#layer1").fill("OFFSHORE EXCHANGE")
    for widget in ["ticker", "peter", "santa"]:
        operator.locator("#widget-choice").select_option(widget)
        operator.locator("#add-widget").click()
    operator.get_by_role("button", name="Send backward · Peter Thiel", exact=True).click()
    operator.get_by_role("button", name="Remove · Santa Claus", exact=True).click()
    operator.locator("#melt").fill("72")
    operator.locator("#hue").fill("61")
    expect(operator.locator("#take-live")).to_be_enabled()
    prepared = panel_state()
    assert prepared["widgets"][0] == "beef" and prepared["widgets"][-2:] == ["peter", "ticker"]
    assert (prepared["melt"], prepared["hue"]) == (72, 61)
    start = len(panel.frames)
    operator.locator("#melt-live").click()
    panel.expect(45, bytes([72, 61]), start)
    assert request.get(url + "/api/stage").json()["mode"] == "intro"
    assert panel_state()["revision"] == prepared["revision"]
    operator.locator("#clear-live-fx").click()
    panel.expect(45, bytes([0, 0]), start)
    assert (42, b"") not in panel.frames[start:]
    operator.locator("#take-live").click()
    panel.expect(42, b"", start)
    expect(stage.locator("#stage-peter")).to_be_visible()
    expect(stage.locator("#stage-beef")).to_be_visible()
    scene = request.get(url + "/api/stage").json()
    assert scene["widgets"] == prepared["widgets"]
    assert [q["symbol"] for q in scene["tickers"]] == ["PISSCOIN", "PRICECOIN", "BONER", "FARTCOIN", "ROGUE", "CROW"]
    assert scene["melt"] == 72 and scene["hue"] == 61
    expect(stage.locator("#l1")).to_have_text("OFFSHORE EXCHANGE")
    operator.locator("#mode-blood").click()
    expect(operator.locator("#widget-stack li")).to_have_count(2)
    operator.locator("#mode-gif").click()
    expect(operator.locator("#gif-source")).to_have_value("beef")
    expect(operator.locator("#melt")).to_have_value("72")



if __name__ == "__main__":
    with show() as (url, password, panel), sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=os.getenv("CHROMIUM"))
        rehearse(browser, url, password, panel)
        browser.close()
    print("Browser rehearsal passed with two phones, booth, stage and USB simulator.")
