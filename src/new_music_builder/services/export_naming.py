from __future__ import annotations

import re
from pathlib import Path

_INVALID_FS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1F]')
_SOUND_SCRIPT_UNSAFE_CHARS = re.compile(r"[,]+")


def sanitize_filesystem_component(value: str, *, fallback: str) -> str:
    cleaned = _INVALID_FS_CHARS.sub("_", (value or "").strip())
    cleaned = cleaned.rstrip(" .")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or fallback


def build_audio_row_folder_name(media_name: str, row_id: int, *, export_id: str | None = None) -> str:
    if export_id:
        return sanitize_filesystem_component(export_id, fallback=f"MediaRow{row_id}")
    return sanitize_sound_script_path_component(media_name, fallback=f"Media Row {row_id}")


def build_audio_side_folder_name(side: str) -> str:
    return f"{side}-Side"


def build_audio_track_file_name(display_label: str, track_number: int, *, track_id: str | None = None) -> str:
    fallback = f"Track{track_number:02d}"
    if track_id:
        cleaned_label = sanitize_filesystem_component(track_id, fallback=fallback)
    else:
        cleaned_label = sanitize_sound_script_path_component(display_label, fallback=fallback)
    return f"{cleaned_label}.ogg"


def build_audio_track_relative_path(
    *,
    media_name: str,
    row_id: int,
    side: str,
    display_label: str,
    track_number: int,
    export_id: str | None = None,
    track_id: str | None = None,
) -> str:
    row_folder = build_audio_row_folder_name(media_name, row_id, export_id=export_id)
    side_folder = build_audio_side_folder_name(side)
    file_name = build_audio_track_file_name(display_label, track_number, track_id=track_id)
    return str(Path(row_folder) / side_folder / file_name)


def sanitize_sound_script_path_component(value: str, *, fallback: str) -> str:
    cleaned = sanitize_filesystem_component(value, fallback=fallback)
    cleaned = _SOUND_SCRIPT_UNSAFE_CHARS.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or fallback
