import os
import struct
import time

from playwright.sync_api import expect, sync_playwright

from show import show


def rehearse(url, password, panel, playwright):
    request = playwright.request.new_context(base_url=url, http_credentials={"username": "beef", "password": password})

    def post(data):
        return request.post("/api/operator", headers={"x-qiron": "1"}, data=data).status

    def stage():
        return request.get("/api/stage").json()

    def status():
        return request.get("/api/panel").json()

    panel.expect(47, bytes([0]))
    panel.expect(42, b"")
    assert post({"mode": "blood"}) == 200
    draft = status()
    assert draft["dirty"]
    assert post({"screen_cue": "unknown"}) == 422
    assert post({"splice_seconds": 1}) == 422
    assert post({"screen_cue": "crack"}) == 200
    cue = stage()["screen_cue"]
    assert cue["kind"] == "crack"
    panel.expect(46, struct.pack("<BI", 1, cue["seed"]))
    assert post({"screen_cue": "stars"}) == 200
    stars = status()["screen_cue"]
    assert stars["kind"] == "stars"
    panel.expect(46, struct.pack("<BI", 2, stars["seed"]))
    panel.reject_methods.update([46, 47])
    assert post({"screen_cue": "crack"}) == 502
    assert post({"splice_seconds": 60}) == 502
    assert stage()["screen_cue"]["seed"] == stars["seed"]
    assert stage()["splice_seconds"] == 0
    panel.reject_methods.clear()
    assert post({"splice_seconds": 5}) == 200
    panel.expect(47, bytes([5]))
    time.sleep(0.35)
    assert post({"splice_seconds": 5}) == 200
    assert status()["splice_elapsed_ms"] >= 350
    assert panel.frames.count((47, bytes([5]))) == 1
    assert panel.frames.count((47, bytes([0]))) == 1
    panel.detach()
    until = time.monotonic() + 10
    while status()["status"] != "disconnected":
        assert time.monotonic() < until
        time.sleep(0.05)
    assert post({"screen_cue": "crack"}) == 200
    offline = stage()["screen_cue"]
    assert offline["kind"] == "crack"
    start = len(panel.frames)
    panel.attach()
    panel.expect(42, b"", start)
    assert [payload for method, payload in panel.frames[start:] if method == 47] == [bytes([0]), bytes([5])]
    assert all(method != 46 for method, data in panel.frames[start:])
    assert stage()["screen_cue"]["seed"] == offline["seed"]
    assert stage()["splice_elapsed_ms"] < stage()["screen_cue"]["elapsed_ms"]
    assert post({"splice_seconds": 0}) == 200
    assert status()["splice_elapsed_ms"] == 0
    assert status()["revision"] == draft["revision"]
    assert status()["dirty"] and stage()["mode"] == "gif"


def browser_rehearsal(url, password, browser):
    context = browser.new_context(http_credentials={"username": "beef", "password": password})
    booth = context.new_page()
    booth.goto(url + "/operator")
    booth.locator('[data-preset="crow"]').click()
    expect(booth.locator("#take-live")).to_be_enabled()
    booth.locator("#take-live").click()
    stage = context.new_page()
    stage.goto(url + "/stage")
    expect(stage.locator("#stage-crow")).to_be_visible()
    stage.evaluate("""() => {
      const g = document.querySelector("#stage-canvas").getContext("2d");
      const draw = g.drawImage.bind(g), clear = g.fillRect.bind(g);
      window.presented = [];
      window.cueKinds = new Set();
      let frame = 0;
      g.fillRect = (...args) => {
        if (args.join(",") === "0,0,128,96") frame++;
        return clear(...args);
      };
      g.drawImage = (image, ...args) => {
        const result = draw(image, ...args);
        if (image.src && image.src.includes("/splice-")) {
          const expected = document.createElement("canvas");
          expected.width = 128;
          expected.height = 96;
          const copy = expected.getContext("2d");
          copy.drawImage(image, 0, 0);
          const reference = copy.getImageData(0, 0, 128, 96).data;
          const actual = g.getImageData(0, 0, 128, 96).data;
          presented.push([image.src.split("/").pop(), frame, actual.every((v, i) => v === reference[i])]);
          document.body.dataset.testPhotos = presented.length;
        }
        return result;
      };
      const effect = window.QyronScreenCues.draw;
      window.QyronScreenCues.draw = (...args) => {
        document.body.dataset.testCue = args[1];
        return effect(...args);
      };
    }""")
    booth.get_by_role("button", name="Crack the screen").click()
    stage.locator('body[data-test-cue="1"]').wait_for()
    booth.get_by_role("button", name="Shooting stars").click()
    stage.locator('body[data-test-cue="2"]').wait_for()
    booth.locator("#splice-seconds").select_option("5")
    stage.locator('body[data-test-photos="2"]').wait_for(timeout=16000)
    photos = stage.evaluate("presented")
    assert [p[0] for p in photos] == ["splice-jfk.png", "splice-911.png"], photos
    assert photos[1][1] - photos[0][1] > 1 and all(p[2] for p in photos)
    booth.locator("#splice-seconds").select_option("60")
    expect(booth.locator("#splice-seconds")).to_be_enabled()
    booth.locator("#splice-seconds").select_option("0")
    expect(booth.locator("#cue-status")).to_contain_text("Ready")
    assert stage.request.get(url + "/api/stage").json()["mode"] == "crow"
    context.close()


if __name__ == "__main__":
    with show() as (url, password, panel), sync_playwright() as playwright:
        rehearse(url, password, panel, playwright)
        browser = playwright.chromium.launch(executable_path=os.getenv("CHROMIUM"))
        browser_rehearsal(url, password, browser)
        browser.close()
    print("Screen cue HTTP/USB rehearsal passed.")
