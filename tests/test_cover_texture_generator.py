from pathlib import Path

from PIL import Image

from new_music_builder.services.cover_texture_generator import generate_cassette_textures_from_cover


ASSETS_ROOT = Path(__file__).resolve().parents[1] / "assets"


def test_generate_cassette_textures_from_cover_writes_expected_outputs(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (500, 500), (255, 0, 0, 255)).save(cover_path)

    result = generate_cassette_textures_from_cover(
        cover_path,
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
