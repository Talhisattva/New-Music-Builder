from __future__ import annotations

import json
from pathlib import Path

_TRANSLATIONS: dict[str, str] = {}


def _locale_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "locale"


def load_translations(locale: str = "zh_CN") -> None:
    global _TRANSLATIONS
    path = _locale_dir() / f"{locale}.json"
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        _TRANSLATIONS = json.load(f)


def t(text: str) -> str:
    return _TRANSLATIONS.get(text, text)
