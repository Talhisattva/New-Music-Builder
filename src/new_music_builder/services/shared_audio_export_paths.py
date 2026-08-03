from __future__ import annotations

from pathlib import Path

from new_music_builder.domain.models import ExportPlan


def assign_shared_audio_export_paths(plan: ExportPlan) -> None:
    canonical_paths_by_source: dict[str, str] = {}

    for side in plan.sides:
        for track in side.tracks:
            default_path = track.export_relative_path.replace("\\", "/")
            track.export_relative_path = default_path
            source_key = normalized_source_path_key(track.source_path)
            shared_path = canonical_paths_by_source.setdefault(source_key, default_path)
            track.shared_export_relative_path = shared_path


def normalized_source_path_key(source_path: str) -> str:
    raw_source_path = str(source_path or "").strip()
    if not raw_source_path:
        return ""

    try:
        resolved = Path(raw_source_path).resolve()
    except OSError:
        return raw_source_path
    return str(resolved)
