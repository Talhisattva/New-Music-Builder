from __future__ import annotations

import math
from pathlib import Path

import miniaudio
import soundfile as sf

from new_music_builder.domain.models import TrackEntry


SUPPORTED_AUDIO_SUFFIXES: tuple[str, ...] = (
    '.ogg',
    '.mp3',
    '.wav',
    '.flac',
    '.m4a',
    '.aac',
    '.wma',
)


def is_supported_audio_path(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_AUDIO_SUFFIXES


def filter_supported_audio_paths(paths: list[str | Path]) -> list[Path]:
    filtered: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            continue
        if not is_supported_audio_path(path):
            continue
        filtered.append(path.resolve())
    return filtered


def _format_duration_seconds(seconds: float) -> str:
    total_seconds = max(0, int(math.floor(seconds + 0.5)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f'{hours:02d}:{minutes:02d}:{secs:02d}'


def read_track_duration(source_path: str | Path) -> str:
    path = Path(source_path).resolve()
    try:
        info = sf.info(str(path))
        duration = float(getattr(info, 'duration', 0.0) or 0.0)
        if duration > 0:
            return _format_duration_seconds(duration)
    except Exception:
        pass

    try:
        info = miniaudio.get_file_info(str(path))
        duration = float(getattr(info, 'duration', 0.0) or 0.0)
        if duration > 0:
            return _format_duration_seconds(duration)
    except Exception:
        pass

    return ''


def build_track_entry(source_path: str | Path) -> TrackEntry:
    path = Path(source_path).resolve()
    return TrackEntry(
        source_path=str(path),
        cached_ogg_path='',
        display_label=path.stem,
        duration=read_track_duration(path),
        conversion_status='source_ogg' if path.suffix.lower() == '.ogg' else 'needs_convert',
    )
