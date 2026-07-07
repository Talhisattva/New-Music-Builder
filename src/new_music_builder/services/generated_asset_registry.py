from __future__ import annotations

from hashlib import sha1
from pathlib import Path

from new_music_builder.platform.paths import generated_textures_root
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


def generated_record_for_asset_key(project: ProjectConfig, asset_key: str) -> GeneratedAssetRecord | None:
    return next((record for record in project.generated_assets if record.asset_key == asset_key), None)


def generated_records_for_cover_path(
    project: ProjectConfig,
    cover_path: str | Path | None,
) -> list[GeneratedAssetRecord]:
    normalized_cover = normalize_cover_path(cover_path)
    if not normalized_cover:
        return []
    return [record for record in project.generated_assets if record.cover_path == normalized_cover]


def generated_records_for_asset_key(project: ProjectConfig, asset_key: str) -> list[GeneratedAssetRecord]:
    record = generated_record_for_asset_key(project, asset_key)
    if record is None:
        return []
    return generated_records_for_cover_path(project, record.cover_path)


def generated_record_for_kind(
    project: ProjectConfig,
    kind: AppearanceKind,
    cover_path: str | Path | None,
) -> GeneratedAssetRecord | None:
    normalized_cover = normalize_cover_path(cover_path)
    if not normalized_cover:
        return None
    return next(
        (
            record
            for record in project.generated_assets
            if record.kind == kind and record.cover_path == normalized_cover
        ),
        None,
    )


def remove_generated_cover_set(project: ProjectConfig, asset_key: str) -> list[GeneratedAssetRecord]:
    removed_records = generated_records_for_asset_key(project, asset_key)
    if not removed_records:
        return []
    removed_keys = {record.asset_key for record in removed_records}
    project.generated_assets = [record for record in project.generated_assets if record.asset_key not in removed_keys]
    return removed_records


def remove_generated_records_for_cover_path(
    project: ProjectConfig,
    cover_path: str | Path | None,
) -> list[GeneratedAssetRecord]:
    removed_records = generated_records_for_cover_path(project, cover_path)
    if not removed_records:
        return []
    removed_keys = {record.asset_key for record in removed_records}
    project.generated_assets = [record for record in project.generated_assets if record.asset_key not in removed_keys]
    return removed_records


def delete_generated_cover_set_files(
    records: list[GeneratedAssetRecord],
    *,
    managed_root: Path | None = None,
) -> int:
    root = (managed_root or generated_textures_root()).resolve(strict=False)
    deleted_file_count = 0
    cleanup_dirs: set[Path] = set()
    for record in records:
        for candidate in (record.inventory_full, record.world_full):
            if not candidate:
                continue
            path = Path(candidate).resolve(strict=False)
            if not _is_within_root(path, root):
                continue
            cleanup_dirs.add(path.parent)
            if path.exists() and path.is_file():
                path.unlink()
                deleted_file_count += 1
    for directory in sorted(cleanup_dirs, key=lambda item: len(item.parts), reverse=True):
        _remove_empty_directory_chain(directory, root)
    return deleted_file_count


def _remove_empty_directory_chain(directory: Path, root: Path) -> None:
    current = directory
    while _is_within_root(current, root) and current != root:
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


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
    if row is None or kind not in {"cassette", "case", "vinyl", "jacket", "cd_cover"}:
        return False
    normalized_cover = normalize_cover_path(row.cover_path)
    if not normalized_cover or not Path(normalized_cover).is_file():
        return False
    if kind in {"cassette", "case"} and not row.enabled_media.get("cassette", False):
        return False
    if kind in {"vinyl", "jacket"} and not row.enabled_media.get("vinyl", False):
        return False
    if kind == "cd_cover" and not row.enabled_media.get("cd", False):
        return False
    return not has_generated_cover(project, kind, normalized_cover)

def can_generate_cover_for_row(project: ProjectConfig, row: MediaRow | None) -> bool:
    if row is None:
        return False
    normalized_cover = normalize_cover_path(row.cover_path)
    if not normalized_cover or not Path(normalized_cover).is_file():
        return False
    return (
        (row.enabled_media.get("cassette", False) and any(
            not has_generated_cover(project, kind, normalized_cover)
            for kind in ("cassette", "case")
        ))
        or (row.enabled_media.get("vinyl", False) and any(
            not has_generated_cover(project, kind, normalized_cover)
            for kind in ("vinyl", "jacket")
        ))
        or (row.enabled_media.get("cd", False) and not has_generated_cover(project, "cd_cover", normalized_cover))
    )


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
