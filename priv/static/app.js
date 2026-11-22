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
    throw new Error((await response.text()).slice(0, 100) || "Request failed (" + response.status + ").");
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
}

function updateField(field, value) {
  if (document.activeElement !== field && field.value === field.defaultValue) {
    field.value = value;
    field.defaultValue = value;
  }
}

function panel(data) {
  el("panel-status").textContent = "USB " + data.status;
  updateField(el("brightness"), String(data.brightness));
  if (!el("action").options.length) {
    const names = {caw: "CAW", dopamine: "DOPAMINE", gifK: "GIF · Koyaanisqatsi", gifO: "GIF · Obama", gifF: "GIF · Flag", gifD: "GIF · Drugs", gifJ: "GIF · Joker", gifS: "GIF · Spooky", gifB: "GIF · SubGenius", gifT: "GIF · Transparent", gifA: "GIF · Alex Jones", gifP: "GIF · Blue Chew", gifH: "GIF · Hank"};
    for (const action of data.actions) {
      const label = action.replace(/([A-Z])/g, " $1");
      el("action").add(new Option(names[action] || label[0].toUpperCase() + label.slice(1), action));
    }
  }
  for (const layer of data.layers) {
    if (!el("layer" + layer.id)) {
      const group = document.createElement("fieldset");
      const legend = document.createElement("legend");
      legend.textContent = ["Middle", "Top", "Bottom", "Left", "Right", "Feature"][layer.id - 1] +
        " · layer " + (layer.id === 6 ? "F" : layer.id);
      group.append(legend);
      for (const key of ["text", "speed"]) {
        const form = document.createElement("form"), label = document.createElement("label"),
          input = document.createElement(key === "text" ? "textarea" : "input"),
          button = document.createElement("button");
        input.id = (key === "text" ? "layer" : "speed") + layer.id;
        if (key === "speed") {
          input.type = "number";
          input.min = "0";
          input.max = "255";
          input.required = true;
        }
        label.textContent = key === "text" ? "Text" : "Speed (0–255)";
        button.textContent = key === "text" ? "Save" : "Set speed";
        label.append(input);
        form.append(label, button);
        group.append(form);
        form.onsubmit = async (e) => {
          e.preventDefault();
          const value = input.value;
          if (await command({layer: layer.id, [key]: key === "text" ? value : Number(value)}, "Layer " + layer.id + " saved.")) {
            input.defaultValue = value;
          }
        };
      }
      el("layers").append(group);
    }
    const input = el("layer" + layer.id);
    updateField(input, layer.override);
    input.placeholder = layer.text;
    updateField(el("speed" + layer.id), String(layer.speed));
  }
}
async function refresh() {
  const seq = ++version;
  try {
    const data = await api(view === "audience" ? "me" : "stage");
    const hardware = view === "operator" ? await api("panel") : null;
    if (seq !== version) return;
    if (hardware) panel(hardware);
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
    return true;
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
  el("set-brightness").onsubmit = async (e) => {
    e.preventDefault();
    const value = el("brightness").value;
    if (await command({brightness: Number(value)}, "Brightness saved.")) el("brightness").defaultValue = value;
  };
  el("panel-action").onsubmit = (e) => {
    e.preventDefault();
    command({action: el("action").value}, "Cue accepted.");
  };
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
