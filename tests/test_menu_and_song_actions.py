from __future__ import annotations

from new_music_builder.ui.main_window import (
    build_generated_asset_failure_log_line,
    build_generated_assets_removed_log_line,
    build_project_saved_log_line,
    preferred_default_asset_key,
    resolve_song_removal_indices,
)


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


def test_build_generated_assets_removed_log_line_uses_done_style_and_counts() -> None:
    line = build_generated_assets_removed_log_line("cover.png", 2, 4)

    assert line.prefix_text == "Removed generated assets from"
    assert line.subject_text == "cover.png"
    assert line.trailing_text == "- 2 record(s), 4 file(s) deleted"
    assert line.color_role == "done"
    assert line.timestamp


def test_build_generated_asset_failure_log_line_uses_error_style_and_reason() -> None:
    line = build_generated_asset_failure_log_line("C:/covers/cover.png", "donor cassette shell was unavailable")

    assert line.prefix_text == "Failed to create assets from"
    assert line.subject_text == "cover.png"
    assert line.trailing_text == "donor cassette shell was unavailable"
    assert line.color_role == "error"
    assert line.timestamp


def test_preferred_default_asset_key_uses_black_outer_cassette_and_case_defaults() -> None:
    assert preferred_default_asset_key('cassette', {'cassette:1', 'cassette:17'}) == 'cassette:17'
    assert preferred_default_asset_key('case', {'case:1', 'case:12'}) == 'case:12'


def test_preferred_default_asset_key_falls_back_when_preferred_key_missing() -> None:
    assert preferred_default_asset_key('cassette', {'cassette:1'}) == ''
    assert preferred_default_asset_key('vinyl', {'vinyl:1'}) == ''
