from __future__ import annotations

from new_music_builder.domain.models import (
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
)
from new_music_builder.services.export_registration_plan import build_export_registration_plan
from new_music_builder.services.export_texture_contract import build_cover_texture_decision

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
    cover_decision = build_cover_texture_decision(album.module_id, album.album_id, row)
    enabled_media = tuple(kind for kind in _MEDIA_ORDER if row.enabled_media.get(kind, False))
    if not enabled_media or not cover_decision.shared_cover_texture_reference:
        return []
    return [
        LuaCoverGroup(
            texture=cover_decision.shared_cover_texture_reference,
            include_playable=enabled_media,
            include_containers=enabled_media,
            include_empty_containers=enabled_media,
        )
    ]
