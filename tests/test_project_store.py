import json
from pathlib import Path

from new_music_builder.domain.models import GeneratedAssetRecord, ProjectConfig, TrackEntry, default_media_row
from new_music_builder.services.dialog_folder_memory import DialogFolderMemory
from new_music_builder.services.project_store import ProjectStore
from new_music_builder.services.session_store import SessionAudioPreferences, SessionStore


def test_project_roundtrip(tmp_path: Path) -> None:
    project = ProjectConfig(mod_name='Test Pack', mod_id='TestPack')
    row = default_media_row(1)
    row.media_name = 'Example Album'
    row.tracks_a.append(TrackEntry(display_label='01 Artist - Song'))
    row.appearances['cassette'].selected_asset_key = 'cassette:1'
    project.media_rows = [row]

    target = tmp_path / 'test.nmbproj.json'
    store = ProjectStore()
    store.save(project, target)
    loaded = store.load(target)

    assert loaded.mod_name == 'Test Pack'
    assert loaded.mod_id == 'TestPack'
    assert loaded.media_rows[0].media_name == 'Example Album'
    assert loaded.media_rows[0].tracks_a[0].display_label == '01 Artist - Song'
    assert loaded.media_rows[0].appearances['cassette'].selected_asset_key == 'cassette:1'
    assert loaded.write_mod_name_on_poster is True
    assert loaded.automatic_textures_enabled is True

def test_project_roundtrip_preserves_stateful_row_fields(tmp_path: Path) -> None:
    project = ProjectConfig(
        mod_name='Stateful Pack',
        mod_id='StatefulPack',
        sample_rate=48000,
        compression_quality=0.65,
        reencode_existing_ogg=False,
    )
    first = default_media_row(1)
    first.media_name = 'First Album'
    first.selected_side = 'B'
    first.preview_mode = 'world'
    first.enabled_media['cd'] = False
    first.media_modes['cassette'] = 'single'
    first.media_modes['vinyl'] = 'single'
    first.expanded = False
    first.tracks_b.append(
        TrackEntry(
            source_path='C:/music/track.wav',
            cached_ogg_path='C:/cache/track.ogg',
            display_label='Track One',
            duration='00:03:21',
            conversion_status='cached_ogg',
        )
    )
    first.song_sort_b.column = 'length'
    first.song_sort_b.direction = 'desc'
    first.appearances['cassette'].source = 'custom'
    first.appearances['cassette'].selected_asset_key = 'custom:cassette:1'
    first.appearances['cassette'].inventory_full = 'C:/art/inventory.png'
    first.appearances['cassette'].world_full = 'C:/art/world.png'
    project.generated_assets = [
        GeneratedAssetRecord(
            kind='cassette',
            cover_path='C:/covers/album.png',
            asset_key='generated:cassette:abc',
            label='album Generated',
            inventory_full='C:/generated/inventory.png',
            world_full='C:/generated/world.png',
            source_name='album.png',
        )
    ]
    project.custom_assets = {
        'cassette': [
            {
                'key': 'custom:cassette:1',
                'label': 'Custom Tape',
                'inventory_full': 'C:/art/inventory.png',
                'world_full': 'C:/art/world.png',
                'sprite_mode': 'single',
            }
        ]
    }
    second = default_media_row(2)
    second.media_name = 'Second Album'
    second.expanded = True
    project.media_rows = [first, second]

    target = tmp_path / 'stateful.nmbproj.json'
    store = ProjectStore()
    store.save(project, target)
    loaded = store.load(target)

    assert loaded.sample_rate == 48000
    assert loaded.compression_quality == 0.65
    assert loaded.reencode_existing_ogg is False
    assert [row.media_name for row in loaded.media_rows] == ['First Album', 'Second Album']
    assert loaded.media_rows[0].selected_side == 'B'
    assert loaded.media_rows[0].preview_mode == 'world'
    assert loaded.media_rows[0].enabled_media['cd'] is False
    assert loaded.media_rows[0].media_modes == {'cassette': 'single', 'vinyl': 'single', 'cd': 'single'}
    assert loaded.media_rows[0].tracks_b[0].cached_ogg_path == 'C:/cache/track.ogg'
    assert loaded.media_rows[0].song_sort_b.column == 'length'
    assert loaded.media_rows[0].song_sort_b.direction == 'desc'
    assert loaded.media_rows[0].appearances['cassette'].selected_asset_key == 'custom:cassette:1'
    assert loaded.custom_assets['cassette'][0]['label'] == 'Custom Tape'
    assert loaded.generated_assets[0].asset_key == 'generated:cassette:abc'
    assert loaded.generated_assets[0].source_name == 'album.png'
    assert loaded.media_rows[1].expanded is True


def test_project_load_coerces_invalid_sample_rate_and_custom_assets(tmp_path: Path) -> None:
    payload = {
        'schema_version': 1,
        'mod_name': 'Coerce Me',
        'mod_id': 'CoerceMe',
        'sample_rate': 'bad-value',
        'compression_quality': 0.57,
        'reencode_existing_ogg': False,
        'custom_assets': {
            'cassette': [
                {
                    'inventory_full': 'C:/custom/tape_inventory.png',
                    'world_full': 'C:/custom/tape_world.png',
                    'sprite_mode': 'weird',
                }
            ],
            'unknown': [{'key': 'ignored'}],
        },
        'media_rows': [],
    }
    target = tmp_path / 'coerce.nmbproj.json'
    target.write_text(json.dumps(payload), encoding='utf-8')

    loaded = ProjectStore().load(target)

    assert loaded.sample_rate == 44100
    assert loaded.compression_quality == 0.5
    assert loaded.reencode_existing_ogg is False
    assert 'unknown' not in loaded.custom_assets
    assert loaded.custom_assets['cassette'][0]['key'] == 'custom:cassette:1'
    assert loaded.custom_assets['cassette'][0]['label'] == 'tape_inventory'
    assert loaded.custom_assets['cassette'][0]['sprite_mode'] == 'single'


def test_session_store_load_returns_default_project_for_invalid_payload(tmp_path: Path) -> None:
    target = tmp_path / 'last_session.json'
    target.write_text('{"project":[]}', encoding='utf-8')

    store = SessionStore(target)
    project, current_path = store.load()

    assert current_path == ''
    assert project.sample_rate == 44100
    assert project.compression_quality == 0.5
    assert project.reencode_existing_ogg is True
    assert project.write_mod_name_on_poster is True
    assert len(project.media_rows) == 1
    assert store.last_dialog_folder_memory.song_folder == ''
    assert store.last_dialog_folder_memory.image_folder == ''
    assert store.last_audio_preferences.sample_rate == 44100
    assert store.last_audio_preferences.compression_quality == 0.5
    assert store.last_audio_preferences.reencode_existing_ogg is True
    assert store.last_automatic_textures_enabled is True
    assert store.last_text_tooltips_enabled is True
    assert store.last_load_used_default is True


def test_project_load_defaults_write_mod_name_on_poster_for_legacy_payload(tmp_path: Path) -> None:
    payload = {
        'schema_version': 1,
        'mod_name': 'Legacy Pack',
        'mod_id': 'LegacyPack',
        'media_rows': [],
    }
    target = tmp_path / 'legacy.nmbproj.json'
    target.write_text(json.dumps(payload), encoding='utf-8')

    loaded = ProjectStore().load(target)

    assert loaded.write_mod_name_on_poster is True


def test_session_store_roundtrip_preserves_generated_assets(tmp_path: Path) -> None:
    target = tmp_path / 'last_session.json'
    project = ProjectConfig(
        generated_assets=[
            GeneratedAssetRecord(
                kind='cassette',
                cover_path='C:/covers/album.png',
                asset_key='generated:cassette:abc',
                label='album Generated',
                inventory_full='C:/generated/inventory.png',
                world_full='C:/generated/world.png',
                source_name='album.png',
            )
        ]
    )

    store = SessionStore(target)
    store.save(project, 'C:/projects/test.nmbproj.json')
    loaded_project, current_path = store.load()

    assert current_path == 'C:/projects/test.nmbproj.json'
    assert loaded_project.generated_assets[0].asset_key == 'generated:cassette:abc'
    assert store.last_load_used_default is False


def test_session_store_roundtrip_preserves_dialog_folder_memory(tmp_path: Path) -> None:
    target = tmp_path / 'last_session.json'
    store = SessionStore(target)

    store.save(
        ProjectConfig(mod_name='Folder Memory'),
        'C:/projects/test.nmbproj.json',
        dialog_folder_memory=DialogFolderMemory(
            song_folder='C:/music',
            image_folder='C:/art',
        ),
    )
    _loaded_project, current_path = store.load()

    assert current_path == 'C:/projects/test.nmbproj.json'
    assert store.last_dialog_folder_memory.song_folder == 'C:/music'
    assert store.last_dialog_folder_memory.image_folder == 'C:/art'


def test_session_store_roundtrip_preserves_master_audio_preferences(tmp_path: Path) -> None:
    target = tmp_path / 'last_session.json'
    store = SessionStore(target)

    store.save(
        ProjectConfig(),
        '',
        audio_preferences=SessionAudioPreferences(
            sample_rate=48000,
            compression_quality=0.65,
            reencode_existing_ogg=False,
        ),
    )
    _loaded_project, _current_path = store.load()

    assert store.last_audio_preferences.sample_rate == 48000
    assert store.last_audio_preferences.compression_quality == 0.65
    assert store.last_audio_preferences.reencode_existing_ogg is False


def test_session_store_roundtrip_preserves_text_tooltips_preference(tmp_path: Path) -> None:
    target = tmp_path / 'last_session.json'
    store = SessionStore(target)
    store.last_text_tooltips_enabled = False

    store.save(ProjectConfig(), '')
    _loaded_project, _current_path = store.load()

    assert store.last_text_tooltips_enabled is False


def test_session_store_roundtrip_preserves_regenerate_textures_on_project_load_preference(tmp_path: Path) -> None:
    target = tmp_path / 'last_session.json'
    store = SessionStore(target)
    store.last_regenerate_textures_on_project_load_enabled = True

    store.save(ProjectConfig(), '')
    _loaded_project, _current_path = store.load()

    assert store.last_regenerate_textures_on_project_load_enabled is True


def test_session_store_roundtrip_preserves_unsaved_row_covers_and_generated_assets(tmp_path: Path) -> None:
    target = tmp_path / 'last_session.json'
    project = ProjectConfig(mod_name='Unsaved Session')
    first = default_media_row(1)
    first.cover_path = 'C:/covers/row-cover.png'
    first.appearances['cassette'].selected_asset_key = 'generated:cassette:abc'
    first.appearances['cassette'].source = 'custom'
    first.appearances['cassette'].inventory_full = 'C:/generated/inventory.png'
    first.appearances['cassette'].world_full = 'C:/generated/world.png'
    second = default_media_row(2)
    second.cover_path = 'C:/covers/row-two.png'
    project.media_rows = [first, second]
    project.generated_assets = [
        GeneratedAssetRecord(
            kind='cassette',
            cover_path='C:/covers/row-cover.png',
            asset_key='generated:cassette:abc',
            label='row-cover Generated',
            inventory_full='C:/generated/inventory.png',
            world_full='C:/generated/world.png',
            source_name='row-cover.png',
        )
    ]

    store = SessionStore(target)
    store.save(project, '')
    loaded_project, current_path = store.load()

    assert current_path == ''
    assert store.last_load_used_default is False
    assert loaded_project.mod_name == 'Unsaved Session'
    assert len(loaded_project.media_rows) == 2
    assert loaded_project.media_rows[0].cover_path == 'C:/covers/row-cover.png'
    assert loaded_project.media_rows[1].cover_path == 'C:/covers/row-two.png'
    assert loaded_project.media_rows[0].appearances['cassette'].selected_asset_key == 'generated:cassette:abc'
    assert loaded_project.generated_assets[0].asset_key == 'generated:cassette:abc'


def test_project_and_session_roundtrip_preserve_automatic_textures_preference(tmp_path: Path) -> None:
    project = ProjectConfig(automatic_textures_enabled=False)

    project_target = tmp_path / 'test.nmbproj.json'
    ProjectStore().save(project, project_target)
    loaded_project = ProjectStore().load(project_target)
    assert loaded_project.automatic_textures_enabled is False

    session_target = tmp_path / 'last_session.json'
    store = SessionStore(session_target)
    store.last_automatic_textures_enabled = False
    store.save(project, '')
    loaded_session_project, _current_path = store.load()
    assert loaded_session_project.automatic_textures_enabled is False
    assert store.last_automatic_textures_enabled is False


def test_session_store_load_defaults_dialog_folder_memory_for_legacy_payload(tmp_path: Path) -> None:
    payload = {
        'current_path': 'C:/projects/legacy.nmbproj.json',
        'project': {
            'schema_version': 1,
            'mod_name': 'Legacy Session',
            'mod_id': 'LegacySession',
            'media_rows': [],
        },
    }
    target = tmp_path / 'legacy-session.json'
    target.write_text(json.dumps(payload), encoding='utf-8')

    store = SessionStore(target)
    _project, current_path = store.load()

    assert current_path == 'C:/projects/legacy.nmbproj.json'
    assert store.last_dialog_folder_memory.song_folder == ''
    assert store.last_dialog_folder_memory.image_folder == ''


def test_session_store_load_legacy_payload_uses_project_audio_settings_as_master_defaults(tmp_path: Path) -> None:
    payload = {
        'current_path': '',
        'project': {
            'schema_version': 1,
            'mod_name': 'Legacy Session',
            'mod_id': 'LegacySession',
            'sample_rate': 48000,
            'compression_quality': 0.65,
            'reencode_existing_ogg': False,
            'media_rows': [],
        },
    }
    target = tmp_path / 'legacy-audio-session.json'
    target.write_text(json.dumps(payload), encoding='utf-8')

    store = SessionStore(target)
    _project, _current_path = store.load()

    assert store.last_audio_preferences.sample_rate == 48000
    assert store.last_audio_preferences.compression_quality == 0.65
    assert store.last_audio_preferences.reencode_existing_ogg is False
    assert store.last_automatic_textures_enabled is True
    assert store.last_regenerate_textures_on_project_load_enabled is False
    assert store.last_text_tooltips_enabled is True


def test_project_load_defaults_automatic_textures_enabled_for_legacy_payload(tmp_path: Path) -> None:
    payload = {
        'schema_version': 1,
        'mod_name': 'Legacy Pack',
        'mod_id': 'LegacyPack',
        'media_rows': [],
    }
    target = tmp_path / 'legacy.nmbproj.json'
    target.write_text(json.dumps(payload), encoding='utf-8')

    loaded = ProjectStore().load(target)

    assert loaded.automatic_textures_enabled is True


def test_project_load_defaults_media_modes_for_legacy_payload(tmp_path: Path) -> None:
    payload = {
        'schema_version': 1,
        'mod_name': 'Legacy Pack',
        'mod_id': 'LegacyPack',
        'media_rows': [
            {
                'row_id': 1,
                'media_name': 'Legacy Album',
                'tracks_a': [{'display_label': 'Song'}],
            }
        ],
    }
    target = tmp_path / 'legacy-media-modes.nmbproj.json'
    target.write_text(json.dumps(payload), encoding='utf-8')

    loaded = ProjectStore().load(target)

    assert loaded.media_rows[0].media_modes == {'cassette': 'split', 'vinyl': 'split', 'cd': 'single'}


def test_project_load_coerces_invalid_media_modes_to_defaults(tmp_path: Path) -> None:
    payload = {
        'schema_version': 1,
        'mod_name': 'Invalid Modes',
        'mod_id': 'InvalidModes',
        'media_rows': [
            {
                'row_id': 1,
                'media_name': 'Odd Album',
                'media_modes': {
                    'cassette': 'full',
                    'vinyl': 'split',
                    'cd': 'banana',
                },
                'tracks_a': [{'display_label': 'Song'}],
            }
        ],
    }
    target = tmp_path / 'invalid-media-modes.nmbproj.json'
    target.write_text(json.dumps(payload), encoding='utf-8')

    loaded = ProjectStore().load(target)

    assert loaded.media_rows[0].media_modes == {'cassette': 'split', 'vinyl': 'split', 'cd': 'single'}
