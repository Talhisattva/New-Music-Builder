from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from new_music_builder.domain.models import (
    AppearanceKind,
    ExportPlan,
    LuaAlbumMediaItems,
    LuaAlbumMediaRegistration,
    LuaAlbumRegistration,
    LuaCoverGroup,
    LuaPackRegistration,
    MediaKind,
    PlannedMediaRow,
    ProjectConfig,
    RegisteredAlbum,
    RegisteredContainerVariant,
    RegisteredMediaVariant,
    ResolvedAppearance,
)
from new_music_builder.services.export_registration_plan import build_export_registration_plan
from new_music_builder.services.export_texture_contract import (
    build_cover_texture_decision,
    exported_world_texture_reference,
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

_MEDIA_ORDER: tuple[MediaKind, ...] = ("cassette", "vinyl", "cd")


def build_export_lua_plan(project: ProjectConfig, export_plan: ExportPlan) -> LuaPackRegistration:
    registration = build_export_registration_plan(project, export_plan)
    rows_by_id = {row.row_id: row for row in export_plan.rows}
    albums = [
        _build_lua_album(registration.module_id, album, rows_by_id[album.row_id])
        for album in registration.albums
    ]
    return LuaPackRegistration(
        module_id=registration.module_id,
        bootstrap_require_names=[album.require_name for album in albums],
        album_table_names=[album.table_name for album in albums],
        albums=albums,
    )


def _build_lua_album(module_id: str, album: RegisteredAlbum, row: PlannedMediaRow) -> LuaAlbumRegistration:
    return LuaAlbumRegistration(
        album_id=album.album_id,
        title=album.title,
        module_id=module_id,
        sound_prefix=album.sound_prefix,
        table_name=f"NM{module_id}Album_{album.album_id}",
        require_name=f"{module_id}_Album_{album.album_id}",
        track_labels=[
            f"{track.sequence_number:02d} {track.display_label}"
            for side in album.sides
            for track in side.tracks
        ],
        media=_build_lua_media(album),
        cover_groups=_build_cover_groups(album, row),
    )


def _build_lua_media(album: RegisteredAlbum) -> list[LuaAlbumMediaRegistration]:
    container_by_kind = {variant.media_kind: variant for variant in album.container_variants}
    side_ranges = {side.side: (side.start_track_number, side.end_track_number) for side in album.sides}
    media: list[LuaAlbumMediaRegistration] = []
    for kind in _MEDIA_ORDER:
        variant = next((item for item in album.media_variants if item.media_kind == kind), None)
        if variant is None:
            continue
        container = container_by_kind[kind]
        items = LuaAlbumMediaItems(
            full=variant.full_item_id,
            a=variant.item_ids.get("A", ""),
            b=variant.item_ids.get("B", ""),
            container_empty=container.empty_item_id,
            container_full=container.full_item_id,
        )
        media.append(
            LuaAlbumMediaRegistration(
                media_kind=kind,
                mode="full" if variant.mode == "single" else "split",
                items=items,
                range_a=side_ranges.get("A") if variant.mode == "split" else None,
                range_b=side_ranges.get("B") if variant.mode == "split" else None,
            )
        )
    return media


def _build_cover_groups(album: RegisteredAlbum, row: PlannedMediaRow) -> list[LuaCoverGroup]:
    grouped: OrderedDict[str, dict[str, set[MediaKind]]] = OrderedDict()
    container_by_kind = {variant.media_kind: variant for variant in album.container_variants}
    cover_decision = build_cover_texture_decision(album.module_id, album.album_id, row)
    has_custom_cover_art = _row_uses_custom_cover_art(row)

    for kind in _MEDIA_ORDER:
        if not row.enabled_media.get(kind, False):
            continue
        playable_appearance = row.appearances.for_kind(_PLAYABLE_APPEARANCE_KIND[kind])
        container_appearance = row.appearances.for_kind(_CONTAINER_APPEARANCE_KIND[kind])
        container_variant = container_by_kind[kind]

        _append_cover_group(
            grouped,
            _playable_texture_reference(
                album.module_id,
                album.album_id,
                kind,
                playable_appearance,
                cover_decision.playable_texture_reference,
                use_custom_cover=has_custom_cover_art,
            ),
            "playable",
            kind,
        )
        _append_cover_group(
            grouped,
            _container_texture_reference(album.module_id, album.album_id, kind, container_appearance, empty=False, container_variant=container_variant),
            "containers",
            kind,
        )
        _append_cover_group(
            grouped,
            _container_texture_reference(album.module_id, album.album_id, kind, container_appearance, empty=True, container_variant=container_variant),
            "empty_containers",
            kind,
        )

    cover_groups: list[LuaCoverGroup] = []
    for texture, buckets in grouped.items():
        if not texture:
            continue
        cover_groups.append(
            LuaCoverGroup(
                texture=texture,
                include_playable=tuple(kind for kind in _MEDIA_ORDER if kind in buckets["playable"]),
                include_containers=tuple(kind for kind in _MEDIA_ORDER if kind in buckets["containers"]),
                include_empty_containers=tuple(kind for kind in _MEDIA_ORDER if kind in buckets["empty_containers"]),
            )
        )
    return cover_groups


def _append_cover_group(
    grouped: OrderedDict[str, dict[str, set[MediaKind]]],
    texture: str,
    bucket: str,
    media_kind: MediaKind,
) -> None:
    if not texture:
        return
    record = grouped.setdefault(
        texture,
        {
            "playable": set(),
            "containers": set(),
            "empty_containers": set(),
        },
    )
    record[bucket].add(media_kind)


def _playable_texture_reference(
    module_id: str,
    album_id: str,
    media_kind: MediaKind,
    appearance: ResolvedAppearance,
    cover_texture_reference: str,
    *,
    use_custom_cover: bool,
) -> str:
    if media_kind == "cassette" and appearance.source == "custom":
        return exported_world_texture_reference("cassette", module_id, album_id)
    if media_kind in {"vinyl", "cd"} and use_custom_cover and cover_texture_reference:
        return cover_texture_reference
    return _world_texture_reference_from_path(appearance.world_path, fallback_dir=_world_items_dir_for_playable(media_kind))


def _container_texture_reference(
    module_id: str,
    album_id: str,
    media_kind: MediaKind,
    appearance: ResolvedAppearance,
    *,
    empty: bool,
    container_variant: RegisteredContainerVariant,
) -> str:
    if appearance.source == "custom":
        appearance_kind: AppearanceKind = _CONTAINER_APPEARANCE_KIND[media_kind]
        base = exported_world_texture_reference(appearance_kind, module_id, album_id)
        if empty and _has_distinct_empty_container_texture(appearance, container_variant):
            return exported_world_texture_reference(appearance_kind, module_id, album_id, empty=True)
        return base

    path = appearance.world_empty_path if empty and appearance.world_empty_path else appearance.world_path
    return _world_texture_reference_from_path(path, fallback_dir=_world_items_dir_for_container(media_kind))


def _has_distinct_empty_container_texture(
    appearance: ResolvedAppearance,
    container_variant: RegisteredContainerVariant,
) -> bool:
    return bool(
        has_distinct_empty_world(appearance)
        and container_variant.empty_model_reference != container_variant.full_model_reference
    )


def _world_texture_reference_from_path(path: str, *, fallback_dir: str) -> str:
    if not path:
        return ""
    candidate = Path(path)
    parts = candidate.parts
    if "WorldItems" in parts:
        start_index = parts.index("WorldItems")
        return "/".join(parts[start_index:]).removesuffix(candidate.suffix)
    return f"{fallback_dir}/{candidate.stem}"


def _world_items_dir_for_playable(media_kind: MediaKind) -> str:
    if media_kind == "cassette":
        return "WorldItems/Cassette"
    if media_kind == "vinyl":
        return "WorldItems/Vinyl"
    return "WorldItems/CD"


def _world_items_dir_for_container(media_kind: MediaKind) -> str:
    if media_kind == "cassette":
        return "WorldItems/Cassette"
    if media_kind == "vinyl":
        return "WorldItems/Vinyl"
    return "WorldItems/CD"


def _row_uses_custom_cover_art(row: PlannedMediaRow) -> bool:
    return any(
        row.appearances.for_kind(kind).source == "custom"
        for kind in ("vinyl", "cd", "jacket", "cd_cover")
    )
