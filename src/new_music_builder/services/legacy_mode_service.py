from __future__ import annotations

import random
from dataclasses import dataclass

from new_music_builder.domain.models import MediaKind, MediaRow, ProjectConfig, TrackAppearanceSelection, TrackEntry
from new_music_builder.services.asset_catalog import AssetEntry
from new_music_builder.ui.widgets.appearance_entries import AppearanceGridEntry, apply_selection_from_grid_entry, merge_appearance_grid_entries
from new_music_builder.ui.widgets.appearance_entries import entry_for_selected_key
from new_music_builder.services.generated_asset_registry import visible_generated_entries_for_kind

_PLAYABLE_KINDS: tuple[MediaKind, ...] = ("cassette", "vinyl", "cd")


@dataclass(frozen=True, slots=True)
class LegacySelectionSnapshot:
    row_id: int
    track_index: int


def enable_legacy_mode(
    project: ProjectConfig,
    asset_catalog: dict[str, list[AssetEntry]],
    *,
    randomizer: random.Random | None = None,
) -> None:
    chooser = randomizer or random.Random()
    for row in project.media_rows:
        row.ensure_appearances()
        row.row_mode = "singles"
        flattened_tracks = list(row.tracks_a) + list(row.tracks_b)
        row.tracks_a = flattened_tracks
        row.tracks_b = []
        row.selected_side = "A"
        _assign_row_legacy_track_appearances(project, row, asset_catalog, chooser=chooser)
    project.legacy_mode_enabled = True
    project.automatic_textures_enabled = False


def disable_legacy_mode(
    project: ProjectConfig,
    *,
    selected_track_by_row_id: dict[int, int] | None = None,
) -> None:
    selections = selected_track_by_row_id or {}
    for row in project.media_rows:
        row.row_mode = "mixtape"
        row.selected_side = "A"
        row.tracks_b = []
        _sync_row_appearances_from_legacy_track(row, selected_track_index=selections.get(row.row_id))
    project.legacy_mode_enabled = False


def enable_row_singles_mode(
    project: ProjectConfig,
    row: MediaRow,
    asset_catalog: dict[str, list[AssetEntry]],
    *,
    randomizer: random.Random | None = None,
) -> None:
    chooser = randomizer or random.Random()
    row.ensure_appearances()
    row.row_mode = "singles"
    row.tracks_a = list(row.tracks_a) + list(row.tracks_b)
    row.tracks_b = []
    row.selected_side = "A"
    _assign_row_legacy_track_appearances(project, row, asset_catalog, chooser=chooser)


def disable_row_singles_mode(row: MediaRow, *, selected_track_index: int | None = None) -> None:
    row.row_mode = "mixtape"
    row.selected_side = "A"
    row.tracks_b = []
    _sync_row_appearances_from_legacy_track(row, selected_track_index=selected_track_index)


def assign_legacy_appearances_to_new_tracks(
    project: ProjectConfig,
    row: MediaRow,
    tracks: list[TrackEntry],
    asset_catalog: dict[str, list[AssetEntry]],
    *,
    randomizer: random.Random | None = None,
) -> None:
    chooser = randomizer or random.Random()
    entries_by_kind = legacy_pool_entries_by_kind(project, row, asset_catalog)
    for track in tracks:
        _assign_track_legacy_appearances(track, entries_by_kind, chooser=chooser)


def legacy_pool_entries_by_kind(
    project: ProjectConfig,
    row: MediaRow,
    asset_catalog: dict[str, list[AssetEntry]],
) -> dict[MediaKind, list[AppearanceGridEntry]]:
    row.ensure_appearances()
    return {
        kind: merge_appearance_grid_entries(
            kind,
            asset_catalog.get(kind, []),
            visible_generated_entries_for_kind(project, kind),
            project.custom_assets.get(kind, []),
        )
        for kind in _PLAYABLE_KINDS
    }


def sync_row_appearances_from_legacy_track(row: MediaRow, *, selected_track_index: int | None = None) -> None:
    _sync_row_appearances_from_legacy_track(row, selected_track_index=selected_track_index)


def apply_entry_to_track(track: TrackEntry, kind: MediaKind, entry: AppearanceGridEntry) -> None:
    selection = track.legacy_appearances.for_kind(kind)
    selection.selected_asset_key = entry.key
    if entry.is_custom or entry.is_generated:
        selection.source = "custom"
        selection.inventory_full = entry.inventory_path
        selection.world_full = entry.world_path
    else:
        selection.source = "default"
        selection.inventory_full = ""
        selection.world_full = ""


def _assign_row_legacy_track_appearances(
    project: ProjectConfig,
    row: MediaRow,
    asset_catalog: dict[str, list[AssetEntry]],
    *,
    chooser: random.Random,
) -> None:
    entries_by_kind = legacy_pool_entries_by_kind(project, row, asset_catalog)
    for track in row.tracks_a:
        _assign_track_legacy_appearances(track, entries_by_kind, chooser=chooser)


def _assign_track_legacy_appearances(
    track: TrackEntry,
    entries_by_kind: dict[MediaKind, list[AppearanceGridEntry]],
    *,
    chooser: random.Random,
) -> None:
    for kind in _PLAYABLE_KINDS:
        entries = entries_by_kind.get(kind, [])
        if not entries:
            continue
        apply_entry_to_track(track, kind, chooser.choice(entries))


def _sync_row_appearances_from_legacy_track(row: MediaRow, *, selected_track_index: int | None = None) -> None:
    row.ensure_appearances()
    if not row.tracks_a:
        return
    chosen_index = selected_track_index if selected_track_index is not None and 0 <= selected_track_index < len(row.tracks_a) else 0
    track = row.tracks_a[chosen_index]
    for kind in _PLAYABLE_KINDS:
        track_selection = track.legacy_appearances.for_kind(kind)
        row_selection = row.appearances[kind]
        row_selection.selected_asset_key = track_selection.selected_asset_key
        row_selection.source = track_selection.source
        row_selection.sprite_mode = "single"
        row_selection.inventory_full = track_selection.inventory_full
        row_selection.world_full = track_selection.world_full
        row_selection.inventory_empty = ""
        row_selection.world_empty = ""


def track_selection_display_entry(
    project: ProjectConfig,
    row: MediaRow,
    track: TrackEntry,
    kind: MediaKind,
    asset_catalog: dict[str, list[AssetEntry]],
) -> AppearanceGridEntry | None:
    entries = legacy_pool_entries_by_kind(project, row, asset_catalog).get(kind, [])
    return entry_for_selected_key(entries, track.legacy_appearances.for_kind(kind).selected_asset_key)
