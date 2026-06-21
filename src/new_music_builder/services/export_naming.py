from __future__ import annotations

import re
from pathlib import Path

_INVALID_FS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1F]')


def sanitize_filesystem_component(value: str, *, fallback: str) -> str:
    cleaned = _INVALID_FS_CHARS.sub("_", (value or "").strip())
    cleaned = cleaned.rstrip(" .")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or fallback


def build_audio_row_folder_name(media_name: str, row_id: int) -> str:
    return sanitize_filesystem_component(media_name, fallback=f"Media Row {row_id}")


def build_audio_side_folder_name(side: str) -> str:
    return f"{side}-Side"


def build_audio_track_file_name(display_label: str, track_number: int) -> str:
    fallback = f"Track {track_number:02d}"
    cleaned_label = sanitize_filesystem_component(display_label, fallback=fallback)
    return f"{track_number:02d} {cleaned_label}.ogg"


def build_audio_track_relative_path(
    *,
    media_name: str,
    row_id: int,
    side: str,
    display_label: str,
    track_number: int,
) -> str:
    row_folder = build_audio_row_folder_name(media_name, row_id)
    side_folder = build_audio_side_folder_name(side)
    file_name = build_audio_track_file_name(display_label, track_number)
    return str(Path(row_folder) / side_folder / file_name)
