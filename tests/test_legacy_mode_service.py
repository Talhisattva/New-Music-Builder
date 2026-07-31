from pathlib import Path

from new_music_builder.domain.models import ProjectConfig, TrackEntry, default_media_row
from new_music_builder.services.asset_catalog import AssetEntry
from new_music_builder.services.legacy_mode_service import (
    assign_legacy_appearances_to_new_tracks,
    disable_legacy_mode,
    enable_legacy_mode,
)


def _asset(kind: str, key: str) -> AssetEntry:
    return AssetEntry(
        key=key,
        label=key,
        inventory_path=f'C:/assets/{kind}/{key}_inv.png',
        world_path=f'C:/assets/{kind}/{key}_world.png',
        sprite_mode='single',
    )


class _DeterministicRandom:
    def choice(self, entries):
        return entries[-1]


def test_enable_legacy_mode_flattens_tracks_and_assigns_random_playable_textures() -> None:
    project = ProjectConfig()
    row = default_media_row(1)
    row.selected_side = 'B'
    row.tracks_a = [TrackEntry(display_label='A1'), TrackEntry(display_label='A2')]
    row.tracks_b = [TrackEntry(display_label='B1')]
    project.media_rows = [row]
    catalog = {
        'cassette': [_asset('cassette', 'cassette:1'), _asset('cassette', 'cassette:2')],
        'vinyl': [_asset('vinyl', 'vinyl:1'), _asset('vinyl', 'vinyl:2')],
        'cd': [_asset('cd', 'cd:1'), _asset('cd', 'cd:2')],
    }

    enable_legacy_mode(project, catalog, randomizer=_DeterministicRandom())

    assert project.legacy_mode_enabled is True
    assert project.automatic_textures_enabled is False
    assert [track.display_label for track in row.tracks_a] == ['A1', 'A2', 'B1']
    assert row.tracks_b == []
    assert row.selected_side == 'A'
    assert row.tracks_a[0].legacy_appearances.cassette.selected_asset_key == 'cassette:2'
    assert row.tracks_a[0].legacy_appearances.vinyl.selected_asset_key == 'vinyl:2'
    assert row.tracks_a[0].legacy_appearances.cd.selected_asset_key == 'cd:2'


def test_disable_legacy_mode_syncs_row_appearances_from_selected_track() -> None:
    project = ProjectConfig(legacy_mode_enabled=True)
    row = default_media_row(1)
    first = TrackEntry(display_label='First')
    second = TrackEntry(display_label='Second')
    second.legacy_appearances.cassette.selected_asset_key = 'cassette:7'
    second.legacy_appearances.vinyl.selected_asset_key = 'vinyl:3'
    second.legacy_appearances.cd.selected_asset_key = 'cd:1'
    second.legacy_appearances.vinyl.source = 'custom'
    second.legacy_appearances.vinyl.inventory_full = 'C:/art/vinyl_inv.png'
    second.legacy_appearances.vinyl.world_full = 'C:/art/vinyl_world.png'
    row.tracks_a = [first, second]
    row.tracks_b = [TrackEntry(display_label='Legacy B')]
    project.media_rows = [row]

    disable_legacy_mode(project, selected_track_by_row_id={1: 1})

    assert project.legacy_mode_enabled is False
    assert row.tracks_b == []
    assert row.selected_side == 'A'
    assert row.appearances['cassette'].selected_asset_key == 'cassette:7'
    assert row.appearances['vinyl'].selected_asset_key == 'vinyl:3'
    assert row.appearances['vinyl'].source == 'custom'
    assert row.appearances['vinyl'].world_full == 'C:/art/vinyl_world.png'


def test_assign_legacy_appearances_to_new_tracks_uses_current_pool() -> None:
    project = ProjectConfig()
    project.custom_assets = {
        'cassette': [
            {
                'key': 'custom:cassette:1',
                'label': 'Custom',
                'inventory_full': 'C:/custom/cassette_inv.png',
                'world_full': 'C:/custom/cassette_world.png',
                'sprite_mode': 'single',
            }
        ]
    }
    row = default_media_row(1)
    new_track = TrackEntry(display_label='New Track')
    catalog = {
        'cassette': [_asset('cassette', 'cassette:1')],
        'vinyl': [_asset('vinyl', 'vinyl:1')],
        'cd': [_asset('cd', 'cd:1')],
    }

    assign_legacy_appearances_to_new_tracks(
        project,
        row,
        [new_track],
        catalog,
        randomizer=_DeterministicRandom(),
    )

    assert new_track.legacy_appearances.cassette.selected_asset_key == 'custom:cassette:1'
    assert new_track.legacy_appearances.cassette.source == 'custom'
    assert new_track.legacy_appearances.vinyl.selected_asset_key == 'vinyl:1'
    assert new_track.legacy_appearances.cd.selected_asset_key == 'cd:1'
