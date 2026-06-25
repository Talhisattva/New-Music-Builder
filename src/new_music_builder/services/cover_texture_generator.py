from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops

from new_music_builder.domain.models import GeneratedAssetRecord
from new_music_builder.platform.paths import assets_root, generated_textures_root
from new_music_builder.services.generated_asset_registry import build_generated_asset_key, build_generated_cover_id, normalize_cover_path


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


CASSETTE_INVENTORY_PRESET = InventoryWarpPreset(
    rotation_degrees=-30.0,
    initial_scale_ratio=1.45,
    max_scale_ratio=2.25,
    scale_step_ratio=0.12,
    right_edge_inset_ratio=0.22,
    right_edge_vertical_inset_ratio=0.14,
)


def generate_cassette_textures_from_cover(
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
    cassette_output_root = resolved_output_root / "Cassette" / cover_id
    cassette_output_root.mkdir(parents=True, exist_ok=True)

    inventory_mask = resolved_mask_root / "Inventory" / "Cassette" / "Item_NM_Cassette_Mask.png"
    inventory_outer = resolved_mask_root / "Inventory" / "Cassette" / "Item_NM_Cassette_Outer.png"
    world_mask = resolved_mask_root / "World" / "Cassette" / "Cassette_World_Mask.png"
    world_outer = resolved_mask_root / "World" / "Cassette" / "Cassette_World_01.png"
    world_overlay = resolved_mask_root / "World" / "Cassette" / "Cassette_World_Overlay.png"
    world_overlay_detail = resolved_mask_root / "World" / "Cassette" / "Cassette_World_Overlay_02.png"

    inventory_output = cassette_output_root / "Item_NM_Cassette_Generated.png"
    world_output = cassette_output_root / "World_NM_Cassette_Generated.png"

    _render_cassette_inventory(
        source_path=source_path,
        mask_path=inventory_mask,
        outer_path=inventory_outer,
        output_path=inventory_output,
    )
    _render_cassette_world(
        source_path=source_path,
        mask_path=world_mask,
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


def _render_cassette_inventory(
    *,
    source_path: Path,
    mask_path: Path,
    outer_path: Path,
    output_path: Path,
) -> None:
    with Image.open(mask_path) as mask_source:
        mask_image = mask_source.convert("RGBA")
    mask_alpha = _alpha_mask(mask_image)
    masked_cover = _build_inventory_masked_cover(
        source_path=source_path,
        mask_size=mask_image.size,
        mask_alpha=mask_alpha,
        preset=CASSETTE_INVENTORY_PRESET,
    )
    base = Image.new("RGBA", masked_cover.size, (0, 0, 0, 0))
    base.alpha_composite(masked_cover)
    with Image.open(outer_path) as outer_source:
        base.alpha_composite(outer_source.convert("RGBA"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(output_path)


def _render_cassette_world(
    *,
    source_path: Path,
    mask_path: Path,
    outer_path: Path,
    overlay_paths: tuple[Path, ...],
    output_path: Path,
) -> None:
    masked_cover = _build_masked_cover(source_path=source_path, mask_path=mask_path)
    base = Image.new("RGBA", masked_cover.size, (0, 0, 0, 0))
    base.alpha_composite(masked_cover)
    with Image.open(outer_path) as outer_source:
        base.alpha_composite(outer_source.convert("RGBA"))
    for overlay_path in overlay_paths:
        with Image.open(overlay_path) as overlay_source:
            base.alpha_composite(overlay_source.convert("RGBA"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(output_path)


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
        placed = _place_transformed_cover_on_canvas(warped, mask_size)
        if _mask_region_is_fully_covered(placed, mask_alpha, alpha_threshold=preset.coverage_alpha_threshold):
            return placed
        square_size = int(ceil(square_size * (1.0 + preset.scale_step_ratio)))
        if square_size <= target_edge:
            square_size = target_edge + 1
    final_square = _prepare_square_source(source_path, max_size)
    final_warped = _apply_inventory_warp(final_square, preset)
    return _place_transformed_cover_on_canvas(final_warped, mask_size)


def _build_masked_cover(*, source_path: Path, mask_path: Path) -> Image.Image:
    with Image.open(mask_path) as mask_source:
        mask_image = mask_source.convert("RGBA")
    fitted_cover = _fit_cover_to_canvas(source_path, mask_image.size)
    return _apply_mask_alpha(fitted_cover, _alpha_mask(mask_image))


def _prepare_square_source(source_path: Path, target_size: int) -> Image.Image:
    with Image.open(source_path) as source_image:
        source = source_image.convert("RGBA")
    crop_size = min(source.width, source.height)
    left = (source.width - crop_size) // 2
    top = (source.height - crop_size) // 2
    square = source.crop((left, top, left + crop_size, top + crop_size))
    return square.resize((target_size, target_size), Image.Resampling.LANCZOS)


def _apply_inventory_warp(image: Image.Image, preset: InventoryWarpPreset) -> Image.Image:
    rotated = image.rotate(
        preset.rotation_degrees,
        resample=Image.Resampling.BICUBIC,
        expand=True,
        fillcolor=(0, 0, 0, 0),
    )
    return _apply_perspective_warp(
        rotated,
        right_edge_inset_ratio=preset.right_edge_inset_ratio,
        right_edge_vertical_inset_ratio=preset.right_edge_vertical_inset_ratio,
    )


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
        resample=Image.Resampling.BICUBIC,
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


def _place_transformed_cover_on_canvas(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    paste_x = (size[0] - image.width) // 2
    paste_y = (size[1] - image.height) // 2
    canvas.alpha_composite(image, (paste_x, paste_y))
    return canvas


def _fit_cover_to_canvas(source_path: Path, size: tuple[int, int]) -> Image.Image:
    with Image.open(source_path) as source_image:
        source = source_image.convert("RGBA")
    fitted = Image.new("RGBA", size, (0, 0, 0, 0))
    contained = source.copy()
    contained.thumbnail(size, Image.Resampling.LANCZOS)
    paste_x = (size[0] - contained.width) // 2
    paste_y = (size[1] - contained.height) // 2
    fitted.paste(contained, (paste_x, paste_y), contained)
    return fitted


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
