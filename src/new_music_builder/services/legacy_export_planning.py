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
from new_music_builder.services.export_ids import unique_export_id
from new_music_builder.services.export_naming import build_audio_row_folder_name, build_audio_track_file_name
from new_music_builder.services.generated_asset_registry import visible_generated_entries_for_kind
from new_music_builder.ui.widgets.appearance_entries import merge_appearance_grid_entries


def build_legacy_export_plan(project: ProjectConfig, asset_catalog: dict[str, list[AssetEntry]]) -> ExportPlan:
    planned_rows: list[PlannedMediaRow] = []
    planned_sides: list[PlannedSide] = []
    used_row_ids: set[str] = set()
    used_track_ids: set[str] = set()
    exported_row_id = 0

    for source_row in project.media_rows:
        source_row.ensure_appearances()
        tracks = list(source_row.tracks_a)
        for track_index, track in enumerate(tracks, start=1):
            exported_row_id += 1
            media_name = track.display_label or Path(track.source_path).stem or f"Track {track_index}"
            row_export_id = unique_export_id(
                f"{source_row.row_id}_{track_index}_{media_name}",
                used_row_ids,
                fallback=f"LegacyTrack{exported_row_id}",
            )
            row_folder_name = build_audio_row_folder_name(media_name, exported_row_id, export_id=row_export_id)
            track_id = unique_export_id(
                f"{row_export_id}_{media_name}",
                used_track_ids,
                fallback=f"{row_export_id}Track1",
            )
            planned_track = PlannedTrack(
                track_number=1,
                source_path=str(track.source_path or ""),
                display_label=media_name,
                duration_text=str(track.duration or ""),
                duration_seconds=_legacy_seconds_from_duration_text(str(track.duration or "")),
                needs_conversion=Path(str(track.source_path or "")).suffix.lower() != ".ogg",
                export_file_name=build_audio_track_file_name(media_name, 1, track_id=track_id),
                export_relative_path=str(Path(row_folder_name) / build_audio_track_file_name(media_name, 1, track_id=track_id)),
                track_id=track_id,
                sound_id=track_id,
            )
            planned_side = PlannedSide(
                row_id=exported_row_id,
                side="A",
                media_name=media_name,
                cover_path=source_row.cover_path,
                side_id=row_export_id,
                export_folder_name=row_folder_name,
                export_relative_dir=row_folder_name,
                tracks=[planned_track],
            )
            planned_row = PlannedMediaRow(
                row_id=exported_row_id,
                media_name=media_name,
                cover_path=source_row.cover_path,
                export_id=row_export_id,
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
