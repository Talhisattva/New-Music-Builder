from __future__ import annotations

from new_music_builder.domain.models import (
    ExportPlan,
    LuaAlbumMediaItems,
    LuaAlbumMediaRegistration,
    LuaAlbumRegistration,
    LuaExplicitTrack,
    LuaTrackLabel,
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
    explicit_tracks = _build_explicit_tracks(module_id, album)
    return LuaAlbumRegistration(
        album_id=album.album_id,
        title=album.title,
        module_id=module_id,
        sound_prefix=album.sound_prefix,
        table_name=f"NM{module_id}Album_{album.album_id}",
        require_name=f"{module_id}_Album_{album.album_id}",
        track_labels=[
            LuaTrackLabel(
                key=f"UI_{module_id}_{album.album_id}_Song_{track.sequence_number:02d}",
                text=track.display_label,
            )
            for side in album.sides
            for track in side.tracks
        ],
        explicit_tracks=explicit_tracks,
        media=_build_lua_media(album),
        cover_groups=_build_cover_groups(album, row),
    )


def _build_explicit_tracks(module_id: str, album: RegisteredAlbum) -> dict[str, list[LuaExplicitTrack]]:
    side_tracks: dict[str, list[LuaExplicitTrack]] = {}
    full_tracks: list[LuaExplicitTrack] = []
    for side in album.sides:
        rows: list[LuaExplicitTrack] = []
        for track in side.tracks:
            label_key = f"UI_{module_id}_{album.album_id}_Song_{track.sequence_number:02d}"
            entry = LuaExplicitTrack(
                label_key=label_key,
                sound=track.sound_id,
                track_number=track.sequence_number,
            )
            rows.append(entry)
            full_tracks.append(entry)
        if rows:
            side_tracks[side.side.lower()] = rows
    if full_tracks:
        side_tracks["full"] = full_tracks
    return side_tracks


def _build_lua_media(album: RegisteredAlbum) -> list[LuaAlbumMediaRegistration]:
    container_by_kind = {variant.media_kind: variant for variant in album.container_variants}
    side_ranges = {side.side: (side.start_track_number, side.end_track_number) for side in album.sides}
    media: list[LuaAlbumMediaRegistration] = []
    for kind in _MEDIA_ORDER:
        variant = next((item for item in album.media_variants if item.media_kind == kind), None)
        if variant is None:
            continue
        container = container_by_kind.get(kind)
        items = LuaAlbumMediaItems(
            full=variant.full_item_id,
            a=variant.item_ids.get("A", ""),
            b=variant.item_ids.get("B", ""),
            container_empty=container.empty_item_id if container is not None else "",
            container_full=container.full_item_id if container is not None else "",
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
    cover_decision = build_cover_texture_decision(
        album.module_id,
        album.album_id,
        row,
        legacy_mode=(row.row_mode == "singles"),
    )
    enabled_media = tuple(kind for kind in _MEDIA_ORDER if row.enabled_media.get(kind, False))
    if not enabled_media or not cover_decision.shared_cover_texture_reference:
        return []
    include_containers = tuple(
        kind for kind in enabled_media if any(variant.media_kind == kind for variant in album.container_variants)
    )
    return [
        LuaCoverGroup(
            texture=cover_decision.shared_cover_texture_reference,
            include_playable=enabled_media,
            include_containers=include_containers,
            include_empty_containers=include_containers,
        )
    ]
