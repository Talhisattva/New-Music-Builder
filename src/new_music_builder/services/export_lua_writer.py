from __future__ import annotations

from pathlib import Path

from new_music_builder.domain.models import (
    ExportPlan,
    ExportTargetPaths,
    LuaAlbumMediaRegistration,
    LuaAlbumRegistration,
    LuaCoverGroup,
    LuaPackRegistration,
    LuaSinglesChunkRegistration,
    LuaSinglesEntry,
    ProjectConfig,
)
from new_music_builder.services.export_lua_plan import build_export_lua_plan

_SINGLES_HELPER_REQUIRE = "NMSinglesPackBuilder"
_SINGLES_HELPER_TEXT = """pcall(require, "shared/contracts/NMMediaContract")
pcall(require, "shared/contracts/NMCoverViewResolver")

NMSinglesPackBuilder = NMSinglesPackBuilder or {}

local carrierByKind = {
    cassette = "tsarcraft_music_01_62",
    vinyl = "tsarcraft_music_01_63",
    cd = "tsarcraft_music_01_64",
}

local function norm(value)
    local text = tostring(value or "")
    if text == "" then
        return ""
    end
    return text
end

local function fullType(moduleName, itemType)
    local name = norm(itemType)
    if name == "" then
        return ""
    end
    if string.find(name, ".", 1, true) then
        return name
    end
    local moduleText = norm(moduleName)
    if moduleText == "" then
        return name
    end
    return moduleText .. "." .. name
end

local function shortType(itemType)
    local key = norm(itemType)
    local dotPos = string.find(key, ".", 1, true)
    if dotPos then
        return string.sub(key, dotPos + 1)
    end
    return key
end

local function registerCarrier(mediaFullType, carrier)
    local short = shortType(mediaFullType)
    if short == "" or carrier == "" then
        return
    end
    if NMMediaContract and NMMediaContract.registerMediaTypeAlias then
        NMMediaContract.registerMediaTypeAlias(short, carrier)
        return
    end
    GlobalMusic = GlobalMusic or {}
    GlobalMusic[short] = carrier
end

local function registerCover(mediaFullType, texture)
    if mediaFullType == "" or texture == "" then
        return
    end
    if NMCoverViewResolver and NMCoverViewResolver.registerLinkedCover then
        NMCoverViewResolver.registerLinkedCover(mediaFullType, texture)
    end
end

function NMSinglesPackBuilder.registerSinglesChunk(moduleName, chunkDef)
    if type(chunkDef) ~= "table" then
        return false
    end
    local entries = type(chunkDef.entries) == "table" and chunkDef.entries or {}
    for i = 1, #entries do
        local entry = entries[i]
        local itemType = norm(entry.itemType)
        local mediaKind = norm(entry.mediaKind)
        local carrier = norm(carrierByKind[mediaKind])
        local coverTexture = norm(entry.coverTexture)
        local mediaFullType = fullType(moduleName, itemType)
        if mediaFullType ~= "" and carrier ~= "" then
            registerCarrier(mediaFullType, carrier)
            registerCover(mediaFullType, coverTexture)
        end
    end
    return true
end

function NMSinglesPackBuilder.registerSinglesPack(packDef)
    if type(packDef) ~= "table" then
        return false
    end
    local moduleName = norm(packDef.module)
    local chunks = type(packDef.chunks) == "table" and packDef.chunks or {}
    for i = 1, #chunks do
        NMSinglesPackBuilder.registerSinglesChunk(moduleName, chunks[i])
    end
    return true
end
"""


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

    for chunk in lua_pack.singles_chunks:
        (lua_root / f"{chunk.require_name}.lua").write_text(_render_singles_chunk(chunk), encoding="utf-8")

    if lua_pack.singles_chunks:
        (lua_root / f"{_SINGLES_HELPER_REQUIRE}.lua").write_text(_SINGLES_HELPER_TEXT, encoding="utf-8")


def _render_bootstrap(lua_pack: LuaPackRegistration) -> str:
    lines = ['pcall(require, "shared/contracts/NMMediaContract")']
    if lua_pack.mixtape_albums:
        lines.append('require "NMAlbumPackBuilder"')
    if lua_pack.singles_chunks:
        lines.append(f'require "{_SINGLES_HELPER_REQUIRE}"')
    lines.extend(f'require "{require_name}"' for require_name in lua_pack.mixtape_bootstrap_require_names)
    lines.extend(f'require "{require_name}"' for require_name in lua_pack.singles_bootstrap_require_names)
    lines.extend(
        [
            "",
            "-- Pack bootstrap:",
            "-- Mixtapes stay on NMAlbumPackBuilder; Singles use flat direct registration.",
            f'local PACK_MODULE = "{lua_pack.module_id}"',
            "",
        ]
    )
    if lua_pack.mixtape_albums:
        lines.extend(
            [
                "NMAlbumPackBuilder.registerAlbumPack({",
                "    module = PACK_MODULE,",
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
    if lua_pack.singles_chunks:
        lines.extend(
            [
                "NMSinglesPackBuilder.registerSinglesPack({",
                "    module = PACK_MODULE,",
                "    chunks = {",
            ]
        )
        lines.extend(f"        {chunk.table_name}," for chunk in lua_pack.singles_chunks)
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


def _render_singles_chunk(chunk: LuaSinglesChunkRegistration) -> str:
    lines = [
        "-- Singles runtime chunk:",
        "-- Direct one-track registrations; no album-contract tables.",
        "",
        f"{chunk.table_name} = {{",
        "    entries = {",
    ]
    for entry in chunk.entries:
        lines.extend(_render_singles_entry(entry))
    lines.extend(
        [
            "    },",
            "}",
            "",
        ]
    )
    return "\n".join(lines)


def _render_singles_entry(entry: LuaSinglesEntry) -> list[str]:
    lines = [
        "        {",
        f'            itemType = "{_escape(entry.item_type)}",',
        f'            sound = "{_escape(entry.sound)}",',
        f'            mediaKind = "{_escape(entry.media_kind)}",',
        f'            label = "{_escape(entry.track_label.key)}",',
        f'            coverTexture = "{_escape(entry.cover_texture)}",',
        "        },",
    ]
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
