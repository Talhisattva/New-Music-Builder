from new_music_builder.domain.models import ProjectConfig, TrackEntry, default_media_row
from new_music_builder.services.asset_catalog import AssetCatalog
from new_music_builder.services.export_planning import build_export_plan
from new_music_builder.services.export_registration_plan import build_export_registration_plan
from new_music_builder.platform.paths import assets_root


def test_legacy_export_plan_creates_one_media_row_per_song() -> None:
    project = ProjectConfig(mod_name='Legacy', mod_id='LegacyPack', legacy_mode_enabled=True)
    row = default_media_row(1)
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
    assert all(side.export_relative_dir == plan.rows[index].export_id for index, side in enumerate(plan.sides))


def test_legacy_registration_omits_container_variants() -> None:
    project = ProjectConfig(mod_name='Legacy', mod_id='LegacyPack', legacy_mode_enabled=True)
    row = default_media_row(1)
    row.tracks_a = [TrackEntry(display_label='Single Song', source_path='C:/music/song.ogg', duration='00:01:00')]
    project.media_rows = [row]

    plan = build_export_plan(project, AssetCatalog(assets_root()).scan())
    registration = build_export_registration_plan(project, plan)

    assert len(registration.albums) == 1
    assert registration.albums[0].container_variants == []
    assert all(variant.mode == 'single' for variant in registration.albums[0].media_variants)
