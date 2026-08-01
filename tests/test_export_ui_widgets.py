from __future__ import annotations

from types import SimpleNamespace

from new_music_builder.domain.models import ExportLogLine, GeneratedPreviewCell, GeneratedPreviewRow
from new_music_builder.ui import spec
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

    def set_groups(self, groups) -> None:
        self.set_calls.append(groups)


class _FakeScroll:
    def __init__(self, *, near_bottom: bool = True, offset: int = 0) -> None:
        self.near_bottom = near_bottom
        self.offset = offset
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
        return self.offset


class _FakePreviewRowWidget:
    def __init__(self) -> None:
        self.row: GeneratedPreviewRow | None = None
        self.animate_dual_phase: bool | None = None
        self.place_calls: list[dict[str, int]] = []
        self.place_forget_calls = 0
        self.destroy_calls = 0
        self.clear_calls = 0

    def set_row(self, row: GeneratedPreviewRow, *, animate_dual_phase: bool = True) -> None:
        self.row = row
        self.animate_dual_phase = animate_dual_phase

    def place(self, **kwargs) -> None:
        self.place_calls.append(kwargs)

    def place_forget(self) -> None:
        self.place_forget_calls += 1

    def clear_row(self) -> None:
        self.clear_calls += 1
        self.row = None

    def destroy(self) -> None:
        self.destroy_calls += 1


def _preview_row(label: str) -> GeneratedPreviewRow:
    cell = GeneratedPreviewCell(label_text=label, section_text="Inventory", song_count=1, duration_text="00:01:00")
    return GeneratedPreviewRow(row_id=1, side="A", inventory_cell=cell, world_cell=cell)


def test_module_four_panel_append_log_line_updates_incrementally() -> None:
    panel = ModuleFourPanel.__new__(ModuleFourPanel)
    panel.state = SimpleNamespace(current_run_log_lines=[])
    panel.log_view = _FakeLogView()
    panel.log_scroll = _FakeScroll(near_bottom=True)
    panel.queue_table = _FakeQueueTable()
    panel.queue_scroll = _FakeScroll()

    line = ExportLogLine(timestamp="12:00:00", subject_text="Exported", color_role="done")

    ModuleFourPanel.append_log_line(panel, line)

    assert len(panel.state.current_run_log_lines) == 1
    assert panel.log_view.append_calls == [panel.state.current_run_log_lines[0]]
    assert panel.log_scroll.scroll_to_bottom_calls == 1
    assert panel.log_scroll.refresh_calls == 1


def test_module_four_panel_update_active_log_line_updates_incrementally() -> None:
    existing = ExportLogLine(timestamp="12:00:00", subject_text="Working", color_role="converting")
    panel = ModuleFourPanel.__new__(ModuleFourPanel)
    panel.state = SimpleNamespace(current_run_log_lines=[existing])
    panel.log_view = _FakeLogView()
    panel.log_scroll = _FakeScroll(near_bottom=False)
    panel.queue_table = _FakeQueueTable()
    panel.queue_scroll = _FakeScroll()

    updated = ExportLogLine(timestamp="12:00:01", subject_text="Done", color_role="done")

    ModuleFourPanel.update_active_log_line(panel, updated)

    assert panel.state.current_run_log_lines == [panel.log_view.update_calls[0]]
    assert panel.log_scroll.scroll_to_bottom_calls == 0
    assert panel.log_scroll.refresh_calls == 1


def test_module_five_panel_flush_pending_rows_batches_and_virtualizes() -> None:
    panel = ModuleFivePanel.__new__(ModuleFivePanel)
    panel._preview_rows = []
    panel._pending_preview_rows = [_preview_row("First"), _preview_row("Second"), _preview_row("Third")]
    panel._row_widgets = [_FakePreviewRowWidget(), _FakePreviewRowWidget(), _FakePreviewRowWidget()]
    panel._flush_after_id = None
    panel._export_active = True
    panel.content_scroll = _FakeScroll(near_bottom=True, offset=0)
    panel._cancel_pending_flush = lambda: None
    panel._ensure_row_widget_pool = lambda: None

    ModuleFivePanel.flush_pending_preview_rows(panel)

    assert [row.inventory_cell.label_text for row in panel._preview_rows] == ["First", "Second", "Third"]
    assert panel._pending_preview_rows == []
    assert panel.content_scroll.virtual_heights[-1] == panel._logical_content_height()
    assert panel.content_scroll.scroll_to_bottom_calls == 1
    assert [widget.row.inventory_cell.label_text for widget in panel._row_widgets] == ["First", "Second", "Third"]
    assert all(widget.animate_dual_phase is False for widget in panel._row_widgets)


def test_module_five_panel_refresh_visible_rows_maps_scroll_window() -> None:
    panel = ModuleFivePanel.__new__(ModuleFivePanel)
    panel._preview_rows = [_preview_row(f"Row {index}") for index in range(10)]
    panel._pending_preview_rows = []
    panel._row_widgets = [_FakePreviewRowWidget(), _FakePreviewRowWidget(), _FakePreviewRowWidget()]
    panel._flush_after_id = None
    panel._export_active = False
    row_height = spec.PHASE_THREE_MODULE_FIVE_ROW_SIZE[1]
    panel.content_scroll = _FakeScroll(offset=row_height * 4)
    panel._ensure_row_widget_pool = lambda: None

    ModuleFivePanel._refresh_visible_rows(panel)

    assert [widget.row.inventory_cell.label_text for widget in panel._row_widgets] == ["Row 4", "Row 5", "Row 6"]
    assert all(widget.animate_dual_phase is True for widget in panel._row_widgets)


def test_module_five_panel_refresh_visible_rows_clears_hidden_widgets() -> None:
    panel = ModuleFivePanel.__new__(ModuleFivePanel)
    panel._preview_rows = [_preview_row("Only Row")]
    panel._pending_preview_rows = []
    panel._row_widgets = [_FakePreviewRowWidget(), _FakePreviewRowWidget()]
    panel._flush_after_id = None
    panel._export_active = False
    panel.content_scroll = _FakeScroll(offset=0)
    panel._ensure_row_widget_pool = lambda: None

    ModuleFivePanel._refresh_visible_rows(panel)

    assert panel._row_widgets[0].row is not None
    assert panel._row_widgets[1].row is None
    assert panel._row_widgets[1].clear_calls == 1
    assert panel._row_widgets[1].place_forget_calls == 1


def test_module_five_panel_set_export_active_flushes_pending_rows_when_deactivating() -> None:
    panel = ModuleFivePanel.__new__(ModuleFivePanel)
    panel._preview_rows = []
    panel._pending_preview_rows = [_preview_row("Queued")]
    panel._row_widgets = [_FakePreviewRowWidget()]
    panel._flush_after_id = None
    panel._export_active = True
    panel.content_scroll = _FakeScroll()
    panel._cancel_pending_flush = lambda: None
    panel._ensure_row_widget_pool = lambda: None

    ModuleFivePanel.set_export_active(panel, False)

    assert panel._export_active is False
    assert [row.inventory_cell.label_text for row in panel._preview_rows] == ["Queued"]
    assert panel._pending_preview_rows == []
