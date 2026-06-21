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
from new_music_builder.services.asset_catalog import AssetEntry

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

    for row in project.media_rows:
        row.ensure_appearances()
        sides: list[PlannedSide] = []
        for side_name, tracks in (("A", row.tracks_a), ("B", row.tracks_b)):
            if not tracks:
                continue
            sides.append(
                PlannedSide(
                    row_id=row.row_id,
                    side=side_name,
                    media_name=row.media_name,
                    cover_path=row.cover_path,
                    tracks=[_build_planned_track(track) for track in tracks],
                )
            )

        if not sides:
            continue

        planned_row = PlannedMediaRow(
            row_id=row.row_id,
            media_name=row.media_name,
            cover_path=row.cover_path,
            enabled_media=dict(row.enabled_media),
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
        converted=sum(1 for side in planned_sides for track in side.tracks if track.needs_conversion),
        mod_size_text="0 KB",
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


def _build_planned_track(track: TrackEntry) -> PlannedTrack:
    source_path = str(track.source_path or "")
    display_label = track.display_label or Path(source_path).stem or "Track"
    return PlannedTrack(
        source_path=source_path,
        display_label=display_label,
        duration_text=str(track.duration or ""),
        duration_seconds=_seconds_from_duration_text(str(track.duration or "")),
        needs_conversion=Path(source_path).suffix.lower() != ".ogg",
    )


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
    if selection.source == "custom":
        return ResolvedAppearance(
            kind=kind,
            selected_asset_key=selection.selected_asset_key,
            source="custom",
            inventory_path=str(selection.inventory_full or ""),
            world_path=str(selection.world_full or ""),
        )

    asset_by_key = {asset.key: asset for asset in assets}
    selected = asset_by_key.get(selection.selected_asset_key)
    if selected is None and assets:
        selected = assets[0]
    if selected is not None:
        return ResolvedAppearance(
            kind=kind,
            selected_asset_key=selected.key,
            source="default",
            inventory_path=selected.inventory_path,
            world_path=selected.world_path,
        )

    for custom_asset in project.custom_assets.get(kind, []):
        if custom_asset.get("key") != selection.selected_asset_key:
            continue
        return ResolvedAppearance(
            kind=kind,
            selected_asset_key=selection.selected_asset_key,
            source="custom",
            inventory_path=str(custom_asset.get("inventory_full", "")),
            world_path=str(custom_asset.get("world_full", "")),
        )

    return ResolvedAppearance(
        kind=kind,
        selected_asset_key=selection.selected_asset_key,
        source="default",
        inventory_path="",
        world_path="",
    )


def _queue_groups_from_plan(plan: ExportPlan) -> list[ConversionSideGroup]:
    return [
        ConversionSideGroup(
            row_id=side.row_id,
            side=side.side,
            display_label=side.display_label,
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
    for appearance_kind, media_kind in _SLOT_KINDS:
        if not planned_row.enabled_media.get(media_kind, True):
            slot_paths.append(None)
            continue
        appearance = planned_row.appearances.for_kind(appearance_kind)
        slot_paths.append(appearance.world_path if mode == "world" else appearance.inventory_path)
    return GeneratedPreviewCell(
        label_text=f"{planned_row.media_name} ({side.side}-Side)",
        section_text="WORLD" if mode == "world" else "INVENTORY",
        song_count=side.song_count,
        duration_text=side.duration_text,
        cover_path=planned_row.cover_path,
        slot_paths=tuple(slot_paths),
    )


def _build_preview_log_lines(plan: ExportPlan, output_path: str) -> list[ExportLogLine]:
    timestamp = datetime.now().strftime("%H:%M:%S")
    lines = [
        ExportLogLine(
            timestamp=timestamp,
            prefix_text="Build plan ready:",
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
