from __future__ import annotations

from dataclasses import dataclass

from new_music_builder.domain.models import ProjectConfig, default_media_row
from new_music_builder.services.project_session import ProjectSession
from new_music_builder.ui.main_window import MainWindow
from new_music_builder.ui.widgets.media_row_list import MediaRowList


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

    def append_row(self, row) -> None:
        self.appended_row_ids.append(row.row_id)

    def set_expanded_row(self, row_id: int | None) -> None:
        self.expanded_row_ids.append(row_id)

    def remove_rows(self, row_ids: set[int], rows=None) -> None:
        self.removed_row_ids.append(set(row_ids))
        self.remove_rows_payloads.append([row.row_id for row in (rows or [])])

    def set_selection_state(self, row_ids: set[int]) -> None:
        self.selection_states.append(set(row_ids))


class _FakeRowWidget:
    def __init__(self, expanded: bool) -> None:
        self._expanded = expanded
        self.set_expanded_calls: list[bool] = []

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self.set_expanded_calls.append(expanded)


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


def test_remove_module_two_media_row_set_remaps_selection_and_updates_remaining_rows() -> None:
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

    assert [row.row_id for row in window.session.project.media_rows] == [1, 2]
    assert window.module_two_selected_row_ids == {1, 2}
    assert window.module_two_selection_anchor_row_id == 2
    assert window.module_two_song_selected_indices == {(1, "A"): {0}, (2, "B"): {1}}
    assert window.module_two_song_selection_anchor_indices == {(1, "A"): 0, (2, "B"): 1}
    assert window.module_two_row_list.removed_row_ids == [{1}]
    assert window.module_two_row_list.remove_rows_payloads == [[1, 2]]
    assert window.module_two_row_list.selection_states == [{1, 2}]
    assert window.module_two_content_viewport.moved_to == [0.25]
    assert getattr(window, "_refreshed_module_three", False) is True
    assert getattr(window, "_project_changed", False) is True


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
