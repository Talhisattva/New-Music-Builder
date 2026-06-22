from __future__ import annotations

from new_music_builder.ui.main_window import build_project_saved_log_line, resolve_song_removal_indices


def test_resolve_song_removal_indices_uses_selection_when_present() -> None:
    assert resolve_song_removal_indices({1, 3}, track_count=5, fallback_to_last=True) == {1, 3}


def test_resolve_song_removal_indices_falls_back_to_last_track_for_button_behavior() -> None:
    assert resolve_song_removal_indices(set(), track_count=4, fallback_to_last=True) == {3}


def test_resolve_song_removal_indices_does_not_fallback_when_disabled_or_empty() -> None:
    assert resolve_song_removal_indices(set(), track_count=4, fallback_to_last=False) == set()
    assert resolve_song_removal_indices(set(), track_count=0, fallback_to_last=True) == set()


def test_build_project_saved_log_line_uses_done_style_and_path() -> None:
    line = build_project_saved_log_line("C:/Projects/test.nmbproj.json")

    assert line.prefix_text == "Project saved:"
    assert line.subject_text == "C:/Projects/test.nmbproj.json"
    assert line.color_role == "done"
    assert line.timestamp
