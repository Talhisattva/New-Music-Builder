from __future__ import annotations

import hashlib
from pathlib import Path

from new_music_builder.domain.models import PlannedAudioWorkItem, ProjectConfig, TrackEntry
from new_music_builder.services.audio_profile import (
    compression_bucket_name,
    compression_profile_id,
    effective_export_compression_quality,
)


def cache_path_for_work_item(cache_root: str | Path, item: PlannedAudioWorkItem) -> Path:
    return _cache_path_for_source(
        cache_root,
        source_path=item.source_path,
        display_label=item.display_label,
        sample_rate=item.sample_rate,
        compression_quality=item.compression_quality,
    )


def cache_path_for_track(
    cache_root: str | Path,
    track: TrackEntry,
    *,
    sample_rate: int,
    compression_quality: float,
) -> Path | None:
    source_path = str(track.source_path or "").strip()
    if not source_path:
        return None
    source = Path(source_path)
    if not source.exists() or not source.is_file():
        return None
    return _cache_path_for_source(
        cache_root,
        source_path=source_path,
        display_label=track.display_label,
        sample_rate=sample_rate,
        compression_quality=compression_quality,
    )


def refresh_project_cached_ogg_links(project: ProjectConfig) -> None:
    cache_root = str(project.ogg_output_folder or "").strip()
    if not cache_root:
        _clear_missing_cached_links(project)
        return

    compression_quality = effective_export_compression_quality(project.compression_quality)
    for row in project.media_rows:
        for track in row.tracks_a + row.tracks_b:
            source_path = Path(str(track.source_path or ""))
            if source_path.suffix.lower() == ".ogg":
                track.cached_ogg_path = ""
                track.conversion_status = "source_ogg"
                continue

            current_cached = Path(str(track.cached_ogg_path or "").strip()) if str(track.cached_ogg_path or "").strip() else None
            if current_cached is not None and current_cached.exists() and current_cached.is_file():
                track.cached_ogg_path = str(current_cached)
                if track.conversion_status != "source_ogg":
                    track.conversion_status = "cached_ogg"
                continue

            expected = cache_path_for_track(
                cache_root,
                track,
                sample_rate=int(project.sample_rate),
                compression_quality=compression_quality,
            )
            if expected is not None and expected.exists() and expected.is_file():
                track.cached_ogg_path = str(expected)
                if track.conversion_status != "source_ogg":
                    track.conversion_status = "cached_ogg"
                continue

            track.cached_ogg_path = ""
            if track.conversion_status == "cached_ogg":
                track.conversion_status = "needs_convert"


def _clear_missing_cached_links(project: ProjectConfig) -> None:
    for row in project.media_rows:
        for track in row.tracks_a + row.tracks_b:
            source_path = Path(str(track.source_path or ""))
            if source_path.suffix.lower() == ".ogg":
                track.cached_ogg_path = ""
                track.conversion_status = "source_ogg"
                continue
            current_cached = Path(str(track.cached_ogg_path or "").strip()) if str(track.cached_ogg_path or "").strip() else None
            if current_cached is not None and current_cached.exists() and current_cached.is_file():
                continue
            track.cached_ogg_path = ""
            if track.conversion_status == "cached_ogg":
                track.conversion_status = "needs_convert"


def _cache_path_for_source(
    cache_root: str | Path,
    *,
    source_path: str,
    display_label: str,
    sample_rate: int,
    compression_quality: float,
) -> Path:
    source = Path(source_path)
    stat = source.stat()
    bucket_dir = Path(cache_root).resolve() / compression_bucket_name(sample_rate, compression_quality)
    key = "|".join(
        (
            str(source.resolve()),
            str(stat.st_mtime_ns),
            str(stat.st_size),
            str(sample_rate),
            compression_profile_id(compression_quality),
        )
    )
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    safe_stem = _safe_file_stem(display_label or source.stem)
    return bucket_dir / f"{safe_stem}-{digest}.ogg"


def _safe_file_stem(value: str) -> str:
    cleaned = "".join(ch if ch not in '<>:"/\\|?*' else "_" for ch in value).strip()
    return cleaned or "track"
