from __future__ import annotations

import re

from new_music_builder.domain.models import (
    ExportPlan,
    LuaAlbumMediaItems,
    LuaAlbumMediaRegistration,
    LuaAlbumRegistration,
    LuaSinglesGroupRegistration,
    LuaSinglesEntry,
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
from new_music_builder.services.export_ids import sanitize_export_id
from new_music_builder.services.export_texture_contract import build_cover_texture_decision

_MEDIA_ORDER: tuple[MediaKind, ...] = ("cassette", "vinyl", "cd")
_DEFAULT_MEDIA_ROW_NAME_RE = re.compile(r"^Media Mix (\d+)$")


def build_export_lua_plan(project: ProjectConfig, export_plan: ExportPlan) -> LuaPackRegistration:
    registration = build_export_registration_plan(project, export_plan)
    rows_by_id = {row.row_id: row for row in export_plan.rows}
    source_row_titles = {row.row_id: row.media_name for row in project.media_rows}
    mixtape_albums = [
        _build_lua_album(
            registration.module_id,
            album,
            rows_by_id[album.row_id],
            source_row_title=source_row_titles.get(rows_by_id[album.row_id].source_row_id, ""),
        )
        for album in registration.albums
        if rows_by_id[album.row_id].row_mode != "singles"
    ]
    singles_groups = _build_singles_groups(registration.module_id, registration.albums, rows_by_id, source_row_titles)

    mixtape_bootstrap_require_names: list[str] = []
    seen_require_names: set[str] = set()
    for album in mixtape_albums:
        if album.require_name in seen_require_names:
            continue
        seen_require_names.add(album.require_name)
        mixtape_bootstrap_require_names.append(album.require_name)
    return LuaPackRegistration(
        module_id=registration.module_id,
        mixtape_bootstrap_require_names=mixtape_bootstrap_require_names,
        mixtape_album_table_names=[album.table_name for album in mixtape_albums],
        mixtape_albums=mixtape_albums,
        singles_bootstrap_require_names=[group.require_name for group in singles_groups],
        singles_groups=singles_groups,
    )


def _build_lua_album(
    module_id: str,
    album: RegisteredAlbum,
    row: PlannedMediaRow,
    *,
    source_row_title: str,
) -> LuaAlbumRegistration:
    explicit_tracks = _build_explicit_tracks(module_id, album)
    require_name = _lua_require_name(module_id, album, row, source_row_title=source_row_title)
    return LuaAlbumRegistration(
        album_id=album.album_id,
        title=album.title,
        module_id=module_id,
        row_mode=row.row_mode,
        sound_prefix=album.sound_prefix,
        table_name=f"NM{module_id}Album_{album.album_id}",
        require_name=require_name,
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


def _lua_require_name(
    module_id: str,
    album: RegisteredAlbum,
    row: PlannedMediaRow,
    *,
    source_row_title: str,
) -> str:
    if row.row_mode != "singles":
        return f"{module_id}_Album_{album.album_id}"
    source_title = source_row_title.strip() or row.media_name
    default_match = _DEFAULT_MEDIA_ROW_NAME_RE.fullmatch(source_title)
    if default_match:
        source_album_id = f"SinglesGroup{default_match.group(1)}"
    else:
        source_album_id = sanitize_export_id(source_title, fallback=f"SinglesGroup{row.source_row_id}")
    return f"{module_id}_Album_{source_album_id}"


def _build_singles_groups(
    module_id: str,
    albums: list[RegisteredAlbum],
    rows_by_id: dict[int, PlannedMediaRow],
    source_row_titles: dict[int, str],
) -> list[LuaSinglesGroupRegistration]:
    grouped: dict[str, list[LuaSinglesEntry]] = {}
    for album in albums:
        row = rows_by_id[album.row_id]
        if row.row_mode != "singles":
            continue
        base_require_name = _lua_require_name(
            module_id,
            album,
            row,
            source_row_title=source_row_titles.get(row.source_row_id, ""),
        )
        grouped.setdefault(base_require_name, []).extend(_build_singles_entries(module_id, album, row))

    groups: list[LuaSinglesGroupRegistration] = []
    for base_require_name, entries in grouped.items():
        groups.append(
            LuaSinglesGroupRegistration(
                require_name=base_require_name,
                entries=entries,
            )
        )
    return groups


def _build_singles_entries(module_id: str, album: RegisteredAlbum, row: PlannedMediaRow) -> list[LuaSinglesEntry]:
    track = album.sides[0].tracks[0]
    label = LuaTrackLabel(
        key=f"UI_{module_id}_{album.album_id}_Song_{track.sequence_number:02d}",
        text=track.display_label,
    )
    cover_groups = _build_cover_groups(album, row)
    cover_group = cover_groups[0] if cover_groups else None
    cover_media = cover_group.include_playable if cover_group is not None else ()
    media_by_kind = {media.media_kind: media for media in _build_lua_media(album)}
    entries: list[LuaSinglesEntry] = []
    for media_kind in _MEDIA_ORDER:
        sound_id = track.singles_sound_ids.get(media_kind)
        media = media_by_kind.get(media_kind)
        item_type = media.items.full if media is not None else ""
        if not sound_id or not item_type:
            continue
        entries.append(
            LuaSinglesEntry(
                item_type=item_type,
                sound=sound_id,
                media_kind=media_kind,
                track_label=label,
                cover_texture=cover_group.texture if cover_group is not None and media_kind in cover_media else "",
            )
        )
    return entries


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
