from pathlib import Path

import pytest
from PIL import Image

from new_music_builder.services.cover_texture_generator import (
    CASSETTE_INVENTORY_PRESET,
    _apply_inventory_warp,
    _alpha_mask,
    _build_inventory_transformed_cover,
    _mask_region_is_fully_covered,
    _prepare_square_source,
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


def test_inventory_warp_preserves_transparent_background_outside_art(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (540, 540), (120, 220, 40, 255)).save(cover_path)
    square_source = _prepare_square_source(cover_path, 48)
    transformed = _apply_inventory_warp(square_source, CASSETTE_INVENTORY_PRESET)

    alpha = transformed.getchannel("A")
    assert alpha.getbbox() is not None
    assert alpha.getbbox() != (0, 0, transformed.width, transformed.height)


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
    outer_only_point = (5, 5)
    center_point = (128, 78)
    outer_pixel = world.getpixel(outer_only_point)
    center_pixel = world.getpixel(center_point)

    assert outer_pixel[1] > outer_pixel[0]
    assert center_pixel[0] > center_pixel[1]
