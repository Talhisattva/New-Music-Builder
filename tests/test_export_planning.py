from pathlib import Path

from new_music_builder.domain.models import GeneratedAssetRecord, ProjectConfig, TrackEntry, default_media_row
from new_music_builder.services.asset_catalog import AssetCatalog
from new_music_builder.services.export_planning import build_export_plan, build_preview_scenario
from new_music_builder.services.export_naming import build_audio_row_folder_name, build_audio_track_file_name


ASSETS_ROOT = Path(__file__).resolve().parents[1] / 'assets'


def _track(source_path: str, label: str, duration: str) -> TrackEntry:
    return TrackEntry(
        source_path=source_path,
        display_label=label,
        duration=duration,
        conversion_status='source_ogg' if source_path.endswith('.ogg') else 'needs_convert',
    )


def test_export_plan_excludes_rows_without_songs() -> None:
    catalog = AssetCatalog(ASSETS_ROOT).scan()
    empty_row = default_media_row(1)
    filled_row = default_media_row(2)
    filled_row.media_name = 'Real Row'
    filled_row.tracks_a = [_track('C:/music/track-a.ogg', 'Track A', '00:03:00')]
    project = ProjectConfig(media_rows=[empty_row, filled_row])

    plan = build_export_plan(project, catalog)

    assert plan.stats.media_rows == 2
    assert plan.stats.exported_media_rows == 1
    assert [row.row_id for row in plan.rows] == [2]
    assert [(side.row_id, side.side) for side in plan.sides] == [(2, 'A')]


def test_export_plan_creates_separate_sides_and_preserves_order() -> None:
    catalog = AssetCatalog(ASSETS_ROOT).scan()
    row = default_media_row(1)
    row.media_name = 'Dual Side'
    row.tracks_a = [
        _track('C:/music/first.mp3', 'First', '00:01:00'),
        _track('C:/music/second.ogg', 'Second', '00:02:00'),
    ]
    row.tracks_b = [
        _track('C:/music/third.wav', 'Third', '00:03:00'),
    ]
    project = ProjectConfig(media_rows=[row])

    plan = build_export_plan(project, catalog)

    assert [(side.side, [track.display_label for track in side.tracks]) for side in plan.sides] == [
        ('A', ['First', 'Second']),
        ('B', ['Third']),
    ]


def test_export_plan_preserves_per_media_modes_on_planned_rows() -> None:
    catalog = AssetCatalog(ASSETS_ROOT).scan()
    row = default_media_row(1)
    row.media_name = 'Modeful Row'
    row.media_modes['cassette'] = 'split'
    row.media_modes['vinyl'] = 'single'
    row.media_modes['cd'] = 'single'
    row.tracks_a = [_track('C:/music/song.ogg', 'Song', '00:03:00')]
    row.tracks_b = [_track('C:/music/song-b.ogg', 'Song B', '00:02:00')]
    project = ProjectConfig(media_rows=[row])

    plan = build_export_plan(project, catalog)

    assert plan.rows[0].media_modes == {'cassette': 'split', 'vinyl': 'single', 'cd': 'single'}


def test_export_plan_aggregates_duration_and_conversion_counts() -> None:
    catalog = AssetCatalog(ASSETS_ROOT).scan()
    row = default_media_row(1)
    row.tracks_a = [
        _track('C:/music/one.mp3', 'One', '00:01:30'),
        _track('C:/music/two.ogg', 'Two', '00:00:45'),
    ]
    row.tracks_b = [
        _track('C:/music/three.flac', 'Three', '00:10:00'),
    ]
    project = ProjectConfig(media_rows=[row])

    plan = build_export_plan(project, catalog)

    assert plan.stats.total_sides == 2
    assert plan.stats.total_songs == 3
    assert plan.stats.converted == 2
    assert plan.sides[0].duration_text == '00:02:15'
    assert plan.sides[1].duration_text == '00:10:00'


def test_export_plan_resolves_selected_builtin_appearance_paths() -> None:
    catalog = AssetCatalog(ASSETS_ROOT).scan()
    row = default_media_row(1)
    row.tracks_a = [_track('C:/music/song.ogg', 'Song', '00:03:00')]
    selected_cassette = next(entry for entry in catalog['cassette'] if entry.key != 'cassette:7')
    row.appearances['cassette'].selected_asset_key = selected_cassette.key
    row.appearances['jacket'].selected_asset_key = catalog['jacket'][0].key
    project = ProjectConfig(media_rows=[row])

    plan = build_export_plan(project, catalog)
    resolved_row = plan.rows[0]

    assert resolved_row.appearances.cassette.selected_asset_key == selected_cassette.key
    assert resolved_row.appearances.cassette.inventory_path == selected_cassette.inventory_path
    assert resolved_row.appearances.cassette.world_path == selected_cassette.world_path
    assert resolved_row.appearances.jacket.inventory_path == catalog['jacket'][0].inventory_path


def test_export_plan_resolves_selected_generated_cassette_paths(tmp_path: Path) -> None:
    catalog = AssetCatalog(ASSETS_ROOT).scan()
    cover_path = tmp_path / "cover.png"
    inventory_path = tmp_path / "generated-inventory.png"
    world_path = tmp_path / "generated-world.png"
    cover_path.write_bytes(b"cover")
    inventory_path.write_bytes(b"inventory")
    world_path.write_bytes(b"world")

    row = default_media_row(1)
    row.cover_path = str(cover_path)
    row.tracks_a = [_track('C:/music/song.ogg', 'Song', '00:03:00')]
    row.appearances['cassette'].selected_asset_key = 'generated:cassette:abc'
    project = ProjectConfig(
        media_rows=[row],
        generated_assets=[
            GeneratedAssetRecord(
                kind='cassette',
                cover_path=str(cover_path),
                asset_key='generated:cassette:abc',
                label='cover Generated',
                inventory_full=str(inventory_path),
                world_full=str(world_path),
                source_name='cover.png',
            )
        ],
    )

    plan = build_export_plan(project, catalog)
    resolved = plan.rows[0].appearances.cassette

    assert resolved.selected_asset_key == 'generated:cassette:abc'
    assert resolved.inventory_path == str(inventory_path)
    assert resolved.world_path == str(world_path)
    assert resolved.source == 'custom'


def test_export_plan_prefers_custom_paths_when_selection_source_is_custom() -> None:
    catalog = AssetCatalog(ASSETS_ROOT).scan()
    row = default_media_row(1)
    row.tracks_a = [_track('C:/music/song.ogg', 'Song', '00:03:00')]
    row.appearances['cassette'].selected_asset_key = 'cassette:7'
    row.appearances['cassette'].source = 'custom'
    row.appearances['cassette'].inventory_full = 'C:/custom/Item_NM_Cassette_Custom.png'
    row.appearances['cassette'].world_full = 'C:/custom/World_NM_Cassette_Custom.png'
    project = ProjectConfig(media_rows=[row])

    plan = build_export_plan(project, catalog)
    resolved = plan.rows[0].appearances.cassette

    assert resolved.selected_asset_key == 'cassette:7'
    assert resolved.inventory_path == 'C:/custom/Item_NM_Cassette_Custom.png'
    assert resolved.world_path == 'C:/custom/World_NM_Cassette_Custom.png'
    assert resolved.source == 'custom'


def test_preview_scenario_respects_enabled_media_filtering() -> None:
    catalog = AssetCatalog(ASSETS_ROOT).scan()
    row = default_media_row(1)
    row.media_name = 'Filtered Row'
    row.enabled_media['vinyl'] = False
    row.tracks_a = [_track('C:/music/song.ogg', 'Song', '00:03:00')]
    project = ProjectConfig(media_rows=[row])

    plan = build_export_plan(project, catalog)
    scenario = build_preview_scenario(plan, 'C:/output')

    assert len(scenario.preview_rows) == 1
    preview_row = scenario.preview_rows[0]
    assert preview_row.inventory_cell.slot_paths[1] is None
    assert preview_row.inventory_cell.slot_paths[4] is None
    assert preview_row.inventory_cell.slot_paths[0]
    assert scenario.queue_groups[0].songs[0].song_label == 'Song'


def test_audio_export_naming_removes_commas_from_sound_script_paths() -> None:
    assert build_audio_row_folder_name('Dark Side, Textures', row_id=1) == 'Dark Side Textures'
    assert build_audio_track_file_name('Unlike Pluto - Revenge, And A Little More', track_number=4) == '04 Unlike Pluto - Revenge And A Little More.ogg'


def test_audio_export_naming_prefers_ascii_safe_export_identity_when_provided() -> None:
    assert build_audio_row_folder_name('伟大的2', row_id=1, export_id='MediaRow1_ABC123') == 'MediaRow1_ABC123'
    assert build_audio_track_file_name('伟大的2', track_number=1, track_id='MediaRow1SideA1_ABC123') == '01 MediaRow1SideA1_ABC123.ogg'


def test_export_plan_uses_stable_ascii_safe_audio_paths_for_non_ascii_labels() -> None:
    catalog = AssetCatalog(ASSETS_ROOT).scan()
    row = default_media_row(1)
    row.media_name = '伟大的2'
    row.tracks_a = [_track('C:/music/track-a.ogg', 'КИНО - Пачка сигарет', '00:03:00')]
    project = ProjectConfig(media_rows=[row])

    plan = build_export_plan(project, catalog)
    row_plan = plan.rows[0]
    track = plan.sides[0].tracks[0]
    normalized_row_export_id = row_plan.export_id.replace('_', '')

    assert row_plan.export_id.startswith('2_')
    assert '伟' not in row_plan.export_id
    assert track.track_id.startswith(f'{normalized_row_export_id}SideA1')
    assert 'КИНО' not in track.track_id
    assert track.export_relative_path.replace('\\', '/') == f'{row_plan.export_id}/A-Side/01 {track.track_id}.ogg'
