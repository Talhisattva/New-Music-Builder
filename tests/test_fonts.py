from new_music_builder.platform.fonts import bundled_font_paths


def test_bundled_font_paths_point_into_assets_fonts() -> None:
    paths = bundled_font_paths()

    assert paths
    assert all(path.parent.name == "fonts" for path in paths)
    assert any(path.name == "Orbitron-VariableFont_wght.ttf" for path in paths)
    assert any(path.name == "Perfect DOS VGA 437 Win.ttf" for path in paths)


def test_bundled_font_files_exist_in_repo() -> None:
    paths = bundled_font_paths()

    assert all(path.exists() for path in paths)
    assert all(path.is_file() for path in paths)
