from new_music_builder.services.asset_catalog import AssetEntry
from new_music_builder.ui.widgets.appearance_selector import (
    appearance_tab_order,
    BUILT_IN_DUAL_EMPTY_TO_FULL,
    can_commit_dual_custom,
    can_commit_single_custom,
    fallback_selected_asset_key_after_delete,
    merge_appearance_grid_entries,
    should_show_dual_sprite_controls,
)


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

    merged = merge_appearance_grid_entries('cassette', defaults, custom_assets)

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

    merged = merge_appearance_grid_entries('jacket', defaults, [])

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

    merged = merge_appearance_grid_entries('cd_cover', defaults, [])

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
    remaining_entries = merge_appearance_grid_entries('cassette', defaults, [])

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
