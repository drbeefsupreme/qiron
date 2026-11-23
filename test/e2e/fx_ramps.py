import os
from pathlib import Path

from playwright.sync_api import sync_playwright


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=os.getenv("CHROMIUM"))
    page = browser.new_page()
    page.add_script_tag(path=Path(__file__).resolve().parents[2] / "priv/static/compositor.js")
    page.evaluate("""() => {
      let now = 0, sequence = 0;
      const pending = new Map();
      performance.now = () => now;
      window.requestAnimationFrame = cb => { pending.set(++sequence, cb); return sequence; };
      window.cancelAnimationFrame = id => pending.delete(id);

      function renderAt(time) {
        now = time;
        for (const [id, draw] of [...pending]) {
          pending.delete(id);
          draw(time);
        }
      }

      function stage() {
        const canvas = document.createElement("canvas");
        const engine = QyronCanvas(canvas);
        return {
          set(melt, hue) {
            engine.update({widgets: ["price", "chart"], mark_cents: 12345, melt, hue,
              candles: [{open: 380, close: 990, high: 1035, low: 124}]});
          },
          pixels: () => canvas.toDataURL(),
          close: () => engine.destroy()
        };
      }

      const live = stage();
      function check(time, melt, hue) {
        now = time - 20000;
        const reference = stage();
        reference.set(melt, hue);
        renderAt(time);
        if (reference.pixels() !== live.pixels())
          throw Error("Unexpected rendered effect levels at " + time + "ms, expected " + melt + "/" + hue);
        reference.close();
      }

      live.set(90, 60);
      check(0, 0, 0);
      check(5000, 30, 20);
      live.set(90, 60);
      check(7500, 45, 30);
      live.set(90, 0);
      check(10000, 60, 25);
      live.set(0, 0);
      check(15000, 40, 15);
      live.set(0, 0);
      check(20000, 20, 5);
      check(22500, 10, 0);
      check(25000, 0, 0);
      live.set(100, 80);
      check(32500, 50, 40);
      check(40000, 100, 80);
      check(45000, 100, 80);
      live.close();
    }""")
    browser.close()

print("Browser pixels matched the 15-second independent melt and hue ramps through polling, retarget and release.")
