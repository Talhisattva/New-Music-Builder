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
    shared_cover_source_path: str = ""
    fallback_source_path: str = ""
    row_cover_source_path: str = ""
    fallback_texture_reference: str = ""
    fallback_texture_relative_path: str = ""
    fallback_transform_kind: str = ""
    hr_texture_reference: str = ""
    shared_cover_texture_reference: str = ""
    fallback_source_is_custom: bool = False
    reuse_existing_cover_texture: bool = False
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
    cover_appearance = _preferred_cover_appearance(row)
    fallback_source_path = cover_appearance.world_path if cover_appearance is not None else ""
    row_cover_source_path = row.cover_path or ""
    fallback_source_is_custom = bool(cover_appearance is not None and cover_appearance.source == "custom")
    fallback_texture_reference = _cover_texture_reference(cover_appearance, module_id, album_id)
    fallback_texture_relative_path = _cover_texture_relative_path(cover_appearance, module_id, album_id)
    fallback_transform_kind = _cover_transform_kind(cover_appearance)
    hr_texture_reference = exported_world_texture_reference("jacket", module_id, album_id, hr=True)
    shared_cover_source_path = row_cover_source_path or fallback_source_path
    export_hr_cover = False
    reuse_existing_cover_texture = False
    if row_cover_source_path:
        if fallback_source_path:
            reuse_existing_cover_texture = _normalized_source_identity(row_cover_source_path) == _normalized_source_identity(fallback_source_path)
            export_hr_cover = not reuse_existing_cover_texture
        else:
            export_hr_cover = True
    shared_cover_texture_reference = hr_texture_reference if export_hr_cover else fallback_texture_reference
    return CoverTextureDecision(
        shared_cover_source_path=shared_cover_source_path,
        fallback_source_path=fallback_source_path,
        row_cover_source_path=row_cover_source_path,
        fallback_texture_reference=fallback_texture_reference,
        fallback_texture_relative_path=fallback_texture_relative_path,
        fallback_transform_kind=fallback_transform_kind,
        hr_texture_reference=hr_texture_reference,
        shared_cover_texture_reference=shared_cover_texture_reference,
        fallback_source_is_custom=fallback_source_is_custom,
        reuse_existing_cover_texture=reuse_existing_cover_texture,
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


def _preferred_cover_appearance(row: PlannedMediaRow) -> ResolvedAppearance | None:
    for kind in ("jacket", "cd_cover", "vinyl", "cd"):
        appearance = row.appearances.for_kind(kind)
        if appearance.world_path:
            return appearance
    return None


def _cover_texture_reference(appearance: ResolvedAppearance | None, module_id: str, album_id: str) -> str:
    if appearance is None:
        return ""
    if appearance.source == "custom":
        return exported_world_texture_reference(appearance.kind, module_id, album_id)
    return _world_texture_reference_from_path(appearance.world_path, fallback_dir=_world_items_dir_for_kind(appearance.kind))


def _cover_texture_relative_path(appearance: ResolvedAppearance | None, module_id: str, album_id: str) -> str:
    if appearance is None or appearance.source != "custom":
        return ""
    return exported_world_texture_relative_path(appearance.kind, module_id, album_id)


def _cover_transform_kind(appearance: ResolvedAppearance | None) -> str:
    if appearance is None:
        return ""
    return "world_square_1024" if appearance.kind == "jacket" else "world_square_256"


def _world_texture_reference_from_path(path: str, *, fallback_dir: str) -> str:
    if not path:
        return ""
    candidate = Path(path)
    parts = candidate.parts
    if "WorldItems" in parts:
        start_index = parts.index("WorldItems")
        return "/".join(parts[start_index:]).removesuffix(candidate.suffix)
    return f"{fallback_dir}/{candidate.stem}"


def _world_items_dir_for_kind(kind: str) -> str:
    if kind in {"cassette", "case"}:
        return "WorldItems/Cassette"
    if kind in {"vinyl", "jacket"}:
        return "WorldItems/Vinyl"
    return "WorldItems/CD"


def _normalized_source_identity(path: str) -> str:
    if not path:
        return ""
    return str(Path(path).expanduser().resolve(strict=False)).replace("\\", "/").lower()
