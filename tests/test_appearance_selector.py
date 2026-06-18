from new_music_builder.ui.widgets.appearance_selector import appearance_tab_order, should_show_dual_sprite_controls


def test_appearance_tab_order_matches_expected_labels() -> None:
    assert appearance_tab_order() == (
        ('cassette', 'Cassette'),
        ('vinyl', 'Vinyl'),
        ('cd', 'CD'),
        ('case', 'Case'),
        ('jacket', 'Jacket'),
        ('cd_cover', 'CD Case'),
    )


def test_should_show_dual_sprite_controls_only_for_cover_kinds() -> None:
    assert should_show_dual_sprite_controls('case') is True
    assert should_show_dual_sprite_controls('jacket') is True
    assert should_show_dual_sprite_controls('cd_cover') is True
    assert should_show_dual_sprite_controls('cassette') is False
    assert should_show_dual_sprite_controls('vinyl') is False
    assert should_show_dual_sprite_controls('cd') is False
