"""Presentation-only translation. Stored states and provider errors stay canonical."""

from functools import lru_cache
import re
import unicodedata
from string import Formatter

from youtube_sync_translations import ENGLISH, TEMPLATES

LANGUAGES = (("es", "Español"), ("en", "English"))
_language = "es"
_qt_translator = None


def normalize_language(value):
    return value if value in {"es", "en"} else "es"


def language():
    return _language


def set_language(value):
    global _language, _qt_translator
    _language = normalize_language(value)
    _translate.cache_clear()
    # Native dialogs must use the same language, not the Windows locale.
    from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is not None:
        if _qt_translator is not None:
            app.removeTranslator(_qt_translator)
        _qt_translator = QTranslator(app)
        if _language == "es":
            _qt_translator.load("qtbase_es", QLibraryInfo.path(QLibraryInfo.TranslationsPath))
            app.installTranslator(_qt_translator)
        QLocale.setDefault(QLocale("es_ES" if _language == "es" else "en_GB"))
    return _language


def _compile(source, destination):
    parts, names = [], []
    for literal, name, _spec, _conversion in Formatter().parse(source):
        parts.append(re.escape(literal))
        if name is not None:
            names.append(name)
            parts.append("(.+?)")
    return re.compile("^" + "".join(parts) + "$", re.DOTALL), names, destination


_patterns = tuple(_compile(source, destination) for source, destination in TEMPLATES)


def _key(text):
    return "".join(char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char)).casefold()


_normalized = {_key(source): destination for source, destination in ENGLISH.items()}


@lru_cache(maxsize=2048)
def _translate(text):
    if text in ENGLISH:
        return ENGLISH[text]
    if _key(text) in _normalized:
        result = _normalized[_key(text)]
        return result.upper() if text.isupper() else result
    for pattern, names, destination in _patterns:
        match = pattern.fullmatch(text)
        if match:
            values = dict(zip(names, match.groups()))
            for name in ("error", "context", "reason", "criterion", "message", "action", "option", "slot"):
                if name in values:
                    values[name] = _translate(values[name])
            return destination.format_map(values)
    # Multi-line notices are assembled from independent, already redacted messages.
    for separator in ("\n", " · ", " | ", " / "):
        if separator in text:
            return separator.join(_translate(part) for part in text.split(separator))
    return text


def t(text):
    if _language != "en" or not isinstance(text, str) or len(text) > 65536:
        return text
    return _translate(text)


def source_text(control):
    return control.property("sourceText") or control.text()
