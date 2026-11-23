"use strict";

function initPhrasePicker() {
  const picker = el("phrase-picker"), search = el("phrase-search"), list = el("phrase-list");
  const spot = el("phrase-spot"), place = el("phrase-place"), random = el("phrase-random");
  const status = el("phrase-status"), previewText = el("phrase-preview");
  let phrases = [], loading = false;

  for (let id = 1; id <= 5; id++) spot.add(new Option(id + " · " + widgetNames["line" + id], id));

  function previewSelection() {
    const phrase = phrases[list.value];
    previewText.textContent = phrase?.text ?? "";
    previewText.scrollTop = 0;
    place.disabled = !phrase;
  }

  function filter() {
    const previous = list.value;
    const query = search.value.trim().toLowerCase().replace(/\s+/g, " ");
    list.replaceChildren();
    phrases.forEach(({title, text}, index) => {
      if ((title + " " + text).toLowerCase().replace(/\s+/g, " ").includes(query)) {
        list.add(new Option(title, index));
      }
    });
    list.value = previous;
    if (list.selectedIndex < 0 && list.length) list.selectedIndex = 0;
    status.textContent = list.length + " of " + phrases.length + " phrases";
    previewSelection();
  }

  picker.ontoggle = async () => {
    if (!picker.open || phrases.length || loading) return;
    loading = true;
    status.textContent = "Loading phrases…";
    try {
      phrases = await api("operator/phrases");
      filter();
      random.disabled = !phrases.length;
    } catch {
      status.textContent = "Library unavailable. Close and reopen to retry.";
    } finally {
      loading = false;
    }
  };

  function stagePhrase() {
    if (!draft || switching || list.selectedIndex < 0) return;
    const layer = Number(spot.value), key = "layer" + layer, widget = "line" + layer;
    const {title, text} = phrases[list.value];
    const widgets = effectiveStack();
    if (!widgets.includes(widget)) setWidgets([...widgets, widget]);
    el(key).value = text;
    edit(key, {layer, text});
    renderPreview();
    status.textContent = title + " → draft scroll " + spot.selectedOptions[0].text;
  }

  search.oninput = filter;
  list.onchange = previewSelection;
  place.onclick = stagePhrase;
  random.onclick = () => {
    if (!draft || switching) return;
    search.value = "";
    filter();
    list.selectedIndex = Math.floor(Math.random() * phrases.length);
    spot.selectedIndex = Math.floor(Math.random() * spot.length);
    previewSelection();
    stagePhrase();
  };
}
