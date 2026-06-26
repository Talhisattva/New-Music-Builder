from new_music_builder.services.project_session import ProjectSession


def test_add_media_row_applies_preferred_cover_defaults() -> None:
    session = ProjectSession()
    session.project.media_rows = []

    row_id = session.add_media_row()

    assert row_id == 1
    row = session.project.media_rows[0]
    assert row.appearances["cassette"].selected_asset_key == "cassette:7"
    assert row.appearances["vinyl"].selected_asset_key == "vinyl:10"
    assert row.appearances["case"].selected_asset_key == "case:4"
    assert row.appearances["jacket"].selected_asset_key == "jacket:4"
    assert row.appearances["cd_cover"].selected_asset_key == "cd_cover:4"


def test_remove_last_media_row_rebuilds_preferred_defaults() -> None:
    session = ProjectSession()

    session.remove_media_row(1)

    row = session.project.media_rows[0]
    assert row.row_id == 1
    assert row.appearances["cassette"].selected_asset_key == "cassette:7"
    assert row.appearances["vinyl"].selected_asset_key == "vinyl:10"
    assert row.appearances["case"].selected_asset_key == "case:4"
    assert row.appearances["jacket"].selected_asset_key == "jacket:4"
    assert row.appearances["cd_cover"].selected_asset_key == "cd_cover:4"
