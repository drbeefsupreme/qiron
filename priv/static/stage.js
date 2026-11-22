"use strict";
const stageTitles = {gif: "GIF mode", blood: "Blood Futures", intro: "Christmas Telethon", crow: "Dr. Crow", beef: "Dr. Beef Supreme"};
let activeMode;

function renderStage(data) {
  if (data.mode !== activeMode) {
    activeMode = data.mode;
    for (const mode of Object.keys(stageTitles))
      el("stage-" + mode).hidden = mode !== activeMode;
    el("stage-title").textContent = stageTitles[activeMode];
    for (const img of document.querySelectorAll(".stage-animation")) {
      if (img.parentElement.id === "stage-" + activeMode) {
        img.src = img.dataset.file + "?start=" + Date.now();
      } else {
        img.removeAttribute("src");
      }
    }
  }
  if (activeMode === "gif") {
    for (const layer of data.layers) {
      const line = el("l" + layer.id);
      if (line) line.textContent = layer.text;
    }
    el("stage-file").textContent = data.gif.playing === false ? "SD playback stopped" :
      "Panel SD playback · " + (data.gif.file || "preset " + data.gif.preset);
  }
  if (activeMode === "blood") {
    el("bulls").textContent = data.up;
    el("bears").textContent = data.down;
    drawCandles(data.candles);
  }
}

function drawCandles(candles) {
  const canvas = el("candles"), g = canvas.getContext("2d");
  const w = canvas.width, h = canvas.height, left = 4, right = w - 50;
  g.fillStyle = "#151d1d";
  g.fillRect(0, 0, w, h);
  if (!candles.length) return;
  const low = Math.min(...candles.map(c => c.low)), high = Math.max(...candles.map(c => c.high));
  const y = price => high === low ? Math.floor(h / 2) : Math.round(9 + (high - price) / (high - low) * (h - 19));
  g.fillStyle = "#3f514e";
  for (const row of [9, h >> 1, h - 10]) g.fillRect(left, row, right - left, 1);
  g.font = "8px monospace";
  g.fillStyle = "#d4ded1";
  g.fillText((high / 100).toFixed(2), right + 4, high === low ? y(high) + 3 : 12);
  if (high !== low) g.fillText((low / 100).toFixed(2), right + 4, h - 7);
  candles.forEach((c, i) => {
    const x = right - 5 - Math.round((candles.length - 1 - i) * (right - left) / 24);
    g.fillStyle = c.close >= c.open ? "#82d8ac" : "#ff846e";
    g.fillRect(x, y(c.high), 1, y(c.low) - y(c.high) + 1);
    g.fillRect(x - 2, Math.min(y(c.open), y(c.close)), 5, Math.abs(y(c.open) - y(c.close)) + 1);
  });
  canvas.setAttribute("aria-label", "10-second candles. Low " + fmt(low / 100) + ", high " + fmt(high / 100));
}
