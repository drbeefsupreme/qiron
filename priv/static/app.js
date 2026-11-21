"use strict";
const el = (id) => document.getElementById(id);
const view = document.body.dataset.view;
const fmt = (value) =>
  value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
let busy = false,
  held = false,
  version = 0;
async function api(path, payload) {
  const response = await fetch(
    "/api/" + path,
    payload
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Qiron": "1" },
          body: JSON.stringify(payload),
        }
      : {},
  );
  if (!response.ok)
    throw new Error("Request failed (" + response.status + ").");
  return response.json();
}
function signal(online) {
  document.body.classList.toggle("online", online);
  el("signal").textContent = online ? "LIVE FEED" : "RECONNECTING";
}
function account(data) {
  el("credits").textContent = fmt(data.credits);
  el("side").textContent =
    "POSITION · " + (data.side === "flat" ? "NONE" : data.side.toUpperCase());
  el("close").hidden = data.side === "flat";
  for (const side of ["up", "down"]) {
    el(side).disabled = busy || data.side === side;
    el(side).setAttribute("aria-pressed", String(data.side === side));
  }
}
function stage(data) {
  el("mark").textContent = fmt(data.mark);
  if (view === "stage") {
    for (const layer of data.layers)
      el("l" + layer.id).textContent = layer.text;
    el("movement").textContent =
      (data.change >= 0 ? "▲ " : "▼ ") + fmt(Math.abs(data.change));
    return;
  }
  held = data.held;
  el("hold").textContent = held ? "Resume drift" : "Hold drift";
  el("hold").disabled = false;
  el("marketmeta").textContent =
    (held ? "Drift held" : "Random drift on") +
    " · " +
    data.up +
    " up / " +
    data.down +
    " down";
  for (const layer of data.layers) {
    if (el("layer" + layer.id)) continue;
    const form = document.createElement("form"),
      label = document.createElement("label"),
      input = document.createElement("input"),
      button = document.createElement("button");
    label.textContent =
      ["Top", "Middle", "Bottom", "Left", "Right"][layer.id - 1] +
      " · layer " +
      layer.id;
    input.id = "layer" + layer.id;
    input.maxLength = 100;
    input.value = layer.override;
    input.placeholder = layer.text;
    label.append(input);
    button.textContent = "Save";
    form.append(label, button);
    el("layers").append(form);
    form.onsubmit = (e) => {
      e.preventDefault();
      command(
        { layer: layer.id, text: input.value },
        "Layer " + layer.id + " saved.",
      );
    };
  }
}
async function refresh() {
  const seq = ++version;
  try {
    const data = await api(view === "audience" ? "me" : "stage");
    if (seq !== version) return;
    (view === "audience" ? account : stage)(data);
    signal(true);
  } catch {
    if (seq === version) signal(false);
  }
}
async function command(payload, message) {
  if (busy) return;
  busy = true;
  ++version;
  el("error").textContent = "";
  try {
    await api(view === "audience" ? "trade" : "operator", payload);
    el("receipt").textContent = message;
  } catch (e) {
    el("error").textContent = e.message + " Check the feed and try again.";
  } finally {
    busy = false;
    await refresh();
  }
}
if (view === "audience") {
  for (const side of ["up", "down", "flat"]) {
    el(side === "flat" ? "close" : side).onclick = () =>
      command(
        { side },
        side === "flat"
          ? "Position closed."
          : "You called " + side + ". Eyes on the Chyron.",
      );
  }
}
if (view === "operator") {
  document
    .querySelectorAll("[data-nudge]")
    .forEach(
      (b) =>
        (b.onclick = () =>
          command({ nudge: Number(b.dataset.nudge) }, "Mark adjusted.")),
    );
  el("hold").onclick = () =>
    command({ hold: !held }, held ? "Drift resumed." : "Drift held.");
  el("setmark").onsubmit = (e) => {
    e.preventDefault();
    command({ mark: Number(el("price").value) }, "Mark set.");
  };
}
async function poll() {
  if (!document.hidden && !busy) await refresh();
  setTimeout(poll, 1500);
}
poll();
