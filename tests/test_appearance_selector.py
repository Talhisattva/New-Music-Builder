from pathlib import Path

from new_music_builder.services.asset_catalog import AssetEntry
from new_music_builder.domain.models import default_media_row
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.appearance_entries import AppearanceGridEntry
from new_music_builder.ui.widgets.appearance_selector import (
    appearance_tab_order,
    BUILT_IN_DUAL_EMPTY_TO_FULL,
    can_commit_dual_custom,
    can_commit_single_custom,
    fallback_selected_asset_key_after_delete,
    generate_button_text_for_state,
    merge_appearance_grid_entries,
    resolve_module_three_control_layout,
    resolve_module_three_vertical_metrics,
    should_show_dual_sprite_controls,
    visible_tab_kinds_for_enabled_media,
)
from new_music_builder.ui.widgets.cursor_tooltip import compute_left_tooltip_placement


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


def test_visible_tab_kinds_follow_enabled_media_in_global_order() -> None:
    visible = visible_tab_kinds_for_enabled_media(
        {
            'cassette': True,
            'vinyl': True,
            'cd': False,
        }
    )

    assert visible == ('cassette', 'vinyl', 'case', 'jacket')


def test_visible_tab_kinds_for_single_vinyl_media_pair() -> None:
    visible = visible_tab_kinds_for_enabled_media(
        {
            'cassette': False,
            'vinyl': True,
            'cd': False,
        }
    )

    assert visible == ('vinyl', 'jacket')


def test_visible_tab_kinds_empty_when_all_media_disabled() -> None:
    visible = visible_tab_kinds_for_enabled_media(
        {
            'cassette': False,
            'vinyl': False,
            'cd': False,
        }
    )

    assert visible == ()


def test_merge_appearance_grid_entries_appends_custom_items_after_defaults() -> None:
    defaults = [
        AssetEntry(
            key='cassette:1',
            label='One',
            inventory_path='default-one.png',
            world_path='world-one.png',
            sprite_mode='single',
            kind='cassette',
        ),
        AssetEntry(
            key='cassette:2',
            label='Two',
            inventory_path='default-two.png',
            world_path='world-two.png',
            sprite_mode='single',
            kind='cassette',
        ),
    ]
    custom_assets = [
        {
            'key': 'custom:cassette:abc',
            'inventory_full': 'custom-one.png',
            'world_full': 'custom-world.png',
            'sprite_mode': 'single',
        }
    ]

    merged = merge_appearance_grid_entries('cassette', defaults, [], custom_assets)

    assert [entry.key for entry in merged] == ['cassette:1', 'cassette:2', 'custom:cassette:abc']
    assert merged[-1].is_custom is True


def test_merge_appearance_grid_entries_collapses_built_in_dual_jacket_pair() -> None:
    defaults = [
        AssetEntry(
            key='jacket:18',
            label='18',
            inventory_path='full.png',
            world_path='world-full.png',
            sprite_mode='dual',
            kind='jacket',
        ),
        AssetEntry(
            key='jacket:18_empty',
            label='18 Empty',
            inventory_path='empty.png',
            world_path='world-empty.png',
            sprite_mode='dual',
            kind='jacket',
        ),
    ]

    merged = merge_appearance_grid_entries('jacket', defaults, [], [])

    assert [entry.key for entry in merged] == ['jacket:18']
    assert merged[0].is_dual is True
    assert merged[0].inventory_empty_path == 'empty.png'


def test_merge_appearance_grid_entries_collapses_cd_cover_blank_empty_pair() -> None:
    defaults = [
        AssetEntry(
            key='cd_cover:_Blank',
            label='Blank',
            inventory_path='blank.png',
            world_path='world-blank.png',
            sprite_mode='single',
            kind='cd_cover',
        ),
        AssetEntry(
            key='cd_cover:_Empty',
            label='Empty',
            inventory_path='empty.png',
            world_path='world-empty.png',
            sprite_mode='single',
            kind='cd_cover',
        ),
    ]

    merged = merge_appearance_grid_entries('cd_cover', defaults, [], [])

    assert [entry.key for entry in merged] == ['cd_cover:_Blank']
    assert merged[0].is_dual is True
    assert BUILT_IN_DUAL_EMPTY_TO_FULL['cd_cover:_Empty'] == 'cd_cover:_Blank'


def test_fallback_selected_asset_key_after_delete_returns_first_remaining_entry() -> None:
    defaults = [
        AssetEntry(
            key='cassette:1',
            label='One',
            inventory_path='default-one.png',
            world_path='world-one.png',
            sprite_mode='single',
            kind='cassette',
        )
    ]
    remaining_entries = merge_appearance_grid_entries('cassette', defaults, [], [])

    assert fallback_selected_asset_key_after_delete(
        remaining_entries,
        deleted_key='custom:cassette:gone',
        selected_key='custom:cassette:gone',
    ) == 'cassette:1'


def test_can_commit_single_custom_requires_full_inventory_and_world() -> None:
    assert can_commit_single_custom({}) is False
    assert can_commit_single_custom({'inventory_full': 'inventory.png'}) is False
    assert can_commit_single_custom({'world_full': 'world.png'}) is False
    assert can_commit_single_custom({'inventory_full': 'inventory.png', 'world_full': 'world.png'}) is True


def test_can_commit_dual_custom_requires_all_four_images() -> None:
    assert can_commit_dual_custom({}) is False
    assert can_commit_dual_custom({'inventory_full': 'inventory.png', 'world_full': 'world.png'}) is False
    assert can_commit_dual_custom(
        {
            'inventory_full': 'inventory.png',
            'world_full': 'world.png',
            'inventory_empty': 'inventory-empty.png',
            'world_empty': 'world-empty.png',
        }
    ) is True


def test_compute_left_tooltip_placement_centers_square_and_points_to_cursor() -> None:
    placement = compute_left_tooltip_placement(
        cursor_x=500,
        cursor_y=300,
        window_left=100,
        window_top=100,
        window_width=1000,
        window_height=700,
    )

    assert placement.window_x == 500 - spec.MODULE_THREE_TOOLTIP_CURSOR_OFFSET_X - spec.MODULE_THREE_TOOLTIP_POINTER_PROTRUSION - spec.MODULE_THREE_TOOLTIP_SQUARE_SIZE[0]
    assert placement.window_y == 300 - (spec.MODULE_THREE_TOOLTIP_SQUARE_SIZE[1] // 2)
    assert placement.pointer_tip_y == spec.MODULE_THREE_TOOLTIP_SQUARE_SIZE[1] // 2
    assert spec.MODULE_THREE_TOOLTIP_SQUARE_SIZE == (258, 258)
    assert spec.MODULE_THREE_TOOLTIP_IMAGE_SIZE == (256, 256)


def test_compute_left_tooltip_placement_clamps_vertically_inside_window() -> None:
    placement = compute_left_tooltip_placement(
        cursor_x=500,
        cursor_y=120,
        window_left=100,
        window_top=100,
        window_width=1000,
        window_height=700,
    )

    assert placement.window_y == 100
    assert placement.pointer_tip_y == 20


def test_dual_grid_entry_resolves_full_and_empty_world_paths() -> None:
    defaults = [
        AssetEntry(
            key='jacket:18',
            label='18',
            inventory_path='full-inventory.png',
            world_path='full-world.png',
            sprite_mode='dual',
            kind='jacket',
        ),
        AssetEntry(
            key='jacket:18_empty',
            label='18 Empty',
            inventory_path='empty-inventory.png',
            world_path='empty-world.png',
            sprite_mode='dual',
            kind='jacket',
        ),
    ]

    merged = merge_appearance_grid_entries('jacket', defaults, [], [])
    entry = merged[0]

    assert entry.displayed_world_path(show_empty=False) == 'full-world.png'
    assert entry.displayed_world_path(show_empty=True) == 'empty-world.png'


def test_dual_grid_entry_resolves_display_path_for_inventory_and_world_modes() -> None:
    defaults = [
        AssetEntry(
            key='jacket:18',
            label='18',
            inventory_path='full-inventory.png',
            world_path='full-world.png',
            sprite_mode='dual',
            kind='jacket',
        ),
        AssetEntry(
            key='jacket:18_empty',
            label='18 Empty',
            inventory_path='empty-inventory.png',
            world_path='empty-world.png',
            sprite_mode='dual',
            kind='jacket',
        ),
    ]

    entry = merge_appearance_grid_entries('jacket', defaults, [], [])[0]

    assert entry.displayed_path('inventory', show_empty=False) == 'full-inventory.png'
    assert entry.displayed_path('inventory', show_empty=True) == 'empty-inventory.png'
    assert entry.displayed_path('world', show_empty=False) == 'full-world.png'
    assert entry.displayed_path('world', show_empty=True) == 'empty-world.png'


def test_merge_appearance_grid_entries_places_generated_before_custom_and_not_deletable() -> None:
    defaults = [
        AssetEntry(
            key='cassette:1',
            label='One',
            inventory_path='default-one.png',
            world_path='world-one.png',
            sprite_mode='single',
            kind='cassette',
        ),
    ]
    generated = [
        AppearanceGridEntry(
            key='generated:cassette:abc',
            label='Generated',
            inventory_path='generated-inventory.png',
            world_path='generated-world.png',
            sprite_mode='single',
            kind='cassette',
            is_custom=False,
            is_generated=True,
        )
    ]
    custom_assets = [
        {
            'key': 'custom:cassette:abc',
            'inventory_full': 'custom-inventory.png',
            'world_full': 'custom-world.png',
            'sprite_mode': 'single',
        }
    ]

    merged = merge_appearance_grid_entries('cassette', defaults, generated, custom_assets)

    assert [entry.key for entry in merged] == ['cassette:1', 'generated:cassette:abc', 'custom:cassette:abc']
    assert merged[1].is_custom is False
    assert merged[1].is_generated is True
    assert merged[2].is_custom is True


def test_generate_button_text_for_state_blanks_when_disabled_for_existing_cover_generation(tmp_path: Path) -> None:
    row = default_media_row(1)
    cover_path = tmp_path / 'cover.png'
    cover_path.write_bytes(b'cover')
    row.cover_path = str(cover_path)

    assert generate_button_text_for_state(
        locked=False,
        row=row,
        kind='cassette',
        enabled=False,
    ) == ''
    assert generate_button_text_for_state(
        locked=False,
        row=row,
        kind='cd',
        enabled=False,
    ) == ''


def test_generate_button_text_for_state_keeps_label_for_general_disabled_cases() -> None:
    row = default_media_row(1)

    assert generate_button_text_for_state(
        locked=True,
        row=row,
        kind='cassette',
        enabled=False,
    ) == 'GENERATE FROM COVER'
    assert generate_button_text_for_state(
        locked=False,
        row=row,
        kind='vinyl',
        enabled=False,
    ) == 'GENERATE FROM COVER'
    assert generate_button_text_for_state(
        locked=False,
        row=row,
        kind='cassette',
        enabled=True,
    ) == 'GENERATE FROM COVER'


def test_resolve_module_three_control_layout_uses_old_single_row_when_automatic_textures_enabled() -> None:
    layout = resolve_module_three_control_layout(
        automatic_textures_enabled=True,
        dual_visible=True,
    )

    assert layout.show_generate is False
    assert layout.preview_row_y == spec.MODULE_THREE_DUAL_SPRITE_ROW_Y
    assert layout.preview_row_size == spec.MODULE_THREE_PREVIEW_MODE_ROW_SIZE
    assert layout.dual_left_x == spec.MODULE_THREE_PREVIEW_MODE_ROW_SIZE[0]


def test_resolve_module_three_control_layout_uses_two_rows_when_automatic_textures_disabled() -> None:
    layout = resolve_module_three_control_layout(
        automatic_textures_enabled=False,
        dual_visible=True,
    )

    assert layout.show_generate is True
    assert layout.preview_row_y == spec.MODULE_THREE_PREVIEW_MODE_ROW_Y
    assert layout.preview_row_size == spec.MODULE_THREE_PREVIEW_MODE_FULL_SIZE
    assert layout.generate_row_size == spec.MODULE_THREE_GENERATE_BUTTON_ROW_SIZE
    assert layout.dual_left_x == spec.MODULE_THREE_GENERATE_BUTTON_ROW_SIZE[0]


def test_resolve_module_three_vertical_metrics_uses_taller_grid_when_automatic_textures_enabled() -> None:
    metrics = resolve_module_three_vertical_metrics(automatic_textures_enabled=True)

    assert metrics.grid_viewport_size == spec.MODULE_THREE_GRID_VIEWPORT_TALL_SIZE
    assert metrics.grid_mask_size == spec.MODULE_THREE_GRID_MASK_TALL_SIZE
    assert metrics.grid_scrollbar_size == spec.MODULE_THREE_GRID_SCROLLBAR_TALL_SIZE


def test_resolve_module_three_vertical_metrics_uses_default_grid_when_automatic_textures_disabled() -> None:
    metrics = resolve_module_three_vertical_metrics(automatic_textures_enabled=False)

    assert metrics.grid_viewport_size == spec.MODULE_THREE_GRID_VIEWPORT_SIZE
    assert metrics.grid_mask_size == spec.MODULE_THREE_GRID_MASK_SIZE
    assert metrics.grid_scrollbar_size == spec.MODULE_THREE_GRID_SCROLLBAR_SIZE
