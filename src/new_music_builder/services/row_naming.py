from __future__ import annotations

import re


_MEDIA_MIX_NAME_RE = re.compile(r"^Media Mix (\d+)$")


def default_media_row_name(row_id: int, *, row_mode: str = "mixtape") -> str:
    if row_mode == "singles":
        return f"Singles Group {row_id}"
    return f"Media Mix {row_id}"


def canonical_media_name(row_id: int, value: str, *, row_mode: str = "mixtape") -> str:
    trimmed = value.strip()
    legacy_default = f"Media Row {row_id}"
    if not trimmed or trimmed == legacy_default:
        return default_media_row_name(row_id, row_mode=row_mode)
    return trimmed


def singles_group_name_for_mode_switch(row_id: int, current_name: str) -> str:
    trimmed = str(current_name or "").strip()
    match = _MEDIA_MIX_NAME_RE.fullmatch(trimmed)
    if match:
        return f"Singles Group {match.group(1)}"
    return default_media_row_name(row_id, row_mode="singles")
