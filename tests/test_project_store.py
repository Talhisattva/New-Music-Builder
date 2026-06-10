from pathlib import Path

from new_music_builder.domain.models import ProjectConfig, TrackEntry, default_media_row
from new_music_builder.services.project_store import ProjectStore


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
