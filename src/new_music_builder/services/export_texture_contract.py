from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from new_music_builder.domain.models import PlannedMediaRow, ResolvedAppearance

_INVENTORY_PREFIX: dict[str, str] = {
    "cassette": "NM_Cassette",
    "vinyl": "NM_Vinyl",
    "cd": "NM_CD",
    "case": "NM_Case",
    "jacket": "NM_Jacket",
    "cd_cover": "NM_CDCover",
}

_WORLD_PREFIX: dict[str, str] = {
    "cassette": "World_NM_Cassette",
    "vinyl": "World_NM_Vinyl",
    "cd": "World_NM_CD",
    "case": "World_NM_CassetteCover",
    "jacket": "World_NM_Cover",
    "cd_cover": "World_NM_CDCover",
}

_WORLD_DIR: dict[str, str] = {
    "cassette": "WorldItems/Cassette",
    "vinyl": "WorldItems/Vinyl",
    "cd": "WorldItems/CD",
    "case": "WorldItems/Cassette",
    "jacket": "WorldItems/Vinyl",
    "cd_cover": "WorldItems/CD",
}


@dataclass(slots=True)
class CoverTextureDecision:
    base_source_path: str = ""
    comparison_source_path: str = ""
    row_cover_source_path: str = ""
    base_texture_reference: str = ""
    hr_texture_reference: str = ""
    playable_texture_reference: str = ""
    export_hr_cover: bool = False


def exported_inventory_texture_stem(kind: str, module_id: str, album_id: str, *, empty: bool = False) -> str:
    stem = f"{_INVENTORY_PREFIX[kind]}_{module_id}_{album_id}"
    return f"{stem}_Empty" if empty else stem


def exported_inventory_texture_filename(kind: str, module_id: str, album_id: str, *, empty: bool = False) -> str:
    return f"Item_{exported_inventory_texture_stem(kind, module_id, album_id, empty=empty)}.png"


def exported_world_texture_stem(kind: str, module_id: str, album_id: str, *, empty: bool = False, hr: bool = False) -> str:
    if hr:
        stem = f"World_NM_Cover_{module_id}_{album_id}"
    else:
        stem = f"{_WORLD_PREFIX[kind]}_{module_id}_{album_id}"
    return f"{stem}_Empty" if empty else stem


def exported_world_texture_reference(kind: str, module_id: str, album_id: str, *, empty: bool = False, hr: bool = False) -> str:
    directory = exported_world_texture_directory(kind, hr=hr)
    stem = exported_world_texture_stem(kind, module_id, album_id, empty=empty, hr=hr)
    return f"{directory}/{stem}"


def exported_world_texture_relative_path(kind: str, module_id: str, album_id: str, *, empty: bool = False, hr: bool = False) -> str:
    return f"{exported_world_texture_reference(kind, module_id, album_id, empty=empty, hr=hr)}.png"


def exported_world_texture_directory(kind: str, *, hr: bool = False) -> str:
    if hr:
        return "WorldItems/Vinyl/HR"
    return _WORLD_DIR[kind]


def build_cover_texture_decision(module_id: str, album_id: str, row: PlannedMediaRow) -> CoverTextureDecision:
    vinyl = row.appearances.vinyl
    jacket = row.appearances.jacket
    cd = row.appearances.cd
    cd_cover = row.appearances.cd_cover

    base_source_path = (
        _preferred_custom_world_path(jacket)
        or _preferred_custom_world_path(cd_cover)
        or _preferred_custom_world_path(vinyl)
        or _preferred_custom_world_path(cd)
        or row.cover_path
    )
    comparison_source_path = (
        _preferred_custom_world_path(vinyl)
        or _preferred_custom_world_path(jacket)
        or _preferred_custom_world_path(cd)
        or _preferred_custom_world_path(cd_cover)
        or base_source_path
    )
    row_cover_source_path = row.cover_path or base_source_path
    base_texture_reference = exported_world_texture_reference("jacket", module_id, album_id)
    hr_texture_reference = exported_world_texture_reference("jacket", module_id, album_id, hr=True)
    export_hr_cover = bool(
        row_cover_source_path
        and comparison_source_path
        and _normalized_source_identity(row_cover_source_path) != _normalized_source_identity(comparison_source_path)
    )
    return CoverTextureDecision(
        base_source_path=base_source_path,
        comparison_source_path=comparison_source_path,
        row_cover_source_path=row_cover_source_path,
        base_texture_reference=base_texture_reference,
        hr_texture_reference=hr_texture_reference,
        playable_texture_reference=hr_texture_reference if export_hr_cover else base_texture_reference,
        export_hr_cover=export_hr_cover,
    )


def has_distinct_empty_inventory(appearance: ResolvedAppearance) -> bool:
    return bool(
        appearance.inventory_empty_path
        and appearance.inventory_empty_path != appearance.inventory_path
    )


def has_distinct_empty_world(appearance: ResolvedAppearance) -> bool:
    return bool(
        appearance.world_empty_path
        and appearance.world_empty_path != appearance.world_path
    )


def normalized_source_identity(path: str) -> str:
    return _normalized_source_identity(path)


def _preferred_custom_world_path(appearance: ResolvedAppearance) -> str:
    if appearance.source == "custom" and appearance.world_path:
        return appearance.world_path
    return ""


def _normalized_source_identity(path: str) -> str:
    if not path:
        return ""
    return str(Path(path).expanduser().resolve(strict=False)).replace("\\", "/").lower()
