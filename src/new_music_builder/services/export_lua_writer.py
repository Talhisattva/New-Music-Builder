from __future__ import annotations

from pathlib import Path

from new_music_builder.domain.models import ExportPlan, ExportTargetPaths, LuaAlbumMediaRegistration, LuaAlbumRegistration, LuaCoverGroup, LuaPackRegistration, ProjectConfig
from new_music_builder.services.export_lua_plan import build_export_lua_plan


def write_export_lua(
    project: ProjectConfig,
    plan: ExportPlan,
    targets: ExportTargetPaths,
) -> None:
    lua_pack = build_export_lua_plan(project, plan)
    lua_root = Path(targets.v42) / "media" / "lua" / "shared"
    lua_root.mkdir(parents=True, exist_ok=True)
    (lua_root / f"{lua_pack.module_id}_PackBootstrap.lua").write_text(_render_bootstrap(lua_pack), encoding="utf-8")
    albums_by_require_name: dict[str, list[LuaAlbumRegistration]] = {}
    for album in lua_pack.albums:
        albums_by_require_name.setdefault(album.require_name, []).append(album)
    for require_name in lua_pack.bootstrap_require_names:
        grouped_albums = albums_by_require_name.get(require_name, [])
        render = _render_singles_chunk if grouped_albums and grouped_albums[0].row_mode == "singles" else _render_album_group
        (lua_root / f"{require_name}.lua").write_text(render(grouped_albums), encoding="utf-8")


def _render_bootstrap(lua_pack: LuaPackRegistration) -> str:
    lines = [
        'pcall(require, "shared/contracts/NMMediaContract")',
        'require "NMAlbumPackBuilder"',
    ]
    lines.extend(f'require "{require_name}"' for require_name in lua_pack.bootstrap_require_names)
    lines.extend(
        [
            "",
            "-- Pack bootstrap:",
            "-- Define the item/module namespace here, then list the album tables below.",
            "-- Most pack edits should happen in the album files, not in this file.",
            f'local PACK_MODULE = "{lua_pack.module_id}"',
            "",
            "NMAlbumPackBuilder.registerAlbumPack({",
            "    module = PACK_MODULE,",
            "    albums = {",
        ]
    )
    lines.extend(f"        {table_name}," for table_name in lua_pack.album_table_names)
    lines.extend(
        [
            "    },",
            "})",
            "",
        ]
    )
    return "\n".join(lines)


def _render_album(album: LuaAlbumRegistration) -> str:
    lines = [
        "-- Album guide:",
        "-- Edit the track list and keep it in numbered order.",
        "-- Media entries may be full or split depending on each builder row toggle.",
        "",
        f"{album.table_name} = {{",
        f'    id = "{_escape(album.album_id)}",',
        f'    title = "{_escape(album.title)}",',
        "    trackSource = {",
        f'        soundPrefix = "{_escape(album.sound_prefix)}",',
        "        explicit = {",
    ]
    for side_key in ("a", "b", "full"):
        rows = album.explicit_tracks.get(side_key, [])
        if not rows:
            continue
        lines.append(f"            {side_key} = {{")
        for row in rows:
            lines.append(
                '                { label = "%s", sound = "%s", trackNumber = %d },'
                % (_escape(row.label_key), _escape(row.sound), row.track_number)
            )
        lines.append("            },")
    lines.extend(
        [
            "        },",
        "        labels = {",
        ]
    )
    lines.extend(f'            "{_escape(label.key)}",' for label in album.track_labels)
    lines.extend(
        [
            "        },",
            "    },",
            "    media = {",
        ]
    )
    for media in album.media:
        lines.extend(_render_media_entry(media))
    lines.extend(
        [
            "    },",
            "    coverGroups = {",
        ]
    )
    for group in album.cover_groups:
        lines.extend(_render_cover_group(group))
    lines.extend(
        [
            "    },",
            "}",
            "",
        ]
    )
    return "\n".join(lines)


def _render_album_group(albums: list[LuaAlbumRegistration]) -> str:
    return "".join(_render_album(album) for album in albums)


def _render_singles_chunk(albums: list[LuaAlbumRegistration]) -> str:
    lines = [
        "-- Singles runtime chunk:",
        "-- Lightweight single-track registrations generated in fixed-size batches.",
        "",
        "local function _nmb_single_media(items)",
        "    local media = {}",
        '    if items.cassette then media.cassette = { mode = "full", items = { full = items.cassette, containerEmpty = "", containerFull = "", }, } end',
        '    if items.vinyl then media.vinyl = { mode = "full", items = { full = items.vinyl, containerEmpty = "", containerFull = "", }, } end',
        '    if items.cd then media.cd = { mode = "full", items = { full = items.cd, containerEmpty = "", containerFull = "", }, } end',
        "    return media",
        "end",
        "",
        "local function _nmb_single_cover(texture, playable)",
        '    if texture == nil or texture == "" then return {} end',
        '    return { { mode = "linked", texture = texture, includePlayable = playable, }, }',
        "end",
        "",
        "local function _nmb_register_single(def)",
        "    local explicit = { { label = def.label, sound = def.sound, trackNumber = 1 }, }",
        "    _G[def.tableName] = {",
        "        id = def.id,",
        "        title = def.title,",
        "        trackSource = {",
        "            soundPrefix = def.soundPrefix,",
        "            explicit = {",
        "                a = explicit,",
        "                full = explicit,",
        "            },",
        "            labels = { def.label },",
        "        },",
        "        media = _nmb_single_media(def.media),",
        "        coverGroups = _nmb_single_cover(def.coverTexture, def.coverPlayable),",
        "    }",
        "end",
        "",
    ]
    for album in albums:
        lines.extend(_render_singles_entry(album))
    return "\n".join(lines) + "\n"


def _render_singles_entry(album: LuaAlbumRegistration) -> list[str]:
    label_key = album.track_labels[0].key if album.track_labels else ""
    sound = album.explicit_tracks.get("full", [])[0].sound if album.explicit_tracks.get("full") else album.sound_prefix
    media_items = {
        media.media_kind: media.items.full
        for media in album.media
        if media.items.full
    }
    cover_group = album.cover_groups[0] if album.cover_groups else None
    lines = [
        "_nmb_register_single({",
        f'    tableName = "{_escape(album.table_name)}",',
        f'    id = "{_escape(album.album_id)}",',
        f'    title = "{_escape(album.title)}",',
        f'    soundPrefix = "{_escape(album.sound_prefix)}",',
        f'    sound = "{_escape(sound)}",',
        f'    label = "{_escape(label_key)}",',
        f"    media = {{ {_render_singles_media_items(media_items)} }},",
    ]
    if cover_group is not None and cover_group.texture:
        lines.append(f'    coverTexture = "{_escape(cover_group.texture)}",')
        lines.append(f"    coverPlayable = {{ {_render_media_list(cover_group.include_playable)} }},")
    else:
        lines.append('    coverTexture = "",')
        lines.append("    coverPlayable = {},")
    lines.extend(
        [
            "})",
            "",
        ]
    )
    return lines


def _render_singles_media_items(items: dict[str, str]) -> str:
    ordered = []
    for kind in ("cassette", "vinyl", "cd"):
        value = items.get(kind, "")
        if value:
            ordered.append(f'{kind} = "{_escape(value)}"')
    return ", ".join(ordered)


def _render_media_entry(media: LuaAlbumMediaRegistration) -> list[str]:
    lines = [
        f"        {media.media_kind} = {{",
        f'            mode = "{media.mode}",',
        "            items = {",
    ]
    if media.mode == "full":
        lines.append(f'                full = "{_escape(media.items.full)}",')
    else:
        lines.extend(
            [
                f'                a = "{_escape(media.items.a)}",',
                f'                b = "{_escape(media.items.b)}",',
            ]
        )
    lines.extend(
        [
            f'                containerEmpty = "{_escape(media.items.container_empty)}",',
            f'                containerFull = "{_escape(media.items.container_full)}",',
            "            },",
        ]
    )
    if media.mode == "split":
        lines.extend(
            [
                "            ranges = {",
                f"                a = {{ {media.range_a[0]}, {media.range_a[1]} }},",
                f"                b = {{ {media.range_b[0]}, {media.range_b[1]} }},",
                "            },",
            ]
        )
    lines.extend(
        [
            "        },",
        ]
    )
    return lines


def _render_cover_group(group: LuaCoverGroup) -> list[str]:
    lines = [
        "        {",
        '            mode = "linked",',
        f'            texture = "{_escape(group.texture)}",',
    ]
    if group.include_playable:
        lines.append(f"            includePlayable = {{ {_render_media_list(group.include_playable)} }},")
    if group.include_containers:
        lines.append(f"            includeContainers = {{ {_render_media_list(group.include_containers)} }},")
    if group.include_empty_containers:
        lines.append(f"            includeEmptyContainers = {{ {_render_media_list(group.include_empty_containers)} }},")
    lines.extend(
        [
            "        },",
        ]
    )
    return lines


def _render_media_list(values: tuple[str, ...]) -> str:
    return ", ".join(f'"{value}"' for value in values)


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
