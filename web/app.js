import { Recognizer, browserLanguage, localeFor, recognitionSupported } from "./speech.js";

const $ = (id) => document.getElementById(id);

const store = {
  get(key, fallback) {
    try {
      const raw = localStorage.getItem(`lt.${key}`);
      return raw === null ? fallback : JSON.parse(raw);
    } catch {
      return fallback;
    }
  },
  set(key, value) {
    try { localStorage.setItem(`lt.${key}`, JSON.stringify(value)); } catch {}
  },
};

const el = {
  conn: $("conn"), feed: $("feed"), empty: $("empty"), emptyTitle: $("emptyTitle"), emptySub: $("emptySub"),
  banner: $("banner"), left: $("leftLang"), right: $("rightLang"), leftLabel: $("leftLabel"), rightLabel: $("rightLabel"),
  swap: $("swapBtn"), micA: $("micA"), micB: $("micB"), micBWrap: $("micBWrap"),
  micAStatus: $("micAStatus"), micBStatus: $("micBStatus"), composer: $("composer"), text: $("textInput"),
  settings: $("settings"), settingsBtn: $("settingsBtn"), themeBtn: $("themeBtn"),
  speak: $("speakToggle"), rate: $("rate"), rateOut: $("rateOut"),
  exportBtn: $("exportBtn"), clearBtn: $("clearBtn"), toast: $("toast"), tpl: $("cardTpl"),
};

const state = {
  server: null,
  codes: new Set(),
  config: null, // mirrored to the server
  prefs: { speak: true, rate: 1 },
  ws: null,
  retry: 0,
  cards: new Map(),
  listening: null, // "a" | "b" | null
  draft: null,
  outbox: [], // phrases waiting for the connection to come back
};

const recognizer = new Recognizer();

// ---------------------------------------------------------------- startup

async function init() {
  try {
    state.server = await (await fetch("api/config")).json();
  } catch {
    showBanner("Could not reach the server. Reload the page once it is running.");
    return;
  }
  const { defaults, languages, limits } = state.server;
  state.codes = new Set(languages.map((l) => l.code));
  state.config = { ...defaults };
  for (const [key, value] of Object.entries(store.get("config", {}))) {
    const valid = key === "mode"
      ? ["translate", "conversation"].includes(value)
      : state.codes.has(value) || (key === "source" && value === "auto");
    if (key in defaults && valid) state.config[key] = value;
  }
  state.prefs = { ...state.prefs, ...store.get("prefs", {}) };
  el.text.maxLength = limits.max_text_chars;

  if (!recognitionSupported) {
    el.micA.disabled = el.micB.disabled = true;
    showBanner("This browser has no speech recognition, so voice input is off. Chrome, Edge and Safari support it. Typing works everywhere.");
  }
  renderMode();
  renderSettings();
  bindEvents();
  connect();
}

// ---------------------------------------------------------------- connection

function connect() {
  const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
  state.ws = ws;
  setConn("connecting");
  ws.onopen = () => {
    state.retry = 0;
    setConn("open");
    send({ type: "config", config: state.config });
    const turns = recentTurns();
    if (turns.length) send({ type: "history", turns });
    for (const payload of state.outbox.splice(0)) send(payload);
  };
  ws.onmessage = (event) => {
    try { handle(JSON.parse(event.data)); } catch (err) { console.error(err); }
  };
  ws.onclose = () => {
    if (state.ws !== ws) return;
    requeueUnfinished();
    // Serverless hosts close connections after a few minutes: reconnect at once, then back off.
    const delay = state.retry === 0 ? 0 : Math.min(15000, 500 * 2 ** state.retry);
    state.retry++;
    setConn(state.retry > 2 ? "closed" : "connecting");
    setTimeout(connect, delay);
  };
}

setInterval(() => send({ type: "ping" }), 25000);

function send(payload) {
  if (state.ws?.readyState !== WebSocket.OPEN) return false;
  state.ws.send(JSON.stringify(payload));
  return true;
}

/** Send a phrase now, or hold it until the connection is back. */
function sendPhrase(payload) {
  if (send(payload)) return;
  state.outbox.push(payload);
  if (state.outbox.length === 1) toast("Reconnecting… your phrase will be sent in a moment.");
}

/** The last few finished exchanges, so a fresh connection keeps the conversation context. */
function recentTurns() {
  return [...state.cards.values()]
    .filter((c) => c.status === "done" && c.target && c.targetLang)
    .slice(-6)
    .map((c) => ({ source_lang: c.sourceLang, source_text: c.source, target_lang: c.targetLang, translated_text: c.target }));
}

/** Phrases cut off by a dropped connection are removed and sent again after reconnecting. */
function requeueUnfinished() {
  const retry = [];
  for (const card of state.cards.values()) {
    if (card.status !== "translating" || !card.source) continue;
    retry.push({ type: "text", text: card.source, ...(card.kind === "voice" && { spoken: card.sourceLang }) });
    card.el.remove();
    state.cards.delete(card.id);
  }
  state.outbox.unshift(...retry);
  if (!state.cards.size && !state.draft) el.empty.hidden = false;
}

function setConn(s) {
  const label = { connecting: "Connecting", open: "Connected", closed: "Offline" }[s];
  el.conn.dataset.state = s;
  el.conn.title = label;
  el.conn.querySelector(".conn-label").textContent = label;
}

// ---------------------------------------------------------------- server events

function handle(msg) {
  const card = msg.id ? state.cards.get(msg.id) : null;
  switch (msg.type) {
    case "utterance.start":
      createCard(msg.id, msg.kind);
      break;
    case "transcript.done":
      if (card) patch(card, { source: msg.text, sourceLang: msg.language, status: "translating" });
      break;
    case "translation.delta":
      if (card) patch(card, { target: card.target + msg.delta });
      break;
    case "translation.done":
      if (!card) break;
      patch(card, { target: msg.text, sourceLang: msg.source || card.sourceLang, targetLang: msg.target, status: "done" });
      if (state.prefs.speak && msg.text) enqueuePlayback(card);
      break;
    case "error":
      if (!card) { toast(msg.message); break; }
      patch(card, { status: card.target ? "done" : "error" });
      Object.assign(card.el.querySelector(".card-error"), { textContent: msg.message, hidden: false });
      break;
  }
}

// ---------------------------------------------------------------- cards

function newCardNode() {
  return el.tpl.content.firstElementChild.cloneNode(true);
}

function insertCard(node) {
  el.empty.hidden = true;
  if (state.draft?.isConnected) el.feed.insertBefore(node, state.draft);
  else el.feed.append(node);
}

function createCard(id, kind) {
  const nearBottom = isNearBottom();
  const node = newCardNode();
  const card = {
    id, kind, el: node, source: "", target: "", sourceLang: null, targetLang: null,
    status: "translating", time: new Date(), mode: state.config.mode, langB: state.config.lang_b,
  };
  node.querySelector(".card-kind").textContent = kind === "voice" ? "Voice" : "Typed";
  const time = node.querySelector(".card-time");
  time.dateTime = card.time.toISOString();
  time.textContent = card.time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  node.querySelector('[data-act="play"]').addEventListener("click", () => enqueuePlayback(card, true));
  node.querySelector('[data-act="copy"]').addEventListener("click", () => copy(card.target));
  state.cards.set(id, card);
  insertCard(node);
  render(card);
  if (nearBottom) scrollToBottom();
}

function patch(card, changes) {
  const nearBottom = isNearBottom();
  Object.assign(card, changes);
  render(card);
  if (nearBottom) scrollToBottom();
}

function render(card) {
  const node = card.el;
  node.dataset.status = card.status;
  node.querySelector(".source").textContent = card.source;
  node.querySelector(".target").textContent = card.target;
  let src = card.status === "done" ? "AUTO" : "…";
  if (card.sourceLang) src = card.sourceLang.toUpperCase();
  const tgt = card.targetLang ? card.targetLang.toUpperCase() : "…";
  const chip = node.querySelector(".chip");
  chip.textContent = `${src} → ${tgt}`;
  chip.title = `${langName(card.sourceLang) || "Detected"} → ${langName(card.targetLang) || ""}`;
  if (card.mode === "conversation" && card.sourceLang) node.dataset.side = card.sourceLang === card.langB ? "b" : "a";
}

function showDraft(text, lang) {
  if (!text) {
    state.draft?.remove();
    state.draft = null;
    if (!state.cards.size) el.empty.hidden = false;
    return;
  }
  const nearBottom = isNearBottom();
  if (!state.draft) {
    state.draft = newCardNode();
    state.draft.classList.add("draft");
    state.draft.querySelector(".card-kind").textContent = "Listening…";
    el.empty.hidden = true;
    el.feed.append(state.draft);
  }
  state.draft.querySelector(".chip").textContent = lang.toUpperCase();
  state.draft.querySelector(".source").textContent = text;
  if (state.config.mode === "conversation") state.draft.dataset.side = lang === state.config.lang_b ? "b" : "a";
  else delete state.draft.dataset.side;
  if (nearBottom) scrollToBottom();
}

function clearCards() {
  for (const card of state.cards.values()) card.el.remove();
  state.cards.clear();
  player.queue.length = 0;
  if ("speechSynthesis" in window) speechSynthesis.cancel();
  if (!state.draft) el.empty.hidden = false;
  send({ type: "reset" });
}

function isNearBottom() {
  return window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 160;
}

function scrollToBottom() {
  requestAnimationFrame(() => window.scrollTo({ top: document.documentElement.scrollHeight, behavior: "smooth" }));
}

// ---------------------------------------------------------------- spoken output

const player = { queue: [], busy: false };

function enqueuePlayback(card, manual = false) {
  if (!card.target || !card.targetLang || !("speechSynthesis" in window)) return;
  if (manual) {
    player.queue.length = 0;
    speechSynthesis.cancel();
  }
  player.queue.push(card);
  if (!player.busy) void playNext();
}

async function playNext() {
  const card = player.queue.shift();
  if (!card) {
    player.busy = false;
    setTimeout(() => { if (!player.busy) resumeListening(); }, 300);
    return;
  }
  player.busy = true;
  pauseListening();
  const btn = card.el.querySelector('[data-act="play"]');
  btn.classList.add("playing");
  await speak(card.target, card.targetLang);
  btn.classList.remove("playing");
  void playNext();
}

function pickVoice(lang) {
  const voices = speechSynthesis.getVoices();
  const locale = localeFor(lang).toLowerCase();
  const base = locale.split("-")[0];
  let best = null;
  let bestScore = -1;
  for (const voice of voices) {
    const vl = voice.lang.toLowerCase().replace("_", "-");
    if (vl.split("-")[0] !== base) continue;
    let score = vl === locale ? 3 : 1;
    if (/natural|neural|online|premium|enhanced/i.test(voice.name)) score += 4;
    if (/google/i.test(voice.name)) score += 2;
    if (score > bestScore) { best = voice; bestScore = score; }
  }
  return best;
}

function speak(text, lang) {
  return new Promise((resolve) => {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = localeFor(lang);
    utterance.rate = state.prefs.rate;
    const voice = pickVoice(lang);
    if (voice) utterance.voice = voice;
    const done = () => { clearTimeout(timer); resolve(); };
    // Some browsers never fire `end`; don't let the queue (and the paused mic) hang.
    const timer = setTimeout(done, 3000 + (text.length * 150) / state.prefs.rate);
    utterance.onend = utterance.onerror = done;
    speechSynthesis.speak(utterance);
  });
}

if ("speechSynthesis" in window) speechSynthesis.onvoiceschanged = () => speechSynthesis.getVoices();

// ---------------------------------------------------------------- voice input

function micLanguage(which) {
  const c = state.config;
  if (c.mode === "conversation") return which === "b" ? c.lang_b : c.lang_a;
  return c.source === "auto" ? browserLanguage(state.codes) : c.source;
}

function startListening(which) {
  state.listening = which;
  recognizer.start(micLanguage(which));
  renderMics();
  if (player.busy) pauseListening();
}

function stopListening() {
  state.listening = null;
  recognizer.stop();
  showDraft("");
  renderMics();
}

function toggleMic(which) {
  if (state.listening === which) stopListening();
  else startListening(which);
}

function pauseListening() {
  if (!state.listening) return;
  recognizer.pause();
  renderMics("paused");
}

function resumeListening() {
  if (!state.listening) return;
  recognizer.resume();
  renderMics();
}

/** Restart recognition after a language or mode change. */
function refreshListening() {
  if (!state.listening) return renderMics();
  const which = state.config.mode === "conversation" ? state.listening : "a";
  startListening(which);
}

function renderMics(mode) {
  const conversation = state.config.mode === "conversation";
  el.micBWrap.hidden = !conversation;
  for (const [which, button, status] of [["a", el.micA, el.micAStatus], ["b", el.micB, el.micBStatus]]) {
    const on = state.listening === which;
    const lang = langName(micLanguage(which)) || "";
    button.setAttribute("aria-pressed", String(on));
    button.dataset.state = on ? mode || "listening" : "off";
    button.setAttribute("aria-label", on ? `Stop listening` : `Start listening in ${lang}`);
    button.title = on ? "Stop listening" : `Speak ${lang}`;
    let label = lang;
    if (on) label = mode === "paused" ? "Speaking…" : "Listening";
    status.textContent = label;
  }
}

recognizer.addEventListener("interim", (e) => {
  if (state.listening) showDraft(e.detail.text, micLanguage(state.listening));
});

recognizer.addEventListener("final", (e) => {
  const lang = recognizer.lang;
  showDraft("");
  sendPhrase({ type: "text", text: e.detail.text, spoken: lang });
});

recognizer.addEventListener("state", (e) => {
  if (!e.detail.listening && state.listening) {
    state.listening = null;
    showDraft("");
    renderMics();
  }
});

const RECOGNITION_ERRORS = {
  "not-allowed": "Microphone access was blocked. Allow it in your browser settings.",
  "service-not-allowed": "Speech recognition is blocked in this browser.",
  "audio-capture": "No microphone was found.",
  network: "Speech recognition needs an internet connection in this browser.",
  "language-not-supported": "Your browser can't recognise that language. Try typing instead.",
  unstable: "Speech recognition keeps stopping. Tap the mic to try again.",
};

recognizer.addEventListener("error", (e) => {
  toast(RECOGNITION_ERRORS[e.detail.error] || `Speech recognition error: ${e.detail.error}`);
});

// ---------------------------------------------------------------- languages & mode

function langName(code) {
  return state.server?.languages.find((l) => l.code === code)?.name;
}

function fillSelect(select, value, withAuto) {
  const options = state.server.languages.map((l) => {
    const label = l.native && l.native !== l.name ? `${l.name} · ${l.native}` : l.name;
    return `<option value="${l.code}">${label}</option>`;
  });
  if (withAuto) options.unshift('<option value="auto">Detect language</option>');
  select.innerHTML = options.join("");
  select.value = value;
}

function renderMode() {
  const c = state.config;
  const conversation = c.mode === "conversation";
  document.querySelectorAll(".segmented [data-mode]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.mode === c.mode)));
  el.feed.classList.toggle("conversation", conversation);
  el.leftLabel.textContent = conversation ? "Person A speaks" : "From";
  el.rightLabel.textContent = conversation ? "Person B speaks" : "To";
  fillSelect(el.left, conversation ? c.lang_a : c.source, !conversation);
  fillSelect(el.right, conversation ? c.lang_b : c.target, false);
  el.emptyTitle.textContent = conversation ? "Take turns on the two mics" : "Tap the mic and start talking";
  el.emptySub.textContent = conversation
    ? "Each person taps their own mic and speaks their language. Every phrase is translated for the other person and read aloud."
    : "Each phrase is translated as soon as you pause. With “Detect language” the mic listens in your browser's language; pick a language to speak another. You can also type below.";
  renderMics();
}

function pushConfig() {
  store.set("config", state.config);
  send({ type: "config", config: state.config }); // also re-sent on every reconnect
}

function onLangChange() {
  if (state.config.mode === "conversation") {
    state.config.lang_a = el.left.value;
    state.config.lang_b = el.right.value;
  } else {
    state.config.source = el.left.value;
    state.config.target = el.right.value;
  }
  pushConfig();
  refreshListening();
}

function swapLanguages() {
  const c = state.config;
  if (c.mode === "conversation") {
    [c.lang_a, c.lang_b] = [c.lang_b, c.lang_a];
  } else {
    const from = c.source === "auto" ? browserLanguage(state.codes) : c.source;
    c.source = c.target;
    c.target = from;
    if (from === c.source) c.target = from === "en" ? "es" : "en";
  }
  renderMode();
  pushConfig();
  refreshListening();
}

// ---------------------------------------------------------------- settings

function renderSettings() {
  el.speak.checked = state.prefs.speak;
  el.rate.value = state.prefs.rate;
  el.rateOut.textContent = `${Number(state.prefs.rate).toFixed(1)}×`;
}

function updatePrefs(changes) {
  Object.assign(state.prefs, changes);
  store.set("prefs", state.prefs);
  renderSettings();
}

function exportTranscript() {
  const cards = [...state.cards.values()].filter((c) => c.target);
  if (!cards.length) return toast("Nothing to export yet.");
  const lines = cards.map((c) =>
    `[${c.time.toLocaleTimeString()}] ${langName(c.sourceLang) || "Detected"} → ${langName(c.targetLang) || ""}\n${c.source}\n${c.target}\n`,
  );
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" }));
  a.download = `translation-${new Date().toISOString().slice(0, 10)}.txt`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

// ---------------------------------------------------------------- misc UI

let toastTimer;
function toast(message) {
  el.toast.textContent = message;
  el.toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.toast.hidden = true; }, 4000);
}

function showBanner(message) {
  el.banner.textContent = message;
  el.banner.hidden = false;
}

async function copy(text) {
  try {
    await navigator.clipboard.writeText(text);
    toast("Copied");
  } catch {
    toast("Copy failed");
  }
}

function autoGrow() {
  el.text.style.height = "auto";
  el.text.style.height = `${el.text.scrollHeight}px`;
}

function submitText() {
  const text = el.text.value.trim();
  if (!text) return;
  sendPhrase({ type: "text", text });
  el.text.value = "";
  autoGrow();
}

function toggleTheme() {
  const root = document.documentElement;
  const dark = root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  root.dataset.theme = dark ? "light" : "dark";
  try { localStorage.setItem("lt.theme", root.dataset.theme); } catch {}
}

function bindEvents() {
  el.micA.addEventListener("click", () => toggleMic("a"));
  el.micB.addEventListener("click", () => toggleMic("b"));
  el.left.addEventListener("change", onLangChange);
  el.right.addEventListener("change", onLangChange);
  el.swap.addEventListener("click", swapLanguages);
  el.themeBtn.addEventListener("click", toggleTheme);
  el.settingsBtn.addEventListener("click", () => { renderSettings(); el.settings.showModal(); });
  el.exportBtn.addEventListener("click", exportTranscript);
  el.clearBtn.addEventListener("click", () => { clearCards(); el.settings.close(); });
  el.speak.addEventListener("change", () => {
    updatePrefs({ speak: el.speak.checked });
    if (!el.speak.checked && "speechSynthesis" in window) { player.queue.length = 0; speechSynthesis.cancel(); }
  });
  el.rate.addEventListener("input", () => updatePrefs({ rate: Number(el.rate.value) }));

  document.querySelectorAll(".segmented [data-mode]").forEach((button) =>
    button.addEventListener("click", () => {
      if (state.config.mode === button.dataset.mode) return;
      state.config.mode = button.dataset.mode;
      renderMode();
      pushConfig();
      refreshListening();
    }),
  );

  el.composer.addEventListener("submit", (e) => { e.preventDefault(); submitText(); });
  el.text.addEventListener("input", autoGrow);
  el.text.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      submitText();
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.code !== "Space" || e.repeat || el.settings.open || el.micA.disabled) return;
    if (e.target.closest("input, textarea, select, button, [contenteditable]")) return;
    e.preventDefault();
    if (state.listening) stopListening();
    else startListening("a");
  });
}

await init();
