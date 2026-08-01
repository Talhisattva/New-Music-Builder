from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from types import SimpleNamespace

from new_music_builder.domain.models import AudioRunEvent, AudioRunResult, BuildSummaryStats, GeneratedPreviewCell, GeneratedPreviewRow, ProjectConfig, TrackEntry, default_media_row
from new_music_builder.services.project_session import ProjectSession
from new_music_builder.services.session_store import SessionAudioPreferences
from new_music_builder.ui.main_window import MainWindow
from new_music_builder.ui.widgets.media_row_list import MediaRowList, MediaRowShell


@dataclass
class _FakeViewport:
    current: tuple[float, float] = (0.0, 1.0)
    moved_to: list[float] | None = None

    def yview(self) -> tuple[float, float]:
        return self.current

    def yview_moveto(self, value: float) -> None:
        if self.moved_to is None:
            self.moved_to = []
        self.moved_to.append(value)


@dataclass
class _FakeScrollArea:
    refresh_count: int = 0

    def refresh_scroll_region(self) -> None:
        self.refresh_count += 1


class _FakeRowList:
    def __init__(self) -> None:
        self.appended_row_ids: list[int] = []
        self.expanded_row_ids: list[int | None] = []
        self.removed_row_ids: list[set[int]] = []
        self.remove_rows_payloads: list[list[int]] = []
        self.selection_states: list[set[int]] = []
        self.reordered_rows: list[list[int]] = []
        self.media_strip_refreshes: list[int] = []
        self.collapsed_detail_refreshes: list[int] = []
        self.row_widgets: list[object] = [object()]

    def append_row(self, row) -> None:
        self.appended_row_ids.append(row.row_id)

    def set_expanded_row(self, row_id: int | None) -> None:
        self.expanded_row_ids.append(row_id)

    def remove_rows(self, row_ids: set[int], rows=None) -> None:
        self.removed_row_ids.append(set(row_ids))
        self.remove_rows_payloads.append([row.row_id for row in (rows or [])])

    def set_selection_state(self, row_ids: set[int]) -> None:
        self.selection_states.append(set(row_ids))

    def reorder_rows(self, rows) -> None:
        self.reordered_rows.append([row.row_id for row in rows])

    def refresh_media_type_strips_for_row(self, row_id: int) -> None:
        self.media_strip_refreshes.append(row_id)

    def refresh_collapsed_details_for_row(self, row_id: int) -> None:
        self.collapsed_detail_refreshes.append(row_id)


class _FakeRowWidget:
    def __init__(self, expanded: bool, row_id: int | None = None) -> None:
        self._expanded = expanded
        self._row_id = row_id
        self.set_expanded_calls: list[bool] = []
        self.refreshed_covers: list[str] = []
        self.song_table_refresh_count = 0
        self.song_selection_states: list[set[int]] = []

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self.set_expanded_calls.append(expanded)

    def refresh_cover(self, cover_path: str) -> None:
        self.refreshed_covers.append(cover_path)

    def refresh_song_table(self) -> None:
        self.song_table_refresh_count += 1

    def set_song_selection_state(self, selected_indices: set[int]) -> None:
        self.song_selection_states.append(set(selected_indices))


class _FakeCollapsedDetails:
    def __init__(self) -> None:
        self.refreshed_rows: list[object] = []

    def refresh_content(self, row) -> None:
        self.refreshed_rows.append(row)


class _FakeModuleFivePanel:
    def __init__(self) -> None:
        self.appended_rows: list[GeneratedPreviewRow] = []
        self.reset_count = 0
        self.set_rows_payloads: list[list[GeneratedPreviewRow]] = []
        self.export_active_states: list[bool] = []

    def append_preview_row(self, row: GeneratedPreviewRow) -> None:
        self.appended_rows.append(row)

    def reset_preview_rows(self) -> None:
        self.reset_count += 1

    def set_preview_rows(self, rows: list[GeneratedPreviewRow]) -> None:
        self.set_rows_payloads.append(list(rows))

    def set_export_active(self, active: bool) -> None:
        self.export_active_states.append(active)


def _generated_preview_row(row_id: int, side: str, label_text: str) -> GeneratedPreviewRow:
    cell = GeneratedPreviewCell(
        label_text=label_text,
        section_text=f"{side}-SIDE",
        song_count=1,
        duration_text="00:01:00",
    )
    return GeneratedPreviewRow(row_id=row_id, side=side, inventory_cell=cell, world_cell=cell)


def test_add_module_two_media_row_uses_incremental_row_list() -> None:
    row = default_media_row(1)
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))
    window = MainWindow.__new__(MainWindow)
    window.session = session
    window.module_two_row_list = _FakeRowList()
    window.module_two_scroll_area = _FakeScrollArea()
    window.module_two_content_viewport = _FakeViewport()
    window._build_module_two_row_list = lambda: (_ for _ in ()).throw(AssertionError("full rebuild should not run"))
    window._is_build_locked = lambda: False
    window._cancel_module_two_song_drag = lambda: None
    window._cancel_module_two_row_drag = lambda: None
    window._refresh_module_three_appearance_selector = lambda: setattr(window, "_refreshed_module_three", True)
    window.on_project_change = lambda: setattr(window, "_project_changed", True)

    MainWindow._add_module_two_media_row(window)

    assert [row.row_id for row in window.session.project.media_rows] == [1, 2]
    assert window.module_two_row_list.appended_row_ids == [2]
    assert window.module_two_row_list.expanded_row_ids == [2]
    assert window.module_two_scroll_area.refresh_count == 1
    assert window.module_two_content_viewport.moved_to == [1.0]
    assert getattr(window, "_refreshed_module_three", False) is True
    assert getattr(window, "_project_changed", False) is True


def test_remove_module_two_media_row_set_prunes_selection_and_updates_remaining_rows() -> None:
    rows = [default_media_row(1), default_media_row(2), default_media_row(3)]
    session = ProjectSession(project=ProjectConfig(media_rows=rows))
    window = MainWindow.__new__(MainWindow)
    window.session = session
    window.module_two_row_list = _FakeRowList()
    window.module_two_scroll_area = _FakeScrollArea()
    window.module_two_content_viewport = _FakeViewport(current=(0.25, 0.75))
    window.module_two_selected_row_ids = {2, 3}
    window.module_two_selection_anchor_row_id = 3
    window.module_two_song_selected_indices = {(2, "A"): {0}, (3, "B"): {1}}
    window.module_two_song_selection_anchor_indices = {(2, "A"): 0, (3, "B"): 1}
    window._is_build_locked = lambda: False
    window._cancel_module_two_song_drag = lambda: None
    window._cancel_module_two_row_drag = lambda: None
    window._refresh_module_three_appearance_selector = lambda: setattr(window, "_refreshed_module_three", True)
    window.on_project_change = lambda: setattr(window, "_project_changed", True)

    MainWindow._remove_module_two_media_row_set(window, {1})

    assert [row.row_id for row in window.session.project.media_rows] == [2, 3]
    assert window.module_two_selected_row_ids == {2, 3}
    assert window.module_two_selection_anchor_row_id == 3
    assert window.module_two_song_selected_indices == {(2, "A"): {0}, (3, "B"): {1}}
    assert window.module_two_song_selection_anchor_indices == {(2, "A"): 0, (3, "B"): 1}
    assert window.module_two_row_list.removed_row_ids == [{1}]
    assert window.module_two_row_list.remove_rows_payloads == [[2, 3]]
    assert window.module_two_row_list.selection_states == [{2, 3}]
    assert window.module_two_content_viewport.moved_to == [0.25]
    assert getattr(window, "_refreshed_module_three", False) is True
    assert getattr(window, "_project_changed", False) is True


def test_set_module_two_media_mode_updates_row_and_refreshes_target_only() -> None:
    row = default_media_row(1)
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))
    window = MainWindow.__new__(MainWindow)
    window.session = session
    window.module_two_row_list = _FakeRowList()
    window._is_build_locked = lambda: False
    window.on_project_change = lambda: setattr(window, "_project_changed", True)

    MainWindow._set_module_two_media_mode(window, 1, "cassette", "single")

    assert row.media_modes["cassette"] == "single"
    assert window.module_two_row_list.media_strip_refreshes == [1]
    assert window.module_two_row_list.collapsed_detail_refreshes == [1]
    assert getattr(window, "_project_changed", False) is True


def test_move_module_two_selected_songs_by_moves_block_and_preserves_selection() -> None:
    row = default_media_row(1)
    row.tracks_a = [
        TrackEntry(display_label="A"),
        TrackEntry(display_label="B"),
        TrackEntry(display_label="C"),
        TrackEntry(display_label="D"),
    ]
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))
    row_widget = _FakeRowWidget(True, row_id=1)
    window = MainWindow.__new__(MainWindow)
    window.session = session
    window._module_two_keyboard_song_key = (1, "A")
    window.module_two_song_selected_indices = {(1, "A"): {1, 2}}
    window.module_two_song_selection_anchor_indices = {(1, "A"): 1}
    window._expanded_row_widget = lambda row_id: row_widget if row_id == 1 else None
    window.on_project_change = lambda: setattr(window, "_project_changed", True)

    MainWindow._move_module_two_selected_songs_by(window, 1)

    assert [track.display_label for track in row.tracks_a] == ["A", "D", "B", "C"]
    assert window.module_two_song_selected_indices[(1, "A")] == {2, 3}
    assert window.module_two_song_selection_anchor_indices[(1, "A")] == 2
    assert row_widget.song_table_refresh_count == 1
    assert row_widget.song_selection_states == [{2, 3}]
    assert getattr(window, "_project_changed", False) is True


def test_sync_converted_song_ogg_link_uses_project_legacy_mode_for_source_tracks() -> None:
    row = default_media_row(1)
    row.selected_side = "B"
    row.tracks_a = [TrackEntry(display_label="A1")]
    row.tracks_b = [TrackEntry(display_label="B1")]
    session = ProjectSession(project=ProjectConfig(legacy_mode_enabled=True, media_rows=[row]))
    row_widget = _FakeRowWidget(True, row_id=1)
    window = MainWindow.__new__(MainWindow)
    window.session = session
    window.module_two_song_selected_indices = {(1, "A"): {0}}
    window.module_two_song_selection_anchor_indices = {(1, "A"): 0}
    window._expanded_row_widget = lambda row_id: row_widget if row_id == 1 else None
    window._legacy_mode_preference_enabled = True

    MainWindow._sync_converted_song_ogg_link(
        window,
        AudioRunEvent(
            kind="song_succeeded",
            row_id=99,
            side="B",
            song_index=7,
            source_row_id=1,
            source_track_index=0,
            cached_ogg_path="C:/cache/A1.ogg",
        ),
    )

    assert row.tracks_a[0].cached_ogg_path == "C:/cache/A1.ogg"
    assert row.tracks_a[0].conversion_status == "cached_ogg"
    assert row_widget.song_table_refresh_count == 1
    assert row_widget.song_selection_states == [{0}]


def test_handle_audio_run_event_appends_preview_row_when_side_completes_after_success() -> None:
    window = MainWindow.__new__(MainWindow)
    window.module_four_panel = type(
        "ModuleFour",
        (),
        {
            "state": type("State", (), {"current_run_log_lines": []})(),
            "append_queue_group": lambda _self, _group: None,
            "ensure_song": lambda _self, *_args: None,
            "update_song_progress": lambda _self, *_args: None,
            "finalize_successful_side": lambda _self, _row_id, _side: None,
            "finalize_active_log_line": lambda _self, _line: None,
            "append_log_line": lambda _self, _line: None,
        },
    )()
    window.module_five_panel = _FakeModuleFivePanel()
    preview_row = _generated_preview_row(7, "A", "Alpha Side")
    window._active_preview_rows_by_side = {(7, "A"): preview_row}
    window._active_preview_keys_in_order = [(7, "A")]
    window._active_successful_sides_by_row = {}
    window._active_emitted_preview_rows = set()
    window._active_ready_preview_keys = set()
    window._active_passthrough_song_count = 0
    window._active_passthrough_logged_count = 0
    window._active_passthrough_log_step = 50
    window._build_locked = False
    window._sync_converted_song_ogg_link = lambda _event: None

    MainWindow._handle_audio_run_event(
        window,
        AudioRunEvent(kind="song_succeeded", row_id=7, side="A", song_index=0, display_label="Alpha Side", size_text="1.0 MB"),
    )
    assert window.module_five_panel.set_rows_payloads == []

    MainWindow._handle_audio_run_event(
        window,
        AudioRunEvent(kind="side_completed", row_id=7, side="A", message="Side complete."),
    )

    assert window.module_five_panel.set_rows_payloads[-1] == [preview_row]
    assert window._active_emitted_preview_rows == {(7, "A")}


def test_handle_audio_run_event_aggregates_parallel_conversion_log_line() -> None:
    updates: list[object] = []
    appended: list[object] = []

    class _ModuleFour:
        def __init__(self) -> None:
            self.state = type("State", (), {"current_run_log_lines": []})()

        def append_queue_group(self, _group) -> None:
            pass

        def activate_song(self, _row_id, _side, _song_index, _song) -> None:
            pass

        def ensure_song(self, *_args) -> None:
            pass

        def update_song_progress(self, *_args) -> None:
            pass

        def settle_queue_state(self) -> None:
            pass

        def finalize_successful_side(self, _row_id, _side) -> None:
            pass

        def append_log_line(self, line) -> None:
            self.state.current_run_log_lines.append(line)
            appended.append(line)

        def update_active_log_line(self, line) -> None:
            if self.state.current_run_log_lines:
                self.state.current_run_log_lines[-1] = line
            else:
                self.state.current_run_log_lines.append(line)
            updates.append(line)

        def finalize_active_log_line(self, line) -> None:
            self.update_active_log_line(line)

    window = MainWindow.__new__(MainWindow)
    window.module_four_panel = _ModuleFour()
    window._active_preview_rows_by_side = {}
    window._active_preview_keys_in_order = []
    window._active_successful_sides_by_row = {}
    window._active_emitted_preview_rows = set()
    window._active_ready_preview_keys = set()
    window._active_converting_song_keys = set()
    window._active_passthrough_song_count = 0
    window._active_passthrough_logged_count = 0
    window._active_passthrough_log_step = 50
    window._sync_converted_song_ogg_link = lambda _event: None

    MainWindow._handle_audio_run_event(
        window,
        AudioRunEvent(kind="song_started", row_id=7, side="A", song_index=0, track_number=1, display_label="Alpha"),
    )
    MainWindow._handle_audio_run_event(
        window,
        AudioRunEvent(kind="song_started", row_id=7, side="A", song_index=1, track_number=2, display_label="Beta"),
    )
    MainWindow._handle_audio_run_event(
        window,
        AudioRunEvent(kind="song_progress", row_id=7, side="A", song_index=1, track_number=2, display_label="Beta", percent=35),
    )

    assert appended[0].prefix_text == "Starting song:"
    assert updates[-1].prefix_text == "Converting:"
    assert updates[-1].subject_text == "2 songs simultaneously"
    assert updates[-1].trailing_text == ""


def test_finalize_audio_run_sets_preview_rows_in_planned_order() -> None:
    window = MainWindow.__new__(MainWindow)
    module_five = _FakeModuleFivePanel()
    finalized_sides: list[tuple[int, str]] = []
    flushed_queue_updates: list[bool] = []
    window.module_five_panel = module_five
    window.module_four_panel = type(
        "ModuleFour",
        (),
        {
            "append_log_line": lambda _self, _line: None,
            "settle_queue_state": lambda _self: None,
            "finalize_successful_side": lambda _self, row_id, side: finalized_sides.append((row_id, side)),
            "flush_queue_updates": lambda _self: flushed_queue_updates.append(True),
            "state": type("State", (), {"current_run_log_lines": []})(),
        },
    )()
    first = _generated_preview_row(1, "A", "Singles")
    second = _generated_preview_row(2, "A", "Gen Mix")
    window._active_preview_rows_by_side = {(1, "A"): first, (2, "A"): second}
    window._active_preview_keys_in_order = [(1, "A"), (2, "A")]
    window._active_build_run_id = "testrun"
    window._active_build_final_targets = None
    window._last_export_output_path = ""
    window._flush_passthrough_song_log = lambda force=False: None
    window.module_six_panel = type("ModuleSix", (), {"set_stats": lambda _self, _stats: None})()
    window._snapshot_current_build_log = lambda: None
    window._refresh_build_summary = lambda: None
    window._clear_active_build_run_state = lambda: None
    window.preview_entries = []
    window._directory_size_text = lambda _path: "0 KB"

    plan = type("Plan", (), {"stats": BuildSummaryStats(planned_media_rows=2, planned_total_sides=2, planned_total_songs=2)})()
    result = AudioRunResult(
        output_path="C:/temp/out",
        successful_sides=[(2, "A"), (1, "A")],
        built_song_count=2,
        converted_count=0,
        mod_size_text="1 KB",
    )

    MainWindow._finalize_audio_run(window, plan, result)

    assert module_five.set_rows_payloads[-1] == [first, second]
    assert finalized_sides == [(2, "A"), (1, "A")]
    assert flushed_queue_updates == [True]


def test_finalize_audio_run_aborted_uses_result_size_text_without_directory_scan() -> None:
    window = MainWindow.__new__(MainWindow)
    window._active_build_run_id = "testrun"
    window._active_build_final_targets = None
    window._last_export_output_path = ""
    window.preview_entries = []
    window.module_six_panel = type("ModuleSix", (), {"set_stats": lambda _self, stats: setattr(window, "_final_stats", stats)})()
    window._snapshot_current_build_log = lambda: setattr(window, "_snapshotted", True)
    window._refresh_build_summary = lambda: setattr(window, "_summary_refreshed", True)
    window._clear_active_build_run_state = lambda: setattr(window, "_cleared", True)
    window._directory_size_text = lambda _path: (_ for _ in ()).throw(AssertionError("directory size scan should not run on abort"))

    plan = type("Plan", (), {"stats": BuildSummaryStats(planned_media_rows=2, planned_total_sides=4, planned_total_songs=40)})()
    result = AudioRunResult(output_path="C:/temp/out", aborted=True, converted_count=3, mod_size_text="0 KB")

    MainWindow._finalize_audio_run(window, plan, result)

    assert getattr(window, "_final_stats").mod_size_text == "0 KB"
    assert getattr(window, "_snapshotted", False) is True
    assert getattr(window, "_summary_refreshed", False) is True
    assert getattr(window, "_cleared", False) is True


def test_run_build_preview_skips_export_planning_when_overwrite_is_cancelled(monkeypatch) -> None:
    window = MainWindow.__new__(MainWindow)
    window.session = ProjectSession(project=ProjectConfig())
    window.asset_catalog = {}
    window._active_build_run_id = None
    window._active_emitted_preview_rows = set()
    window._sync_phase_one_project_state = lambda: None
    window._is_build_locked = lambda: False
    window._request_abort_export = lambda: (_ for _ in ()).throw(AssertionError("abort path should not run"))
    window.module_four_panel = type(
        "ModuleFour",
        (),
        {
            "archive_current_run": lambda _self: None,
            "reset_current_run": lambda _self: None,
            "set_output_path": lambda _self, _path: None,
            "set_log_lines": lambda _self, _lines: None,
        },
    )()
    window.module_five_panel = type(
        "ModuleFive",
        (),
        {
            "reset_preview_rows": lambda _self: None,
            "set_export_active": lambda _self, _active: None,
        },
    )()
    window.module_six_panel = type("ModuleSix", (), {"set_stats": lambda _self, _stats: None})()
    window.build_summary = type("BuildSummary", (), {"refresh": lambda _self: None})()
    window.update_idletasks = lambda: None
    window._set_build_locked = lambda _locked: None
    window._start_audio_build_run = lambda **_kwargs: (_ for _ in ()).throw(AssertionError("build should not start on cancel"))
    window._module_four_log_line_text = lambda line: line.prefix_text

    calls: list[str] = []

    monkeypatch.setattr(
        "new_music_builder.ui.main_window.build_export_plan",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("export planning should not run before overwrite confirm")),
    )
    monkeypatch.setattr(
        "new_music_builder.ui.main_window.resolve_export_target",
        lambda *_args, **_kwargs: SimpleNamespace(root="C:/already-exists"),
    )
    monkeypatch.setattr("new_music_builder.ui.main_window.deepcopy", lambda project: project)
    monkeypatch.setattr("new_music_builder.ui.main_window.uuid4", lambda: SimpleNamespace(hex="12345678abcdef"))
    monkeypatch.setattr("new_music_builder.ui.main_window.Path.exists", lambda _self: True)

    def _confirm(_output_root):
        calls.append("confirm")
        return False

    window._confirm_overwrite_export_root = _confirm

    MainWindow.run_build_preview(window)

    assert calls == ["confirm"]


def test_handle_module_two_keyboard_reorder_uses_last_clicked_song_owner() -> None:
    rows = [default_media_row(1), default_media_row(2), default_media_row(3)]
    rows[0].tracks_a = [
        TrackEntry(display_label="A"),
        TrackEntry(display_label="B"),
        TrackEntry(display_label="C"),
    ]
    session = ProjectSession(project=ProjectConfig(media_rows=rows))
    row_widget = _FakeRowWidget(True, row_id=1)
    window = MainWindow.__new__(MainWindow)
    window.session = session
    window._module_two_keyboard_owner = "songs"
    window._module_two_keyboard_song_key = (1, "A")
    window.module_two_selected_row_ids = {2}
    window.module_two_selection_anchor_row_id = 2
    window.module_two_song_selected_indices = {(1, "A"): {1}}
    window.module_two_song_selection_anchor_indices = {(1, "A"): 1}
    window._expanded_row_widget = lambda row_id: row_widget if row_id == 1 else None
    window.module_two_row_list = _FakeRowList()
    window.module_two_scroll_area = _FakeScrollArea()
    window.module_two_content_viewport = _FakeViewport(current=(0.25, 0.75))
    window._refresh_module_three_appearance_selector = lambda: setattr(window, "_refreshed_module_three", True)
    window.on_project_change = lambda: setattr(window, "_project_changed", True)
    window._is_build_locked = lambda: False
    window.focus_get = lambda: None

    result = MainWindow._handle_module_two_keyboard_reorder(window, None, 1)

    assert result == "break"
    assert [row.row_id for row in window.session.project.media_rows] == [1, 2, 3]
    assert [track.display_label for track in rows[0].tracks_a] == ["A", "C", "B"]
    assert row_widget.song_selection_states == [{2}]


def test_move_module_two_selected_rows_by_moves_block_and_preserves_selection() -> None:
    rows = [default_media_row(1), default_media_row(2), default_media_row(3), default_media_row(4)]
    session = ProjectSession(project=ProjectConfig(media_rows=rows))
    window = MainWindow.__new__(MainWindow)
    window.session = session
    window.module_two_selected_row_ids = {2, 3}
    window.module_two_selection_anchor_row_id = 2
    window.module_two_row_list = _FakeRowList()
    window.module_two_scroll_area = _FakeScrollArea()
    window.module_two_content_viewport = _FakeViewport(current=(0.25, 0.75))
    window._refresh_module_three_appearance_selector = lambda: setattr(window, "_refreshed_module_three", True)
    window.on_project_change = lambda: setattr(window, "_project_changed", True)

    MainWindow._move_module_two_selected_rows_by(window, -1)

    assert [row.row_id for row in window.session.project.media_rows] == [2, 3, 1, 4]
    assert window.module_two_selected_row_ids == {2, 3}
    assert window.module_two_selection_anchor_row_id == 2
    assert window.module_two_row_list.reordered_rows == [[2, 3, 1, 4]]
    assert window.module_two_row_list.selection_states == [{2, 3}]
    assert window.module_two_scroll_area.refresh_count == 1
    assert window.module_two_content_viewport.moved_to == [0.25]
    assert getattr(window, "_refreshed_module_three", False) is True
    assert getattr(window, "_project_changed", False) is True


def test_move_module_two_selected_rows_by_blocks_expanded_rows() -> None:
    rows = [default_media_row(1), default_media_row(2), default_media_row(3)]
    rows[1].expanded = True
    session = ProjectSession(project=ProjectConfig(media_rows=rows))
    window = MainWindow.__new__(MainWindow)
    window.session = session
    window.module_two_selected_row_ids = {2}
    window.module_two_selection_anchor_row_id = 2
    window.module_two_row_list = _FakeRowList()
    window.module_two_scroll_area = _FakeScrollArea()
    window.module_two_content_viewport = _FakeViewport(current=(0.25, 0.75))
    window._refresh_module_three_appearance_selector = lambda: setattr(window, "_refreshed_module_three", True)
    window.on_project_change = lambda: setattr(window, "_project_changed", True)

    MainWindow._move_module_two_selected_rows_by(window, -1)

    assert [row.row_id for row in window.session.project.media_rows] == [1, 2, 3]
    assert window.module_two_row_list.reordered_rows == []
    assert window.module_two_row_list.selection_states == []
    assert window.module_two_scroll_area.refresh_count == 0
    assert window.module_two_content_viewport.moved_to is None
    assert window.__dict__.get("_refreshed_module_three", False) is False
    assert window.__dict__.get("_project_changed", False) is False


def test_media_row_list_set_expanded_row_only_touches_changed_widgets() -> None:
    rows = [default_media_row(1), default_media_row(2), default_media_row(3)]
    rows[0].expanded = True
    rows[1].expanded = False
    rows[2].expanded = False
    row_list = MediaRowList.__new__(MediaRowList)
    row_list.rows = rows
    row_list.row_widgets = [_FakeRowWidget(True), _FakeRowWidget(False), _FakeRowWidget(False)]
    row_list._display_expanded_row_id = None
    badge_calls: list[int] = []
    layout_calls: list[tuple[int, bool]] = []
    row_list.refresh_badge_numbers = lambda start_index=0: badge_calls.append(start_index)
    row_list.refresh_row_layouts = lambda start_index=0, refresh_badges=True: layout_calls.append((start_index, refresh_badges))

    MediaRowList.set_expanded_row(row_list, 2)

    assert rows[0].expanded is False
    assert rows[1].expanded is True
    assert rows[2].expanded is False
    assert row_list.row_widgets[0].set_expanded_calls == [False]
    assert row_list.row_widgets[1].set_expanded_calls == [True]
    assert row_list.row_widgets[2].set_expanded_calls == []
    assert badge_calls == [0]
    assert layout_calls == [(0, False)]


def test_media_row_list_reorder_rows_preserves_widget_row_ownership() -> None:
    first_row = default_media_row(1)
    second_row = default_media_row(2)
    row_list = MediaRowList.__new__(MediaRowList)
    row_list.rows = [first_row, second_row]
    first_widget = type("Widget", (), {"_row_id": 1, "_row": first_row})()
    second_widget = type("Widget", (), {"_row_id": 2, "_row": second_row})()
    row_list.row_widgets = [first_widget, second_widget]
    layout_calls: list[int] = []
    row_list.refresh_row_layouts = lambda start_index=0: layout_calls.append(start_index)

    MediaRowList.reorder_rows(row_list, [second_row, first_row])

    assert row_list.rows == [second_row, first_row]
    assert row_list.row_widgets == [second_widget, first_widget]
    assert second_widget._row is second_row
    assert first_widget._row is first_row
    assert layout_calls == [0]


def test_media_row_list_remove_rows_keeps_survivor_widget_ids_stable() -> None:
    first_row = default_media_row(1)
    second_row = default_media_row(2)
    third_row = default_media_row(3)
    row_list = MediaRowList.__new__(MediaRowList)
    row_list.rows = [first_row, second_row, third_row]
    first_widget = type("Widget", (), {"_row_id": 1, "_row": first_row, "destroy": lambda self: None})()
    second_widget = type("Widget", (), {"_row_id": 2, "_row": second_row, "destroy": lambda self: None})()
    third_widget = type("Widget", (), {"_row_id": 3, "_row": third_row, "destroy": lambda self: None})()
    row_list.row_widgets = [first_widget, second_widget, third_widget]
    row_list._row_drag_active = False
    row_list._row_drag_ids = []
    badge_calls: list[int] = []
    layout_calls: list[tuple[int, bool]] = []
    row_list.refresh_badge_numbers = lambda start_index=0: badge_calls.append(start_index)
    row_list.refresh_row_layouts = lambda start_index=0, refresh_badges=False: layout_calls.append((start_index, refresh_badges))

    MediaRowList.remove_rows(row_list, {2}, rows=[first_row, third_row])

    assert row_list.rows == [first_row, third_row]
    assert row_list.row_widgets == [first_widget, third_widget]
    assert first_widget._row_id == 1
    assert third_widget._row_id == 3
    assert badge_calls == [1]
    assert layout_calls == [(1, False)]


def test_media_row_shell_callback_wrappers_use_shell_row_identity() -> None:
    shell = MediaRowShell.__new__(MediaRowShell)
    shell._row_id = 7
    selected: list[int] = []
    removed: list[int] = []
    covers: list[int] = []
    names: list[tuple[int, str]] = []
    song_drops: list[tuple[int, list[str]]] = []
    shell._on_select = lambda row_id: selected.append(row_id)
    shell._on_remove_row = lambda row_id: removed.append(row_id)
    shell._on_cover_selected = lambda row_id: covers.append(row_id)
    shell._on_name_committed = lambda row_id, value: names.append((row_id, value))
    shell._on_song_drop = lambda row_id, paths: song_drops.append((row_id, list(paths)))

    shell._handle_select()
    shell._handle_remove_row()
    shell._handle_cover_selected()
    shell._handle_name_committed("Night Drive")
    shell._handle_song_drop(["A.ogg"])

    assert selected == [7]
    assert removed == [7]
    assert covers == [7]
    assert names == [(7, "Night Drive")]
    assert song_drops == [(7, ["A.ogg"])]


def test_media_row_shell_refresh_collapsed_details_does_not_rebind_background_handlers() -> None:
    row = default_media_row(4)
    shell = MediaRowShell.__new__(MediaRowShell)
    shell._row = row
    shell.collapsed_details = _FakeCollapsedDetails()
    bind_calls: list[object] = []
    shell._bind_widget_to_background_interactions = lambda widget: bind_calls.append(widget)

    MediaRowShell.refresh_collapsed_details(shell)
    MediaRowShell.refresh_collapsed_details(shell)

    assert shell.collapsed_details.refreshed_rows == [row, row]
    assert bind_calls == []


def test_select_module_two_media_cover_refreshes_row_cover_before_async_generation(monkeypatch, tmp_path) -> None:
    row = default_media_row(1)
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))
    row_widget = _FakeRowWidget(True, row_id=1)
    window = MainWindow.__new__(MainWindow)
    window.session = session
    image_dir = tmp_path / "art"
    image_dir.mkdir()
    selected_cover = image_dir / "new-cover.png"
    window.dialog_folder_memory = type("DialogFolderMemory", (), {"song_folder": "", "image_folder": str(image_dir)})()
    session_saves: list[tuple[str, str]] = []
    window._save_session_snapshot = lambda: session_saves.append(
        (window.dialog_folder_memory.song_folder, window.dialog_folder_memory.image_folder)
    )
    window.module_two_row_list = type("RowList", (), {"row_widgets": [row_widget]})()
    window._is_build_locked = lambda: False
    window._image_filetypes = lambda: [("Images", "*.png")]
    window._repair_active_generated_appearance_selections = lambda: []
    window._refresh_module_two_live_preview_for_row = lambda _row_id: None
    window._automatic_textures_enabled = lambda: True
    window._generate_module_three_from_cover = lambda row_id, **kwargs: setattr(window, "_generated_request", (row_id, kwargs.get("force_refresh", False)))
    window._refresh_module_three_appearance_selector = lambda: setattr(window, "_refreshed_module_three", True)
    window.on_project_change = lambda: setattr(window, "_project_changed", True)

    dialog_calls: list[str] = []

    def _askopenfilename(**kwargs):
        dialog_calls.append(kwargs["initialdir"])
        return str(selected_cover)

    monkeypatch.setattr("new_music_builder.ui.main_window.fd.askopenfilename", _askopenfilename)

    MainWindow._select_module_two_media_cover(window, 1)

    assert dialog_calls == [str(image_dir)]
    assert row.cover_path == str(selected_cover)
    assert row_widget.refreshed_covers == [str(selected_cover)]
    assert session_saves == [("", str(image_dir))]
    assert window.__dict__.get("_generated_request") == (1, True)
    assert window.__dict__.get("_refreshed_module_three", False) is False
    assert window.__dict__.get("_project_changed", False) is False


def test_safe_askopenfilename_retries_with_safer_initialdirs(monkeypatch, tmp_path) -> None:
    window = MainWindow.__new__(MainWindow)
    preferred_dir = tmp_path / "preferred"
    preferred_dir.mkdir()
    selected_path = preferred_dir / "cover.png"
    call_args: list[tuple[str | None, bool]] = []

    def _askopenfilename(**kwargs):
        call_args.append((kwargs.get("initialdir"), "parent" in kwargs))
        if len(call_args) == 1:
            raise tk.TclError("Nieokreslony blad.")
        return str(selected_path)

    monkeypatch.setattr("new_music_builder.ui.main_window.fd.askopenfilename", _askopenfilename)
    monkeypatch.setattr("new_music_builder.ui.main_window.messagebox.showerror", lambda *args, **kwargs: None)

    selected = MainWindow._safe_askopenfilename(
        window,
        title="Select Image",
        filetypes=[("Images", "*.png")],
        preferred_initialdir=str(preferred_dir),
    )

    assert selected == str(selected_path)
    assert call_args[0] == (str(preferred_dir), True)
    assert call_args[1] == (str(Path.home()), True)


def test_safe_askopenfilename_shows_friendly_error_when_all_retries_fail(monkeypatch, tmp_path) -> None:
    window = MainWindow.__new__(MainWindow)
    preferred_dir = tmp_path / "preferred"
    preferred_dir.mkdir()
    call_args: list[tuple[str | None, bool]] = []
    error_messages: list[tuple[str, str]] = []

    def _askopenfilename(**kwargs):
        call_args.append((kwargs.get("initialdir"), "parent" in kwargs))
        raise tk.TclError("Nieokreslony blad.")

    monkeypatch.setattr("new_music_builder.ui.main_window.fd.askopenfilename", _askopenfilename)
    monkeypatch.setattr(
        "new_music_builder.ui.main_window.messagebox.showerror",
        lambda title, message, **kwargs: error_messages.append((title, message)),
    )

    selected = MainWindow._safe_askopenfilename(
        window,
        title="Select Image",
        filetypes=[("Images", "*.png")],
        preferred_initialdir=str(preferred_dir),
    )

    assert selected == ""
    assert call_args == [
        (str(preferred_dir), True),
        (str(Path.home()), True),
        (None, True),
        (None, False),
    ]
    assert error_messages
    assert error_messages[0][0] == "Open File Dialog Failed"
    assert "Could not open the file browser." in error_messages[0][1]


def test_select_module_two_media_cover_recovers_after_initial_dialog_failure(monkeypatch, tmp_path) -> None:
    row = default_media_row(1)
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))
    row_widget = _FakeRowWidget(True, row_id=1)
    window = MainWindow.__new__(MainWindow)
    window.session = session
    preferred_dir = tmp_path / "art"
    preferred_dir.mkdir()
    selected_cover = preferred_dir / "new-cover.png"
    window.dialog_folder_memory = type("DialogFolderMemory", (), {"song_folder": "", "image_folder": str(preferred_dir)})()
    session_saves: list[tuple[str, str]] = []
    window._save_session_snapshot = lambda: session_saves.append(
        (window.dialog_folder_memory.song_folder, window.dialog_folder_memory.image_folder)
    )
    window.module_two_row_list = type("RowList", (), {"row_widgets": [row_widget]})()
    window._is_build_locked = lambda: False
    window._image_filetypes = lambda: [("Images", "*.png")]
    window._repair_active_generated_appearance_selections = lambda: []
    window._refresh_module_two_live_preview_for_row = lambda _row_id: None
    window._automatic_textures_enabled = lambda: True
    window._generate_module_three_from_cover = lambda row_id, **kwargs: setattr(window, "_generated_request", (row_id, kwargs.get("force_refresh", False)))
    window._refresh_module_three_appearance_selector = lambda: setattr(window, "_refreshed_module_three", True)
    window.on_project_change = lambda: setattr(window, "_project_changed", True)

    dialog_calls: list[tuple[str | None, bool]] = []

    def _askopenfilename(**kwargs):
        dialog_calls.append((kwargs.get("initialdir"), "parent" in kwargs))
        if len(dialog_calls) == 1:
            raise tk.TclError("Nieokreslony blad.")
        return str(selected_cover)

    monkeypatch.setattr("new_music_builder.ui.main_window.fd.askopenfilename", _askopenfilename)
    monkeypatch.setattr("new_music_builder.ui.main_window.messagebox.showerror", lambda *args, **kwargs: None)

    MainWindow._select_module_two_media_cover(window, 1)

    assert row.cover_path == str(selected_cover)
    assert row_widget.refreshed_covers == [str(selected_cover)]
    assert session_saves == [("", str(preferred_dir))]
    assert window.__dict__.get("_generated_request") == (1, True)
    assert dialog_calls[0] == (str(preferred_dir), True)
    assert dialog_calls[1] == (str(Path.home()), True)


def test_drop_module_two_media_cover_files_triggers_automatic_textures(monkeypatch, tmp_path) -> None:
    row = default_media_row(1)
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))
    row_widget = _FakeRowWidget(True, row_id=1)
    image_dir = tmp_path / "art"
    image_dir.mkdir()
    selected_cover = image_dir / "drop-cover.png"
    selected_cover.write_bytes(b"png")
    window = MainWindow.__new__(MainWindow)
    window.session = session
    window.dialog_folder_memory = type("DialogFolderMemory", (), {"song_folder": "", "image_folder": ""})()
    session_saves: list[tuple[str, str]] = []
    window._save_session_snapshot = lambda: session_saves.append(
        (window.dialog_folder_memory.song_folder, window.dialog_folder_memory.image_folder)
    )
    window.module_two_row_list = type("RowList", (), {"row_widgets": [row_widget]})()
    window._repair_active_generated_appearance_selections = lambda: []
    window._refresh_module_two_live_preview_for_row = lambda _row_id: None
    window._automatic_textures_enabled = lambda: True
    window._generate_module_three_from_cover = lambda row_id, **kwargs: setattr(window, "_generated_request", (row_id, kwargs.get("force_refresh", False)))
    window._refresh_module_three_appearance_selector = lambda: setattr(window, "_refreshed_module_three", True)
    window.on_project_change = lambda: setattr(window, "_project_changed", True)

    MainWindow._drop_module_two_media_cover_files(window, 1, [str(selected_cover)])

    assert row.cover_path == str(selected_cover)
    assert row_widget.refreshed_covers == [str(selected_cover)]
    assert session_saves == [("", str(image_dir))]
    assert window.__dict__.get("_generated_request") == (1, True)
    assert window.__dict__.get("_refreshed_module_three", False) is False
    assert window.__dict__.get("_project_changed", False) is False


def test_apply_module_two_media_cover_does_not_force_regeneration_when_automatic_textures_disabled(tmp_path) -> None:
    row = default_media_row(1)
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))
    row_widget = _FakeRowWidget(True, row_id=1)
    selected_cover = tmp_path / "same-cover.png"
    selected_cover.write_bytes(b"png")
    window = MainWindow.__new__(MainWindow)
    window.session = session
    window.dialog_folder_memory = type("DialogFolderMemory", (), {"song_folder": "", "image_folder": ""})()
    window._save_session_snapshot = lambda: setattr(window, "_saved", True)
    window.module_two_row_list = type("RowList", (), {"row_widgets": [row_widget]})()
    window._repair_active_generated_appearance_selections = lambda: []
    window._refresh_module_two_live_preview_for_row = lambda _row_id: None
    window._automatic_textures_enabled = lambda: False
    window._generate_module_three_from_cover = lambda row_id, **kwargs: setattr(window, "_generated_request", (row_id, kwargs.get("force_refresh", False)))
    window._refresh_module_three_appearance_selector = lambda: setattr(window, "_refreshed_module_three", True)
    window.on_project_change = lambda: setattr(window, "_project_changed", True)

    MainWindow._apply_module_two_media_cover(window, 1, str(selected_cover))

    assert window.__dict__.get("_generated_request") is None
    assert window.__dict__.get("_refreshed_module_three", False) is True
    assert window.__dict__.get("_project_changed", False) is True


def test_regenerate_loaded_project_cover_textures_respects_preferences_and_rows() -> None:
    first = default_media_row(1)
    first.cover_path = "C:/art/first.png"
    second = default_media_row(2)
    second.cover_path = ""
    third = default_media_row(3)
    third.cover_path = "C:/art/third.png"
    third.enabled_media = {"cassette": False, "vinyl": False, "cd": False}
    session = ProjectSession(project=ProjectConfig(media_rows=[first, second, third]))
    window = MainWindow.__new__(MainWindow)
    window.session = session
    requests: list[tuple[int, bool]] = []
    window._automatic_textures_enabled = lambda: True
    window._regenerate_textures_on_project_load_enabled = lambda: True
    window._generate_module_three_from_cover = lambda row_id, **kwargs: requests.append((row_id, kwargs.get("force_refresh", False)))

    MainWindow._regenerate_loaded_project_cover_textures(window)

    assert requests == [(1, True)]


def test_regenerate_loaded_project_cover_textures_skips_when_preference_disabled() -> None:
    row = default_media_row(1)
    row.cover_path = "C:/art/first.png"
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))
    window = MainWindow.__new__(MainWindow)
    window.session = session
    window._automatic_textures_enabled = lambda: True
    window._regenerate_textures_on_project_load_enabled = lambda: False
    window._generate_module_three_from_cover = lambda row_id, **kwargs: setattr(window, "_generated_request", (row_id, kwargs.get("force_refresh", False)))

    MainWindow._regenerate_loaded_project_cover_textures(window)

    assert window.__dict__.get("_generated_request") is None


def test_cover_generation_success_ignores_stale_tokens_and_applies_current_result(monkeypatch) -> None:
    row = default_media_row(1)
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))
    window = MainWindow.__new__(MainWindow)
    window.session = session
    window._module_three_cover_generation_tokens = {1: 7}
    ended_loading: list[tuple[int, int]] = []
    window.module_three_appearance_selector = type(
        "Selector",
        (),
        {"end_cover_generation_loading": lambda _self, row_id, token: ended_loading.append((row_id, token))},
    )()
    window._append_generated_cover_set_logs = lambda cover_path, result: setattr(window, "_logged_cover_path", cover_path)
    window._refresh_module_two_live_preview_for_row = lambda row_id: setattr(window, "_refreshed_row_id", row_id)
    window._refresh_module_three_appearance_selector = lambda: setattr(window, "_refreshed_module_three", True)
    window.on_project_change = lambda: setattr(window, "_project_changed", True)
    apply_calls: list[str] = []
    monkeypatch.setattr(
        "new_music_builder.ui.main_window.apply_generated_cover_set_result",
        lambda project, target_row, result: apply_calls.append(target_row.cover_path),
    )
    result = type("Result", (), {"outcomes": (), "source_name": "cover.png"})()

    MainWindow._finish_module_three_cover_generation_success(window, 1, 6, "C:/art/old.png", result)

    assert apply_calls == []
    assert window._module_three_cover_generation_tokens == {1: 7}

    MainWindow._finish_module_three_cover_generation_success(window, 1, 7, "C:/art/new.png", result)

    assert apply_calls == [row.cover_path]
    assert window._module_three_cover_generation_tokens == {}
    assert ended_loading == [(1, 7)]
    assert window.__dict__.get("_logged_cover_path") == "C:/art/new.png"
    assert window.__dict__.get("_refreshed_row_id") == 1
    assert window.__dict__.get("_refreshed_module_three", False) is True
    assert window.__dict__.get("_project_changed", False) is True


def test_cover_generation_error_clears_current_token_and_logs_failure() -> None:
    window = MainWindow.__new__(MainWindow)
    window._module_three_cover_generation_tokens = {4: 11}
    ended_loading: list[tuple[int, int]] = []
    window.module_three_appearance_selector = type(
        "Selector",
        (),
        {"end_cover_generation_loading": lambda _self, row_id, token: ended_loading.append((row_id, token))},
    )()
    window._append_generated_asset_failure_log = lambda cover_path, reason: setattr(window, "_failure", (cover_path, reason))

    MainWindow._finish_module_three_cover_generation_error(window, 4, 11, "C:/art/fail.png", "boom")

    assert window._module_three_cover_generation_tokens == {}
    assert ended_loading == [(4, 11)]
    assert window.__dict__.get("_failure") == ("C:/art/fail.png", "boom")


def test_generate_module_three_from_cover_marks_loading_before_worker_start(monkeypatch) -> None:
    row = default_media_row(3)
    row.cover_path = "C:/art/cover.png"
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))
    window = MainWindow.__new__(MainWindow)
    window.session = session
    window._is_build_locked = lambda: False
    window._module_three_cover_generation_seq = 0
    window._module_three_cover_generation_tokens = {}
    window.module_three_appearance_selector = type(
        "Selector",
        (),
        {"begin_cover_generation_loading": lambda _self, row_id, token: setattr(window, "_loading_begin", (row_id, token))},
    )()
    window._module_three_selected_path_for_row = lambda *_args, **_kwargs: ""

    class _ImmediateThread:
        def __init__(self, *, target, name, daemon) -> None:
            self.target = target
            self.name = name
            self.daemon = daemon

        def start(self) -> None:
            return None

    monkeypatch.setattr("new_music_builder.ui.main_window.deepcopy", lambda project: project)
    monkeypatch.setattr("new_music_builder.ui.main_window.threading.Thread", _ImmediateThread)

    MainWindow._generate_module_three_from_cover(window, 3)

    assert window._module_three_cover_generation_tokens == {3: 1}
    assert window.__dict__.get("_loading_begin") == (3, 1)


def test_generate_module_three_from_cover_force_refresh_preserves_cassette_and_case_donor_selection(monkeypatch) -> None:
    row = default_media_row(6)
    row.cover_path = "C:/art/cover.png"
    row.enabled_media["cassette"] = True
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))
    window = MainWindow.__new__(MainWindow)
    window.session = session
    window._is_build_locked = lambda: False
    window._module_three_cover_generation_seq = 0
    window._module_three_cover_generation_tokens = {}
    window.module_three_appearance_selector = type(
        "Selector",
        (),
        {"begin_cover_generation_loading": lambda _self, row_id, token: setattr(window, "_loading_begin", (row_id, token))},
    )()
    selected_requests: list[tuple[str, str]] = []
    selected_paths = {
        ("cassette", "inventory"): "C:/masks/cassette_inventory.png",
        ("cassette", "world"): "C:/masks/cassette_world.png",
        ("case", "inventory"): "C:/masks/case_inventory.png",
        ("case", "world"): "C:/masks/case_world.png",
    }
    window._module_three_selected_path_for_row = (
        lambda _row, kind, mode: selected_requests.append((kind, mode)) or selected_paths[(kind, mode)]
    )
    window._repair_active_generated_appearance_selections = lambda: []
    window._refresh_module_three_appearance_selector = lambda: setattr(window, "_selector_refreshed", True)

    class _ImmediateThread:
        def __init__(self, *, target, name, daemon) -> None:
            self.target = target
            self.name = name
            self.daemon = daemon

        def start(self) -> None:
            self.target()

    def _capture_generation(_project, _snapshot_row, **kwargs):
        window._captured_generation_kwargs = kwargs
        raise RuntimeError("stop after capture")

    monkeypatch.setattr("new_music_builder.ui.main_window.deepcopy", lambda project: project)
    monkeypatch.setattr("new_music_builder.ui.main_window.threading.Thread", _ImmediateThread)
    monkeypatch.setattr("new_music_builder.ui.main_window.remove_generated_records_for_cover_path", lambda *_args, **_kwargs: ["record"])
    monkeypatch.setattr("new_music_builder.ui.main_window.delete_generated_cover_set_files", lambda records: len(records))
    monkeypatch.setattr("new_music_builder.ui.main_window.generate_supported_cover_set_for_row", _capture_generation)

    window.after = lambda _delay, callback: callback()
    window._finish_module_three_cover_generation_error = (
        lambda row_id, token, cover_path, reason: setattr(window, "_generation_error", (row_id, token, cover_path, reason))
    )

    MainWindow._generate_module_three_from_cover(window, 6, force_refresh=True)

    assert selected_requests == [
        ("cassette", "inventory"),
        ("cassette", "world"),
        ("case", "inventory"),
        ("case", "world"),
    ]
    assert window._captured_generation_kwargs["force_refresh"] is True
    assert window._captured_generation_kwargs["cassette_donor_inventory_path"] == "C:/masks/cassette_inventory.png"
    assert window._captured_generation_kwargs["cassette_donor_world_path"] == "C:/masks/cassette_world.png"
    assert window._captured_generation_kwargs["case_donor_inventory_path"] == "C:/masks/case_inventory.png"
    assert window._captured_generation_kwargs["case_donor_world_path"] == "C:/masks/case_world.png"
    assert window.__dict__.get("_generation_error") == (6, 1, "C:/art/cover.png", "stop after capture")


def test_show_audio_settings_dialog_updates_project_and_persists_session(monkeypatch, tmp_path) -> None:
    project = ProjectConfig(sample_rate=44100, compression_quality=0.5, reencode_existing_ogg=True)
    session = ProjectSession(project=project)
    session.current_path = "C:/projects/test.nmbproj.json"
    window = MainWindow.__new__(MainWindow)
    window.session = session
    window._is_build_locked = lambda: False
    window._native_icon_path = lambda: tmp_path / "icon.ico"
    window._check_icon_path = lambda: tmp_path / "check.png"

    session_saves: list[tuple[int, float, bool, str]] = []
    window.session_store = type(
        "SessionStore",
        (),
        {
            "save": lambda _self, project, current_path, dialog_folder_memory=None, audio_preferences=None: session_saves.append(
                (
                    project.sample_rate,
                    project.compression_quality,
                    project.reencode_existing_ogg,
                    current_path,
                )
            )
        },
    )()
    window._commit_phase_one_project_state = lambda: None
    window._refresh_module_one_poster_preview = lambda: None
    window.on_project_change = lambda: MainWindow.on_project_change(window)
    window.module_two_row_list = type("RowList", (), {"refresh_collapsed_details": lambda _self: None})()
    window.build_summary = type("BuildSummary", (), {"refresh": lambda _self: None})()
    window.dialog_folder_memory = type("DialogFolderMemory", (), {"song_folder": "", "image_folder": ""})()
    window.audio_preferences = SessionAudioPreferences()

    class _FakeDialog:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def show(self):
            return (48000, 0.65, False)

    monkeypatch.setattr("new_music_builder.ui.main_window.AudioSettingsDialog", _FakeDialog)

    MainWindow._show_audio_settings_dialog(window)

    assert window.session.project.sample_rate == 48000
    assert window.session.project.compression_quality == 0.65
    assert window.session.project.reencode_existing_ogg is False
    assert window.audio_preferences.sample_rate == 48000
    assert window.audio_preferences.compression_quality == 0.65
    assert window.audio_preferences.reencode_existing_ogg is False
    assert session_saves == [(48000, 0.65, False, "C:/projects/test.nmbproj.json")]


def test_reset_project_to_defaults_preserves_master_audio_preferences() -> None:
    row = default_media_row(1)
    session = ProjectSession(project=ProjectConfig(media_rows=[row], sample_rate=22050, compression_quality=0.2, reencode_existing_ogg=True))
    window = MainWindow.__new__(MainWindow)
    window.session = session
    window.audio_preferences = SessionAudioPreferences(
        sample_rate=48000,
        compression_quality=0.65,
        reencode_existing_ogg=False,
    )
    window.session_store = type("SessionStoreStub", (), {"last_ogg_output_folder": ""})()
    window._legacy_mode_preference_enabled = False
    window._cancel_module_two_song_drag = lambda: None
    window._cancel_module_two_row_drag = lambda: None
    window._restore_unsaved_phase_two_default = lambda *args, **kwargs: None
    window._sync_phase_one_ui_from_project = lambda: None
    window._build_module_two_row_list = lambda: None
    window._refresh_preference_menu_states = lambda: None
    window._refresh_module_three_appearance_selector = lambda: None
    window.refresh_all = lambda: None
    window.on_project_change = lambda: None
    window.module_three_staged_custom_images = {}
    window.module_two_selected_row_ids = set()
    window.module_two_selection_anchor_row_id = None
    window.module_two_song_selected_indices = {}
    window.module_two_song_selection_anchor_indices = {}
    window._last_export_output_path = ''
    window.build_log = []
    window.preview_entries = []
    window.module_four_panel = type("ModuleFour", (), {"reset_current_run": lambda _self: None})()
    window.module_five_panel = type("ModuleFive", (), {"reset_preview_rows": lambda _self: None})()
    window.module_six_panel = type("ModuleSix", (), {"reset": lambda _self: None})()
    window.module_two_row_list = type("RowList", (), {"destroy": lambda _self: None})()

    MainWindow._reset_project_to_defaults(window)

    assert window.session.project.sample_rate == 48000
    assert window.session.project.compression_quality == 0.65
    assert window.session.project.reencode_existing_ogg is False


def test_reset_project_to_defaults_preserves_last_ogg_output_folder() -> None:
    row = default_media_row(1)
    session = ProjectSession(project=ProjectConfig(media_rows=[row], ogg_output_folder='C:/CurrentFolder'))
    window = MainWindow.__new__(MainWindow)
    window.session = session
    window.session_store = type("SessionStoreStub", (), {"last_ogg_output_folder": "C:/RememberedOGG"})()
    window._legacy_mode_preference_enabled = False
    window._cancel_module_two_song_drag = lambda: None
    window._cancel_module_two_row_drag = lambda: None
    window._apply_master_project_preferences = lambda: None
    window._restore_unsaved_phase_two_default = lambda *args, **kwargs: None
    window._sync_phase_one_ui_from_project = lambda: None
    window._build_module_two_row_list = lambda: None
    window.module_three_staged_custom_images = {}
    window.module_two_selected_row_ids = set()
    window.module_two_selection_anchor_row_id = None
    window.module_two_song_selected_indices = {}
    window.module_two_song_selection_anchor_indices = {}
    window._last_export_output_path = ''
    window.build_log = []
    window.preview_entries = []
    window._refresh_preference_menu_states = lambda: None
    window._refresh_module_three_appearance_selector = lambda: None
    window.refresh_all = lambda: None
    window.on_project_change = lambda: None
    window.module_four_panel = type("ModuleFour", (), {"reset_current_run": lambda _self: None})()
    window.module_five_panel = type("ModuleFive", (), {"reset_preview_rows": lambda _self: None})()
    window.module_six_panel = type("ModuleSix", (), {"reset": lambda _self: None})()
    window.module_two_row_list = type("RowList", (), {"destroy": lambda _self: None})()

    MainWindow._reset_project_to_defaults(window)

    assert window.session.project.ogg_output_folder == 'C:/RememberedOGG'


def test_select_workshop_poster_image_uses_image_lane_and_remembers_selection(monkeypatch, tmp_path) -> None:
    session = ProjectSession(project=ProjectConfig())
    window = MainWindow.__new__(MainWindow)
    window.session = session
    image_dir = tmp_path / "posters"
    image_dir.mkdir()
    selected_poster = (tmp_path / "new-posters")
    selected_poster.mkdir()
    selected_path = selected_poster / "poster.png"
    window.dialog_folder_memory = type("DialogFolderMemory", (), {"song_folder": "", "image_folder": str(image_dir)})()
    window._is_build_locked = lambda: False
    window._image_filetypes = lambda: [("Images", "*.png")]
    window._refresh_module_one_poster_preview = lambda: setattr(window, "_poster_refreshed", True)
    window._save_session_snapshot = lambda: setattr(window, "_saved_session", True)
    window.on_project_change = lambda: setattr(window, "_project_changed", True)

    dialog_calls: list[str] = []

    def _askopenfilename(**kwargs):
        dialog_calls.append(kwargs["initialdir"])
        return str(selected_path)

    monkeypatch.setattr("new_music_builder.ui.main_window.fd.askopenfilename", _askopenfilename)

    MainWindow._select_workshop_poster_image(window)

    assert dialog_calls == [str(image_dir)]
    assert window.session.project.workshop_poster_path == str(selected_path)
    assert window.dialog_folder_memory.image_folder == str(selected_poster)
    assert window.__dict__.get("_saved_session", False) is True
    assert window.__dict__.get("_poster_refreshed", False) is True
    assert window.__dict__.get("_project_changed", False) is True


def test_drop_workshop_poster_files_updates_project_and_image_lane(tmp_path) -> None:
    session = ProjectSession(project=ProjectConfig())
    selected_dir = tmp_path / "new-posters"
    selected_dir.mkdir()
    selected_path = selected_dir / "poster.png"
    selected_path.write_bytes(b"png")
    window = MainWindow.__new__(MainWindow)
    window.session = session
    window.dialog_folder_memory = type("DialogFolderMemory", (), {"song_folder": "", "image_folder": ""})()
    window._refresh_module_one_poster_preview = lambda: setattr(window, "_poster_refreshed", True)
    window.on_project_change = lambda: setattr(window, "_project_changed", True)
    window._save_session_snapshot = lambda: setattr(window, "_saved_session", True)

    MainWindow._drop_workshop_poster_files(window, [str(selected_path)])

    assert window.session.project.workshop_poster_path == str(selected_path)
    assert window.dialog_folder_memory.image_folder == str(selected_dir)
    assert window.__dict__.get("_saved_session", False) is True
    assert window.__dict__.get("_poster_refreshed", False) is True
    assert window.__dict__.get("_project_changed", False) is True


def test_pick_module_three_custom_image_uses_image_lane_and_remembers_selection(monkeypatch, tmp_path) -> None:
    row = default_media_row(1)
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))
    window = MainWindow.__new__(MainWindow)
    window.session = session
    image_dir = tmp_path / "custom-art"
    image_dir.mkdir()
    selected_dir = tmp_path / "picked-art"
    selected_dir.mkdir()
    selected_path = selected_dir / "world.png"
    window.dialog_folder_memory = type("DialogFolderMemory", (), {"song_folder": "", "image_folder": str(image_dir)})()
    window._image_filetypes = lambda: [("Images", "*.png")]
    window._active_module_three_row = lambda: row
    window._refresh_module_three_appearance_selector = lambda: setattr(window, "_appearance_refreshed", True)
    window.module_three_staged_custom_images = {}
    window._save_session_snapshot = lambda: setattr(window, "_saved_session", True)

    dialog_calls: list[str] = []

    def _askopenfilename(**kwargs):
        dialog_calls.append(kwargs["initialdir"])
        return str(selected_path)

    monkeypatch.setattr("new_music_builder.ui.main_window.fd.askopenfilename", _askopenfilename)

    MainWindow._pick_module_three_custom_image(window, "cassette", "world_full")

    assert dialog_calls == [str(image_dir)]
    assert window.module_three_staged_custom_images["cassette"]["world_full"] == str(selected_path)
    assert window.dialog_folder_memory.image_folder == str(selected_dir)
    assert window.__dict__.get("_saved_session", False) is True
    assert window.__dict__.get("_appearance_refreshed", False) is True


def test_add_module_two_songs_uses_song_lane_and_remembers_selection(monkeypatch, tmp_path) -> None:
    row = default_media_row(1)
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))
    window = MainWindow.__new__(MainWindow)
    window.session = session
    song_dir = tmp_path / "music"
    song_dir.mkdir()
    selected_dir = tmp_path / "mixes"
    selected_dir.mkdir()
    first_song = selected_dir / "a.ogg"
    second_song = selected_dir / "b.ogg"
    window.dialog_folder_memory = type("DialogFolderMemory", (), {"song_folder": str(song_dir), "image_folder": ""})()
    window._is_build_locked = lambda: False
    window._audio_filetypes = lambda: [("Audio", "*.ogg")]
    window._save_session_snapshot = lambda: setattr(window, "_saved_session", True)
    added_paths: list[tuple[int, list[str]]] = []
    window._add_module_two_songs_from_paths = lambda row_id, paths: added_paths.append((row_id, list(paths)))

    dialog_calls: list[str] = []

    def _askopenfilenames(**kwargs):
        dialog_calls.append(kwargs["initialdir"])
        return (str(first_song), str(second_song))

    monkeypatch.setattr("new_music_builder.ui.main_window.fd.askopenfilenames", _askopenfilenames)

    MainWindow._add_module_two_songs(window, 1)

    assert dialog_calls == [str(song_dir)]
    assert window.dialog_folder_memory.song_folder == str(selected_dir)
    assert window.__dict__.get("_saved_session", False) is True
    assert added_paths == [(1, [str(first_song), str(second_song)])]


def test_pick_module_three_custom_image_prefers_global_image_lane_over_existing_slot_path(monkeypatch, tmp_path) -> None:
    row = default_media_row(1)
    existing_dir = tmp_path / "existing-slot"
    existing_dir.mkdir()
    existing_path = existing_dir / "world.png"
    existing_path.write_bytes(b"png")
    row.appearances["cassette"].world_full = str(existing_path)
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))
    window = MainWindow.__new__(MainWindow)
    window.session = session
    image_dir = tmp_path / "remembered-images"
    image_dir.mkdir()
    selected_dir = tmp_path / "picked-art"
    selected_dir.mkdir()
    selected_path = selected_dir / "replacement.png"
    window.dialog_folder_memory = type("DialogFolderMemory", (), {"song_folder": "", "image_folder": str(image_dir)})()
    window._image_filetypes = lambda: [("Images", "*.png")]
    window._active_module_three_row = lambda: row
    window._refresh_module_three_appearance_selector = lambda: setattr(window, "_appearance_refreshed", True)
    window.module_three_staged_custom_images = {}
    window._save_session_snapshot = lambda: setattr(window, "_saved_session", True)

    dialog_calls: list[str] = []

    def _askopenfilename(**kwargs):
        dialog_calls.append(kwargs["initialdir"])
        return str(selected_path)

    monkeypatch.setattr("new_music_builder.ui.main_window.fd.askopenfilename", _askopenfilename)

    MainWindow._pick_module_three_custom_image(window, "cassette", "world_full")

    assert dialog_calls == [str(image_dir)]
    assert window.module_three_staged_custom_images["cassette"]["world_full"] == str(selected_path)
    assert window.dialog_folder_memory.image_folder == str(selected_dir)
    assert window.__dict__.get("_saved_session", False) is True
    assert window.__dict__.get("_appearance_refreshed", False) is True


def test_can_accept_image_drop_requires_supported_existing_file(tmp_path) -> None:
    image_path = tmp_path / "cover.png"
    image_path.write_bytes(b"png")
    text_path = tmp_path / "cover.txt"
    text_path.write_bytes(b"text")
    window = MainWindow.__new__(MainWindow)

    assert MainWindow._can_accept_image_drop(window, [str(image_path)]) is True
    assert MainWindow._can_accept_image_drop(window, [str(text_path)]) is False
    assert MainWindow._can_accept_image_drop(window, [str(tmp_path / "missing.png")]) is False
