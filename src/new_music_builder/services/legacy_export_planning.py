from __future__ import annotations

from pathlib import Path

from new_music_builder.domain.models import (
    BuildSummaryStats,
    ExportPlan,
    PlannedMediaRow,
    PlannedSide,
    PlannedTrack,
    ProjectConfig,
    ResolvedAppearance,
    ResolvedAppearanceSet,
    TrackEntry,
)
from new_music_builder.services.asset_catalog import AssetEntry
from new_music_builder.services.export_ids import sanitize_export_id
from new_music_builder.services.export_naming import sanitize_sound_script_path_component
from new_music_builder.services.generated_asset_registry import visible_generated_entries_for_kind
from new_music_builder.ui.widgets.appearance_entries import merge_appearance_grid_entries


def build_legacy_export_plan(
    project: ProjectConfig,
    asset_catalog: dict[str, list[AssetEntry]],
    *,
    source_rows: list | None = None,
) -> ExportPlan:
    planned_rows: list[PlannedMediaRow] = []
    planned_sides: list[PlannedSide] = []
    used_row_ids: set[str] = set()
    used_track_ids: set[str] = set()
    used_audio_file_stems: set[str] = set()
    exported_row_id = 0

    candidate_rows = list(project.media_rows if source_rows is None else source_rows)
    for source_row in candidate_rows:
        source_row.ensure_appearances()
        tracks = list(source_row.tracks_a)
        for track_index, track in enumerate(tracks, start=1):
            exported_row_id += 1
            media_name = track.display_label or Path(track.source_path).stem or f"Track {track_index}"
            row_export_id = _build_legacy_export_id(
                media_name,
                used_ids=used_row_ids,
                fallback=f"LegacyTrack{exported_row_id}",
            )
            track_id = _build_legacy_export_id(
                media_name,
                used_ids=used_track_ids,
                fallback=row_export_id,
            )
            export_file_name = _build_legacy_audio_track_file_name(
                media_name,
                fallback_track_id=track_id,
                used_file_stems=used_audio_file_stems,
            )
            planned_track = PlannedTrack(
                track_number=1,
                source_path=str(track.source_path or ""),
                display_label=media_name,
                duration_text=str(track.duration or ""),
                duration_seconds=_legacy_seconds_from_duration_text(str(track.duration or "")),
                needs_conversion=Path(str(track.source_path or "")).suffix.lower() != ".ogg",
                source_row_id=source_row.row_id,
                source_track_index=max(0, track_index - 1),
                export_file_name=export_file_name,
                export_relative_path=export_file_name,
                track_id=track_id,
                sound_id=track_id,
            )
            planned_side = PlannedSide(
                row_id=exported_row_id,
                side="A",
                media_name=media_name,
                cover_path=source_row.cover_path,
                side_id=row_export_id,
                export_folder_name="",
                export_relative_dir="",
                tracks=[planned_track],
            )
            planned_row = PlannedMediaRow(
                row_id=exported_row_id,
                source_row_id=source_row.row_id,
                media_name=media_name,
                cover_path=source_row.cover_path,
                row_mode="singles",
                export_id=row_export_id,
                containers_enabled=False,
                share_playable_texture_sources=True,
                enabled_media=dict(source_row.enabled_media),
                media_modes={kind: "single" for kind in ("cassette", "vinyl", "cd")},
                appearances=_resolve_legacy_track_appearance_set(project, source_row, track, asset_catalog),
                sides=[planned_side],
            )
            planned_rows.append(planned_row)
            planned_sides.append(planned_side)

    stats = BuildSummaryStats(
        media_rows=len(project.media_rows),
        exported_media_rows=len(planned_rows),
        total_sides=len(planned_sides),
        total_songs=len(planned_sides),
        built_songs=len(planned_sides),
        planned_media_rows=len(project.media_rows),
        planned_total_sides=len(planned_sides),
        planned_total_songs=len(planned_sides),
        converted=sum(1 for side in planned_sides for item in side.tracks if item.needs_conversion),
        mod_size_text="0 KB",
        errors=0,
    )
    return ExportPlan(rows=planned_rows, sides=planned_sides, stats=stats)


def _resolve_legacy_track_appearance_set(
    project: ProjectConfig,
    row,
    track: TrackEntry,
    asset_catalog: dict[str, list[AssetEntry]],
) -> ResolvedAppearanceSet:
    resolved = ResolvedAppearanceSet()
    for kind in ("cassette", "vinyl", "cd"):
        selection = track.legacy_appearances.for_kind(kind)
        entries = merge_appearance_grid_entries(
            kind,
            asset_catalog.get(kind, []),
            visible_generated_entries_for_kind(project, kind),
            project.custom_assets.get(kind, []),
        )
        selected = next((entry for entry in entries if entry.key == selection.selected_asset_key), None)
        if selected is not None:
            setattr(
                resolved,
                kind,
                ResolvedAppearance(
                    kind=kind,
                    selected_asset_key=selected.key,
                    source="custom" if selected.is_custom or selected.is_generated else "default",
                    inventory_path=selected.inventory_path,
                    world_path=selected.world_path,
                    sprite_mode="single",
                ),
            )
            continue
        setattr(
            resolved,
            kind,
            ResolvedAppearance(
                kind=kind,
                selected_asset_key=selection.selected_asset_key,
                source=selection.source,
                inventory_path=selection.inventory_full,
                world_path=selection.world_full,
                sprite_mode="single",
            ),
        )
    return resolved


def _legacy_seconds_from_duration_text(value: str) -> int:
    parts = value.strip().split(":")
    if len(parts) != 3:
        return 0
    try:
        hours, minutes, seconds = (int(part) for part in parts)
    except ValueError:
        return 0
    return max(0, hours) * 3600 + max(0, minutes) * 60 + max(0, seconds)


def _build_legacy_audio_track_file_name(
    media_name: str,
    *,
    fallback_track_id: str,
    used_file_stems: set[str],
) -> str:
    preferred_stem = sanitize_sound_script_path_component(media_name, fallback="").strip()
    if not preferred_stem or not preferred_stem.isascii():
        stem = fallback_track_id
        used_file_stems.add(stem)
        return f"{stem}.ogg"

    if preferred_stem not in used_file_stems:
        used_file_stems.add(preferred_stem)
        return f"{preferred_stem}.ogg"

    suffix_index = 2
    while True:
        candidate = f"{preferred_stem}_{suffix_index}"
        if candidate not in used_file_stems:
            used_file_stems.add(candidate)
            return f"{candidate}.ogg"
        suffix_index += 1


def _build_legacy_export_id(value: str, *, used_ids: set[str], fallback: str) -> str:
    base = sanitize_export_id(value, fallback=fallback)
    if base and not base.isdigit() and base not in used_ids:
        used_ids.add(base)
        return base

    if base.isdigit():
        base = fallback

    if base not in used_ids:
        used_ids.add(base)
        return base

    suffix_index = 2
    while True:
        candidate = f"{base}_{suffix_index}"
        if candidate not in used_ids:
            used_ids.add(candidate)
            return candidate
        suffix_index += 1
