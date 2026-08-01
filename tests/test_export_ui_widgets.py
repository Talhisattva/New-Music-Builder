from __future__ import annotations

from types import SimpleNamespace

from new_music_builder.domain.models import ExportLogLine, GeneratedPreviewCell, GeneratedPreviewRow
from new_music_builder.ui.widgets.module_five_panel import ModuleFivePanel
from new_music_builder.ui.widgets.module_four_panel import ModuleFourPanel


class _FakeLogView:
    def __init__(self) -> None:
        self.set_calls: list[list[ExportLogLine]] = []
        self.append_calls: list[ExportLogLine] = []
        self.update_calls: list[ExportLogLine] = []

    def set_lines(self, lines: list[ExportLogLine]) -> None:
        self.set_calls.append(list(lines))

    def append_line(self, line: ExportLogLine) -> None:
        self.append_calls.append(line)

    def update_active_line(self, line: ExportLogLine) -> None:
        self.update_calls.append(line)


class _FakeQueueTable:
    def __init__(self) -> None:
        self.set_calls: list[object] = []
        self.append_calls: list[object] = []
        self.progress_calls: list[tuple[int, str, int, int, str, str]] = []
        self.scroll_offsets: list[int] = []

    def set_groups(self, groups) -> None:
        self.set_calls.append(groups)

    def append_group(self, group) -> None:
        self.append_calls.append(group)

    def update_song_progress(self, row_id: int, side: str, song_index: int, percent: int, status: str, size_label: str) -> None:
        self.progress_calls.append((row_id, side, song_index, percent, status, size_label))

    def logical_content_height(self) -> int:
        return 123

    def set_scroll_offset(self, offset: int) -> None:
        self.scroll_offsets.append(offset)


class _FakeScroll:
    def __init__(self, *, near_bottom: bool = True) -> None:
        self.near_bottom = near_bottom
        self.scroll_to_bottom_calls = 0
        self.refresh_calls = 0
        self.virtual_heights: list[int] = []

    def is_near_bottom(self, *, threshold_px: int = 24) -> bool:
        return self.near_bottom

    def scroll_to_bottom(self) -> None:
        self.scroll_to_bottom_calls += 1

    def refresh_scroll_region(self) -> None:
        self.refresh_calls += 1

    def set_virtual_content_height(self, height: int) -> None:
        self.virtual_heights.append(height)

    def current_scroll_offset_pixels(self) -> int:
        return 0


class _FakePreviewRowWidget:
    def __init__(self, _parent) -> None:
        self.row = None
        self.pack_calls = 0
        self.destroy_calls = 0

    def set_row(self, row: GeneratedPreviewRow) -> None:
        self.row = row

    def pack(self, *, anchor: str) -> None:
        self.pack_calls += 1

    def destroy(self) -> None:
        self.destroy_calls += 1


def _preview_row(label: str) -> GeneratedPreviewRow:
    cell = GeneratedPreviewCell(label_text=label, section_text="Inventory", song_count=1, duration_text="00:01:00")
    return GeneratedPreviewRow(row_id=1, side="A", inventory_cell=cell, world_cell=cell)


def test_module_four_panel_append_log_line_updates_view_immediately() -> None:
    panel = ModuleFourPanel.__new__(ModuleFourPanel)
    panel.state = SimpleNamespace(current_run_log_lines=[])
    panel.log_view = _FakeLogView()
    panel.log_scroll = _FakeScroll(near_bottom=True)
    panel.queue_table = _FakeQueueTable()
    panel.queue_scroll = _FakeScroll()
    panel._sync_queue_scroll_offset = lambda: None

    line = ExportLogLine(timestamp="12:00:00", subject_text="Exported", color_role="done")

    ModuleFourPanel.append_log_line(panel, line)

    assert len(panel.state.current_run_log_lines) == 1
    assert panel.log_view.append_calls == [panel.state.current_run_log_lines[0]]
    assert panel.log_scroll.scroll_to_bottom_calls == 1
    assert panel.log_scroll.refresh_calls == 1


def test_module_four_panel_update_active_log_line_updates_view_immediately() -> None:
    existing = ExportLogLine(timestamp="12:00:00", subject_text="Working", color_role="converting")
    panel = ModuleFourPanel.__new__(ModuleFourPanel)
    panel.state = SimpleNamespace(current_run_log_lines=[existing])
    panel.log_view = _FakeLogView()
    panel.log_scroll = _FakeScroll(near_bottom=False)
    panel.queue_table = _FakeQueueTable()
    panel.queue_scroll = _FakeScroll()
    panel._sync_queue_scroll_offset = lambda: None

    updated = ExportLogLine(timestamp="12:00:01", subject_text="Done", color_role="done")

    ModuleFourPanel.update_active_log_line(panel, updated)

    assert panel.state.current_run_log_lines == [panel.log_view.update_calls[0]]
    assert panel.log_scroll.scroll_to_bottom_calls == 0
    assert panel.log_scroll.refresh_calls == 1


def test_module_five_panel_append_preview_row_preserves_accumulated_widgets(monkeypatch) -> None:
    created_widgets: list[_FakePreviewRowWidget] = []

    def _fake_preview_row_widget(parent) -> _FakePreviewRowWidget:
        widget = _FakePreviewRowWidget(parent)
        created_widgets.append(widget)
        return widget

    monkeypatch.setattr("new_music_builder.ui.widgets.module_five_panel.ModuleFivePreviewRow", _fake_preview_row_widget)

    panel = ModuleFivePanel.__new__(ModuleFivePanel)
    panel._preview_rows = []
    panel._row_widgets = []
    panel.content_scroll = _FakeScroll(near_bottom=True)
    panel.content_scroll.content_frame = object()

    first = _preview_row("First")
    second = _preview_row("Second")

    ModuleFivePanel.append_preview_row(panel, first)
    ModuleFivePanel.append_preview_row(panel, second)

    assert [row.inventory_cell.label_text for row in panel._preview_rows] == ["First", "Second"]
    assert len(panel._row_widgets) == 2
    assert [widget.row.inventory_cell.label_text for widget in created_widgets] == ["First", "Second"]
    assert panel.content_scroll.scroll_to_bottom_calls == 2
    assert panel.content_scroll.refresh_calls == 2


def test_module_five_panel_set_preview_rows_rebuilds_widget_list(monkeypatch) -> None:
    created_widgets: list[_FakePreviewRowWidget] = []

    def _fake_preview_row_widget(parent) -> _FakePreviewRowWidget:
        widget = _FakePreviewRowWidget(parent)
        created_widgets.append(widget)
        return widget

    monkeypatch.setattr("new_music_builder.ui.widgets.module_five_panel.ModuleFivePreviewRow", _fake_preview_row_widget)

    stale_widget = _FakePreviewRowWidget(None)
    panel = ModuleFivePanel.__new__(ModuleFivePanel)
    panel._preview_rows = []
    panel._row_widgets = [stale_widget]
    panel.content_scroll = _FakeScroll(near_bottom=False)
    panel.content_scroll.content_frame = object()

    ModuleFivePanel.set_preview_rows(panel, [_preview_row("Latest")])

    assert stale_widget.destroy_calls == 1
    assert len(panel._row_widgets) == 1
    assert panel._row_widgets[0].row.inventory_cell.label_text == "Latest"
    assert panel.content_scroll.scroll_to_bottom_calls == 1
