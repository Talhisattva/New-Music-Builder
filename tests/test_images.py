from pathlib import Path

from PIL import Image

from new_music_builder.ui.widgets.images import load_contained_pil_image


def test_load_contained_pil_image_letterboxes_rectangular_source(tmp_path: Path) -> None:
    source = tmp_path / 'rect.png'
    Image.new('RGBA', (400, 200), (255, 0, 0, 255)).save(source)

    result = load_contained_pil_image(source, (100, 100))

    assert result is not None
    assert result.size == (100, 100)
    assert result.getpixel((50, 50)) == (255, 0, 0, 255)
    assert result.getpixel((50, 5))[3] == 0


def test_load_contained_pil_image_returns_none_for_missing_file() -> None:
    assert load_contained_pil_image('missing-file.png', (100, 100)) is None
