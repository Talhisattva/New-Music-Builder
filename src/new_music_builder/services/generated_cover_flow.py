from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from new_music_builder.domain.models import AppearanceKind, GeneratedAssetRecord, MediaRow, ProjectConfig
from new_music_builder.services.cover_texture_generator import (
    CoverGenerationResult,
    generate_case_textures_from_cover,
    generate_cassette_textures_from_cover,
    generate_jacket_textures_from_cover,
    generate_vinyl_textures_from_cover,
)
from new_music_builder.services.generated_asset_registry import (
    generated_record_for_kind,
    has_generated_cover,
    normalize_cover_path,
    upsert_generated_asset_record,
)
from new_music_builder.ui.widgets.appearance_entries import AppearanceGridEntry, apply_selection_from_grid_entry

SupportedGeneratedKind = Literal["cassette", "case", "vinyl", "jacket"]
GenerationStatus = Literal["generated", "skipped", "failed"]


@dataclass(frozen=True, slots=True)
class GeneratedKindOutcome:
    kind: SupportedGeneratedKind
    status: GenerationStatus
    record: GeneratedAssetRecord | None = None
    successful_outputs: int = 0
    total_outputs: int = 0
    error: str = ""


@dataclass(frozen=True, slots=True)
class GeneratedCoverSetResult:
    source_name: str
    generated_kinds: tuple[SupportedGeneratedKind, ...] = ()
    skipped_kinds: tuple[SupportedGeneratedKind, ...] = ()
    failed_kinds: tuple[SupportedGeneratedKind, ...] = ()
    output_counts: dict[SupportedGeneratedKind, tuple[int, int]] = field(default_factory=dict)
    outcomes: tuple[GeneratedKindOutcome, ...] = ()


def supported_generated_kinds_for_row(row: MediaRow) -> tuple[SupportedGeneratedKind, ...]:
    supported: list[SupportedGeneratedKind] = []
    if row.enabled_media.get("cassette", False):
        supported.extend(("cassette", "case"))
    if row.enabled_media.get("vinyl", False):
        supported.extend(("vinyl", "jacket"))
    return tuple(supported)


def generate_supported_cover_set_for_row(
    project: ProjectConfig,
    row: MediaRow,
    *,
    cassette_donor_inventory_path: str | Path = "",
    cassette_donor_world_path: str | Path = "",
    case_donor_inventory_path: str | Path = "",
    case_donor_world_path: str | Path = "",
    mask_root: Path | None = None,
    output_root: Path | None = None,
    cassette_generator=generate_cassette_textures_from_cover,
    case_generator=generate_case_textures_from_cover,
    vinyl_generator=generate_vinyl_textures_from_cover,
    jacket_generator=generate_jacket_textures_from_cover,
) -> GeneratedCoverSetResult:
    normalized_cover = normalize_cover_path(row.cover_path)
    if not normalized_cover:
        raise FileNotFoundError("Cover image was not provided.")
    cover_path = Path(normalized_cover)
    if not cover_path.is_file():
        raise FileNotFoundError(f"Cover image was not found: {cover_path}")

    row.ensure_appearances()
    source_name = cover_path.name or "cover"
    generated_kinds: list[SupportedGeneratedKind] = []
    skipped_kinds: list[SupportedGeneratedKind] = []
    failed_kinds: list[SupportedGeneratedKind] = []
    output_counts: dict[SupportedGeneratedKind, tuple[int, int]] = {}
    outcomes: list[GeneratedKindOutcome] = []

    for kind in supported_generated_kinds_for_row(row):
        if has_generated_cover(project, kind, normalized_cover):
            existing_record = generated_record_for_kind(project, kind, normalized_cover)
            if existing_record is not None:
                _apply_generated_record_selection(row, existing_record)
            skipped_kinds.append(kind)
            output_counts[kind] = (0, 0)
            outcomes.append(
                GeneratedKindOutcome(
                    kind=kind,
                    status="skipped",
                    record=existing_record,
                )
            )
            continue
        try:
            result = _generate_kind_from_cover(
                kind,
                normalized_cover,
                cassette_donor_inventory_path=cassette_donor_inventory_path,
                cassette_donor_world_path=cassette_donor_world_path,
                case_donor_inventory_path=case_donor_inventory_path,
                case_donor_world_path=case_donor_world_path,
                mask_root=mask_root,
                output_root=output_root,
                cassette_generator=cassette_generator,
                case_generator=case_generator,
                vinyl_generator=vinyl_generator,
                jacket_generator=jacket_generator,
            )
        except Exception as exc:
            failed_kinds.append(kind)
            outcomes.append(
                GeneratedKindOutcome(
                    kind=kind,
                    status="failed",
                    error=str(exc),
                )
            )
            continue

        record = upsert_generated_asset_record(project, result.record)
        _apply_generated_record_selection(row, record)
        generated_kinds.append(kind)
        output_counts[kind] = (result.successful_outputs, result.total_outputs)
        outcomes.append(
            GeneratedKindOutcome(
                kind=kind,
                status="generated",
                record=record,
                successful_outputs=result.successful_outputs,
                total_outputs=result.total_outputs,
            )
        )

    return GeneratedCoverSetResult(
        source_name=source_name,
        generated_kinds=tuple(generated_kinds),
        skipped_kinds=tuple(skipped_kinds),
        failed_kinds=tuple(failed_kinds),
        output_counts=output_counts,
        outcomes=tuple(outcomes),
    )


def _generate_kind_from_cover(
    kind: SupportedGeneratedKind,
    cover_path: str,
    *,
    cassette_donor_inventory_path: str | Path,
    cassette_donor_world_path: str | Path,
    case_donor_inventory_path: str | Path,
    case_donor_world_path: str | Path,
    mask_root: Path | None,
    output_root: Path | None,
    cassette_generator,
    case_generator,
    vinyl_generator,
    jacket_generator,
) -> CoverGenerationResult:
    if kind == "cassette":
        return cassette_generator(
            cover_path,
            donor_inventory_path=cassette_donor_inventory_path,
            donor_world_path=cassette_donor_world_path,
            mask_root=mask_root,
            output_root=output_root,
        )
    if kind == "case":
        return case_generator(
            cover_path,
            donor_inventory_path=case_donor_inventory_path,
            donor_world_path=case_donor_world_path,
            mask_root=mask_root,
            output_root=output_root,
        )
    if kind == "jacket":
        return jacket_generator(
            cover_path,
            mask_root=mask_root,
            output_root=output_root,
        )
    return vinyl_generator(
        cover_path,
        mask_root=mask_root,
        output_root=output_root,
    )


def _apply_generated_record_selection(row: MediaRow, record: GeneratedAssetRecord) -> None:
    selection = row.appearances[record.kind]
    apply_selection_from_grid_entry(selection, _grid_entry_from_record(record))


def _grid_entry_from_record(record: GeneratedAssetRecord) -> AppearanceGridEntry:
    return AppearanceGridEntry(
        key=record.asset_key,
        label=record.label,
        inventory_path=record.inventory_full,
        world_path=record.world_full,
        sprite_mode="single",
        kind=record.kind,
        is_custom=False,
        is_generated=True,
        is_dual=False,
    )
