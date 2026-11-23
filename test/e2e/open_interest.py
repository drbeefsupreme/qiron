import struct
import time

from playwright.sync_api import sync_playwright

from show import show


def rehearse(url, password, panel, playwright):
    booth = playwright.request.new_context(base_url=url, http_credentials={"username": "beef", "password": password})
    phone = playwright.request.new_context(base_url=url)

    def set_booth(data):
        assert booth.post("/api/operator", headers={"x-qiron": "1"}, data=data).ok

    def trade(side):
        assert phone.post("/api/trade", headers={"x-qiron": "1"}, data={"side": side, "leverage": 50}).ok

    def load(data, fields):
        start = len(panel.frames)
        set_booth(data)
        deadline = time.monotonic() + 10
        while not (draft := booth.get("/api/panel").json())["ready"]:
            assert time.monotonic() < deadline
            time.sleep(0.05)
        sent = [payload[0] for method, payload in panel.frames[start:] if method == 41 and payload[0] in [38, 43, 49]]
        assert set(sent) == set(fields)
        assert sent.count(49) == fields.count(49)
        set_booth({"take": draft["revision"]})
        panel.expect(42, b"", start)

    panel.expect(42, b"")
    set_booth({"hold": True})
    set_booth({"mark": 100})
    load({"preset": "blood"}, [38, 43, 49])
    panel.expect(41, bytes([44, 0, 0, 1, 15, 16]))
    panel.expect(41, bytes([49]) + struct.pack("<IQQ", 10_000, 0, 0))
    load({"widgets": ["price"]}, [49])
    load({"widgets": ["chart"]}, [38])
    load({"widgets": ["ticker"]}, [43])
    load({"widgets": ["interest"]}, [43, 49])
    load({"widgets": ["ticker", "price", "interest"]}, [43, 49])
    for _ in range(3):
        set_booth({"mark": 1})
        trade("up")
        set_booth({"mark": 10_000})
        stage = booth.get("/api/stage").json()
        cents = int(stage["long_oi_cents"])
        assert stage["short_oi_cents"] == 0
        if cents > 2 ** 53 - 1:
            assert isinstance(stage["long_oi_cents"], str)
        panel.expect(49, struct.pack("<IQQ", 1_000_000, min(cents, 2 ** 64 - 1), 0))
        trade("flat")
    assert cents > 2 ** 64 - 1
    assert booth.get("/api/panel").json()["long_oi_cents"] == 0


if __name__ == "__main__":
    with show() as (server, password, device), sync_playwright() as playwright:
        rehearse(server, password, device, playwright)
    print("Open interest HTTP/USB rehearsal passed.")
