// Browser speech recognition (Web Speech API) and language-to-locale helpers.

const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
export const recognitionSupported = Boolean(SR);

// Default regional variant per language, used when the browser's own languages don't name one.
const LOCALES = {
  af: "af-ZA", ar: "ar-SA", az: "az-AZ", bg: "bg-BG", bn: "bn-IN", ca: "ca-ES", cs: "cs-CZ", cy: "cy-GB",
  da: "da-DK", de: "de-DE", el: "el-GR", en: "en-US", es: "es-ES", et: "et-EE", eu: "eu-ES", fa: "fa-IR",
  fi: "fi-FI", fr: "fr-FR", gl: "gl-ES", gu: "gu-IN", he: "he-IL", hi: "hi-IN", hr: "hr-HR", hu: "hu-HU",
  hy: "hy-AM", id: "id-ID", is: "is-IS", it: "it-IT", ja: "ja-JP", kk: "kk-KZ", kn: "kn-IN", ko: "ko-KR",
  lt: "lt-LT", lv: "lv-LV", ml: "ml-IN", mr: "mr-IN", ms: "ms-MY", nl: "nl-NL", no: "nb-NO", pa: "pa-IN",
  pl: "pl-PL", pt: "pt-BR", ro: "ro-RO", ru: "ru-RU", sk: "sk-SK", sl: "sl-SI", sr: "sr-RS", sv: "sv-SE",
  sw: "sw-KE", ta: "ta-IN", te: "te-IN", th: "th-TH", tl: "fil-PH", tr: "tr-TR", uk: "uk-UA", ur: "ur-PK",
  vi: "vi-VN", zh: "zh-CN",
};

/** Best BCP-47 locale for a language code, preferring the user's own regional variant. */
export function localeFor(code) {
  const base = LOCALES[code]?.split("-")[0] || code;
  const own = (navigator.languages || []).find((l) => l.toLowerCase().split("-")[0] === base && l.includes("-"));
  return own || LOCALES[code] || code;
}

/** The user's browser language, if it is one we support. */
export function browserLanguage(supported) {
  for (const l of navigator.languages || [navigator.language]) {
    let code = l.toLowerCase().split("-")[0];
    if (code === "nb" || code === "nn") code = "no";
    if (code === "fil") code = "tl";
    if (supported.has(code)) return code;
  }
  return "en";
}

/**
 * Continuous recognition that restarts itself (browsers end sessions on long silences)
 * and can be paused while the app is speaking, so it doesn't transcribe its own voice.
 * Events: "interim" {text}, "final" {text}, "error" {error}, "state" {listening}.
 */
export class Recognizer extends EventTarget {
  constructor() {
    super();
    this.rec = null;
    this.lang = null;
    this.wanted = false;
    this.paused = false;
    this.restarts = [];
  }

  get active() { return this.wanted; }

  start(lang) {
    this.lang = lang;
    this.wanted = true;
    this.paused = false;
    this.restarts = [];
    this.#kill();
    this.#spawn();
    this.#emit("state", { listening: true });
  }

  stop() {
    this.wanted = false;
    this.paused = false;
    this.#kill();
    this.#emit("state", { listening: false });
  }

  pause() {
    if (!this.wanted || this.paused) return;
    this.paused = true;
    this.#kill(true);
  }

  resume() {
    if (!this.wanted || !this.paused) return;
    this.paused = false;
    this.#spawn();
  }

  #spawn() {
    const rec = new SR();
    rec.lang = localeFor(this.lang);
    rec.continuous = true;
    rec.interimResults = true;
    rec.maxAlternatives = 1;

    rec.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        const text = result[0].transcript.trim();
        if (result.isFinal) {
          if (text) this.#emit("final", { text });
        } else {
          interim += `${result[0].transcript}`;
        }
      }
      this.#emit("interim", { text: interim.trim() });
    };

    rec.onerror = (event) => {
      if (event.error === "no-speech" || event.error === "aborted") return;
      if (["not-allowed", "service-not-allowed", "language-not-supported", "audio-capture"].includes(event.error)) {
        this.wanted = false;
        this.#emit("state", { listening: false });
      }
      this.#emit("error", { error: event.error });
    };

    rec.onend = () => {
      if (this.rec !== rec) return;
      this.rec = null;
      if (!this.wanted || this.paused) return;
      // Browsers end recognition after silences; restart, but give up if it keeps dying at once.
      const now = Date.now();
      this.restarts = this.restarts.filter((t) => now - t < 5000);
      this.restarts.push(now);
      if (this.restarts.length > 6) {
        this.wanted = false;
        this.#emit("state", { listening: false });
        this.#emit("error", { error: "unstable" });
        return;
      }
      setTimeout(() => { if (this.wanted && !this.paused && !this.rec) this.#spawn(); }, 150);
    };

    this.rec = rec;
    try {
      rec.start();
    } catch (err) {
      console.warn("speech recognition failed to start", err);
    }
  }

  // `graceful` lets the browser deliver the result for speech already heard.
  #kill(graceful = false) {
    const rec = this.rec;
    this.rec = null;
    if (!rec) return;
    try { graceful ? rec.stop() : rec.abort(); } catch {}
    if (!graceful) this.#emit("interim", { text: "" });
  }

  #emit(type, detail) {
    this.dispatchEvent(new CustomEvent(type, { detail }));
  }
}
