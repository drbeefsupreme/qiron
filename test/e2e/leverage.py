import os

from playwright.sync_api import expect, sync_playwright

from show import show


with show() as (url, password, panel), sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=os.getenv("CHROMIUM"))
    booth = pw.request.new_context(base_url=url, http_credentials={"username": "beef", "password": password})
    headers = {"x-qiron": "1"}

    def mark(value):
        assert booth.post("/api/operator", headers=headers, data={"mark": value}).ok

    assert booth.post("/api/operator", headers=headers, data={"hold": True}).ok
    for button, side, delta in [("up", "Long", 1), ("down", "Short", -1)]:
        mark(100)
        phone = browser.new_page(viewport={"width": 390, "height": 844})
        phone.goto(url)
        phone.locator("#" + button).click()
        expect(phone.locator("#side")).to_have_text(side + " · 1×")
        entry = 100 + delta * 10
        mark(entry)
        expect(phone.locator("#balance")).to_have_text("55,000.00")
        phone.locator("#leverage").fill("5")
        expect(phone.locator("#side")).to_have_text(side + " · 5×", timeout=3500)
        expect(phone.locator("#balance")).to_have_text("55,000.00")
        expect(phone.locator("#active-liq")).to_contain_text(f"{entry * (1 - delta / 5):.2f}")
        oi_key = "long_oi_cents" if delta == 1 else "short_oi_cents"
        assert booth.get("/api/stage").json()[oi_key] == 27500000
        mark(entry * (1 + delta / 10))
        expect(phone.locator("#balance")).to_have_text("82,500.00")
        phone.reload()
        expect(phone.locator("#leverage")).to_have_value("5")
        for _ in range(3):
            phone.locator("#leverage").press("ArrowLeft")
        expect(phone.locator("#side")).to_have_text(side + " · 2×")
        expect(phone.locator("#pnl-value")).to_have_text("+32,500.00")
        phone.locator("#close").click()
        expect(phone.locator("#side")).to_have_text("Flat")
        phone.close()
    browser.close()
    print("Long and short positions resized in both directions, preserved equity, and survived reload.")
