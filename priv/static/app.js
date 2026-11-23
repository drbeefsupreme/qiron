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
let latestAccount, leverageEdit, queuedResize;
let resizing = false;
const sideNames = { flat: "Flat", up: "Long", down: "Short" };

function liquidation(cents) {
  return cents == null ? "Outside range" : fmt(cents / 100);
}

function showQuotes() {
  const lev = Number(el("leverage").value);
  el("multiplier").value = lev + "×";
  el("leverage").style.setProperty("--fill", ((lev - 1) * 100 / 49) + "%");
  if (!latestAccount) return;
  for (const side of ["up", "down"]) {
    const quote = latestAccount.quotes_cents[side][lev - 1];
    el(side + "-liq").textContent = latestAccount.refill_in === null ? liquidation(quote) : "—";
  }
}

function account(data) {
  latestAccount = data;
  if (!resizing && !leverageEdit && data.side !== "flat") {
    el("leverage").value = data.leverage;
  }
  showQuotes();
  const busted = data.refill_in !== null;
  el("balance").textContent = fmt(data.piss_coin);
  el("blood-price").textContent = fmt(data.mark_cents / 100);
  drawPnl(data);
  el("refill").hidden = !busted;
  el("leverage").disabled = busted || (busy && !resizing);
  if (busted) {
    const seconds = data.refill_in;
    el("cooldown").textContent = seconds
      ? "Liquidated. Next slug in " + Math.floor(seconds / 60) + ":" + String(seconds % 60).padStart(2, "0")
      : "Your next slug is ready.";
    el("receipt").textContent = "";
  }
  el("side").textContent = data.side === "flat" ? "Flat" : sideNames[data.side] + " · " + data.leverage + "×";
  el("active-liq").textContent = data.side === "flat" ? "" : "Liquidation · " + liquidation(data.liquidation_cents);
  el("close").disabled = busy || resizing;
  el("close").hidden = data.side === "flat";
  for (const side of ["up", "down"]) {
    el(side).disabled = busy || resizing || busted || data.side === side;
    el(side).setAttribute("aria-pressed", String(data.side === side));
  }
}
function stage(data) {
  el("mark").textContent = fmt(data.mark);
  if (view === "stage") {
    renderStage(data);
    return;
  }
  held = data.held;
  el("hold").textContent = held ? "Resume drift" : "Hold drift";
  el("hold").disabled = false;
  el("marketmeta").textContent =
    (held ? "Drift held" : "Random drift on") +
    " · Open interest in PISS COIN · Long " + fmt((data.long_oi_cents ?? 0) / 100) +
    " / Short " + fmt((data.short_oi_cents ?? 0) / 100);
}

async function refresh() {
  const seq = ++version;
  try {
    const data = await api(view === "audience" ? "me" : "stage");
    const hardware = view === "operator" ? await api("panel") : null;
    if (seq !== version) return;
    if (hardware) {
      previewMarket = data;
      if (!writeTask) renderBooth(hardware);
    }
    (view === "audience" ? account : stage)(data);
    signal(true);
  } catch {
    if (seq === version) signal(false);
  }
}
async function command(payload, message, path = view === "audience" ? "trade" : "operator") {
  if (busy) return;
  busy = true;
  ++version;
  if (view === "audience" && latestAccount) account(latestAccount);
  el("error").textContent = "";
  try {
    await api(path, payload);
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
  const slider = el("leverage");
  slider.oninput = () => {
    leverageEdit ??= latestAccount;
    showQuotes();
  };
  slider.onchange = async () => {
    const position = leverageEdit ?? latestAccount;
    leverageEdit = null;
    if (!position?.position_id) return;
    queuedResize = {position_id: position.position_id, leverage: Number(slider.value)};
    if (resizing) return;
    resizing = true;
    try {
      while (queuedResize) {
        const change = queuedResize;
        queuedResize = null;
        if (!await command(change, "Leverage changed to " + change.leverage + "×.", "leverage")) {
          queuedResize = null;
        }
      }
    } finally {
      resizing = false;
      account(latestAccount);
    }
  };
  el("pnl-run").onchange = () => { if (latestAccount) drawPnl(latestAccount); };
  for (const side of ["up", "down", "flat"]) {
    el(side === "flat" ? "close" : side).onclick = () =>
      command(
        { side, leverage: Number(el("leverage").value) },
        side === "flat"
          ? "Position closed."
          : sideNames[side] + " opened.",
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
  initBooth();
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
