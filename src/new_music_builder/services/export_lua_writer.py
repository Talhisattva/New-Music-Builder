from __future__ import annotations

from pathlib import Path

from new_music_builder.domain.models import (
    ExportPlan,
    ExportTargetPaths,
    LuaAlbumMediaRegistration,
    LuaAlbumRegistration,
    LuaCoverGroup,
    LuaPackRegistration,
    LuaSinglesGroupRegistration,
    LuaSinglesEntry,
    ProjectConfig,
)
from new_music_builder.services.export_lua_plan import build_export_lua_plan

_CARRIER_BY_KIND = {
    "cassette": "nm_carrier_cassette",
    "vinyl": "nm_carrier_vinyl",
    "cd": "nm_carrier_cd",
}


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
    for album in lua_pack.mixtape_albums:
        albums_by_require_name.setdefault(album.require_name, []).append(album)
    for require_name in lua_pack.mixtape_bootstrap_require_names:
        grouped_albums = albums_by_require_name.get(require_name, [])
        (lua_root / f"{require_name}.lua").write_text(_render_album_group(grouped_albums), encoding="utf-8")

    for group in lua_pack.singles_groups:
        (lua_root / f"{group.require_name}.lua").write_text(
            _render_singles_group(lua_pack.module_id, group),
            encoding="utf-8",
        )


def _render_bootstrap(lua_pack: LuaPackRegistration) -> str:
    lines = ['pcall(require, "shared/contracts/NMMediaContract")']
    if lua_pack.mixtape_albums:
        lines.append('require "NMAlbumPackBuilder"')
    lines.extend(f'require "{require_name}"' for require_name in lua_pack.mixtape_bootstrap_require_names)
    lines.extend(f'require "{require_name}"' for require_name in lua_pack.singles_bootstrap_require_names)
    lines.extend(
        [
            "",
            "-- Pack bootstrap:",
            "-- Mixtapes stay on NMAlbumPackBuilder; Singles self-register directly.",
            "",
        ]
    )
    if lua_pack.mixtape_albums:
        lines.extend(
            [
                "NMAlbumPackBuilder.registerAlbumPack({",
                f'    module = "{lua_pack.module_id}",',
                "    albums = {",
            ]
        )
        lines.extend(f"        {table_name}," for table_name in lua_pack.mixtape_album_table_names)
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


def _render_singles_group(module_id: str, group: LuaSinglesGroupRegistration) -> str:
    lines = ['pcall(require, "TCMusicDefenitions")']
    if group.has_linked_covers:
        lines.append('pcall(require, "shared/contracts/NMCoverViewResolver")')
    lines.extend(
        [
            "",
            "GlobalMusic = GlobalMusic or {}",
            "",
            "-- Singles runtime:",
            "-- Direct one-track registrations with item-type-matched sound ids.",
            "",
        ]
    )
    for entry in group.entries:
        lines.extend(_render_singles_entry(module_id, entry))
    return "\n".join(lines)


def _render_singles_entry(module_id: str, entry: LuaSinglesEntry) -> list[str]:
    carrier = _CARRIER_BY_KIND[entry.media_kind]
    lines = [
        f'GlobalMusic["{_escape(entry.item_type)}"] = "{carrier}"',
    ]
    if entry.cover_texture:
        lines.extend(
            [
                f'if NMCoverViewResolver then NMCoverViewResolver.registerLinkedCover("{_escape(module_id)}.{_escape(entry.item_type)}", "{_escape(entry.cover_texture)}") end',
            ]
        )
    lines.append("")
    return lines


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
    lines.extend(["        },"])
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
    lines.extend(["        },"])
    return lines


def _render_media_list(values: tuple[str, ...]) -> str:
    return ", ".join(f'"{value}"' for value in values)


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
