import os
from pathlib import Path

from playwright.sync_api import sync_playwright


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=os.getenv("CHROMIUM"))
    page = browser.new_page()
    page.add_script_tag(path=Path(__file__).resolve().parents[2] / "priv/static/compositor.js")
    page.evaluate("""() => {
      let now = 0;
      performance.now = () => now;
      const fictional = "CALL 555-0100";
      function strip(widgets, ms, caption = fictional, expected = fictional) {
        now = 0;
        let render;
        window.requestAnimationFrame = cb => { render = cb; return 1; };
        window.cancelAnimationFrame = () => {};
        const canvas = document.createElement("canvas");
        const screen = QyronCanvas(canvas);
        screen.update({widgets, callin_banner: caption, join_banner: expected,
          tickers: [{symbol: "PISSCOIN", price_cents: 140, color: "#ffd84a"}]});
        now = ms;
        render(ms);
        const y = widgets.length === 1 && widgets[0] === "join" ? 0 : 87;
        const rgb = canvas.getContext("2d").getImageData(0, y, 128, 9).data;
        screen.destroy();
        return rgb;
      }
      const same = (a, b) => a.every((v, i) => v === b[i]);
      const start = strip(["callin"], 0), moved = strip(["callin"], 50);
      if (!start.some((v, i) => i%4 === 0 && v === 255)) throw Error("No phone lettering");
      if (same(start, moved)) throw Error("Stationary phone number");
      for (let y = 0; y < 9; ++y) {
        for (let x = 0; x < 127; ++x) {
          const i = (y*128+x)*4;
          if (start[i+4] !== moved[i]) throw Error("Expected one pixel of leftward motion");
        }
      }
      const reference = strip(["join"], 0);
      for (let i = 0; i < start.length; i += 4) {
        if ((start[i] === 255) !== (reference[i] === 255)) throw Error("Wrong phone text");
      }
      const fallback = strip(["callin"], 0, null);
      const fallbackText = strip(["join"], 0, null, "TELETHON CALL-IN");
      for (let i = 0; i < fallback.length; i += 4) {
        if ((fallback[i] === 255) !== (fallbackText[i] === 255)) throw Error("Wrong default banner");
      }
      for (const widget of ["ticker", "interest"]) {
        const ticker = strip([widget], 50);
        if (same(moved, ticker)) throw Error("Missing ticker or call-in content");
        if (!same(strip([widget, "callin"], 50), moved)) throw Error("Call-in failed to cover ticker");
        if (!same(strip(["callin", widget], 50), ticker)) throw Error("Ticker failed to cover call-in");
      }
    }""")
    browser.close()

print("Browser call-in lettering, leftward scroll and lower-band stack order passed.")
