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

const widgetNames = {sd: "Panel SD", chart: "Blood Futures", ticker: "Ticker", ...stageTitles};
let previousWidgets;

function renderStage(data) {
  const widgets = data.widgets || (data.mode === "gif" ? ["sd", ...stageLines] : [stageSource[data.mode]]);
  stageCanvas.update(data);
  const title = stageTitles[data.mode] || "Stage mix";
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
      if (stageSource[id] === id) label.id = "stage-" + id;
      caption.append(label);
    });
    el("stage-gif").hidden = !widgets.includes("sd");
    el("stage-blood").hidden = !widgets.includes("chart");
  }
  const gif = data.gif || {};
  el("stage-file").textContent = gif.playing === false ? "SD playback stopped" :
    "Panel SD playback · " + (gif.file || "preset " + gif.preset) + " · Media is available on the physical panel only.";
  el("bulls").textContent = data.up;
  el("bears").textContent = data.down;
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
