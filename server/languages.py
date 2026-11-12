"""Supported languages, keyed by ISO-639-1 code."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    code: str
    name: str
    native: str


LANGUAGES: tuple[Language, ...] = (
    Language("af", "Afrikaans", "Afrikaans"),
    Language("ar", "Arabic", "العربية"),
    Language("hy", "Armenian", "Հայերեն"),
    Language("az", "Azerbaijani", "Azərbaycanca"),
    Language("eu", "Basque", "Euskara"),
    Language("bn", "Bengali", "বাংলা"),
    Language("bg", "Bulgarian", "Български"),
    Language("ca", "Catalan", "Català"),
    Language("zh", "Chinese", "中文"),
    Language("hr", "Croatian", "Hrvatski"),
    Language("cs", "Czech", "Čeština"),
    Language("da", "Danish", "Dansk"),
    Language("nl", "Dutch", "Nederlands"),
    Language("en", "English", "English"),
    Language("et", "Estonian", "Eesti"),
    Language("tl", "Filipino", "Filipino"),
    Language("fi", "Finnish", "Suomi"),
    Language("fr", "French", "Français"),
    Language("gl", "Galician", "Galego"),
    Language("de", "German", "Deutsch"),
    Language("el", "Greek", "Ελληνικά"),
    Language("gu", "Gujarati", "ગુજરાતી"),
    Language("he", "Hebrew", "עברית"),
    Language("hi", "Hindi", "हिन्दी"),
    Language("hu", "Hungarian", "Magyar"),
    Language("is", "Icelandic", "Íslenska"),
    Language("id", "Indonesian", "Bahasa Indonesia"),
    Language("it", "Italian", "Italiano"),
    Language("ja", "Japanese", "日本語"),
    Language("kn", "Kannada", "ಕನ್ನಡ"),
    Language("kk", "Kazakh", "Қазақ"),
    Language("ko", "Korean", "한국어"),
    Language("lv", "Latvian", "Latviešu"),
    Language("lt", "Lithuanian", "Lietuvių"),
    Language("ms", "Malay", "Bahasa Melayu"),
    Language("ml", "Malayalam", "മലയാളം"),
    Language("mr", "Marathi", "मराठी"),
    Language("no", "Norwegian", "Norsk"),
    Language("fa", "Persian", "فارسی"),
    Language("pl", "Polish", "Polski"),
    Language("pt", "Portuguese", "Português"),
    Language("pa", "Punjabi", "ਪੰਜਾਬੀ"),
    Language("ro", "Romanian", "Română"),
    Language("ru", "Russian", "Русский"),
    Language("sr", "Serbian", "Српски"),
    Language("sk", "Slovak", "Slovenčina"),
    Language("sl", "Slovenian", "Slovenščina"),
    Language("es", "Spanish", "Español"),
    Language("sw", "Swahili", "Kiswahili"),
    Language("sv", "Swedish", "Svenska"),
    Language("ta", "Tamil", "தமிழ்"),
    Language("te", "Telugu", "తెలుగు"),
    Language("th", "Thai", "ไทย"),
    Language("tr", "Turkish", "Türkçe"),
    Language("uk", "Ukrainian", "Українська"),
    Language("ur", "Urdu", "اردو"),
    Language("vi", "Vietnamese", "Tiếng Việt"),
    Language("cy", "Welsh", "Cymraeg"),
)

BY_CODE: dict[str, Language] = {lang.code: lang for lang in LANGUAGES}

# Alternate codes a speech model might report, mapped to ours.
_ALIASES = {"nb": "no", "nn": "no", "iw": "he", "fil": "tl", "cmn": "zh", "yue": "zh"}
_NAMES = {lang.name.lower(): lang.code for lang in LANGUAGES}


def is_supported(code: str | None) -> bool:
    return code in BY_CODE


def name_of(code: str) -> str:
    lang = BY_CODE.get(code)
    return lang.name if lang else code


def normalize(code: str | None) -> str | None:
    """Map a reported language code or name ("en-US", "nb", "english") to a supported code."""
    if not code:
        return None
    raw = code.strip().lower().replace("_", "-")
    if raw in _NAMES:
        return _NAMES[raw]
    base = raw.split("-")[0]
    base = _ALIASES.get(base, base)
    return base if base in BY_CODE else None
