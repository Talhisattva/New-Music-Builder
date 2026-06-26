from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops

from new_music_builder.domain.models import GeneratedAssetRecord
from new_music_builder.platform.paths import assets_root, generated_textures_root
from new_music_builder.services.generated_asset_registry import build_generated_asset_key, build_generated_cover_id, normalize_cover_path

INVENTORY_COVER_RESAMPLE = Image.Resampling.BILINEAR


@dataclass(frozen=True, slots=True)
class CoverGenerationResult:
    record: GeneratedAssetRecord
    successful_outputs: int
    total_outputs: int


@dataclass(frozen=True, slots=True)
class InventoryWarpPreset:
    rotation_degrees: float
    initial_scale_ratio: float
    max_scale_ratio: float
    scale_step_ratio: float
    right_edge_inset_ratio: float
    right_edge_vertical_inset_ratio: float
    coverage_alpha_threshold: int = 8


@dataclass(frozen=True, slots=True)
class InventoryShearPreset:
    initial_edge: int
    max_edge: int
    shear_degrees: float
    edge_step: int = 1
    coverage_alpha_threshold: int = 8


CASSETTE_INVENTORY_PRESET = InventoryWarpPreset(
    rotation_degrees=25.0,
    initial_scale_ratio=2.10,
    max_scale_ratio=3.30,
    scale_step_ratio=0.12,
    right_edge_inset_ratio=0.5,
    right_edge_vertical_inset_ratio=0.25,
)
CASE_INVENTORY_PRESET = InventoryShearPreset(
    initial_edge=23,
    max_edge=40,
    shear_degrees=50.0,
)
JACKET_INVENTORY_PRESET = InventoryShearPreset(
    initial_edge=30,
    max_edge=46,
    shear_degrees=60.0,
)
CD_COVER_INVENTORY_PRESET = InventoryShearPreset(
    initial_edge=24,
    max_edge=40,
    shear_degrees=50.0,
)

WORLD_OVERLAY_SECOND_MULTIPLY_RATIO = 0.50
VINYL_OVERLAY_SECOND_MULTIPLY_RATIO = 0.50
VINYL_INVENTORY_TARGET_SIZE = (12, 7)
VINYL_WORLD_TARGET_SIZE = (68, 68)
JACKET_WORLD_OUTPUT_SIZE = (1024, 1024)


def generate_cassette_textures_from_cover(
    cover_path: str | Path,
    *,
    donor_inventory_path: str | Path,
    donor_world_path: str | Path,
    mask_root: Path | None = None,
    output_root: Path | None = None,
) -> CoverGenerationResult:
    normalized_cover = normalize_cover_path(cover_path)
    if not normalized_cover:
        raise FileNotFoundError("Cover image was not provided.")

    source_path = Path(normalized_cover)
    if not source_path.is_file():
        raise FileNotFoundError(f"Cover image was not found: {source_path}")
    normalized_donor_inventory = normalize_cover_path(donor_inventory_path)
    if not normalized_donor_inventory:
        raise FileNotFoundError("Donor cassette shell was unavailable.")
    donor_source_path = Path(normalized_donor_inventory)
    if not donor_source_path.is_file():
        raise FileNotFoundError(f"Donor cassette shell was not found: {donor_source_path}")
    normalized_donor_world = normalize_cover_path(donor_world_path)
    if not normalized_donor_world:
        raise FileNotFoundError("Donor cassette world shell was unavailable.")
    donor_world_source_path = Path(normalized_donor_world)
    if not donor_world_source_path.is_file():
        raise FileNotFoundError(f"Donor cassette world shell was not found: {donor_world_source_path}")

    resolved_mask_root = mask_root or (assets_root() / "Mask")
    resolved_output_root = output_root or generated_textures_root()
    cover_id = build_generated_cover_id(normalized_cover)
    cassette_output_root = resolved_output_root / "Cassette" / cover_id
    cassette_output_root.mkdir(parents=True, exist_ok=True)

    inventory_mask = resolved_mask_root / "Inventory" / "Cassette" / "Item_NM_Cassette_Mask.png"
    inventory_outer_mask = resolved_mask_root / "Inventory" / "Cassette" / "Item_NM_Cassette_Outer_Mask.png"
    world_mask = resolved_mask_root / "World" / "Cassette" / "Cassette_World_Mask.png"
    world_outer_mask = resolved_mask_root / "World" / "Cassette" / "Cassette_World_Outer_Mask.png"
    world_outer = resolved_mask_root / "World" / "Cassette" / "Cassette_World_Outer.png"
    world_overlay = resolved_mask_root / "World" / "Cassette" / "Cassette_World_Overlay.png"
    world_overlay_detail = resolved_mask_root / "World" / "Cassette" / "Cassette_World_Overlay_02.png"

    inventory_output = cassette_output_root / "Item_NM_Cassette_Generated.png"
    world_output = cassette_output_root / "World_NM_Cassette_Generated.png"

    _render_cassette_inventory(
        source_path=source_path,
        donor_inventory_path=donor_source_path,
        mask_path=inventory_mask,
        outer_mask_path=inventory_outer_mask,
        output_path=inventory_output,
    )
    _render_cassette_world(
        source_path=source_path,
        mask_path=world_mask,
        donor_world_path=donor_world_source_path,
        outer_mask_path=world_outer_mask,
        outer_path=world_outer,
        overlay_paths=(world_overlay, world_overlay_detail),
        output_path=world_output,
    )

    record = GeneratedAssetRecord(
        kind="cassette",
        cover_path=normalized_cover,
        asset_key=build_generated_asset_key("cassette", normalized_cover),
        label=f"{source_path.stem} Generated",
        inventory_full=str(inventory_output),
        world_full=str(world_output),
        source_name=source_path.name,
    )
    return CoverGenerationResult(record=record, successful_outputs=2, total_outputs=2)


def generate_vinyl_textures_from_cover(
    cover_path: str | Path,
    *,
    mask_root: Path | None = None,
    output_root: Path | None = None,
) -> CoverGenerationResult:
    normalized_cover = normalize_cover_path(cover_path)
    if not normalized_cover:
        raise FileNotFoundError("Cover image was not provided.")

    source_path = Path(normalized_cover)
    if not source_path.is_file():
        raise FileNotFoundError(f"Cover image was not found: {source_path}")

    resolved_mask_root = mask_root or (assets_root() / "Mask")
    resolved_output_root = output_root or generated_textures_root()
    cover_id = build_generated_cover_id(normalized_cover)
    vinyl_output_root = resolved_output_root / "Vinyl" / cover_id
    vinyl_output_root.mkdir(parents=True, exist_ok=True)

    inventory_mask = resolved_mask_root / "Inventory" / "Vinyl" / "Item_NM_Vinyl_Mask.png"
    inventory_outer = resolved_mask_root / "Inventory" / "Vinyl" / "Item_NM_Vinyl_Outer.png"
    inventory_overlay = resolved_mask_root / "Inventory" / "Vinyl" / "Item_NM_Vinyl_Overlay.png"
    world_mask = resolved_mask_root / "World" / "Vinyl" / "World_NM_Vinyl_Mask.png"
    world_outer = resolved_mask_root / "World" / "Vinyl" / "World_NM_Vinyl_Outer.png"
    world_overlay = resolved_mask_root / "World" / "Vinyl" / "World_NM_Vinyl_Overlay.png"

    inventory_output = vinyl_output_root / "Item_NM_Vinyl_Generated.png"
    world_output = vinyl_output_root / "World_NM_Vinyl_Generated.png"

    _render_single_mask_composite(
        source_path=source_path,
        mask_path=inventory_mask,
        outer_path=inventory_outer,
        overlay_paths=(inventory_overlay,),
        overlay_second_pass_ratio=VINYL_OVERLAY_SECOND_MULTIPLY_RATIO,
        cover_target_size=VINYL_INVENTORY_TARGET_SIZE,
        preserve_square=False,
        use_average_cover_fill=True,
        output_path=inventory_output,
    )
    _render_single_mask_composite(
        source_path=source_path,
        mask_path=world_mask,
        outer_path=world_outer,
        overlay_paths=(world_overlay,),
        overlay_second_pass_ratio=VINYL_OVERLAY_SECOND_MULTIPLY_RATIO,
        cover_target_size=VINYL_WORLD_TARGET_SIZE,
        preserve_square=True,
        output_path=world_output,
    )

    record = GeneratedAssetRecord(
        kind="vinyl",
        cover_path=normalized_cover,
        asset_key=build_generated_asset_key("vinyl", normalized_cover),
        label=f"{source_path.stem} Generated",
        inventory_full=str(inventory_output),
        world_full=str(world_output),
        source_name=source_path.name,
    )
    return CoverGenerationResult(record=record, successful_outputs=2, total_outputs=2)


def generate_case_textures_from_cover(
    cover_path: str | Path,
    *,
    donor_inventory_path: str | Path,
    donor_world_path: str | Path,
    mask_root: Path | None = None,
    output_root: Path | None = None,
) -> CoverGenerationResult:
    normalized_cover = normalize_cover_path(cover_path)
    if not normalized_cover:
        raise FileNotFoundError("Cover image was not provided.")

    source_path = Path(normalized_cover)
    if not source_path.is_file():
        raise FileNotFoundError(f"Cover image was not found: {source_path}")

    resolved_mask_root = mask_root or (assets_root() / "Mask")
    resolved_output_root = output_root or generated_textures_root()
    cover_id = build_generated_cover_id(normalized_cover)
    case_output_root = resolved_output_root / "Case" / cover_id
    case_output_root.mkdir(parents=True, exist_ok=True)

    inventory_mask = resolved_mask_root / "Inventory" / "CassetteCase" / "Item_NM_Case_Mask.png"
    inventory_outer_mask = resolved_mask_root / "Inventory" / "CassetteCase" / "Item_NM_Case_Outer_Mask.png"
    inventory_outer = resolved_mask_root / "Inventory" / "CassetteCase" / "Item_NM_Case_Outer.png"
    world_mask = resolved_mask_root / "World" / "CassetteCase" / "World_NM_CassetteCase_Mask.png"
    world_outer = resolved_mask_root / "World" / "CassetteCase" / "World_NM_CassetteCase_Outer.png"

    inventory_output = case_output_root / "Item_NM_Case_Generated.png"
    world_output = case_output_root / "World_NM_CassetteCover_Generated.png"

    normalized_donor_inventory = normalize_cover_path(donor_inventory_path)
    normalized_donor_world = normalize_cover_path(donor_world_path)

    _render_case_inventory(
        source_path=source_path,
        donor_inventory_path=Path(normalized_donor_inventory) if normalized_donor_inventory else None,
        mask_path=inventory_mask,
        outer_mask_path=inventory_outer_mask,
        fallback_outer_path=inventory_outer,
        output_path=inventory_output,
    )
    _render_case_world(
        source_path=source_path,
        donor_world_path=Path(normalized_donor_world) if normalized_donor_world else None,
        mask_path=world_mask,
        fallback_outer_path=world_outer,
        output_path=world_output,
    )

    record = GeneratedAssetRecord(
        kind="case",
        cover_path=normalized_cover,
        asset_key=build_generated_asset_key("case", normalized_cover),
        label=f"{source_path.stem} Generated",
        inventory_full=str(inventory_output),
        world_full=str(world_output),
        source_name=source_path.name,
    )
    return CoverGenerationResult(record=record, successful_outputs=2, total_outputs=2)


def generate_jacket_textures_from_cover(
    cover_path: str | Path,
    *,
    mask_root: Path | None = None,
    output_root: Path | None = None,
) -> CoverGenerationResult:
    normalized_cover = normalize_cover_path(cover_path)
    if not normalized_cover:
        raise FileNotFoundError("Cover image was not provided.")

    source_path = Path(normalized_cover)
    if not source_path.is_file():
        raise FileNotFoundError(f"Cover image was not found: {source_path}")

    resolved_mask_root = mask_root or (assets_root() / "Mask")
    resolved_output_root = output_root or generated_textures_root()
    cover_id = build_generated_cover_id(normalized_cover)
    jacket_output_root = resolved_output_root / "Jacket" / cover_id
    jacket_output_root.mkdir(parents=True, exist_ok=True)

    inventory_mask = resolved_mask_root / "Inventory" / "VinylJacket" / "Item_NM_Jacket_Mask.png"
    inventory_overlay = resolved_mask_root / "Inventory" / "VinylJacket" / "Item_NM_Jacket_Overlay.png"

    inventory_output = jacket_output_root / "Item_NM_Jacket_Generated.png"
    world_output = jacket_output_root / "World_NM_Cover_Generated.png"

    _render_jacket_inventory(
        source_path=source_path,
        mask_path=inventory_mask,
        overlay_path=inventory_overlay,
        output_path=inventory_output,
    )
    _render_letterboxed_square_cover(
        source_path=source_path,
        output_size=JACKET_WORLD_OUTPUT_SIZE,
        output_path=world_output,
    )

    record = GeneratedAssetRecord(
        kind="jacket",
        cover_path=normalized_cover,
        asset_key=build_generated_asset_key("jacket", normalized_cover),
        label=f"{source_path.stem} Generated",
        inventory_full=str(inventory_output),
        world_full=str(world_output),
        source_name=source_path.name,
    )
    return CoverGenerationResult(record=record, successful_outputs=2, total_outputs=2)


def generate_cd_cover_textures_from_cover(
    cover_path: str | Path,
    *,
    mask_root: Path | None = None,
    output_root: Path | None = None,
) -> CoverGenerationResult:
    normalized_cover = normalize_cover_path(cover_path)
    if not normalized_cover:
        raise FileNotFoundError("Cover image was not provided.")

    source_path = Path(normalized_cover)
    if not source_path.is_file():
        raise FileNotFoundError(f"Cover image was not found: {source_path}")

    resolved_mask_root = mask_root or (assets_root() / "Mask")
    resolved_output_root = output_root or generated_textures_root()
    cover_id = build_generated_cover_id(normalized_cover)
    output_root_dir = resolved_output_root / "CDCover" / cover_id
    output_root_dir.mkdir(parents=True, exist_ok=True)

    inventory_mask = resolved_mask_root / "Inventory" / "CD" / "Item_NM_CDCover_Mask.png"
    inventory_outer = resolved_mask_root / "Inventory" / "CD" / "Item_NM_CDCover_Outer.png"
    world_mask = resolved_mask_root / "World" / "CDCover" / "World_NM_CDCover_Mask.png"
    world_outer = resolved_mask_root / "World" / "CDCover" / "World_NM_CDCover_Outer.png"

    inventory_output = output_root_dir / "Item_NM_CDCover_Generated.png"
    world_output = output_root_dir / "World_NM_CDCover_Generated.png"

    _render_cd_cover_inventory(
        source_path=source_path,
        mask_path=inventory_mask,
        outer_path=inventory_outer,
        output_path=inventory_output,
    )
    _render_cd_cover_world(
        source_path=source_path,
        mask_path=world_mask,
        outer_path=world_outer,
        output_path=world_output,
    )

    record = GeneratedAssetRecord(
        kind="cd_cover",
        cover_path=normalized_cover,
        asset_key=build_generated_asset_key("cd_cover", normalized_cover),
        label=f"{source_path.stem} Generated",
        inventory_full=str(inventory_output),
        world_full=str(world_output),
        source_name=source_path.name,
    )
    return CoverGenerationResult(record=record, successful_outputs=2, total_outputs=2)


def _render_cassette_inventory(
    *,
    source_path: Path,
    donor_inventory_path: Path,
    mask_path: Path,
    outer_mask_path: Path,
    output_path: Path,
) -> None:
    with Image.open(mask_path) as mask_source:
        mask_image = mask_source.convert("RGBA")
    mask_alpha = _alpha_mask(mask_image)
    with Image.open(outer_mask_path) as outer_mask_source:
        outer_mask_alpha = _alpha_mask(outer_mask_source.convert("RGBA"))
    masked_cover = _build_inventory_masked_cover(
        source_path=source_path,
        mask_size=mask_image.size,
        mask_alpha=mask_alpha,
        preset=CASSETTE_INVENTORY_PRESET,
    )
    donor_outer = _build_masked_donor_layer(
        source_path=donor_inventory_path,
        size=mask_image.size,
        mask_alpha=outer_mask_alpha,
    )
    base = _compose_inventory_layers(masked_cover, donor_outer)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(output_path)


def _render_cassette_world(
    *,
    source_path: Path,
    donor_world_path: Path,
    mask_path: Path,
    outer_mask_path: Path,
    outer_path: Path,
    overlay_paths: tuple[Path, ...],
    output_path: Path,
) -> None:
    with Image.open(mask_path) as mask_source:
        mask_image = mask_source.convert("RGBA")
    mask_alpha = _alpha_mask(mask_image)
    with Image.open(outer_mask_path) as outer_mask_source:
        outer_mask_alpha = _alpha_mask(outer_mask_source.convert("RGBA"))
    masked_cover = _build_masked_cover_from_mask_alpha(
        source_path=source_path,
        size=mask_image.size,
        mask_alpha=mask_alpha,
    )
    with Image.open(outer_path) as outer_source:
        outer_image = outer_source.convert("RGBA")
    donor_outer = _build_masked_donor_layer(
        source_path=donor_world_path,
        size=mask_image.size,
        mask_alpha=outer_mask_alpha,
    )
    fallback_outer = _apply_mask_alpha(outer_image, outer_mask_alpha)
    base = Image.new("RGBA", masked_cover.size, (0, 0, 0, 0))
    base.alpha_composite(masked_cover)
    base.alpha_composite(fallback_outer)
    base.alpha_composite(donor_outer)
    if overlay_paths:
        with Image.open(overlay_paths[0]) as overlay_source:
            base = _multiply_with_second_pass(
                base,
                overlay_source.convert("RGBA"),
                second_pass_ratio=WORLD_OVERLAY_SECOND_MULTIPLY_RATIO,
            )
    for overlay_path in overlay_paths[1:]:
        with Image.open(overlay_path) as overlay_source:
            base.alpha_composite(overlay_source.convert("RGBA"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(output_path)


def _render_single_mask_composite(
    *,
    source_path: Path,
    mask_path: Path,
    outer_path: Path,
    overlay_paths: tuple[Path, ...],
    overlay_second_pass_ratio: float,
    cover_target_size: tuple[int, int] | None = None,
    preserve_square: bool = True,
    use_average_cover_fill: bool = False,
    output_path: Path,
) -> None:
    with Image.open(mask_path) as mask_source:
        mask_image = mask_source.convert("RGBA")
    mask_alpha = _alpha_mask(mask_image)
    if use_average_cover_fill:
        masked_cover = _build_average_color_masked_cover(
            source_path=source_path,
            size=mask_image.size,
            mask_alpha=mask_alpha,
        )
    elif cover_target_size is None:
        masked_cover = _build_masked_cover_from_mask_alpha(
            source_path=source_path,
            size=mask_image.size,
            mask_alpha=mask_alpha,
        )
    else:
        masked_cover = _build_targeted_masked_cover(
            source_path=source_path,
            size=mask_image.size,
            mask_alpha=mask_alpha,
            target_size=cover_target_size,
            preserve_square=preserve_square,
        )
    base = Image.new("RGBA", masked_cover.size, (0, 0, 0, 0))
    base.alpha_composite(masked_cover)
    with Image.open(outer_path) as outer_source:
        base.alpha_composite(outer_source.convert("RGBA"))
    if overlay_paths:
        with Image.open(overlay_paths[0]) as overlay_source:
            base = _multiply_with_second_pass(
                base,
                overlay_source.convert("RGBA"),
                second_pass_ratio=overlay_second_pass_ratio,
            )
    for overlay_path in overlay_paths[1:]:
        with Image.open(overlay_path) as overlay_source:
            base.alpha_composite(overlay_source.convert("RGBA"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(output_path)


def _render_case_inventory(
    *,
    source_path: Path,
    donor_inventory_path: Path | None,
    mask_path: Path,
    outer_mask_path: Path,
    fallback_outer_path: Path,
    output_path: Path,
) -> None:
    with Image.open(mask_path) as mask_source:
        mask_image = mask_source.convert("RGBA")
    mask_alpha = _alpha_mask(mask_image)
    with Image.open(outer_mask_path) as outer_mask_source:
        outer_mask_alpha = _alpha_mask(outer_mask_source.convert("RGBA"))
    masked_cover = _build_case_inventory_masked_cover(
        source_path=source_path,
        mask_size=mask_image.size,
        mask_alpha=mask_alpha,
    )
    donor_outer = _build_optional_masked_donor_layer(
        source_path=donor_inventory_path,
        size=mask_image.size,
        mask_alpha=outer_mask_alpha,
    )
    with Image.open(fallback_outer_path) as fallback_outer_source:
        fallback_outer = _apply_mask_alpha(fallback_outer_source.convert("RGBA"), outer_mask_alpha)
    base = Image.new("RGBA", mask_image.size, (0, 0, 0, 0))
    base.alpha_composite(masked_cover)
    base.alpha_composite(fallback_outer)
    if donor_outer is not None:
        base.alpha_composite(donor_outer)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(output_path)


def _render_cd_cover_inventory(
    *,
    source_path: Path,
    mask_path: Path,
    outer_path: Path,
    output_path: Path,
) -> None:
    with Image.open(mask_path) as mask_source:
        mask_image = mask_source.convert("RGBA")
    mask_alpha = _alpha_mask(mask_image)
    masked_cover = _build_inventory_sheared_cover(
        source_path=source_path,
        mask_size=mask_image.size,
        mask_alpha=mask_alpha,
        preset=CD_COVER_INVENTORY_PRESET,
    )
    masked_cover = _apply_mask_alpha(masked_cover, mask_alpha)
    base = Image.new("RGBA", mask_image.size, (0, 0, 0, 0))
    base.alpha_composite(masked_cover)
    with Image.open(outer_path) as outer_source:
        base.alpha_composite(outer_source.convert("RGBA"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(output_path)


def _render_case_world(
    *,
    source_path: Path,
    donor_world_path: Path | None,
    mask_path: Path,
    fallback_outer_path: Path,
    output_path: Path,
) -> None:
    with Image.open(mask_path) as mask_source:
        mask_image = mask_source.convert("RGBA")
    mask_alpha = _alpha_mask(mask_image)
    masked_cover = _build_masked_cover_to_mask_height(
        source_path=source_path,
        size=mask_image.size,
        mask_alpha=mask_alpha,
    )
    with Image.open(fallback_outer_path) as outer_source:
        fallback_outer = outer_source.convert("RGBA")
    donor_outer = _build_optional_inverse_masked_donor_layer(
        source_path=donor_world_path,
        size=mask_image.size,
        cover_mask_alpha=mask_alpha,
    )
    base = Image.new("RGBA", mask_image.size, (0, 0, 0, 0))
    base.alpha_composite(masked_cover)
    base.alpha_composite(fallback_outer)
    if donor_outer is not None:
        base.alpha_composite(donor_outer)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(output_path)


def _render_cd_cover_world(
    *,
    source_path: Path,
    mask_path: Path,
    outer_path: Path,
    output_path: Path,
) -> None:
    with Image.open(mask_path) as mask_source:
        mask_image = mask_source.convert("RGBA")
    mask_alpha = _alpha_mask(mask_image)
    masked_cover = _build_masked_cover_from_mask_alpha(
        source_path=source_path,
        size=mask_image.size,
        mask_alpha=mask_alpha,
    )
    base = Image.new("RGBA", mask_image.size, (0, 0, 0, 0))
    base.alpha_composite(masked_cover)
    with Image.open(outer_path) as outer_source:
        base.alpha_composite(outer_source.convert("RGBA"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(output_path)


def _render_jacket_inventory(
    *,
    source_path: Path,
    mask_path: Path,
    overlay_path: Path,
    output_path: Path,
) -> None:
    with Image.open(mask_path) as mask_source:
        mask_image = mask_source.convert("RGBA")
    mask_alpha = _alpha_mask(mask_image)
    masked_cover = _build_inventory_sheared_cover(
        source_path=source_path,
        mask_size=mask_image.size,
        mask_alpha=mask_alpha,
        preset=JACKET_INVENTORY_PRESET,
    )
    with Image.open(overlay_path) as overlay_source:
        base = _alpha_composite_overlay(
            masked_cover,
            overlay_source.convert("RGBA"),
            opacity=0.6,
        )
    base = _apply_mask_alpha(base, mask_alpha)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(output_path)


def _render_letterboxed_square_cover(
    *,
    source_path: Path,
    output_size: tuple[int, int],
    output_path: Path,
) -> None:
    image = _fit_cover_to_canvas(source_path, output_size, allow_upscale=True, crop_to_visible_bounds=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def _build_inventory_masked_cover(
    *,
    source_path: Path,
    mask_size: tuple[int, int],
    mask_alpha: Image.Image,
    preset: InventoryWarpPreset,
) -> Image.Image:
    transformed = _build_inventory_transformed_cover(
        source_path=source_path,
        mask_size=mask_size,
        mask_alpha=mask_alpha,
        preset=preset,
    )
    return _apply_mask_alpha(transformed, mask_alpha)


def _build_case_inventory_masked_cover(
    *,
    source_path: Path,
    mask_size: tuple[int, int],
    mask_alpha: Image.Image,
) -> Image.Image:
    transformed = _build_inventory_sheared_cover(
        source_path=source_path,
        mask_size=mask_size,
        mask_alpha=mask_alpha,
        preset=CASE_INVENTORY_PRESET,
    )
    return _apply_mask_alpha(transformed, mask_alpha)


def _build_masked_cover_from_mask_alpha(
    *,
    source_path: Path,
    size: tuple[int, int],
    mask_alpha: Image.Image,
) -> Image.Image:
    fitted_cover = _fit_cover_to_mask_width(source_path, size, mask_alpha)
    return _apply_mask_alpha(fitted_cover, mask_alpha)


def _build_masked_cover_to_mask_height(
    *,
    source_path: Path,
    size: tuple[int, int],
    mask_alpha: Image.Image,
) -> Image.Image:
    fitted_cover = _fit_cover_to_mask_height(source_path, size, mask_alpha)
    return _apply_mask_alpha(fitted_cover, mask_alpha)


def _build_targeted_masked_cover(
    *,
    source_path: Path,
    size: tuple[int, int],
    mask_alpha: Image.Image,
    target_size: tuple[int, int],
    preserve_square: bool,
) -> Image.Image:
    fitted_cover = _fit_cover_to_target_region(
        source_path=source_path,
        size=size,
        mask_alpha=mask_alpha,
        target_size=target_size,
        preserve_square=preserve_square,
    )
    return _apply_mask_alpha(fitted_cover, mask_alpha)


def _build_inventory_transformed_cover(
    *,
    source_path: Path,
    mask_size: tuple[int, int],
    mask_alpha: Image.Image,
    preset: InventoryWarpPreset,
) -> Image.Image:
    target_edge = max(mask_size)
    base_square_size = target_edge * preset.initial_scale_ratio
    max_square_size = target_edge * preset.max_scale_ratio
    square_size = max(target_edge, int(ceil(base_square_size)))
    max_size = max(square_size, int(ceil(max_square_size)))
    while square_size <= max_size:
        square_source = _prepare_square_source(source_path, square_size)
        warped = _apply_inventory_warp(square_source, preset)
        placed = _place_transformed_cover_on_canvas(
            warped,
            mask_size,
            mask_alpha=mask_alpha,
            alpha_threshold=preset.coverage_alpha_threshold,
        )
        if _mask_region_is_fully_covered(placed, mask_alpha, alpha_threshold=preset.coverage_alpha_threshold):
            return placed
        square_size = int(ceil(square_size * (1.0 + preset.scale_step_ratio)))
        if square_size <= target_edge:
            square_size = target_edge + 1
    final_square = _prepare_square_source(source_path, max_size)
    final_warped = _apply_inventory_warp(final_square, preset)
    return _place_transformed_cover_on_canvas(
        final_warped,
        mask_size,
        mask_alpha=mask_alpha,
        alpha_threshold=preset.coverage_alpha_threshold,
    )


def _build_inventory_sheared_cover(
    *,
    source_path: Path,
    mask_size: tuple[int, int],
    mask_alpha: Image.Image,
    preset: InventoryShearPreset,
) -> Image.Image:
    edge = max(1, preset.initial_edge)
    max_edge = max(edge, preset.max_edge)
    while edge <= max_edge:
        square_source = _prepare_square_source(source_path, edge)
        sheared = _apply_inventory_shear(square_source, preset)
        placed = _place_transformed_cover_on_canvas(
            sheared,
            mask_size,
            mask_alpha=mask_alpha,
            alpha_threshold=preset.coverage_alpha_threshold,
        )
        if _mask_region_is_fully_covered(placed, mask_alpha, alpha_threshold=preset.coverage_alpha_threshold):
            return placed
        edge += max(1, preset.edge_step)
    square_source = _prepare_square_source(source_path, max_edge)
    sheared = _apply_inventory_shear(square_source, preset)
    return _place_transformed_cover_on_canvas(
        sheared,
        mask_size,
        mask_alpha=mask_alpha,
        alpha_threshold=preset.coverage_alpha_threshold,
    )


def _build_masked_cover(*, source_path: Path, mask_path: Path) -> Image.Image:
    with Image.open(mask_path) as mask_source:
        mask_image = mask_source.convert("RGBA")
    return _build_masked_cover_from_mask_alpha(
        source_path=source_path,
        size=mask_image.size,
        mask_alpha=_alpha_mask(mask_image),
    )


def _build_average_color_masked_cover(
    *,
    source_path: Path,
    size: tuple[int, int],
    mask_alpha: Image.Image,
) -> Image.Image:
    average_color = _average_visible_cover_color(source_path)
    filled = Image.new("RGBA", size, average_color)
    return _apply_mask_alpha(filled, mask_alpha)


def _prepare_square_source(source_path: Path, target_size: int) -> Image.Image:
    with Image.open(source_path) as source_image:
        source = source_image.convert("RGBA")
    crop_size = min(source.width, source.height)
    left = (source.width - crop_size) // 2
    top = (source.height - crop_size) // 2
    square = source.crop((left, top, left + crop_size, top + crop_size))
    return square.resize((target_size, target_size), INVENTORY_COVER_RESAMPLE)


def _average_visible_cover_color(source_path: Path) -> tuple[int, int, int, int]:
    with Image.open(source_path) as source_image:
        source = source_image.convert("RGBA")
    alpha = np.asarray(source.getchannel("A"), dtype=np.float32)
    visible = alpha > 0
    if not np.any(visible):
        return (0, 0, 0, 0)
    rgb = np.asarray(source.convert("RGB"), dtype=np.float32)
    weights = (alpha / 255.0)[visible]
    visible_rgb = rgb[visible]
    weighted = (visible_rgb * weights[:, None]).sum(axis=0) / max(weights.sum(), 1e-6)
    return (
        int(round(float(weighted[0]))),
        int(round(float(weighted[1]))),
        int(round(float(weighted[2]))),
        255,
    )


def _apply_inventory_warp(image: Image.Image, preset: InventoryWarpPreset) -> Image.Image:
    rotated = image.rotate(
        preset.rotation_degrees,
        resample=INVENTORY_COVER_RESAMPLE,
        expand=True,
        fillcolor=(0, 0, 0, 0),
    )
    return _apply_perspective_warp(
        rotated,
        right_edge_inset_ratio=preset.right_edge_inset_ratio,
        right_edge_vertical_inset_ratio=preset.right_edge_vertical_inset_ratio,
    )


def _apply_inventory_shear(image: Image.Image, preset: InventoryShearPreset) -> Image.Image:
    shear_ratio = preset.shear_degrees / 180.0
    width, height = image.size
    vertical_offset = max(1, int(round(abs(shear_ratio) * width)))
    output_height = height + vertical_offset
    output = Image.new("RGBA", (width, output_height), (0, 0, 0, 0))
    width_divisor = max(1, width - 1)
    for x in range(width):
        column = image.crop((x, 0, x + 1, height))
        if shear_ratio >= 0:
            y_offset = int(round((x / width_divisor) * vertical_offset))
        else:
            y_offset = int(round(((width_divisor - x) / width_divisor) * vertical_offset))
        output.alpha_composite(column, (x, y_offset))
    return output


def _apply_perspective_warp(
    image: Image.Image,
    *,
    right_edge_inset_ratio: float,
    right_edge_vertical_inset_ratio: float,
) -> Image.Image:
    width, height = image.size
    right_inset = max(1, int(round(width * right_edge_inset_ratio)))
    vertical_inset = max(1, int(round(height * right_edge_vertical_inset_ratio)))
    destination_quad = (
        (0.0, 0.0),
        (width - right_inset, float(vertical_inset)),
        (width - right_inset, float(height - vertical_inset)),
        (0.0, float(height)),
    )
    source_quad = (
        (0.0, 0.0),
        (float(width), 0.0),
        (float(width), float(height)),
        (0.0, float(height)),
    )
    coefficients = _find_perspective_coefficients(source_quad, destination_quad)
    return image.transform(
        (width, height),
        Image.Transform.PERSPECTIVE,
        coefficients,
        resample=INVENTORY_COVER_RESAMPLE,
        fillcolor=(0, 0, 0, 0),
    )


def _find_perspective_coefficients(
    source_quad: tuple[tuple[float, float], ...],
    destination_quad: tuple[tuple[float, float], ...],
) -> tuple[float, ...]:
    matrix: list[list[float]] = []
    vector: list[float] = []
    for (src_x, src_y), (dst_x, dst_y) in zip(source_quad, destination_quad, strict=True):
        matrix.append([dst_x, dst_y, 1.0, 0.0, 0.0, 0.0, -src_x * dst_x, -src_x * dst_y])
        matrix.append([0.0, 0.0, 0.0, dst_x, dst_y, 1.0, -src_y * dst_x, -src_y * dst_y])
        vector.extend([src_x, src_y])
    solution = np.linalg.solve(np.array(matrix, dtype=float), np.array(vector, dtype=float))
    return tuple(float(value) for value in solution)


def _place_transformed_cover_on_canvas(
    image: Image.Image,
    size: tuple[int, int],
    *,
    mask_alpha: Image.Image | None = None,
    alpha_threshold: int = 8,
) -> Image.Image:
    centered_x = (size[0] - image.width) // 2
    centered_y = (size[1] - image.height) // 2
    if mask_alpha is None:
        return _composite_image_on_canvas(image, size, centered_x, centered_y)

    max_offset_x = max(0, image.width - size[0])
    max_offset_y = max(0, image.height - size[1])
    best_canvas: Image.Image | None = None
    best_distance: tuple[int, int, int] | None = None
    for offset_x in range(-max_offset_x, max_offset_x + 1):
        for offset_y in range(-max_offset_y, max_offset_y + 1):
            canvas = _composite_image_on_canvas(
                image,
                size,
                centered_x + offset_x,
                centered_y + offset_y,
            )
            if not _mask_region_is_fully_covered(canvas, mask_alpha, alpha_threshold=alpha_threshold):
                continue
            distance = (
                abs(offset_x) + abs(offset_y),
                abs(offset_y),
                abs(offset_x),
            )
            if best_distance is None or distance < best_distance:
                best_canvas = canvas
                best_distance = distance

    if best_canvas is not None:
        return best_canvas
    return _composite_image_on_canvas(image, size, centered_x, centered_y)


def _composite_image_on_canvas(
    image: Image.Image,
    size: tuple[int, int],
    paste_x: int,
    paste_y: int,
) -> Image.Image:
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(image, (paste_x, paste_y))
    return canvas


def _fit_cover_to_canvas(
    source_path: Path,
    size: tuple[int, int],
    *,
    allow_upscale: bool = False,
    crop_to_visible_bounds: bool = False,
) -> Image.Image:
    with Image.open(source_path) as source_image:
        source = source_image.convert("RGBA")
    if crop_to_visible_bounds:
        source = _crop_image_to_visible_bounds(source)
    fitted = Image.new("RGBA", size, (0, 0, 0, 0))
    if allow_upscale:
        scale_ratio = min(size[0] / max(1, source.width), size[1] / max(1, source.height))
        target_size = (
            max(1, int(round(source.width * scale_ratio))),
            max(1, int(round(source.height * scale_ratio))),
        )
        contained = source.resize(target_size, Image.Resampling.LANCZOS)
    else:
        contained = source.copy()
        contained.thumbnail(size, Image.Resampling.LANCZOS)
    paste_x = (size[0] - contained.width) // 2
    paste_y = (size[1] - contained.height) // 2
    fitted.paste(contained, (paste_x, paste_y), contained)
    return fitted


def _crop_image_to_visible_bounds(image: Image.Image) -> Image.Image:
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        return image
    return image.crop(bbox)


def _fit_cover_to_mask_width(
    source_path: Path,
    size: tuple[int, int],
    mask_alpha: Image.Image,
) -> Image.Image:
    with Image.open(source_path) as source_image:
        source = source_image.convert("RGBA")
    crop_size = min(source.width, source.height)
    left = (source.width - crop_size) // 2
    top = (source.height - crop_size) // 2
    square = source.crop((left, top, left + crop_size, top + crop_size))
    bbox = mask_alpha.getbbox()
    target_width = size[0] if bbox is None else max(1, bbox[2] - bbox[0])
    resized = square.resize((target_width, target_width), Image.Resampling.LANCZOS)
    fitted = Image.new("RGBA", size, (0, 0, 0, 0))
    if bbox is None:
        paste_x = (size[0] - resized.width) // 2
        paste_y = (size[1] - resized.height) // 2
    else:
        mask_center_x = (bbox[0] + bbox[2]) // 2
        mask_center_y = (bbox[1] + bbox[3]) // 2
        paste_x = mask_center_x - (resized.width // 2)
        paste_y = mask_center_y - (resized.height // 2)
    fitted.paste(resized, (paste_x, paste_y), resized)
    return fitted


def _fit_cover_to_mask_height(
    source_path: Path,
    size: tuple[int, int],
    mask_alpha: Image.Image,
) -> Image.Image:
    with Image.open(source_path) as source_image:
        source = source_image.convert("RGBA")
    crop_size = min(source.width, source.height)
    left = (source.width - crop_size) // 2
    top = (source.height - crop_size) // 2
    square = source.crop((left, top, left + crop_size, top + crop_size))
    bbox = mask_alpha.getbbox()
    target_height = size[1] if bbox is None else max(1, bbox[3] - bbox[1])
    resized = square.resize((target_height, target_height), Image.Resampling.LANCZOS)
    fitted = Image.new("RGBA", size, (0, 0, 0, 0))
    if bbox is None:
        paste_x = (size[0] - resized.width) // 2
        paste_y = (size[1] - resized.height) // 2
    else:
        mask_center_x = (bbox[0] + bbox[2]) // 2
        mask_center_y = (bbox[1] + bbox[3]) // 2
        paste_x = mask_center_x - (resized.width // 2)
        paste_y = mask_center_y - (resized.height // 2)
    fitted.paste(resized, (paste_x, paste_y), resized)
    return fitted


def _fit_cover_to_target_region(
    *,
    source_path: Path,
    size: tuple[int, int],
    mask_alpha: Image.Image,
    target_size: tuple[int, int],
    preserve_square: bool,
) -> Image.Image:
    with Image.open(source_path) as source_image:
        source = source_image.convert("RGBA")
    crop_size = min(source.width, source.height)
    left = (source.width - crop_size) // 2
    top = (source.height - crop_size) // 2
    square = source.crop((left, top, left + crop_size, top + crop_size))
    resized_size = _resolved_target_cover_size(target_size, preserve_square=preserve_square)
    resized = square.resize(resized_size, Image.Resampling.LANCZOS)
    fitted = Image.new("RGBA", size, (0, 0, 0, 0))
    bbox = mask_alpha.getbbox()
    if bbox is None:
        paste_x = (size[0] - resized.width) // 2
        paste_y = (size[1] - resized.height) // 2
    else:
        mask_center_x = (bbox[0] + bbox[2]) // 2
        mask_center_y = (bbox[1] + bbox[3]) // 2
        paste_x = mask_center_x - (resized.width // 2)
        paste_y = mask_center_y - (resized.height // 2)
    fitted.paste(resized, (paste_x, paste_y), resized)
    return fitted


def _resolved_target_cover_size(
    target_size: tuple[int, int],
    *,
    preserve_square: bool,
) -> tuple[int, int]:
    if not preserve_square:
        return (max(1, target_size[0]), max(1, target_size[1]))
    square_edge = max(1, min(target_size))
    return (square_edge, square_edge)


def _build_masked_donor_layer(
    *,
    source_path: Path,
    size: tuple[int, int],
    mask_alpha: Image.Image,
) -> Image.Image:
    fitted = _fit_cover_to_canvas(source_path, size)
    return _apply_mask_alpha(fitted, mask_alpha)


def _build_optional_masked_donor_layer(
    *,
    source_path: Path | None,
    size: tuple[int, int],
    mask_alpha: Image.Image,
) -> Image.Image | None:
    if source_path is None or not source_path.is_file():
        return None
    return _build_masked_donor_layer(
        source_path=source_path,
        size=size,
        mask_alpha=mask_alpha,
    )


def _build_optional_inverse_masked_donor_layer(
    *,
    source_path: Path | None,
    size: tuple[int, int],
    cover_mask_alpha: Image.Image,
) -> Image.Image | None:
    if source_path is None or not source_path.is_file():
        return None
    inverse_mask = ImageChops.invert(cover_mask_alpha)
    fitted = _fit_cover_to_canvas(source_path, size)
    return _apply_mask_alpha(fitted, inverse_mask)


def _compose_inventory_layers(center_layer: Image.Image, donor_outer_layer: Image.Image) -> Image.Image:
    base = Image.new("RGBA", center_layer.size, (0, 0, 0, 0))
    base.alpha_composite(center_layer)
    base.alpha_composite(donor_outer_layer)
    return base


def _multiply_overlay(base: Image.Image, overlay: Image.Image) -> Image.Image:
    overlay_alpha = overlay.getchannel("A")
    multiplied_rgb = ImageChops.multiply(base.convert("RGB"), overlay.convert("RGB")).convert("RGBA")
    multiplied_rgb.putalpha(base.getchannel("A"))
    return Image.composite(multiplied_rgb, base, overlay_alpha)


def _soft_light_overlay(base: Image.Image, overlay: Image.Image) -> Image.Image:
    overlay_alpha = overlay.getchannel("A")
    softened_rgb = ImageChops.soft_light(base.convert("RGB"), overlay.convert("RGB")).convert("RGBA")
    softened_rgb.putalpha(base.getchannel("A"))
    return Image.composite(softened_rgb, base, overlay_alpha)


def _alpha_composite_overlay(base: Image.Image, overlay: Image.Image, *, opacity: float) -> Image.Image:
    composited = base.copy()
    fitted_overlay = overlay.resize(base.size, Image.Resampling.LANCZOS)
    alpha = fitted_overlay.getchannel("A").point(lambda value: int(round(value * max(0.0, min(1.0, opacity)))))
    fitted_overlay.putalpha(alpha)
    composited.alpha_composite(fitted_overlay)
    return composited


def _multiply_with_second_pass(
    base: Image.Image,
    overlay: Image.Image,
    *,
    second_pass_ratio: float,
) -> Image.Image:
    first_pass = _multiply_overlay(base, overlay)
    if second_pass_ratio <= 0.0:
        return first_pass
    second_pass = _multiply_overlay(first_pass, overlay)
    blended = Image.blend(first_pass.convert("RGB"), second_pass.convert("RGB"), max(0.0, min(1.0, second_pass_ratio))).convert("RGBA")
    blended.putalpha(base.getchannel("A"))
    return blended


def _apply_mask_alpha(image: Image.Image, mask_alpha: Image.Image) -> Image.Image:
    masked = image.copy()
    combined_alpha = ImageChops.multiply(masked.getchannel("A"), mask_alpha)
    masked.putalpha(combined_alpha)
    return masked


def _mask_region_is_fully_covered(
    image: Image.Image,
    mask_alpha: Image.Image,
    *,
    alpha_threshold: int,
) -> bool:
    image_alpha = np.array(image.getchannel("A"), dtype=np.uint8)
    mask_values = np.array(mask_alpha, dtype=np.uint8)
    visible_mask = mask_values > 0
    if not np.any(visible_mask):
        return True
    return bool(np.all(image_alpha[visible_mask] > alpha_threshold))


def _alpha_mask(image: Image.Image) -> Image.Image:
    alpha = image.getchannel("A")
    if alpha.getbbox() is not None:
        return alpha
    return image.convert("L")
