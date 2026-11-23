import os
import time

from playwright.sync_api import expect, sync_playwright

from show import show


with show() as (url, password, panel), sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=os.getenv("CHROMIUM"))
    booth = browser.new_context(base_url=url, http_credentials={"username": "beef", "password": password})
    phone = browser.new_context(base_url=url, viewport={"width": 390, "height": 844})
    page = phone.new_page()

    def operator(data):
        assert booth.request.post("/api/operator", data=data, headers={"x-qiron": "1"}).ok

    operator({"hold": True})
    operator({"mark": 100})
    page.goto(url)
    expect(page.locator("#blood-price")).to_have_text("100.00")
    page.locator("#leverage").press("End")
    page.locator("#up").click()
    expect(page.locator("#side")).to_contain_text("Long")
    operator({"mark": 101})
    expect(page.locator("#pnl-value")).to_have_text("+25,000.00")
    page.close()
    operator({"mark": 97})
    first = phone.request.get("/api/me").json()["pnl_runs"][0]
    assert first["points"][-1][1] == -5000000
    time.sleep(max(0, (first["ended_at_ms"] + 300100) / 1000 - time.time()))
    page = phone.new_page()
    page.goto(url)
    expect(page.locator("#balance")).to_have_text("50,000.00")
    expect(page.locator("#pnl-chart path[data-slug]")).to_have_count(2)
    expect(page.locator("#pnl-value")).to_have_text("0.00")
    second = phone.request.get("/api/me").json()["pnl_runs"][1]
    assert second["started_at_ms"] == first["ended_at_ms"] + 300000
    page.locator("#pnl-run").select_option("1")
    expect(page.locator("#pnl-value")).to_have_text("−50,000.00")
    expect(page.locator("#pnl-chart path")).to_have_count(1)
    page.locator("#pnl-run").select_option("all")
    page.reload()
    expect(page.locator("#pnl-chart path")).to_have_count(2)
    browser.close()
    print("Phone chart retained both slugs across a five-minute offline liquidation and automatic refill.")
