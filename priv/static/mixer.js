"use strict";

const mediaNames = {sd: "SD card GIF", crow: "Dr. Crow", beef: "Dr. Beef Supreme", peter: "Peter Thiel", santa: "Santa Claus", intro: "Telethon intro"};
const widgetNames = {...mediaNames, chart: "Blood Futures chart", ticker: "Exchange ticker", line1: "Middle text", line2: "Top text", line3: "Bottom text", line4: "Left text", line5: "Right text", lineF: "Feature text"};
let preview, previewMarket = {}, liveFxBusy = false, lastStack;

function effectiveStack() {
  return edits.get("widgets")?.widgets ?? draft.widgets;
}

function renderPreview() {
  if (!draft) return;
  const layers = draft.layers.map(layer => {
    const update = edits.get("layer" + layer.id);
    return {...layer, text: update ? update.text : layer.text, speed: edits.get("speed" + layer.id)?.speed ?? layer.speed};
  });
  preview.update({...previewMarket, ...draft, widgets: effectiveStack(), layers,
    melt: edits.get("melt")?.melt ?? draft.melt, hue: edits.get("hue")?.hue ?? draft.hue});
}

function setWidgets(widgets) {
  edit("widgets", {widgets});
  renderMixer();
}

function drawStack(widgets) {
  const list = el("widget-stack");
  const focused = document.activeElement;
  const restore = list.contains(focused) ? [focused.dataset.id, focused.dataset.step] : null;
  list.replaceChildren();
  for (const [index, id] of widgets.entries()) {
    const row = document.createElement("li");
    const name = document.createElement("strong");
    name.textContent = widgetNames[id];
    row.append(name);
    for (const [step, glyph, title] of [[-1, "↑", "Send backward"], [1, "↓", "Bring forward"], [0, "×", "Remove"]]) {
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.id = id;
      button.dataset.step = step;
      button.title = title + " · " + widgetNames[id];
      button.setAttribute("aria-label", button.title);
      button.textContent = glyph;
      button.disabled = step === -1 && index === 0 || step === 1 && index === widgets.length - 1;
      button.onclick = () => {
        const next = [...effectiveStack()];
        next.splice(index, 1);
        if (step) next.splice(index + step, 0, id);
        setWidgets(next);
      };
      row.append(button);
    }
    list.append(row);
  }
  const choice = el("widget-choice"), selected = choice.value;
  choice.replaceChildren();
  for (const [id, name] of Object.entries(widgetNames)) {
    if (!widgets.includes(id)) choice.add(new Option(name, id));
  }
  if (Array.from(choice.options).some(option => option.value === selected)) choice.value = selected;
  choice.disabled = el("add-widget").disabled = !choice.options.length;
  if (restore) list.querySelector('button[data-id="' + restore[0] + '"][data-step="' + restore[1] + '"]:enabled')?.focus();
}

function renderMixer() {
  const widgets = effectiveStack();
  const signature = widgets.join(",");
  if (signature !== lastStack) {
    drawStack(widgets);
    lastStack = signature;
  }
  el("gif-source-label").hidden = draft.mode !== "gif";
  el("gif-source").value = widgets[0] in mediaNames ? widgets[0] : "";
  const sd = widgets.includes("sd"), hasText = widgets.some(id => id.startsWith("line"));
  el("sd-preview").hidden = !sd;
  el("gif-controls").hidden = !sd && !hasText;
  el("sd-controls").hidden = !sd;
  el("line-controls").hidden = !hasText;
  for (let i = 1; i <= 6; i++) {
    const field = el("layer" + i);
    if (field) field.closest("fieldset").hidden = !widgets.includes("line" + (i === 6 ? "F" : i));
  }
  for (const key of ["melt", "hue"]) {
    const value = edits.get(key)?.[key] ?? draft[key];
    el(key).value = value;
    el(key + "-value").value = value + "%";
  }
  el("live-fx-status").textContent = "Melt " + draft.live_melt + "% · Hue " + draft.live_hue + "%";
  renderPreview();
}

async function liveFx(melt, hue) {
  if (liveFxBusy || switching) return;
  liveFxBusy = true;
  draftStatus();
  try {
    await api("operator", {live_fx: {melt, hue}});
    el("receipt").textContent = melt || hue ? "On-air melt applied." : "On-air effects cleared.";
    await refresh();
  } catch (error) {
    el("error").textContent = error.message;
  } finally {
    liveFxBusy = false;
    draftStatus();
  }
}

function initMixer() {
  preview = window.QyronCanvas(el("draft-canvas"));
  const source = el("gif-source");
  source.add(new Option("Choose a background", ""));
  source.options[0].disabled = true;
  for (const [id, name] of Object.entries(mediaNames)) source.add(new Option(name, id));
  source.onchange = () => {
    const widgets = [...effectiveStack()];
    if (widgets[0] in mediaNames) widgets.shift();
    setWidgets([source.value, ...widgets.filter(id => id !== source.value)]);
  };
  el("add-widget").onclick = () => setWidgets([...effectiveStack(), el("widget-choice").value]);
  for (const key of ["melt", "hue"]) {
    el(key).oninput = () => {
      const value = el(key).valueAsNumber;
      edit(key, {[key]: value});
      el(key + "-value").value = value + "%";
      renderPreview();
    };
  }
  el("melt-live").onclick = () => {
    const melt = el("melt").valueAsNumber, hue = el("hue").valueAsNumber;
    liveFx(melt || hue ? melt : 75, melt || hue ? hue : 65);
  };
  el("clear-live-fx").onclick = () => liveFx(0, 0);
}
