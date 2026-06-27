from pathlib import Path

import pytest
from PIL import Image, ImageChops

from new_music_builder.services.cover_texture_generator import (
    CASSETTE_INVENTORY_PRESET,
    CASE_INVENTORY_PRESET,
    CD_COVER_INVENTORY_PRESET,
    JACKET_INVENTORY_PRESET,
    JACKET_WORLD_OUTPUT_SIZE,
    VINYL_INVENTORY_TARGET_SIZE,
    VINYL_WORLD_TARGET_SIZE,
    _apply_preferred_canvas_shift,
    _apply_inventory_warp,
    _alpha_mask,
    _build_inventory_transformed_cover,
    _build_inventory_sheared_cover,
    _build_case_inventory_masked_cover,
    _fit_cover_to_target_region,
    _fit_cover_to_mask_height,
    _fit_cover_to_mask_width,
    _mask_region_is_fully_covered,
    _multiply_overlay,
    _multiply_with_second_pass,
    _prepare_square_source,
    WORLD_OVERLAY_SECOND_MULTIPLY_RATIO,
    generate_cd_cover_textures_from_cover,
    generate_case_textures_from_cover,
    generate_jacket_textures_from_cover,
    generate_vinyl_textures_from_cover,
    generate_cassette_textures_from_cover,
)


ASSETS_ROOT = Path(__file__).resolve().parents[1] / "assets"


def test_generate_cassette_textures_from_cover_writes_expected_outputs(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    donor_path = tmp_path / "donor.png"
    donor_world_path = tmp_path / "donor-world.png"
    Image.new("RGBA", (500, 500), (255, 0, 0, 255)).save(cover_path)
    Image.new("RGBA", (32, 32), (40, 40, 220, 255)).save(donor_path)
    Image.new("RGBA", (256, 156), (80, 180, 40, 255)).save(donor_world_path)

    result = generate_cassette_textures_from_cover(
        cover_path,
        donor_inventory_path=donor_path,
        donor_world_path=donor_world_path,
        mask_root=ASSETS_ROOT / "Mask",
        output_root=tmp_path / "Generated Textures",
    )

    assert result.successful_outputs == 2
    assert result.total_outputs == 2
    assert Path(result.record.inventory_full).is_file()
    assert Path(result.record.world_full).is_file()
    assert result.record.asset_key.startswith("generated:cassette:")

    inventory = Image.open(result.record.inventory_full)
    world = Image.open(result.record.world_full)
    assert inventory.size == (32, 32)
    assert world.size == (256, 156)
    assert inventory.mode == "RGBA"
    assert world.mode == "RGBA"


def test_generate_vinyl_textures_from_cover_writes_expected_outputs(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (500, 500), (255, 0, 0, 255)).save(cover_path)

    result = generate_vinyl_textures_from_cover(
        cover_path,
        mask_root=ASSETS_ROOT / "Mask",
        output_root=tmp_path / "Generated Textures",
    )

    assert result.successful_outputs == 2
    assert result.total_outputs == 2
    assert Path(result.record.inventory_full).is_file()
    assert Path(result.record.world_full).is_file()
    assert result.record.asset_key.startswith("generated:vinyl:")

    inventory = Image.open(result.record.inventory_full)
    world = Image.open(result.record.world_full)
    assert inventory.size == (32, 32)
    assert world.size == (256, 256)
    assert inventory.mode == "RGBA"
    assert world.mode == "RGBA"


def test_generate_case_textures_from_cover_writes_expected_outputs(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    donor_path = tmp_path / "donor.png"
    donor_world_path = tmp_path / "donor-world.png"
    Image.new("RGBA", (500, 500), (255, 0, 0, 255)).save(cover_path)
    Image.new("RGBA", (32, 32), (40, 40, 220, 255)).save(donor_path)
    Image.new("RGBA", (256, 256), (80, 180, 40, 255)).save(donor_world_path)

    result = generate_case_textures_from_cover(
        cover_path,
        donor_inventory_path=donor_path,
        donor_world_path=donor_world_path,
        mask_root=ASSETS_ROOT / "Mask",
        output_root=tmp_path / "Generated Textures",
    )

    assert result.successful_outputs == 2
    assert result.total_outputs == 2
    assert Path(result.record.inventory_full).is_file()
    assert Path(result.record.world_full).is_file()
    assert result.record.asset_key.startswith("generated:case:")

    inventory = Image.open(result.record.inventory_full)
    world = Image.open(result.record.world_full)
    assert inventory.size == (32, 32)
    assert world.size == (256, 256)
    assert inventory.mode == "RGBA"
    assert world.mode == "RGBA"


def test_generate_jacket_textures_from_cover_writes_expected_outputs(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (500, 300), (255, 0, 0, 255)).save(cover_path)

    result = generate_jacket_textures_from_cover(
        cover_path,
        mask_root=ASSETS_ROOT / "Mask",
        output_root=tmp_path / "Generated Textures",
    )

    assert result.successful_outputs == 2
    assert result.total_outputs == 2
    assert Path(result.record.inventory_full).is_file()
    assert Path(result.record.world_full).is_file()
    assert result.record.asset_key.startswith("generated:jacket:")

    inventory = Image.open(result.record.inventory_full)
    world = Image.open(result.record.world_full)
    assert inventory.size == (32, 32)
    assert world.size == JACKET_WORLD_OUTPUT_SIZE
    assert inventory.mode == "RGBA"
    assert world.mode == "RGBA"


def test_generate_cd_cover_textures_from_cover_writes_expected_outputs(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (500, 300), (255, 0, 0, 255)).save(cover_path)

    result = generate_cd_cover_textures_from_cover(
        cover_path,
        mask_root=ASSETS_ROOT / "Mask",
        output_root=tmp_path / "Generated Textures",
    )

    assert result.successful_outputs == 2
    assert result.total_outputs == 2
    assert Path(result.record.inventory_full).is_file()
    assert Path(result.record.world_full).is_file()
    assert result.record.asset_key.startswith("generated:cd_cover:")

    inventory = Image.open(result.record.inventory_full)
    world = Image.open(result.record.world_full)
    assert inventory.size == (32, 32)
    assert world.size == (256, 256)
    assert inventory.mode == "RGBA"
    assert world.mode == "RGBA"


def test_generate_cassette_textures_from_rectangular_cover_keeps_outputs_valid(tmp_path: Path) -> None:
    cover_path = tmp_path / "wide-cover.png"
    donor_path = tmp_path / "donor.png"
    donor_world_path = tmp_path / "donor-world.png"
    Image.new("RGBA", (700, 400), (20, 140, 220, 255)).save(cover_path)
    Image.new("RGBA", (32, 32), (220, 220, 20, 255)).save(donor_path)
    Image.new("RGBA", (256, 156), (20, 220, 180, 255)).save(donor_world_path)

    result = generate_cassette_textures_from_cover(
        cover_path,
        donor_inventory_path=donor_path,
        donor_world_path=donor_world_path,
        mask_root=ASSETS_ROOT / "Mask",
        output_root=tmp_path / "Generated Textures",
    )

    inventory = Image.open(result.record.inventory_full)
    world = Image.open(result.record.world_full)
    assert inventory.size == (32, 32)
    assert world.size == (256, 156)
    assert inventory.getbbox() is not None
    assert world.getbbox() is not None


def test_generate_vinyl_textures_from_rectangular_cover_keeps_outputs_valid(tmp_path: Path) -> None:
    cover_path = tmp_path / "wide-cover.png"
    Image.new("RGBA", (700, 400), (20, 140, 220, 255)).save(cover_path)

    result = generate_vinyl_textures_from_cover(
        cover_path,
        mask_root=ASSETS_ROOT / "Mask",
        output_root=tmp_path / "Generated Textures",
    )

    inventory = Image.open(result.record.inventory_full)
    world = Image.open(result.record.world_full)
    assert inventory.size == (32, 32)
    assert world.size == (256, 256)
    assert inventory.getbbox() is not None
    assert world.getbbox() is not None


def test_case_inventory_transform_is_centered_in_requested_target_region(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (540, 540), (255, 0, 0, 255)).save(cover_path)
    with Image.open(ASSETS_ROOT / "Mask" / "Inventory" / "CassetteCase" / "Item_NM_Case_Mask.png") as mask_source:
        mask_alpha = _alpha_mask(mask_source.convert("RGBA"))
    fitted = _build_case_inventory_masked_cover(
        source_path=cover_path,
        mask_size=mask_alpha.size,
        mask_alpha=mask_alpha,
    )
    alpha = fitted.getchannel("A")
    bbox = alpha.getbbox()
    assert bbox is not None
    assert _mask_region_is_fully_covered(
        fitted,
        mask_alpha,
        alpha_threshold=CASE_INVENTORY_PRESET.coverage_alpha_threshold,
    ) is True


def test_jacket_inventory_transform_covers_mask_region(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (540, 540), (255, 0, 0, 255)).save(cover_path)
    with Image.open(ASSETS_ROOT / "Mask" / "Inventory" / "VinylJacket" / "Item_NM_Jacket_Mask.png") as mask_source:
        mask_alpha = _alpha_mask(mask_source.convert("RGBA"))
    fitted = _build_inventory_sheared_cover(
        source_path=cover_path,
        mask_size=mask_alpha.size,
        mask_alpha=mask_alpha,
        preset=JACKET_INVENTORY_PRESET,
    )
    assert _mask_region_is_fully_covered(
        fitted,
        mask_alpha,
        alpha_threshold=JACKET_INVENTORY_PRESET.coverage_alpha_threshold,
    ) is True


def test_cd_cover_inventory_transform_covers_mask_region(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (540, 540), (255, 0, 0, 255)).save(cover_path)
    with Image.open(ASSETS_ROOT / "Mask" / "Inventory" / "CD" / "Item_NM_CDCover_Mask.png") as mask_source:
        mask_alpha = _alpha_mask(mask_source.convert("RGBA"))
    fitted = _build_inventory_sheared_cover(
        source_path=cover_path,
        mask_size=mask_alpha.size,
        mask_alpha=mask_alpha,
        preset=CD_COVER_INVENTORY_PRESET,
    )
    assert _mask_region_is_fully_covered(
        fitted,
        mask_alpha,
        alpha_threshold=CD_COVER_INVENTORY_PRESET.coverage_alpha_threshold,
    ) is True


def test_generate_cd_cover_inventory_is_clipped_to_mask(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (540, 540), (0, 255, 0, 255)).save(cover_path)

    result = generate_cd_cover_textures_from_cover(
        cover_path,
        mask_root=ASSETS_ROOT / "Mask",
        output_root=tmp_path / "Generated Textures",
    )

    inventory = Image.open(result.record.inventory_full).convert("RGBA")
    with Image.open(ASSETS_ROOT / "Mask" / "Inventory" / "CD" / "Item_NM_CDCover_Mask.png") as mask_source:
        mask_alpha = _alpha_mask(mask_source.convert("RGBA"))
    for x in range(inventory.width):
        for y in range(inventory.height):
            if mask_alpha.getpixel((x, y)) > 0:
                continue
            red, green, blue, alpha = inventory.getpixel((x, y))
            assert not (alpha > 0 and green > 200 and red < 40 and blue < 40)


def test_apply_preferred_canvas_shift_moves_cd_cover_right_without_losing_mask_coverage(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (540, 540), (255, 0, 0, 255)).save(cover_path)
    with Image.open(ASSETS_ROOT / "Mask" / "Inventory" / "CD" / "Item_NM_CDCover_Mask.png") as mask_source:
        mask_alpha = _alpha_mask(mask_source.convert("RGBA"))

    fitted = _build_inventory_sheared_cover(
        source_path=cover_path,
        mask_size=mask_alpha.size,
        mask_alpha=mask_alpha,
        preset=CD_COVER_INVENTORY_PRESET,
    )
    shifted = _apply_preferred_canvas_shift(
        fitted,
        mask_alpha=mask_alpha,
        preferred_dx=2,
        alpha_threshold=CD_COVER_INVENTORY_PRESET.coverage_alpha_threshold,
    )

    assert _mask_region_is_fully_covered(
        shifted,
        mask_alpha,
        alpha_threshold=CD_COVER_INVENTORY_PRESET.coverage_alpha_threshold,
    ) is True
    assert shifted.getchannel("A").getbbox() is not None
    assert fitted.getchannel("A").getbbox() is not None
    assert shifted.getchannel("A").getbbox()[0] >= fitted.getchannel("A").getbbox()[0]


def test_generate_cd_cover_world_fills_wider_mask_dimension(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (540, 540), (255, 0, 0, 255)).save(cover_path)
    with Image.open(ASSETS_ROOT / "Mask" / "World" / "CDCover" / "World_NM_CDCover_Mask.png") as mask_source:
        mask_alpha = _alpha_mask(mask_source.convert("RGBA"))

    fitted = _fit_cover_to_mask_width(cover_path, mask_alpha.size, mask_alpha)
    alpha = fitted.getchannel("A")
    bbox = alpha.getbbox()
    assert bbox is not None
    assert _mask_region_is_fully_covered(fitted, mask_alpha, alpha_threshold=1) is True


def test_generate_jacket_textures_from_cover_world_is_letterboxed_square(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (600, 300), (255, 0, 0, 255)).save(cover_path)

    result = generate_jacket_textures_from_cover(
        cover_path,
        mask_root=ASSETS_ROOT / "Mask",
        output_root=tmp_path / "Generated Textures",
    )

    world = Image.open(result.record.world_full).convert("RGBA")
    assert world.size == JACKET_WORLD_OUTPUT_SIZE
    assert world.getpixel((0, 0)) == (255, 0, 0, 255)
    assert world.getpixel((512, 512))[3] > 0


def test_generate_jacket_textures_from_tall_cover_fills_side_padding_with_average_color(tmp_path: Path) -> None:
    cover_path = tmp_path / "tall-cover.png"
    cover = Image.new("RGBA", (300, 600), (0, 0, 0, 0))
    for x in range(50, 250):
        for y in range(50, 550):
            if y < 300:
                cover.putpixel((x, y), (255, 0, 0, 255))
            else:
                cover.putpixel((x, y), (0, 0, 255, 255))
    cover.save(cover_path)

    result = generate_jacket_textures_from_cover(
        cover_path,
        mask_root=ASSETS_ROOT / "Mask",
        output_root=tmp_path / "Generated Textures",
    )

    world = Image.open(result.record.world_full).convert("RGBA")
    left_padding_pixel = world.getpixel((16, 512))
    right_padding_pixel = world.getpixel((1008, 512))
    assert left_padding_pixel[3] == 255
    assert right_padding_pixel[3] == 255


def test_generate_jacket_textures_from_small_cover_upscales_world_preview_square(tmp_path: Path) -> None:
    cover_path = tmp_path / "small-cover.png"
    Image.new("RGBA", (64, 32), (255, 0, 255, 255)).save(cover_path)

    result = generate_jacket_textures_from_cover(
        cover_path,
        mask_root=ASSETS_ROOT / "Mask",
        output_root=tmp_path / "Generated Textures",
    )

    world = Image.open(result.record.world_full).convert("RGBA")
    assert world.size == JACKET_WORLD_OUTPUT_SIZE
    assert world.getpixel((512, 512))[3] > 0
    assert world.getpixel((128, 512))[3] > 0
    assert world.getpixel((896, 512))[3] > 0


def test_generate_jacket_textures_from_square_cover_fills_world_preview_square(tmp_path: Path) -> None:
    cover_path = tmp_path / "square-cover.png"
    Image.new("RGBA", (500, 500), (255, 0, 255, 255)).save(cover_path)

    result = generate_jacket_textures_from_cover(
        cover_path,
        mask_root=ASSETS_ROOT / "Mask",
        output_root=tmp_path / "Generated Textures",
    )

    world = Image.open(result.record.world_full).convert("RGBA")
    assert world.size == JACKET_WORLD_OUTPUT_SIZE
    assert world.getchannel("A").getbbox() == (0, 0, 1024, 1024)


def test_generate_jacket_textures_crops_transparent_padding_before_world_fit(tmp_path: Path) -> None:
    cover_path = tmp_path / "padded-cover.png"
    padded = Image.new("RGBA", (500, 500), (0, 0, 0, 0))
    inner = Image.new("RGBA", (240, 400), (255, 0, 255, 255))
    padded.paste(inner, (130, 50), inner)
    padded.save(cover_path)

    result = generate_jacket_textures_from_cover(
        cover_path,
        mask_root=ASSETS_ROOT / "Mask",
        output_root=tmp_path / "Generated Textures",
    )

    world = Image.open(result.record.world_full).convert("RGBA")
    assert world.size == JACKET_WORLD_OUTPUT_SIZE
    assert world.getchannel("A").getbbox() == (0, 0, 1024, 1024)
    assert world.getpixel((16, 512))[3] == 255
    assert world.getpixel((512, 512))[3] == 255


def test_generate_vinyl_textures_from_cover_uses_requested_inventory_target_region(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (540, 540), (255, 0, 0, 255)).save(cover_path)
    with Image.open(ASSETS_ROOT / "Mask" / "Inventory" / "Vinyl" / "Item_NM_Vinyl_Mask.png") as mask_source:
        mask_alpha = _alpha_mask(mask_source.convert("RGBA"))
    fitted = _fit_cover_to_target_region(
        source_path=cover_path,
        size=mask_alpha.size,
        mask_alpha=mask_alpha,
        target_size=VINYL_INVENTORY_TARGET_SIZE,
        preserve_square=False,
    )
    alpha = fitted.getchannel("A")
    bbox = mask_alpha.getbbox()
    assert bbox is not None
    mask_center_x = (bbox[0] + bbox[2]) // 2
    mask_center_y = (bbox[1] + bbox[3]) // 2
    expected_bbox = (
        mask_center_x - (VINYL_INVENTORY_TARGET_SIZE[0] // 2),
        mask_center_y - (VINYL_INVENTORY_TARGET_SIZE[1] // 2),
        mask_center_x - (VINYL_INVENTORY_TARGET_SIZE[0] // 2) + VINYL_INVENTORY_TARGET_SIZE[0],
        mask_center_y - (VINYL_INVENTORY_TARGET_SIZE[1] // 2) + VINYL_INVENTORY_TARGET_SIZE[1],
    )
    assert alpha.getbbox() == expected_bbox


def test_generate_vinyl_textures_from_cover_uses_average_color_for_inventory_center(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    cover = Image.new("RGBA", (20, 10), (0, 0, 0, 0))
    for x in range(10):
        for y in range(10):
            cover.putpixel((x, y), (255, 0, 0, 255))
    for x in range(10, 20):
        for y in range(10):
            cover.putpixel((x, y), (0, 0, 255, 255))
    cover.save(cover_path)

    result = generate_vinyl_textures_from_cover(
        cover_path,
        mask_root=ASSETS_ROOT / "Mask",
        output_root=tmp_path / "Generated Textures",
    )

    inventory = Image.open(result.record.inventory_full).convert("RGBA")
    with Image.open(ASSETS_ROOT / "Mask" / "Inventory" / "Vinyl" / "Item_NM_Vinyl_Mask.png") as mask_source:
        bbox = _alpha_mask(mask_source.convert("RGBA")).getbbox()
    assert bbox is not None
    center_pixel = inventory.getpixel(((bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2))
    assert abs(center_pixel[0] - center_pixel[2]) <= 20


def test_generate_vinyl_textures_from_cover_uses_requested_world_target_region(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (540, 540), (255, 0, 0, 255)).save(cover_path)
    with Image.open(ASSETS_ROOT / "Mask" / "World" / "Vinyl" / "World_NM_Vinyl_Mask.png") as mask_source:
        mask_alpha = _alpha_mask(mask_source.convert("RGBA"))
    fitted = _fit_cover_to_target_region(
        source_path=cover_path,
        size=mask_alpha.size,
        mask_alpha=mask_alpha,
        target_size=VINYL_WORLD_TARGET_SIZE,
        preserve_square=True,
    )
    alpha = fitted.getchannel("A")
    bbox = mask_alpha.getbbox()
    assert bbox is not None
    mask_center_x = (bbox[0] + bbox[2]) // 2
    mask_center_y = (bbox[1] + bbox[3]) // 2
    expected_bbox = (
        mask_center_x - (VINYL_WORLD_TARGET_SIZE[0] // 2),
        mask_center_y - (VINYL_WORLD_TARGET_SIZE[1] // 2),
        mask_center_x - (VINYL_WORLD_TARGET_SIZE[0] // 2) + VINYL_WORLD_TARGET_SIZE[0],
        mask_center_y - (VINYL_WORLD_TARGET_SIZE[1] // 2) + VINYL_WORLD_TARGET_SIZE[1],
    )
    assert alpha.getbbox() == expected_bbox


def test_fit_cover_to_target_region_fills_vinyl_world_padding_with_average_color_for_non_square_cover(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    cover = Image.new("RGBA", (10, 20), (0, 0, 0, 0))
    for x in range(10):
        for y in range(5, 15):
            if x < 5:
                cover.putpixel((x, y), (255, 0, 0, 255))
            else:
                cover.putpixel((x, y), (0, 0, 255, 255))
    cover.save(cover_path)

    with Image.open(ASSETS_ROOT / "Mask" / "World" / "Vinyl" / "World_NM_Vinyl_Mask.png") as mask_source:
        mask_image = mask_source.convert("RGBA")
    mask_alpha = _alpha_mask(mask_image)
    without_fill = _fit_cover_to_target_region(
        source_path=cover_path,
        size=mask_image.size,
        mask_alpha=mask_alpha,
        target_size=VINYL_WORLD_TARGET_SIZE,
        preserve_square=True,
        fill_background_with_average_color=False,
    )
    fitted = _fit_cover_to_target_region(
        source_path=cover_path,
        size=mask_image.size,
        mask_alpha=mask_alpha,
        target_size=VINYL_WORLD_TARGET_SIZE,
        preserve_square=True,
        fill_background_with_average_color=True,
    )
    sample_point = (0, 0)
    assert without_fill.getpixel(sample_point)[3] == 0
    padding_pixel = fitted.getpixel(sample_point)
    assert padding_pixel[3] == 255


def test_inventory_transform_returns_mask_sized_rgba_and_covers_mask(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (540, 540), (255, 180, 0, 255)).save(cover_path)
    mask_path = ASSETS_ROOT / "Mask" / "Inventory" / "Cassette" / "Item_NM_Cassette_Mask.png"

    with Image.open(mask_path) as mask_source:
        mask_image = mask_source.convert("RGBA")
    mask_alpha = _alpha_mask(mask_image)
    transformed = _build_inventory_transformed_cover(
        source_path=cover_path,
        mask_size=mask_image.size,
        mask_alpha=mask_alpha,
        preset=CASSETTE_INVENTORY_PRESET,
    )

    assert transformed.size == mask_image.size
    assert transformed.mode == "RGBA"
    assert _mask_region_is_fully_covered(
        transformed,
        mask_alpha,
        alpha_threshold=CASSETTE_INVENTORY_PRESET.coverage_alpha_threshold,
    ) is True


def test_cassette_inventory_transform_rotates_source_counterclockwise_before_warp(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    rotated_cover_path = tmp_path / "cover-rotated.png"
    cover = Image.new("RGBA", (320, 540), (0, 0, 0, 0))
    for x in range(0, 160):
        for y in range(0, 540):
            cover.putpixel((x, y), (255, 0, 0, 255))
    for x in range(160, 320):
        for y in range(0, 540):
            cover.putpixel((x, y), (0, 0, 255, 255))
    cover.save(cover_path)
    cover.rotate(90, resample=Image.Resampling.BILINEAR, expand=True).save(rotated_cover_path)

    with Image.open(ASSETS_ROOT / "Mask" / "Inventory" / "Cassette" / "Item_NM_Cassette_Mask.png") as mask_source:
        mask_image = mask_source.convert("RGBA")
    mask_alpha = _alpha_mask(mask_image)

    transformed = _build_inventory_transformed_cover(
        source_path=cover_path,
        mask_size=mask_image.size,
        mask_alpha=mask_alpha,
        preset=CASSETTE_INVENTORY_PRESET,
        rotate_quarter_turns=1,
    )
    expected = _build_inventory_transformed_cover(
        source_path=rotated_cover_path,
        mask_size=mask_image.size,
        mask_alpha=mask_alpha,
        preset=CASSETTE_INVENTORY_PRESET,
    )

    assert ImageChops.difference(transformed, expected).getbbox() is None


def test_inventory_warp_preserves_transparent_background_outside_art(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (540, 540), (120, 220, 40, 255)).save(cover_path)
    square_source = _prepare_square_source(cover_path, 48)
    transformed = _apply_inventory_warp(square_source, CASSETTE_INVENTORY_PRESET)

    alpha = transformed.getchannel("A")
    assert alpha.getbbox() is not None
    assert alpha.getbbox() != (0, 0, transformed.width, transformed.height)


def test_fit_cover_to_mask_width_reaches_world_inner_mask_edges(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (540, 540), (255, 0, 0, 255)).save(cover_path)
    mask_path = ASSETS_ROOT / "Mask" / "World" / "Cassette" / "Cassette_World_Mask.png"

    with Image.open(mask_path) as mask_source:
        mask_alpha = _alpha_mask(mask_source.convert("RGBA"))
    fitted = _fit_cover_to_mask_width(cover_path, mask_alpha.size, mask_alpha)
    bbox = mask_alpha.getbbox()
    assert bbox is not None

    mask_center_y = (bbox[1] + bbox[3]) // 2
    visible_x = [x for x in range(mask_alpha.width) if mask_alpha.getpixel((x, mask_center_y)) > 0]
    assert visible_x
    left_x = visible_x[0]
    right_x = visible_x[-1]

    fitted_alpha = fitted.getchannel("A")
    assert fitted_alpha.getpixel((left_x, mask_center_y)) > 0
    assert fitted_alpha.getpixel((right_x, mask_center_y)) > 0


def test_fit_cover_to_mask_height_reaches_case_world_inner_mask_top_and_bottom(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (540, 540), (255, 0, 0, 255)).save(cover_path)
    mask_path = ASSETS_ROOT / "Mask" / "World" / "CassetteCase" / "World_NM_CassetteCase_Mask.png"

    with Image.open(mask_path) as mask_source:
        mask_alpha = _alpha_mask(mask_source.convert("RGBA"))
    fitted = _fit_cover_to_mask_height(cover_path, mask_alpha.size, mask_alpha)
    bbox = mask_alpha.getbbox()
    assert bbox is not None

    mask_center_x = (bbox[0] + bbox[2]) // 2
    visible_y = [y for y in range(mask_alpha.height) if mask_alpha.getpixel((mask_center_x, y)) > 0]
    assert visible_y
    top_y = visible_y[0]
    bottom_y = visible_y[-1]

    fitted_alpha = fitted.getchannel("A")
    assert fitted_alpha.getpixel((mask_center_x, top_y)) > 0
    assert fitted_alpha.getpixel((mask_center_x, bottom_y)) > 0


def test_multiply_with_second_pass_only_affects_masked_overlay_region() -> None:
    base = Image.new("RGBA", (4, 1), (120, 80, 40, 255))
    overlay = Image.new("RGBA", (4, 1), (128, 128, 128, 0))
    overlay.putpixel((1, 0), (128, 128, 128, 255))

    result = _multiply_with_second_pass(base, overlay, second_pass_ratio=WORLD_OVERLAY_SECOND_MULTIPLY_RATIO)
    first_pass = _multiply_overlay(base, overlay)
    second_pass = _multiply_overlay(first_pass, overlay)

    assert result.getpixel((0, 0)) == (120, 80, 40, 255)
    changed = result.getpixel((1, 0))
    first_pixel = first_pass.getpixel((1, 0))
    second_pixel = second_pass.getpixel((1, 0))
    assert first_pixel[0] < 120
    assert first_pixel[1] < 80
    assert first_pixel[2] < 40
    assert second_pixel[0] < first_pixel[0]
    assert second_pixel[1] < first_pixel[1]
    assert second_pixel[2] < first_pixel[2]
    assert second_pixel[0] < changed[0] < first_pixel[0]
    assert second_pixel[1] < changed[1] < first_pixel[1]
    assert second_pixel[2] < changed[2] < first_pixel[2]


def test_generate_cassette_textures_from_cover_uses_donor_shell_on_outer_region(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    donor_path = tmp_path / "donor.png"
    donor_world_path = tmp_path / "donor-world.png"
    Image.new("RGBA", (540, 540), (255, 0, 0, 255)).save(cover_path)
    Image.new("RGBA", (32, 32), (0, 0, 255, 255)).save(donor_path)
    Image.new("RGBA", (256, 156), (0, 255, 0, 255)).save(donor_world_path)

    result = generate_cassette_textures_from_cover(
        cover_path,
        donor_inventory_path=donor_path,
        donor_world_path=donor_world_path,
        mask_root=ASSETS_ROOT / "Mask",
        output_root=tmp_path / "Generated Textures",
    )

    inventory = Image.open(result.record.inventory_full).convert("RGBA")
    outer_only_point = (20, 2)
    center_only_point = (20, 4)
    outer_pixel = inventory.getpixel(outer_only_point)
    center_pixel = inventory.getpixel(center_only_point)

    assert outer_pixel[2] > outer_pixel[0]
    assert center_pixel[0] > center_pixel[2]


def test_generate_cassette_textures_from_cover_fails_when_donor_shell_is_missing(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    donor_world_path = tmp_path / "donor-world.png"
    Image.new("RGBA", (500, 500), (255, 0, 0, 255)).save(cover_path)
    Image.new("RGBA", (256, 156), (0, 255, 0, 255)).save(donor_world_path)

    with pytest.raises(FileNotFoundError, match="Donor cassette shell was unavailable"):
        generate_cassette_textures_from_cover(
            cover_path,
            donor_inventory_path="",
            donor_world_path=donor_world_path,
            mask_root=ASSETS_ROOT / "Mask",
            output_root=tmp_path / "Generated Textures",
        )


def test_generate_cassette_textures_from_cover_uses_donor_world_shell_on_outer_region(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    donor_path = tmp_path / "donor.png"
    donor_world_path = tmp_path / "donor-world.png"
    donor_world_path_alt = tmp_path / "donor-world-alt.png"
    Image.new("RGBA", (540, 540), (255, 0, 0, 255)).save(cover_path)
    Image.new("RGBA", (32, 32), (0, 0, 255, 255)).save(donor_path)
    Image.new("RGBA", (256, 156), (0, 255, 0, 255)).save(donor_world_path)
    Image.new("RGBA", (256, 156), (0, 0, 255, 255)).save(donor_world_path_alt)

    first_result = generate_cassette_textures_from_cover(
        cover_path,
        donor_inventory_path=donor_path,
        donor_world_path=donor_world_path,
        mask_root=ASSETS_ROOT / "Mask",
        output_root=tmp_path / "Generated Textures",
    )
    second_result = generate_cassette_textures_from_cover(
        cover_path,
        donor_inventory_path=donor_path,
        donor_world_path=donor_world_path_alt,
        mask_root=ASSETS_ROOT / "Mask",
        output_root=tmp_path / "Generated Textures Alt",
    )

    first_world = Image.open(first_result.record.world_full).convert("RGBA")
    second_world = Image.open(second_result.record.world_full).convert("RGBA")
    outer_only_point = (5, 5)
    center_point = (128, 78)
    first_outer_pixel = first_world.getpixel(outer_only_point)
    second_outer_pixel = second_world.getpixel(outer_only_point)
    first_center_pixel = first_world.getpixel(center_point)
    second_center_pixel = second_world.getpixel(center_point)

    assert first_outer_pixel != second_outer_pixel
    assert first_center_pixel == second_center_pixel


def test_generate_cassette_textures_from_cover_preserves_world_outer_center_oval(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    donor_path = tmp_path / "donor.png"
    donor_world_path = tmp_path / "donor-world.png"
    Image.new("RGBA", (540, 540), (255, 0, 0, 255)).save(cover_path)
    Image.new("RGBA", (32, 32), (0, 0, 255, 255)).save(donor_path)
    Image.new("RGBA", (256, 156), (0, 255, 0, 255)).save(donor_world_path)

    result = generate_cassette_textures_from_cover(
        cover_path,
        donor_inventory_path=donor_path,
        donor_world_path=donor_world_path,
        mask_root=ASSETS_ROOT / "Mask",
        output_root=tmp_path / "Generated Textures",
    )

    world = Image.open(result.record.world_full).convert("RGBA")
    center_oval_point = (128, 58)
    center_pixel = world.getpixel(center_oval_point)

    assert center_pixel[3] == 255
    assert center_pixel[1] > 0


def test_generate_case_textures_from_cover_uses_donor_shell_on_inventory_outer_region(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    donor_path = tmp_path / "donor.png"
    donor_world_path = tmp_path / "donor-world.png"
    Image.new("RGBA", (540, 540), (255, 0, 0, 255)).save(cover_path)
    Image.new("RGBA", (32, 32), (0, 0, 255, 255)).save(donor_path)
    Image.new("RGBA", (256, 256), (0, 255, 0, 255)).save(donor_world_path)

    result = generate_case_textures_from_cover(
        cover_path,
        donor_inventory_path=donor_path,
        donor_world_path=donor_world_path,
        mask_root=ASSETS_ROOT / "Mask",
        output_root=tmp_path / "Generated Textures",
    )

    inventory = Image.open(result.record.inventory_full).convert("RGBA")
    outer_only_point = (8, 4)
    center_point = (14, 16)
    outer_pixel = inventory.getpixel(outer_only_point)
    center_pixel = inventory.getpixel(center_point)

    assert outer_pixel[2] > outer_pixel[0]
    assert center_pixel[0] > center_pixel[2]


def test_generate_case_textures_from_cover_uses_donor_world_shell_on_outer_region(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    donor_path = tmp_path / "donor.png"
    donor_world_path = tmp_path / "donor-world.png"
    Image.new("RGBA", (540, 540), (255, 0, 0, 255)).save(cover_path)
    Image.new("RGBA", (32, 32), (0, 0, 255, 255)).save(donor_path)
    Image.new("RGBA", (256, 256), (0, 255, 0, 255)).save(donor_world_path)

    result = generate_case_textures_from_cover(
        cover_path,
        donor_inventory_path=donor_path,
        donor_world_path=donor_world_path,
        mask_root=ASSETS_ROOT / "Mask",
        output_root=tmp_path / "Generated Textures",
    )

    world = Image.open(result.record.world_full).convert("RGBA")
    outer_only_point = (5, 5)
    center_point = (128, 128)
    outer_pixel = world.getpixel(outer_only_point)
    center_pixel = world.getpixel(center_point)

    assert outer_pixel[1] > outer_pixel[0]
    assert center_pixel[0] > center_pixel[1]


def test_generate_case_textures_from_cover_falls_back_when_donor_shells_missing(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (540, 540), (255, 0, 0, 255)).save(cover_path)

    result = generate_case_textures_from_cover(
        cover_path,
        donor_inventory_path="",
        donor_world_path="",
        mask_root=ASSETS_ROOT / "Mask",
        output_root=tmp_path / "Generated Textures",
    )

    inventory = Image.open(result.record.inventory_full).convert("RGBA")
    world = Image.open(result.record.world_full).convert("RGBA")
    assert inventory.getpixel((8, 4))[3] > 0
    assert world.getpixel((5, 5))[3] > 0
