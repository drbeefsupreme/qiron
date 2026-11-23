"use strict";
const stageTitles = {gif: "GIF mode", blood: "Blood Futures", intro: "Christmas Telethon",
  crow: "Dr. Crow", beef: "Dr. Beef Supreme", peter: "Peter Thiel", santa: "Santa"};
const stageSource = {gif: "sd", blood: "chart", intro: "intro", crow: "crow", beef: "beef",
  peter: "peter", santa: "santa"};
const stageLines = ["line1", "line2", "line3", "line4", "line5", "lineF"];
const stageCanvas = window.QyronCanvas(document.getElementById("stage-canvas"));
const stageText = document.querySelector("#stage-scrolls dl");
stageLines.forEach((id, i) => {
  const term = document.createElement("dt"), value = document.createElement("dd");
  term.textContent = i === 5 ? "Feature line" : "Line " + (i + 1);
  value.id = "l" + (i + 1);
  stageText.append(term, value);
});

const widgetNames = {sd: "Panel SD", chart: "Candlestick chart", price: "Baby Blood price", interest: "Open interest and ticker", ticker: "Ticker", join: "Audience join banner", callin: "Telethon call-in", ...stageTitles};
let previousWidgets;

function renderStage(data) {
  const defaults = {gif: ["sd", ...stageLines], blood: ["chart", "price", "interest"]};
  const widgets = data.widgets || defaults[data.mode] || [stageSource[data.mode]];
  stageCanvas.update(data);
  const title = data.preset_name || stageTitles[data.mode] || "Stage mix";
  el("stage-title").textContent = title;
  el("stage-canvas").setAttribute("aria-label", title + " · on-air composition");
  const order = widgets.join(",");
  if (order !== previousWidgets) {
    previousWidgets = order;
    const caption = el("stage-layers");
    caption.textContent = widgets.length ? "" : "Empty stage";
    widgets.forEach((id, i) => {
      if (i) caption.append(" / ");
      const label = document.createElement("span");
      label.textContent = widgetNames[id] || (id === "lineF" ? "Feature line" : "Line " + id.slice(4));
      if (id === "callin" || stageSource[id] === id) label.id = "stage-" + id;
      caption.append(label);
    });
    el("stage-gif").hidden = !widgets.includes("sd");
    el("stage-price").hidden = !widgets.includes("price");
    el("stage-interest").hidden = !widgets.includes("interest");
    el("stage-chart").hidden = !widgets.includes("chart");
    const summary = ["chart", "price", "interest"].filter(id => widgets.includes(id));
    el("stage-blood").hidden = !summary.length;
    el("stage-canvas").setAttribute("aria-describedby", ["stage-layers", ...summary.map(id => "stage-" + id)].join(" "));
  }
  if (widgets.includes("callin")) el("stage-callin").textContent = data.callin_banner || "TELETHON CALL-IN";
  const gif = data.gif || {};
  el("stage-file").textContent = gif.playing === false ? "SD playback stopped" :
    "Panel SD playback · " + (gif.file || "preset " + gif.preset) + " · Media is available on the physical panel only.";
  el("long-oi").textContent = fmt((data.long_oi_cents ?? 0) / 100);
  el("short-oi").textContent = fmt((data.short_oi_cents ?? 0) / 100);
  const candles = data.candles || [];
  const bar = candles[candles.length - 1];
  el("stage-chart").textContent = bar
    ? "Latest candle · Open " + fmt(bar.open / 100) + " · High " + fmt(bar.high / 100) +
      " · Low " + fmt(bar.low / 100) + " · Close " + fmt(bar.close / 100)
    : "Awaiting first candle";
  let hasText = false;
  stageLines.forEach((id, i) => {
    const layer = (data.layers || []).find(item => item.id === i + 1);
    const text = widgets.includes(id) && layer ? layer.text : "";
    const value = el("l" + (i + 1));
    if (value.textContent !== text) value.textContent = text;
    value.hidden = value.previousElementSibling.hidden = !text;
    if (text) hasText = true;
  });
  el("stage-scrolls").hidden = !hasText;
}
