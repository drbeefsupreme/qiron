"use strict";

const pnlTime = new Intl.DateTimeFormat(undefined, {hour: "numeric", minute: "2-digit"});
const pnlAmount = cents => (cents < 0 ? "−" : cents > 0 ? "+" : "") + fmt(Math.abs(cents) / 100);

const pnlScale = new Intl.NumberFormat("en-US", {notation: "compact", maximumFractionDigits: 1});

function drawPnl(data) {
  const runs = data.pnl_runs;
  if (!runs?.length) return;
  const menu = el("pnl-run");
  const signature = runs.map(run => run.id).join(",");
  if (menu.dataset.runs !== signature) {
    const previous = menu.value;
    menu.replaceChildren(new Option("All slugs", "all"), ...runs.slice().reverse().map(run => new Option("Slug " + run.id, run.id)));
    menu.value = runs.some(run => String(run.id) === previous) ? previous : "all";
    menu.dataset.runs = signature;
  }

  const selected = menu.value === "all" ? runs : runs.filter(run => String(run.id) === menu.value);
  const last = selected[selected.length - 1];
  const lastValue = last.points[last.points.length - 1][1];
  const end = last.ended_at_ms && menu.value !== "all" ? last.ended_at_ms : data.as_of_ms;
  const begin = selected[0].points[0][0];
  let low = 0, high = 0;
  for (const run of selected) {
    for (const [, value] of run.points) {
      low = Math.min(low, value);
      high = Math.max(high, value);
    }
  }
  const x = time => 5 + 470 * (time - begin) / Math.max(1, end - begin);
  const y = value => high === low ? 60 : 112 - 104 * (value - low) / (high - low);
  const svg = el("pnl-chart");
  function shape(tag, attributes) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [k, v] of Object.entries(attributes)) node.setAttribute(k, v);
    return node;
  }
  const zero = y(0);
  const parts = [shape("line", {x1: 0, x2: 480, y1: zero, y2: zero, class: "pnl-zero"})];
  for (const run of selected) {
    const points = run.points;
    const latest = points[points.length - 1];
    const color = latest[1] < 0 ? "var(--red)" : "var(--green)";
    const path = points.map(([ms, cents], i) => (i ? "L" : "M") + x(ms).toFixed(2) + " " + y(cents).toFixed(2));
    const stop = run.ended_at_ms ?? end;
    path.push("L" + x(stop).toFixed(2) + " " + y(latest[1]).toFixed(2));
    parts.push(shape("path", {d: path.join(" "), fill: "none", stroke: color, "stroke-width": 2, "data-slug": run.id}),
      shape("circle", {cx: x(stop), cy: y(latest[1]), r: 3, fill: color}));
  }
  svg.replaceChildren(...parts);
  svg.setAttribute("aria-label", selected.length + " portfolio line" + (selected.length === 1 ? "" : "s") + ". Slug " + last.id + " profit and loss " + pnlAmount(lastValue) + " PISS COIN.");
  el("pnl-slug").textContent = "Slug " + last.id;
  el("pnl-high").textContent = high === low ? "" : pnlScale.format(high / 100);
  el("pnl-low").textContent = high === low ? "" : pnlScale.format(low / 100);
  el("pnl-value").textContent = pnlAmount(lastValue);
  el("pnl-value").style.color = lastValue < 0 ? "var(--red)" : "var(--green)";
  el("pnl-from").textContent = pnlTime.format(begin);
  el("pnl-to").textContent = last.ended_at_ms && menu.value !== "all" ? "Liquidated · " + pnlTime.format(end) : "Now";
}
