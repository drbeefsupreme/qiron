"use strict";
const modeNames = {gif: "GIF", blood: "Blood Futures", intro: "Introduction"};
const gifDirectories = {gifK: "koyaanisqatsi", gifO: "obama", gifF: "flag", gifD: "drugs", gifJ: "joker", gifS: "spooky", gifB: "subgenius", gifT: "transparent", gifA: "aj", gifP: "blue", gifH: "hank"};
const edits = new Map();
let draft, timer, writeTask, failedEdit, switching = false;

function draftStatus() {
  if (!draft) return;
  const offline = draft.readiness === "offline";
  const statuses = {ready: "Draft preloaded on panel.", loading: "Preloading panel…", error: "Panel could not prepare this draft.", offline: "Panel offline · browser stage only."};
  el("discard-edits").hidden = !failedEdit;
  el("draft-status").textContent = failedEdit ? "Draft has unsaved changes." : writeTask || edits.size ? "Saving draft…" :
    (!draft.dirty ? "Draft matches live. " : "") + (statuses[draft.readiness] || "");
  el("take-live").disabled = switching || !!writeTask || edits.size > 0 || !draft.dirty || !(offline || draft.ready);
  for (const button of document.querySelectorAll("[data-mode]")) {
    button.disabled = switching;
    button.setAttribute("aria-pressed", String(draft.mode === button.dataset.mode));
  }
}

function edit(key, payload) {
  edits.set(key, payload);
  failedEdit = null;
  clearTimeout(timer);
  timer = setTimeout(saveDraft, 350);
  draftStatus();
}

async function flushEdits() {
  while (edits.size) {
    const [key, payload] = edits.entries().next().value;
    try {
      await api("operator", payload);
    } catch (error) {
      if (edits.get(key) !== payload) continue;
      failedEdit = key;
      throw error;
    }
    if (edits.get(key) === payload) edits.delete(key);
  }
}

function saveDraft(afterSave) {
  if (writeTask) return writeTask;
  writeTask = (async () => {
    ++version;
    el("error").textContent = "";
    try {
      await flushEdits();
      if (afterSave) await afterSave();
    } catch (error) {
      el("error").textContent = error.message;
    }
    try {
      renderBooth(await api("panel"));
    } catch {
      signal(false);
    }
  })().finally(() => {
    ++version;
    writeTask = null;
    if (edits.size && !failedEdit) {
      clearTimeout(timer);
      timer = setTimeout(saveDraft, 0);
    }
    draftStatus();
  });
  draftStatus();
  return writeTask;
}

function fieldValue(id, key, value) {
  const field = el(id);
  if (!edits.has(key) && field.value !== String(value)) field.value = value;
}

function layerFields(layer) {
  const group = document.createElement("fieldset");
  const legend = document.createElement("legend");
  legend.textContent = ["Middle", "Top", "Bottom", "Left", "Right", "Feature"][layer.id - 1] + " · layer " + (layer.id === 6 ? "F" : layer.id);
  group.append(legend);
  for (const key of ["text", "speed"]) {
    const label = document.createElement("label");
    label.textContent = key === "text" ? "Text" : "Speed (0–255)";
    const field = document.createElement(key === "text" ? "textarea" : "input");
    field.id = (key === "text" ? "layer" : "speed") + layer.id;
    if (key === "speed") {
      field.type = "number";
      field.min = 0;
      field.max = 255;
      field.required = true;
    }
    field.oninput = () => {
      const value = key === "text" ? field.value : field.valueAsNumber;
      edit(field.id, {layer: layer.id, [key]: value});
    };
    label.append(field);
    group.append(label);
  }
  el("layers").append(group);
}

function renderBooth(data) {
  draft = data;
  el("on-air").textContent = "On air · " + modeNames[data.live_mode];
  el("panel-status").textContent = "USB " + data.status;
  el("panel-error").textContent = data.error || "";
  el("gif-controls").hidden = data.mode !== "gif";
  el("blood-info").hidden = data.mode !== "blood";
  el("intro-info").hidden = data.mode !== "intro";
  fieldValue("brightness", "brightness", data.brightness);
  if (data.mode === "gif") {
    el("gif-playback").textContent = !data.gif.playing ? "DRAFT · STOPPED" : data.gif.file ? "DRAFT · LOOP FILE" : "DRAFT · CYCLE FOLDER";
    fieldValue("gif-preset", "gif", data.gif.preset);
    fieldValue("gif-file", "gif", data.gif.file);
    el("gif-file").placeholder = "/gifs/" + gifDirectories[el("gif-preset").value] + "/filename.gif";
    if (!el("action").options.length) {
      el("action").add(new Option("None", ""));
      const names = {caw: "CAW", dopamine: "DOPAMINE"};
      for (const action of data.actions.filter(name => !(name in gifDirectories))) {
        const label = action.replace(/([A-Z])/g, " $1");
        el("action").add(new Option(names[action] || label[0].toUpperCase() + label.slice(1), action));
      }
    }
    fieldValue("action", "action", data.action || "");
    for (const l of data.layers) {
      if (!el("layer" + l.id)) layerFields(l);
      fieldValue("layer" + l.id, "layer" + l.id, l.override);
      fieldValue("speed" + l.id, "speed" + l.id, l.speed);
      el("layer" + l.id).placeholder = l.text;
    }
  }
  draftStatus();
}

function initBooth() {
  for (const [id, directory] of Object.entries(gifDirectories))
    el("gif-preset").add(new Option("/gifs/" + directory, id));
  const gifEdit = () => edit("gif", {gif: {preset: el("gif-preset").value, file: el("gif-file").value}});
  el("gif-preset").onchange = () => {
    el("gif-file").value = "";
    el("gif-file").placeholder = "/gifs/" + gifDirectories[el("gif-preset").value] + "/filename.gif";
    gifEdit();
  };
  el("gif-file").oninput = gifEdit;
  el("brightness").oninput = () => edit("brightness", {brightness: el("brightness").valueAsNumber});
  el("action").onchange = () => edit("action", {action: el("action").value || null});
  for (const button of document.querySelectorAll("[data-mode]")) {
    button.onclick = async () => {
      if (switching || draft.mode === button.dataset.mode) return;
      switching = true;
      draftStatus();
      if (writeTask) await writeTask;
      clearTimeout(timer);
      await saveDraft(() => api("operator", {mode: button.dataset.mode}));
      switching = false;
      draftStatus();
    };
  }
  el("discard-edits").onclick = async () => {
    clearTimeout(timer);
    if (writeTask) await writeTask;
    edits.clear();
    failedEdit = null;
    el("error").textContent = "";
    renderBooth(draft);
  };
  const take = el("take-live");
  document.addEventListener("keydown", event => {
    if (event.key !== "Enter" || !event.altKey || event.ctrlKey || event.metaKey || event.shiftKey ||
        event.isComposing || event.defaultPrevented) return;
    event.preventDefault();
    if (!event.repeat && !take.disabled) take.click();
  });
  take.onclick = async () => {
    const revision = draft.revision;
    await saveDraft(async () => {
      await api("operator", {take: revision});
      el("receipt").textContent = modeNames[draft.mode] + " taken live.";
    });
  };
}
