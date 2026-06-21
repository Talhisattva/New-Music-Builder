from __future__ import annotations

from new_music_builder.domain.models import TrackEntry


def duration_seconds_from_text(value: str) -> int:
    parts = value.strip().split(":")
    if len(parts) != 3:
        return 0
    try:
        hours, minutes, seconds = (int(part) for part in parts)
    except ValueError:
        return 0
    return max(0, hours) * 3600 + max(0, minutes) * 60 + max(0, seconds)


def format_duration_seconds(total_seconds: int) -> str:
    total_seconds = max(0, int(total_seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def summarize_tracks(tracks: list[TrackEntry]) -> tuple[int, str]:
    return len(tracks), format_duration_seconds(sum(duration_seconds_from_text(track.duration or "") for track in tracks))
