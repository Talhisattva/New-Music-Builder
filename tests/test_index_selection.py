from new_music_builder.domain.models import TrackEntry
from new_music_builder.services.index_selection import apply_index_selection
from new_music_builder.services.project_session import ProjectSession


def test_apply_index_selection_single_selects_one() -> None:
    selected, anchor = apply_index_selection(set(), None, 2, 6, shift=False, additive=False)
    assert selected == {2}
    assert anchor == 2


def test_apply_index_selection_ctrl_toggles_membership() -> None:
    selected, anchor = apply_index_selection({1, 3}, 3, 1, 6, shift=False, additive=True)
    assert selected == {3}
    assert anchor == 1


def test_apply_index_selection_shift_selects_range_from_anchor() -> None:
    selected, anchor = apply_index_selection({2}, 2, 5, 8, shift=True, additive=False)
    assert selected == {2, 3, 4, 5}
    assert anchor == 2


def test_project_session_remove_tracks_from_media_row_preserves_remaining_order(tmp_path) -> None:
    session = ProjectSession()
    row = session.project.media_rows[0]
    row.tracks_a = [
        TrackEntry(display_label='A'),
        TrackEntry(display_label='B'),
        TrackEntry(display_label='C'),
        TrackEntry(display_label='D'),
    ]
    removed = session.remove_tracks_from_media_row(row.row_id, 'A', {1, 3})
    assert removed == [1, 3]
    assert [track.display_label for track in row.tracks_a] == ['A', 'C']


def test_project_session_move_tracks_within_media_row_moves_single_track() -> None:
    session = ProjectSession()
    row = session.project.media_rows[0]
    row.tracks_a = [
        TrackEntry(display_label='A'),
        TrackEntry(display_label='B'),
        TrackEntry(display_label='C'),
        TrackEntry(display_label='D'),
    ]
    moved = session.move_tracks_within_media_row(row.row_id, 'A', {1}, 4)
    assert moved == [3]
    assert [track.display_label for track in row.tracks_a] == ['A', 'C', 'D', 'B']


def test_project_session_move_tracks_within_media_row_moves_multiselect_block_stably() -> None:
    session = ProjectSession()
    row = session.project.media_rows[0]
    row.tracks_a = [
        TrackEntry(display_label='A'),
        TrackEntry(display_label='B'),
        TrackEntry(display_label='C'),
        TrackEntry(display_label='D'),
        TrackEntry(display_label='E'),
    ]
    moved = session.move_tracks_within_media_row(row.row_id, 'A', {1, 3}, 5)
    assert moved == [3, 4]
    assert [track.display_label for track in row.tracks_a] == ['A', 'C', 'E', 'B', 'D']


def test_project_session_move_tracks_within_media_row_adjusts_target_from_removed_rows_above() -> None:
    session = ProjectSession()
    row = session.project.media_rows[0]
    row.tracks_a = [
        TrackEntry(display_label='A'),
        TrackEntry(display_label='B'),
        TrackEntry(display_label='C'),
        TrackEntry(display_label='D'),
        TrackEntry(display_label='E'),
    ]
    moved = session.move_tracks_within_media_row(row.row_id, 'A', {1, 2}, 4)
    assert moved == [2, 3]
    assert [track.display_label for track in row.tracks_a] == ['A', 'D', 'B', 'C', 'E']
