from __future__ import annotations

from pathlib import Path

from new_music_builder.domain.models import (
    AppearanceKind,
    ExportPlan,
    ExportRegistrationPlan,
    MediaKind,
    PlannedMediaRow,
    PlannedSide,
    ProjectConfig,
    RegisteredAlbum,
    RegisteredContainerVariant,
    RegisteredMediaVariant,
    RegisteredSide,
    RegisteredTrack,
    RegistrationMode,
    ResolvedAppearance,
)
from new_music_builder.services.export_ids import sanitize_export_id
from new_music_builder.services.export_texture_contract import (
    exported_inventory_texture_stem,
    exported_world_texture_stem,
    has_distinct_empty_inventory,
    has_distinct_empty_world,
)


_PLAYABLE_APPEARANCE_KIND: dict[MediaKind, AppearanceKind] = {
    "cassette": "cassette",
    "vinyl": "vinyl",
    "cd": "cd",
}

_CONTAINER_APPEARANCE_KIND: dict[MediaKind, AppearanceKind] = {
    "cassette": "case",
    "vinyl": "jacket",
    "cd": "cd_cover",
}

_MEDIA_SUFFIX: dict[MediaKind, str] = {
    "cassette": "Cassette",
    "vinyl": "Vinyl",
    "cd": "CD",
}

_CONTAINER_SUFFIX: dict[MediaKind, str] = {
    "cassette": "CassetteCase",
    "vinyl": "Jacket",
    "cd": "CDCover",
}


def build_export_registration_plan(project: ProjectConfig, export_plan: ExportPlan) -> ExportRegistrationPlan:
    module_id = sanitize_export_id(project.mod_id or "NewMusicPack", fallback="NewMusicPack")
    albums = [
        _build_registered_album(module_id, row)
        for row in export_plan.rows
    ]
    return ExportRegistrationPlan(module_id=module_id, albums=albums)


def _build_registered_album(module_id: str, row: PlannedMediaRow) -> RegisteredAlbum:
    ordered_sides = sorted(row.sides, key=lambda side: 0 if side.side == "A" else 1)
    album_id = row.export_id or sanitize_export_id(row.media_name, fallback=f"MediaRow{row.row_id}")
    sound_prefix = f"{module_id}{album_id}"
    registered_sides: list[RegisteredSide] = []
    next_sequence_number = 1
    for side in ordered_sides:
        registered_side = _build_registered_side(module_id, sound_prefix, side, next_sequence_number)
        registered_sides.append(registered_side)
        next_sequence_number = registered_side.end_track_number + 1
    media_variants = _build_media_variants(module_id, row)
    mode: RegistrationMode = "split" if any(variant.mode == "split" for variant in media_variants) else "single"
    return RegisteredAlbum(
        row_id=row.row_id,
        album_id=album_id,
        title=row.media_name,
        module_id=module_id,
        mode=mode,
        sound_prefix=sound_prefix,
        sides=registered_sides,
        media_variants=media_variants,
        container_variants=_build_container_variants(module_id, row),
    )


def _build_registered_side(
    module_id: str,
    sound_prefix: str,
    side: PlannedSide,
    start_sequence_number: int,
) -> RegisteredSide:
    tracks: list[RegisteredTrack] = []
    for offset, track in enumerate(side.tracks):
        sequence_number = start_sequence_number + offset
        tracks.append(
            RegisteredTrack(
                sequence_number=sequence_number,
                track_id=track.track_id,
                sound_id=f"{sound_prefix}{sequence_number:02d}",
                display_label=track.display_label,
                export_audio_relative_path=f"media/sound/{module_id}/{track.export_relative_path.replace('\\', '/')}",
            )
        )
    return RegisteredSide(
        side=side.side,
        side_id=side.side_id,
        start_track_number=tracks[0].sequence_number if tracks else 0,
        end_track_number=tracks[-1].sequence_number if tracks else 0,
        tracks=tracks,
    )


def _build_media_variants(module_id: str, row: PlannedMediaRow) -> list[RegisteredMediaVariant]:
    variants: list[RegisteredMediaVariant] = []
    available_sides = tuple(side.side for side in sorted(row.sides, key=lambda item: 0 if item.side == "A" else 1))
    for media_kind in ("cassette", "vinyl", "cd"):
        if not row.enabled_media.get(media_kind, False):
            continue
        mode = _effective_media_mode(row, media_kind)
        appearance = row.appearances.for_kind(_PLAYABLE_APPEARANCE_KIND[media_kind])
        full_item_id = ""
        full_display_name = ""
        item_ids: dict[str, str] = {}
        display_names: dict[str, str] = {}
        if mode == "single":
            full_item_id = f"{row.export_id}{_MEDIA_SUFFIX[media_kind]}"
            full_display_name = _playable_display_name(row.media_name, media_kind, "A", mode)
        else:
            item_ids = {
                side_name: f"{row.export_id}{_MEDIA_SUFFIX[media_kind]}{side_name}"
                for side_name in available_sides
            }
            display_names = {
                side_name: _playable_display_name(row.media_name, media_kind, side_name, mode)
                for side_name in available_sides
            }
        variant = RegisteredMediaVariant(
            media_kind=media_kind,
            mode=mode,
            full_item_id=full_item_id,
            full_display_name=full_display_name,
            item_ids=item_ids,
            display_names=display_names,
            icon_reference=_appearance_icon_reference_from_appearance(appearance),
            model_reference=_appearance_model_reference_from_appearance(appearance),
            selected_asset_key=appearance.selected_asset_key,
            asset_source=appearance.source,
        )
        if appearance.source == "custom":
            variant.icon_reference = exported_inventory_texture_stem(media_kind, module_id, row.export_id)
            variant.model_reference = exported_world_texture_stem(media_kind, module_id, row.export_id)
        variants.append(variant)
    return variants


def _effective_media_mode(row: PlannedMediaRow, media_kind: MediaKind) -> RegistrationMode:
    requested = row.media_modes.get(media_kind, "single" if media_kind == "cd" else "split")
    if requested == "split" and len(row.sides) > 1:
        return "split"
    return "single"


def _build_container_variants(module_id: str, row: PlannedMediaRow) -> list[RegisteredContainerVariant]:
    variants: list[RegisteredContainerVariant] = []
    for media_kind in ("cassette", "vinyl", "cd"):
        if not row.enabled_media.get(media_kind, False):
            continue
        appearance_kind = _CONTAINER_APPEARANCE_KIND[media_kind]
        appearance = row.appearances.for_kind(appearance_kind)
        container_label = _CONTAINER_SUFFIX[media_kind].replace("CD", "CD ").replace("CassetteCase", "Cassette Case")
        variant = RegisteredContainerVariant(
            media_kind=media_kind,
            container_kind=appearance_kind,
            empty_item_id=f"{row.export_id}{_CONTAINER_SUFFIX[media_kind]}Empty",
            full_item_id=f"{row.export_id}{_CONTAINER_SUFFIX[media_kind]}Full",
            empty_display_name=f"{row.media_name} {container_label} (Empty)",
            full_display_name=f"{row.media_name} {container_label} (Full)",
            empty_icon_reference=_appearance_icon_reference(appearance.inventory_empty_path or appearance.inventory_path),
            full_icon_reference=_appearance_icon_reference(appearance.inventory_path),
            empty_model_reference=_appearance_model_reference(appearance.world_empty_path or appearance.world_path),
            full_model_reference=_appearance_model_reference(appearance.world_path),
            selected_asset_key=appearance.selected_asset_key,
            asset_source=appearance.source,
        )
        if appearance.source == "custom":
            variant.full_icon_reference = exported_inventory_texture_stem(appearance_kind, module_id, row.export_id)
            variant.empty_icon_reference = (
                exported_inventory_texture_stem(appearance_kind, module_id, row.export_id, empty=True)
                if has_distinct_empty_inventory(appearance)
                else variant.full_icon_reference
            )
            variant.full_model_reference = exported_world_texture_stem(appearance_kind, module_id, row.export_id)
            variant.empty_model_reference = (
                exported_world_texture_stem(appearance_kind, module_id, row.export_id, empty=True)
                if has_distinct_empty_world(appearance)
                else variant.full_model_reference
            )
        variants.append(variant)
    return variants


def _playable_display_name(title: str, media_kind: MediaKind, side_name: str, mode: RegistrationMode) -> str:
    media_label = _MEDIA_SUFFIX[media_kind]
    if mode == "single":
        return f"{title} ({media_label})"
    return f"{title} ({media_label} {side_name}-side)"


def _appearance_icon_reference(path: str) -> str:
    candidate = Path(path)
    stem = candidate.stem
    if stem.startswith("Item_"):
        return stem.removeprefix("Item_")
    return stem


def _appearance_model_reference(path: str) -> str:
    return Path(path).stem


def _appearance_icon_reference_from_appearance(appearance: ResolvedAppearance) -> str:
    path = appearance.inventory_path or appearance.world_path
    if not path:
        return ""
    return _appearance_icon_reference(path)


def _appearance_model_reference_from_appearance(appearance: ResolvedAppearance) -> str:
    path = appearance.world_path or appearance.inventory_path
    if not path:
        return ""
    return _appearance_model_reference(path)
