from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path


MAX_EXPORT_ID_LENGTH = 48


def sanitize_export_id(value: str, *, fallback: str = "Track") -> str:
    base = Path(value).stem
    normalized = unicodedata.normalize("NFD", base)
    stripped = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    cleaned = re.sub(r"[^A-Za-z0-9]", "", stripped)
    if not cleaned:
        cleaned = fallback
    return cleaned[:MAX_EXPORT_ID_LENGTH]


def unique_export_id(value: str, used_ids: set[str], *, fallback: str = "Track") -> str:
    stem = Path(value).stem
    normalized = unicodedata.normalize("NFD", stem)
    stripped = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    raw_base = re.sub(r"[^A-Za-z0-9]", "", stripped)
    base = sanitize_export_id(value, fallback=fallback)
    needs_suffix = raw_base == "" or raw_base.isdigit()
    if not needs_suffix and base not in used_ids:
        used_ids.add(base)
        return base

    digest = hashlib.sha1(stem.encode("utf-8")).hexdigest().upper()[:6]
    max_base_len = max(1, MAX_EXPORT_ID_LENGTH - 1 - len(digest))
    candidate = f"{base[:max_base_len]}_{digest}"
    if candidate not in used_ids:
        used_ids.add(candidate)
        return candidate

    suffix_index = 2
    while True:
        suffix = f"_{digest}{suffix_index}"
        max_base_len = max(1, MAX_EXPORT_ID_LENGTH - len(suffix))
        candidate = f"{base[:max_base_len]}{suffix}"
        if candidate not in used_ids:
            used_ids.add(candidate)
            return candidate
        suffix_index += 1
