from new_music_builder.domain.models import MediaRow, ProjectConfig, TrackEntry, project_from_dict, project_to_dict
from new_music_builder.services.project_session import ProjectSession


def _make_track(source_path: str, display_label: str, duration: str) -> TrackEntry:
    return TrackEntry(
        source_path=source_path,
        display_label=display_label,
        duration=duration,
    )


def test_sort_tracks_by_song_name_toggles_direction() -> None:
    row = MediaRow(row_id=1)
    row.tracks_a = [
        _make_track("c.wav", "Charlie", "00:03:00"),
        _make_track("a.wav", "alpha", "00:01:00"),
        _make_track("b.wav", "Bravo", "00:02:00"),
    ]
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))

    state = session.sort_tracks_in_media_row(1, "A", "song_name")
    assert state is not None
    assert state.column == "song_name"
    assert state.direction == "asc"
    assert [track.display_label for track in row.tracks_a] == ["alpha", "Bravo", "Charlie"]

    state = session.sort_tracks_in_media_row(1, "A", "song_name")
    assert state is not None
    assert state.direction == "desc"
    assert [track.display_label for track in row.tracks_a] == ["Charlie", "Bravo", "alpha"]


def test_sort_tracks_by_length_uses_numeric_duration() -> None:
    row = MediaRow(row_id=1)
    row.tracks_a = [
        _make_track("a.wav", "One", "00:10:00"),
        _make_track("b.wav", "Two", "00:02:00"),
        _make_track("c.wav", "Three", "00:01:30"),
    ]
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))

    state = session.sort_tracks_in_media_row(1, "A", "length")
    assert state is not None
    assert state.direction == "asc"
    assert [track.display_label for track in row.tracks_a] == ["Three", "Two", "One"]


def test_sort_tracks_by_ogg_defaults_descending() -> None:
    row = MediaRow(row_id=1)
    row.tracks_a = [
        _make_track("a.mp3", "MP3", "00:01:00"),
        _make_track("b.ogg", "OGG A", "00:02:00"),
        _make_track("c.ogg", "OGG B", "00:03:00"),
    ]
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))

    state = session.sort_tracks_in_media_row(1, "A", "ogg")
    assert state is not None
    assert state.direction == "desc"
    assert [track.display_label for track in row.tracks_a] == ["OGG A", "OGG B", "MP3"]


def test_switching_sort_columns_resets_to_column_default_direction() -> None:
    row = MediaRow(row_id=1)
    row.tracks_a = [
        _make_track("b.ogg", "Bravo", "00:02:00"),
        _make_track("a.wav", "Alpha", "00:01:00"),
    ]
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))

    session.sort_tracks_in_media_row(1, "A", "song_name")
    state = session.sort_tracks_in_media_row(1, "A", "length")
    assert state is not None
    assert state.column == "length"
    assert state.direction == "asc"


def test_song_sort_state_serializes_and_loads() -> None:
    row = MediaRow(row_id=1)
    row.song_sort_a.column = "length"
    row.song_sort_a.direction = "desc"
    project = ProjectConfig(media_rows=[row])

    loaded = project_from_dict(project_to_dict(project))

    assert loaded.media_rows[0].song_sort_a.column == "length"
    assert loaded.media_rows[0].song_sort_a.direction == "desc"


def test_drag_reorder_clears_song_sort_state() -> None:
    row = MediaRow(row_id=1)
    row.tracks_a = [
        _make_track("a.wav", "Alpha", "00:01:00"),
        _make_track("b.wav", "Bravo", "00:02:00"),
        _make_track("c.wav", "Charlie", "00:03:00"),
    ]
    row.song_sort_a.column = "song_name"
    row.song_sort_a.direction = "asc"
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))

    moved = session.move_tracks_within_media_row(1, "A", {0}, 3)

    assert moved == [2]
    assert row.song_sort_a.column is None
    assert row.song_sort_a.direction == "asc"
