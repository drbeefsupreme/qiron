import os
import struct

from playwright.sync_api import expect, sync_playwright

from show import show


def rehearse(url, password, panel, playwright):
    public = playwright.request.new_context(base_url=url)
    assert public.get("/api/operator/phrases").status == 401
    for path in ("/phrases.json", "/booth/phrases.json", "/static/phrases.json"):
        assert public.get(path).status == 404
    public.dispose()
    browser = playwright.chromium.launch(executable_path=os.getenv("CHROMIUM"))
    context = browser.new_context(base_url=url, http_credentials={"username": "beef", "password": password})
    page = context.new_page()
    api = context.request

    def post(payload):
        return api.post("/api/operator", headers={"x-qiron": "1"}, data=payload).status

    library = api.get("/api/operator/phrases").json()
    assert all(0 < len(entry["text"].encode()) <= 32767 for entry in library)
    longest = max(library, key=lambda entry: len(entry["text"].encode()))
    live = api.get("/api/stage").json()
    assert post({"widgets": ["crow", "join"]}) == 200
    page.goto("/operator")
    page.locator("#phrase-picker summary").click()
    expect(page.locator("#phrase-list option")).to_have_count(len(library))
    search = page.locator("#phrase-search")
    search.fill("no matches for this search")
    expect(page.locator("#phrase-place")).to_be_disabled()
    search.fill(longest["text"].splitlines()[-1][-35:])
    expect(page.locator("#phrase-list option")).to_have_count(1)
    assert page.locator("#phrase-preview").text_content() == longest["text"]
    page.locator("#phrase-spot").select_option("3")
    page.locator("#phrase-place").click()
    expect(page.locator("#layer3")).to_have_value(longest["text"])
    panel.expect(41, bytes([2]) + struct.pack("<i", -1) + longest["text"].encode())
    expect(page.locator("#take-live")).to_be_enabled()
    assert api.get("/api/panel").json()["widgets"] == ["crow", "join", "line3"]

    for spot in range(1, 6):
        search.fill("no matches for this search")
        page.locator("#phrase-random").evaluate("""(button, spot) => {
          const original = Math.random, draws = [spot % 2 ? 0 : 0.999999, (spot - 0.5) / 5];
          Math.random = () => draws.shift();
          try { button.click(); } finally { Math.random = original; }
        }""", spot)
        expect(page.locator("#phrase-spot")).to_have_value(str(spot))
        expect(page.locator("#layer" + str(spot))).to_have_value(library[0 if spot % 2 else -1]["text"])
        expect(page.locator("#take-live")).to_be_enabled()
    state = api.get("/api/panel").json()
    assert state["widgets"] == ["crow", "join", "line3", "line1", "line2", "line4", "line5"]
    assert state["dirty"]
    current = api.get("/api/stage").json()
    for key in ("widgets", "layers", "mode"):
        assert current[key] == live[key]
    boundary = "é" * 16383 + "!"
    assert post({"layer": 1, "text": boundary}) == 200
    panel.expect(41, bytes([0]) + struct.pack("<i", -1) + boundary.encode())
    assert post({"layer": 1, "text": boundary + "!"}) == 422
    browser.close()


if __name__ == "__main__":
    with show() as args, sync_playwright() as playwright:
        rehearse(*args, playwright)
    print("Phrase browsing, draft placement, random spots, access and byte limits passed.")
