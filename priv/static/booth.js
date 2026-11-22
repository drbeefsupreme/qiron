"use strict";
const modeNames = {gif: "GIF", blood: "Blood Futures", intro: "Introduction", crow: "Dr. Crow", beef: "Dr. Beef Supreme"};
const gifDirectories = {gifK: "koyaanisqatsi", gifO: "obama", gifF: "flag", gifD: "drugs", gifJ: "joker", gifS: "spooky", gifB: "subgenius", gifT: "transparent", gifA: "aj", gifP: "blue", gifH: "hank"};
const edits = new Map();
let draft, timer, writeTask, failedEdit, desiredPreset = null, switching = false, panelCurrent = false;

function draftStatus() {
  if (!draft) return;
  const offline = draft.readiness === "offline";
  const statuses = {ready: "Draft preloaded on panel.", loading: "Preloading panel…", error: "Panel could not prepare this draft.", offline: "Panel offline · browser stage only."};
  el("discard-edits").hidden = !failedEdit;
  const selected = desiredPreset ?? draft.preset_id;
  for (const button of el("preset-rail").children) {
    const active = button.dataset.preset === selected;
    button.setAttribute("aria-pressed", String(active));
    button.tabIndex = active ? 0 : -1;
  }
  const status = desiredPreset ? "Loading " + presetName(desiredPreset) + "…" :
    failedEdit ? "Draft has unsaved changes." :
    writeTask || edits.size ? "Saving draft…" :
    !panelCurrent ? "Reconnecting…" :
    (!draft.dirty ? "Draft matches live. " : "") + (statuses[draft.readiness] || "");
  if (el("draft-status").textContent !== status) el("draft-status").textContent = status;
  el("take-live").disabled = switching || !panelCurrent || !!writeTask || edits.size > 0 || !draft.dirty || !(offline || draft.ready);
  el("save-stack").disabled = switching || !panelCurrent || !el("stack-name").value.trim();
  el("brightness").readOnly = switching;
  el("gif-controls").inert = switching;
  el("mixer").inert = switching;
  for (const id of ["melt-live", "clear-live-fx"]) el(id).disabled = liveFxBusy;
}

function presetName(id, mode) {
  return draft.presets.find(preset => preset.id === id)?.name ?? modeNames[mode] ?? id;
}

function renderRail() {
  const rail = el("preset-rail");
  const buttons = new Map(Array.from(rail.children, button => [button.dataset.preset, button]));
  draft.presets.forEach(({id, name}, index) => {
    const button = buttons.get(id) ?? document.createElement("button");
    buttons.delete(id);
    button.type = "button";
    button.dataset.preset = id;
    if (button.textContent !== name) button.textContent = name;
    if (rail.children[index] !== button) rail.insertBefore(button, rail.children[index] ?? null);
  });
  for (const button of buttons.values()) button.remove();
}

async function selectPreset(id) {
  desiredPreset = id;
  const alreadySwitching = switching;
  switching = true;
  draftStatus();
  if (alreadySwitching) return;
  try {
    if (writeTask) await writeTask;
    while (desiredPreset !== null) {
      clearTimeout(timer);
      let requested = desiredPreset;
      await saveDraft(async () => {
        do {
          requested = desiredPreset;
          await api("operator", {preset: requested});
        } while (desiredPreset !== requested);
      });
      if (desiredPreset === requested || failedEdit) desiredPreset = null;
    }
  } finally {
    switching = false;
    draftStatus();
  }
}

async function saveNamedStack(event) {
  event.preventDefault();
  const name = el("stack-name").value.trim();
  if (!name || switching || !panelCurrent) return;
  switching = true;
  draftStatus();
  try {
    if (writeTask) await writeTask;
    clearTimeout(timer);
    await saveDraft(async () => {
      await api("operator", {save_as: name});
      if (el("stack-name").value.trim() === name) el("stack-name").value = "";
      el("receipt").textContent = name + " saved.";
    });
  } finally {
    switching = false;
    if (desiredPreset !== null) selectPreset(desiredPreset);
    else draftStatus();
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
    if (failedEdit === key) failedEdit = null;
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
      panelCurrent = false;
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
      renderPreview();
    };
    label.append(field);
    group.append(label);
  }
  el("layers").append(group);
}

let editingVolatility = false;
function showVolatility(bps) {
  const value = "±" + (bps / 100).toFixed(2) + "%";
  el("volatility-label").value = value;
  el("volatility").setAttribute("aria-valuetext", value + " per two seconds");
}

function renderBooth(data) {
  draft = data;
  panelCurrent = true;
  renderRail();
  if (!editingVolatility && !el("volatility").matches(":active")) {
    el("volatility").disabled = false;
    el("volatility").value = data.volatility_bps;
    showVolatility(data.volatility_bps);
  }
  el("on-air").textContent = "On air · " + presetName(data.live_preset_id, data.live_mode);
  el("panel-status").textContent = "USB " + data.status;
  el("panel-error").textContent = data.error || "";
  fieldValue("brightness", "brightness", data.brightness);
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
  renderMixer();
  draftStatus();
}

function initBooth() {
  initMixer();
  const volatility = el("volatility");
  volatility.oninput = () => {
    showVolatility(volatility.valueAsNumber);
  };
  volatility.onchange = async () => {
    editingVolatility = true;
    const focused = document.activeElement === volatility;
    volatility.disabled = true;
    ++version;
    el("error").textContent = "";
    try {
      await api("operator", {volatility_bps: volatility.valueAsNumber});
    } catch (error) {
      el("error").textContent = error.message;
    } finally {
      editingVolatility = false;
      volatility.disabled = false;
      if (focused && document.activeElement === document.body) volatility.focus({preventScroll: true});
      await refresh();
    }
  };
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
  const rail = el("preset-rail");
  rail.onclick = event => {
    const button = event.target.closest("button[data-preset]");
    if (button) selectPreset(button.dataset.preset);
  };
  rail.onkeydown = event => {
    if (!draft || (event.target !== rail && !event.target.matches("button[data-preset]")) ||
        event.altKey || event.metaKey || event.ctrlKey || event.shiftKey ||
        !["ArrowDown", "ArrowUp"].includes(event.key)) return;
    const buttons = Array.from(rail.children);
    const current = event.target === rail ? rail.querySelector('[aria-pressed="true"]') : event.target;
    const index = buttons.indexOf(current) + (event.key === "ArrowDown" ? 1 : -1);
    const next = buttons[Math.max(0, Math.min(buttons.length - 1, index))];
    if (!next) return;
    event.preventDefault();
    next.focus();
    if (next !== current) selectPreset(next.dataset.preset);
  };
  el("stack-name").oninput = draftStatus;
  el("save-stack-form").onsubmit = saveNamedStack;
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
      el("receipt").textContent = presetName(draft.preset_id, draft.mode) + " taken live.";
    });
  };
}
