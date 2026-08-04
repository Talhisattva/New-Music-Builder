from __future__ import annotations

from datetime import datetime
from pathlib import Path

from new_music_builder.domain.models import (
    AppearanceKind,
    BuildPreviewScenario,
    BuildSummaryStats,
    ConversionSideGroup,
    ConversionSongProgress,
    ExportLogLine,
    ExportPlan,
    GeneratedPreviewCell,
    GeneratedPreviewRow,
    MediaKind,
    PlannedMediaRow,
    PlannedSide,
    PlannedTrack,
    ProjectConfig,
    ResolvedAppearance,
    ResolvedAppearanceSet,
    TrackEntry,
)
from new_music_builder.platform.i18n import t
from new_music_builder.services.asset_catalog import AssetEntry
from new_music_builder.services.export_ids import unique_export_id
from new_music_builder.services.generated_asset_registry import visible_generated_entries_for_kind
from new_music_builder.services.legacy_export_planning import build_legacy_export_plan
from new_music_builder.services.export_naming import (
    build_audio_row_folder_name,
    build_audio_side_folder_name,
    build_audio_track_file_name,
    build_audio_track_relative_path,
)
from new_music_builder.ui.widgets.appearance_entries import merge_appearance_grid_entries

_SLOT_KINDS: tuple[tuple[AppearanceKind, MediaKind], ...] = (
    ("cassette", "cassette"),
    ("vinyl", "vinyl"),
    ("cd", "cd"),
    ("case", "cassette"),
    ("jacket", "vinyl"),
    ("cd_cover", "cd"),
)


def build_export_plan(project: ProjectConfig, asset_catalog: dict[str, list[AssetEntry]]) -> ExportPlan:
    planned_rows: list[PlannedMediaRow] = []
    planned_sides: list[PlannedSide] = []
    used_row_ids: set[str] = set()
    used_track_ids: set[str] = set()
    next_singles_exported_row_id = max((row.row_id for row in project.media_rows), default=0)

    for row in project.media_rows:
        if row.row_mode == "singles":
            singles_plan = build_legacy_export_plan(project, asset_catalog, source_rows=[row])
            next_singles_exported_row_id = _remap_singles_plan_row_ids(
                singles_plan,
                next_exported_row_id=next_singles_exported_row_id,
            )
            planned_rows.extend(singles_plan.rows)
            planned_sides.extend(singles_plan.sides)
            used_row_ids.update(item.export_id for item in singles_plan.rows if item.export_id)
            used_track_ids.update(track.track_id for side in singles_plan.sides for track in side.tracks if track.track_id)
            continue
        row.ensure_appearances()
        sides: list[PlannedSide] = []
        row_export_id = unique_export_id(row.media_name, used_row_ids, fallback=f"MediaRow{row.row_id}")
        row_folder_name = build_audio_row_folder_name(row.media_name, row.row_id, export_id=row_export_id)
        show_side_suffix = _planned_row_uses_split_side_suffix(row)
        for side_name, tracks in (("A", row.tracks_a), ("B", row.tracks_b)):
            if not tracks:
                continue
            side_folder_name = build_audio_side_folder_name(side_name)
            side_id = f"{row_export_id}Side{side_name}"
            sides.append(
                PlannedSide(
                    row_id=row.row_id,
                    side=side_name,
                    media_name=row.media_name,
                    cover_path=row.cover_path,
                    side_id=side_id,
                    export_folder_name=side_folder_name,
                    export_relative_dir=str(Path(row_folder_name) / side_folder_name),
                    queue_label=row.media_name,
                    show_side_suffix=show_side_suffix,
                    side_display_text=f"{side_name}-SIDE" if show_side_suffix else "",
                    tracks=[
                        _build_planned_track(
                            row_id=row.row_id,
                            media_name=row.media_name,
                            row_export_id=row_export_id,
                            side_name=side_name,
                            track=track,
                            track_number=index,
                            side_id=side_id,
                            used_track_ids=used_track_ids,
                        )
                        for index, track in enumerate(tracks, start=1)
                    ],
                )
            )

        if not sides:
            continue

        planned_row = PlannedMediaRow(
            row_id=row.row_id,
            source_row_id=row.row_id,
            media_name=row.media_name,
            cover_path=row.cover_path,
            row_mode="mixtape",
            export_id=row_export_id,
            containers_enabled=True,
            share_playable_texture_sources=False,
            enabled_media=dict(row.enabled_media),
            media_modes=dict(row.media_modes),
            appearances=_resolve_appearance_set(project, row, asset_catalog),
            sides=sides,
        )
        planned_rows.append(planned_row)
        planned_sides.extend(sides)

    stats = BuildSummaryStats(
        media_rows=len(project.media_rows),
        exported_media_rows=len(planned_rows),
        total_sides=len(planned_sides),
        total_songs=sum(side.song_count for side in planned_sides),
        built_songs=sum(side.song_count for side in planned_sides),
        planned_media_rows=len(project.media_rows),
        planned_total_sides=len(planned_sides),
        planned_total_songs=sum(side.song_count for side in planned_sides),
        converted=sum(1 for side in planned_sides for track in side.tracks if track.needs_conversion),
        mod_size_text=t("0 KB"),
        errors=0,
    )
    return ExportPlan(rows=planned_rows, sides=planned_sides, stats=stats)


def build_preview_scenario(plan: ExportPlan, output_path: str) -> BuildPreviewScenario:
    queue_groups = _queue_groups_from_plan(plan)
    preview_rows = _preview_rows_from_plan(plan)
    log_lines = _build_preview_log_lines(plan, output_path)
    return BuildPreviewScenario(
        queue_groups=queue_groups,
        log_lines=log_lines,
        preview_rows=preview_rows,
        stats=plan.stats,
    )


def _build_planned_track(
    *,
    row_id: int,
    media_name: str,
    row_export_id: str,
    side_name: str,
    track: TrackEntry,
    track_number: int,
    side_id: str,
    used_track_ids: set[str],
) -> PlannedTrack:
    source_path = str(track.source_path or "")
    display_label = track.display_label or Path(source_path).stem or t("Track")
    track_id = unique_export_id(
        f"{side_id}_{track_number}_{display_label}",
        used_track_ids,
        fallback=f"{side_id}Track{track_number}",
    )
    return PlannedTrack(
        track_number=track_number,
        source_path=source_path,
        display_label=display_label,
        duration_text=str(track.duration or ""),
        duration_seconds=_seconds_from_duration_text(str(track.duration or "")),
        needs_conversion=Path(source_path).suffix.lower() != ".ogg",
        source_row_id=row_id,
        source_track_index=max(0, track_number - 1),
        export_file_name=build_audio_track_file_name(display_label, track_number, track_id=track_id),
        export_relative_path=build_audio_track_relative_path(
            media_name=media_name,
            row_id=row_id,
            side=side_name,
            display_label=display_label,
            track_number=track_number,
            export_id=row_export_id,
            track_id=track_id,
        ),
        track_id=track_id,
        sound_id=track_id,
    )


def _remap_singles_plan_row_ids(plan: ExportPlan, *, next_exported_row_id: int) -> int:
    row_id_map: dict[int, int] = {}
    for planned_row in plan.rows:
        next_exported_row_id += 1
        row_id_map[planned_row.row_id] = next_exported_row_id
        planned_row.row_id = next_exported_row_id
        for side in planned_row.sides:
            side.row_id = next_exported_row_id
    for side in plan.sides:
        mapped_row_id = row_id_map.get(side.row_id)
        if mapped_row_id is not None:
            side.row_id = mapped_row_id
    return next_exported_row_id


def _resolve_appearance_set(
    project: ProjectConfig,
    row,
    asset_catalog: dict[str, list[AssetEntry]],
) -> ResolvedAppearanceSet:
    resolved = ResolvedAppearanceSet()
    for kind in ("cassette", "vinyl", "cd", "case", "jacket", "cd_cover"):
        selection = row.appearances[kind]
        asset = _resolve_appearance(project, kind, selection, asset_catalog.get(kind, []))
        setattr(resolved, kind, asset)
    return resolved


def _resolve_appearance(
    project: ProjectConfig,
    kind: AppearanceKind,
    selection,
    assets: list[AssetEntry],
) -> ResolvedAppearance:
    merged_entries = merge_appearance_grid_entries(
        kind,
        assets,
        visible_generated_entries_for_kind(project, kind),
        project.custom_assets.get(kind, []),
    )
    selected = next((entry for entry in merged_entries if entry.key == selection.selected_asset_key), None)
    if (
        selection.source == "custom"
        and (selection.inventory_full or selection.world_full)
        and (selected is None or (not selected.is_custom and not selected.is_generated))
    ):
        return ResolvedAppearance(
            kind=kind,
            selected_asset_key=selection.selected_asset_key,
            source="custom",
            inventory_path=str(selection.inventory_full or ""),
            world_path=str(selection.world_full or ""),
            sprite_mode=selection.sprite_mode if selection.sprite_mode in {"single", "dual"} else "single",
            inventory_empty_path=str(selection.inventory_empty or ""),
            world_empty_path=str(selection.world_empty or ""),
        )
    if selected is not None:
        return ResolvedAppearance(
            kind=kind,
            selected_asset_key=selected.key,
            source="custom" if selected.is_custom or selected.is_generated else "default",
            inventory_path=selected.inventory_path,
            world_path=selected.world_path,
            sprite_mode="dual" if selected.is_dual else "single",
            inventory_empty_path=selected.inventory_empty_path if selected.is_dual else "",
            world_empty_path=selected.world_empty_path if selected.is_dual else "",
        )

    if merged_entries:
        fallback = merged_entries[0]
        return ResolvedAppearance(
            kind=kind,
            selected_asset_key=fallback.key,
            source="custom" if fallback.is_custom or fallback.is_generated else "default",
            inventory_path=fallback.inventory_path,
            world_path=fallback.world_path,
            sprite_mode="dual" if fallback.is_dual else "single",
            inventory_empty_path=fallback.inventory_empty_path if fallback.is_dual else "",
            world_empty_path=fallback.world_empty_path if fallback.is_dual else "",
        )

    return ResolvedAppearance(
        kind=kind,
        selected_asset_key=selection.selected_asset_key,
        source="default",
        inventory_path="",
        world_path="",
        sprite_mode="single",
        inventory_empty_path="",
        world_empty_path="",
    )


def _queue_groups_from_plan(plan: ExportPlan) -> list[ConversionSideGroup]:
    return [
        ConversionSideGroup(
            row_id=side.row_id,
            side=side.side,
            row_mode=next((row.row_mode for row in plan.rows if row.row_id == side.row_id), "mixtape"),
            display_label=side.display_label,
            queue_label=side.queue_label or side.media_name,
            queue_mode=next((row.row_mode for row in plan.rows if row.row_id == side.row_id), "mixtape"),
            show_side_suffix=side.show_side_suffix,
            side_display_text=side.side_display_text,
            songs=[
                ConversionSongProgress(
                    song_label=track.display_label,
                    queue_index=index,
                    percent=0,
                    status="queued",
                    size_label="",
                )
                for index, track in enumerate(side.tracks, start=1)
            ],
        )
        for side in plan.sides
    ]


def _preview_rows_from_plan(plan: ExportPlan) -> list[GeneratedPreviewRow]:
    preview_rows: list[GeneratedPreviewRow] = []
    row_lookup = {row.row_id: row for row in plan.rows}
    for side in plan.sides:
        planned_row = row_lookup.get(side.row_id)
        if planned_row is None:
            continue
        preview_rows.append(
            GeneratedPreviewRow(
                row_id=side.row_id,
                side=side.side,
                inventory_cell=_build_preview_cell(planned_row, side, mode="inventory"),
                world_cell=_build_preview_cell(planned_row, side, mode="world"),
            )
        )
    return preview_rows


def _build_preview_cell(planned_row: PlannedMediaRow, side: PlannedSide, *, mode: str) -> GeneratedPreviewCell:
    slot_paths: list[str | None] = []
    empty_slot_paths: list[str | None] = []
    for appearance_kind, media_kind in _SLOT_KINDS:
        if not planned_row.enabled_media.get(media_kind, True):
            slot_paths.append(None)
            empty_slot_paths.append(None)
            continue
        appearance = planned_row.appearances.for_kind(appearance_kind)
        slot_paths.append(appearance.world_path if mode == "world" else appearance.inventory_path)
        empty_slot_paths.append(appearance.world_empty_path if mode == "world" else appearance.inventory_empty_path)
    label_text = planned_row.media_name if planned_row.row_mode == "singles" else (side.queue_label or planned_row.media_name)
    if planned_row.row_mode != "singles" and side.show_side_suffix and side.side_display_text:
        label_text = f"{label_text} ({side.side_display_text})"
    return GeneratedPreviewCell(
        label_text=label_text,
        section_text=t("WORLD") if mode == "world" else t("INVENTORY"),
        song_count=side.song_count,
        duration_text=side.duration_text,
        cover_path=planned_row.cover_path,
        slot_paths=tuple(slot_paths),
        empty_slot_paths=tuple(empty_slot_paths),
    )


def _build_preview_log_lines(plan: ExportPlan, output_path: str) -> list[ExportLogLine]:
    timestamp = datetime.now().strftime("%H:%M:%S")
    lines = [
        ExportLogLine(
            timestamp=timestamp,
            prefix_text=t("Build plan ready:"),
            subject_text=f"{plan.stats.total_sides} sides / {plan.stats.total_songs} songs queued.",
            color_role="neutral",
        )
    ]
    if output_path:
        lines.append(ExportLogLine(timestamp="", prefix_text=output_path, color_role="neutral"))
    return lines


def _seconds_from_duration_text(value: str) -> int:
    parts = value.strip().split(":")
    if len(parts) != 3:
        return 0
    try:
        hours, minutes, seconds = (int(part) for part in parts)
    except ValueError:
        return 0
    return max(0, hours) * 3600 + max(0, minutes) * 60 + max(0, seconds)


def _planned_row_uses_split_side_suffix(row) -> bool:
    if getattr(row, "row_mode", "mixtape") == "singles":
        return False
    tracks_b = getattr(row, "tracks_b", [])
    if not tracks_b:
        return False
    enabled_media = getattr(row, "enabled_media", {})
    media_modes = getattr(row, "media_modes", {})
    return any(
        enabled_media.get(kind, False) and media_modes.get(kind, "single" if kind == "cd" else "split") == "split"
        for kind in ("cassette", "vinyl", "cd")
    )
