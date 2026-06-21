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
    for album in lua_pack.albums:
        (lua_root / f"{album.require_name}.lua").write_text(_render_album(album), encoding="utf-8")


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
        "-- One row maps to one album registration shape across enabled media.",
        "-- For different full/split media releases, create separate rows in the builder.",
        "",
        f"{album.table_name} = {{",
        f'    id = "{_escape(album.album_id)}",',
        f'    title = "{_escape(album.title)}",',
        "    trackSource = {",
        f'        soundPrefix = "{_escape(album.sound_prefix)}",',
        "        labels = {",
    ]
    lines.extend(f'            "{_escape(label)}",' for label in album.track_labels)
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
