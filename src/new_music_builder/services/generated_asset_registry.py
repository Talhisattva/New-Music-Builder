from __future__ import annotations

from hashlib import sha1
from pathlib import Path

from new_music_builder.domain.models import AppearanceKind, GeneratedAssetRecord, MediaRow, ProjectConfig
from new_music_builder.ui.widgets.appearance_entries import AppearanceGridEntry


def normalize_cover_path(cover_path: str | Path | None) -> str:
    if not cover_path:
        return ""
    return str(Path(cover_path).expanduser().resolve(strict=False))


def build_generated_cover_id(cover_path: str | Path | None) -> str:
    normalized = normalize_cover_path(cover_path)
    if not normalized:
        return ""
    return sha1(normalized.encode("utf-8")).hexdigest()[:16]


def build_generated_asset_key(kind: AppearanceKind, cover_path: str | Path | None) -> str:
    cover_id = build_generated_cover_id(cover_path)
    if not cover_id:
        return ""
    return f"generated:{kind}:{cover_id}"


def is_generated_asset_key(asset_key: str) -> bool:
    return asset_key.startswith("generated:")


def upsert_generated_asset_record(project: ProjectConfig, record: GeneratedAssetRecord) -> GeneratedAssetRecord:
    normalized_cover = normalize_cover_path(record.cover_path)
    normalized_key = record.asset_key or build_generated_asset_key(record.kind, normalized_cover)
    next_record = GeneratedAssetRecord(
        kind=record.kind,
        cover_path=normalized_cover,
        asset_key=normalized_key,
        label=record.label,
        inventory_full=record.inventory_full,
        world_full=record.world_full,
        source_name=record.source_name,
    )
    for index, existing in enumerate(project.generated_assets):
        if existing.kind == next_record.kind and existing.cover_path == next_record.cover_path:
            project.generated_assets[index] = next_record
            return next_record
    project.generated_assets.append(next_record)
    return next_record


def has_generated_cover(project: ProjectConfig, kind: AppearanceKind, cover_path: str | Path | None) -> bool:
    normalized_cover = normalize_cover_path(cover_path)
    if not normalized_cover:
        return False
    return any(
        entry.kind == kind
        and entry.cover_path == normalized_cover
        and bool(entry.inventory_full and entry.world_full)
        for entry in project.generated_assets
    )


def can_generate_cover_for_kind(
    project: ProjectConfig,
    row: MediaRow | None,
    kind: AppearanceKind | None,
) -> bool:
    if row is None or kind != "cassette":
        return False
    normalized_cover = normalize_cover_path(row.cover_path)
    if not normalized_cover or not Path(normalized_cover).is_file():
        return False
    return not has_generated_cover(project, kind, normalized_cover)


def visible_generated_entries_for_kind(
    project: ProjectConfig,
    kind: AppearanceKind,
) -> list[AppearanceGridEntry]:
    active_covers = {
        normalize_cover_path(row.cover_path)
        for row in project.media_rows
        if normalize_cover_path(row.cover_path)
    }
    visible: list[AppearanceGridEntry] = []
    for record in project.generated_assets:
        if record.kind != kind or record.cover_path not in active_covers:
            continue
        if not Path(record.inventory_full).is_file() or not Path(record.world_full).is_file():
            continue
        visible.append(
            AppearanceGridEntry(
                key=record.asset_key,
                label=record.label,
                inventory_path=record.inventory_full,
                world_path=record.world_full,
                sprite_mode="single",
                kind=kind,
                is_custom=False,
                is_generated=True,
                is_dual=False,
            )
        )
    visible.sort(key=lambda entry: entry.label.casefold())
    return visible
