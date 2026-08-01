from new_music_builder.domain.models import ProjectConfig, TrackEntry, default_media_row
from new_music_builder.services.asset_catalog import AssetCatalog
from new_music_builder.services.export_lua_plan import build_export_lua_plan
from new_music_builder.services.export_planning import build_export_plan
from new_music_builder.services.export_registration_plan import build_export_registration_plan
from new_music_builder.services.export_scaffold import resolve_export_target
from new_music_builder.services.export_texture_writer import write_export_textures
from new_music_builder.platform.paths import assets_root
from PIL import Image


def test_legacy_export_plan_creates_one_media_row_per_song() -> None:
    project = ProjectConfig(mod_name='Legacy', mod_id='LegacyPack', legacy_mode_enabled=True)
    row = default_media_row(1)
    row.row_mode = 'singles'
    row.enabled_media = {'cassette': True, 'vinyl': False, 'cd': True}
    row.tracks_a = [
        TrackEntry(display_label='First Song', source_path='C:/music/first.wav', duration='00:01:00'),
        TrackEntry(display_label='Second Song', source_path='C:/music/second.ogg', duration='00:02:00'),
    ]
    row.tracks_b = [TrackEntry(display_label='Third Song', source_path='C:/music/third.mp3', duration='00:03:00')]
    row.selected_side = 'A'
    project.media_rows = [row]

    plan = build_export_plan(project, AssetCatalog(assets_root()).scan())

    assert [planned_row.media_name for planned_row in plan.rows] == ['First Song', 'Second Song']
    assert len(plan.sides) == 2
    assert all(len(side.tracks) == 1 for side in plan.sides)
    assert all(side.export_relative_dir == '' for side in plan.sides)
    assert all('/' not in side.tracks[0].export_relative_path.replace('\\', '/') for side in plan.sides)
    assert [planned_row.export_id for planned_row in plan.rows] == ['FirstSong', 'SecondSong']
    assert [side.tracks[0].track_id for side in plan.sides] == ['FirstSong', 'SecondSong']
    assert plan.sides[0].tracks[0].export_file_name == 'First Song.ogg'
    assert plan.sides[1].tracks[0].export_file_name == 'Second Song.ogg'


def test_legacy_export_plan_uses_ascii_safe_flat_audio_filenames_for_non_ascii_labels() -> None:
    project = ProjectConfig(mod_name='Legacy', mod_id='LegacyPack', legacy_mode_enabled=True)
    row = default_media_row(1)
    row.row_mode = 'singles'
    row.tracks_a = [TrackEntry(display_label='КИНО - Пачка сигарет', source_path='C:/music/track-a.ogg', duration='00:03:00')]
    project.media_rows = [row]

    plan = build_export_plan(project, AssetCatalog(assets_root()).scan())
    track = plan.sides[0].tracks[0]

    assert 'КИНО' not in track.export_relative_path
    assert track.export_relative_path == f'{track.track_id}.ogg'


def test_legacy_export_plan_adds_numeric_suffix_only_when_needed() -> None:
    project = ProjectConfig(mod_name='Legacy', mod_id='LegacyPack', legacy_mode_enabled=True)
    row = default_media_row(1)
    row.row_mode = 'singles'
    row.tracks_a = [
        TrackEntry(display_label='Same Song', source_path='C:/music/track-a.ogg', duration='00:03:00'),
        TrackEntry(display_label='Same Song', source_path='C:/music/track-b.ogg', duration='00:03:00'),
    ]
    project.media_rows = [row]

    plan = build_export_plan(project, AssetCatalog(assets_root()).scan())

    assert [planned_row.export_id for planned_row in plan.rows] == ['SameSong', 'SameSong_2']
    assert [side.tracks[0].track_id for side in plan.sides] == ['SameSong', 'SameSong_2']
    assert plan.sides[0].tracks[0].export_file_name == 'Same Song.ogg'
    assert plan.sides[1].tracks[0].export_file_name == 'Same Song_2.ogg'


def test_legacy_registration_omits_container_variants() -> None:
    project = ProjectConfig(mod_name='Legacy', mod_id='LegacyPack', legacy_mode_enabled=True)
    row = default_media_row(1)
    row.row_mode = 'singles'
    row.tracks_a = [TrackEntry(display_label='Single Song', source_path='C:/music/song.ogg', duration='00:01:00')]
    project.media_rows = [row]

    plan = build_export_plan(project, AssetCatalog(assets_root()).scan())
    registration = build_export_registration_plan(project, plan)

    assert len(registration.albums) == 1
    assert registration.albums[0].container_variants == []
    assert all(variant.mode == 'single' for variant in registration.albums[0].media_variants)


def test_legacy_lua_plan_allows_missing_container_variants() -> None:
    project = ProjectConfig(mod_name='Legacy', mod_id='LegacyPack', legacy_mode_enabled=True)
    row = default_media_row(1)
    row.row_mode = 'singles'
    row.enabled_media = {'cassette': True, 'vinyl': False, 'cd': True}
    row.tracks_a = [TrackEntry(display_label='Single Song', source_path='C:/music/song.ogg', duration='00:01:00')]
    project.media_rows = [row]

    plan = build_export_plan(project, AssetCatalog(assets_root()).scan())
    lua_pack = build_export_lua_plan(project, plan)

    assert len(lua_pack.albums) == 1
    assert lua_pack.albums[0].media[0].items.container_empty == ""
    assert lua_pack.albums[0].media[0].items.container_full == ""
    for group in lua_pack.albums[0].cover_groups:
        assert group.include_containers == ()
        assert group.include_empty_containers == ()


def test_legacy_lua_plan_groups_multiple_singles_from_one_source_row_into_one_require_name() -> None:
    project = ProjectConfig(mod_name='Legacy', mod_id='LegacyPack', legacy_mode_enabled=True)
    row = default_media_row(1)
    row.media_name = 'Legacy Singles'
    row.row_mode = 'singles'
    row.tracks_a = [
        TrackEntry(display_label='First Song', source_path='C:/music/first.ogg', duration='00:01:00'),
        TrackEntry(display_label='Second Song', source_path='C:/music/second.ogg', duration='00:02:00'),
    ]
    project.media_rows = [row]

    plan = build_export_plan(project, AssetCatalog(assets_root()).scan())
    lua_pack = build_export_lua_plan(project, plan)

    assert len(lua_pack.albums) == 2
    assert lua_pack.bootstrap_require_names == ['LegacyPack_Album_LegacySingles']
    assert {album.require_name for album in lua_pack.albums} == {'LegacyPack_Album_LegacySingles'}


def test_legacy_lua_plan_uses_singles_group_name_for_default_media_mix_rows() -> None:
    project = ProjectConfig(mod_name='Legacy', mod_id='LegacyPack', legacy_mode_enabled=True)
    row = default_media_row(1)
    row.row_mode = 'singles'
    row.tracks_a = [
        TrackEntry(display_label='First Song', source_path='C:/music/first.ogg', duration='00:01:00'),
        TrackEntry(display_label='Second Song', source_path='C:/music/second.ogg', duration='00:02:00'),
    ]
    project.media_rows = [row]

    plan = build_export_plan(project, AssetCatalog(assets_root()).scan())
    lua_pack = build_export_lua_plan(project, plan)

    assert lua_pack.bootstrap_require_names == ['LegacyPack_Album_SinglesGroup1']
    assert {album.require_name for album in lua_pack.albums} == {'LegacyPack_Album_SinglesGroup1'}


def test_legacy_texture_export_reuses_shared_custom_texture_files(tmp_path) -> None:
    project = ProjectConfig(
        mod_name='Legacy',
        mod_id='LegacyPack',
        legacy_mode_enabled=True,
        workshop_output_folder=str(tmp_path / 'Workshop'),
    )
    (tmp_path / 'Workshop').mkdir()
    shared_inventory = tmp_path / 'shared-inventory.png'
    shared_world = tmp_path / 'shared-world.png'
    Image.new('RGBA', (64, 64), (255, 0, 0, 255)).save(shared_inventory)
    Image.new('RGBA', (256, 256), (0, 255, 0, 255)).save(shared_world)

    first = default_media_row(1)
    second = default_media_row(2)
    first.row_mode = 'singles'
    second.row_mode = 'singles'
    first.tracks_a = [TrackEntry(display_label='First Song', source_path='C:/music/first.ogg', duration='00:01:00')]
    second.tracks_a = [TrackEntry(display_label='Second Song', source_path='C:/music/second.ogg', duration='00:01:00')]
    for track in (first.tracks_a[0], second.tracks_a[0]):
        track.legacy_appearances.cassette.source = 'custom'
        track.legacy_appearances.cassette.selected_asset_key = 'custom:cassette:shared'
        track.legacy_appearances.cassette.inventory_full = str(shared_inventory)
        track.legacy_appearances.cassette.world_full = str(shared_world)
    project.media_rows = [first, second]

    plan = build_export_plan(project, AssetCatalog(assets_root()).scan())
    registration = build_export_registration_plan(project, plan)

    cassette_refs = [album.media_variants[0].model_reference for album in registration.albums]
    assert len(set(cassette_refs)) == 1

    targets = resolve_export_target(plan, project.workshop_output_folder, mod_name=project.mod_name, mod_id=project.mod_id)
    result = write_export_textures(project, plan, targets)

    assert result.written_file_count == 2
