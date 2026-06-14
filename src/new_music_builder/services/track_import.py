from __future__ import annotations

from pathlib import Path

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


def build_track_entry(source_path: str | Path) -> TrackEntry:
    path = Path(source_path).resolve()
    return TrackEntry(
        source_path=str(path),
        cached_ogg_path='',
        display_label=path.stem,
        duration='',
        conversion_status='source_ogg' if path.suffix.lower() == '.ogg' else 'needs_convert',
    )
