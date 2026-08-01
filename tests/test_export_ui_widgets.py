from __future__ import annotations

from types import SimpleNamespace

from new_music_builder.domain.models import ConversionSongProgress, ExportLogLine, GeneratedPreviewCell, GeneratedPreviewRow
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.module_five_panel import ModuleFivePanel
from new_music_builder.ui.widgets.module_four_panel import ModuleFourPanel
from new_music_builder.ui.widgets.scroll_area import ScrollViewport


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
        self.scroll_offsets: list[int] = []

    def set_groups(self, groups) -> None:
        self.set_calls.append(groups)

    def total_content_height(self) -> int:
        return 1234

    def set_scroll_offset(self, offset: int) -> None:
        self.scroll_offsets.append(offset)

    def row_index_for_group_song(self, group_index: int, song_index: int) -> int | None:
        if group_index < 0 or song_index < 0:
            return None
        return song_index

    def row_bounds_for_index(self, row_index: int) -> tuple[int, int] | None:
        top = spec.PHASE_THREE_MODULE_FOUR_QUEUE_HEADER_HEIGHT + (row_index * spec.PHASE_THREE_MODULE_FOUR_QUEUE_ROW_HEIGHT)
        return (top, top + spec.PHASE_THREE_MODULE_FOUR_QUEUE_ROW_HEIGHT)


class _FakeScroll:
    def __init__(self, *, near_bottom: bool = True, offset: int = 0) -> None:
        self.near_bottom = near_bottom
        self.offset = offset
        self.scroll_to_bottom_calls = 0
        self.scroll_to_offset_calls: list[int] = []
        self.refresh_calls = 0
        self.virtual_heights: list[int] = []
        self.view_changed_callbacks: list[object] = []

    def is_near_bottom(self, *, threshold_px: int = 24) -> bool:
        return self.near_bottom

    def scroll_to_bottom(self) -> None:
        self.scroll_to_bottom_calls += 1

    def scroll_to_offset_pixels(self, offset: int) -> None:
        self.offset = offset
        self.scroll_to_offset_calls.append(offset)

    def refresh_scroll_region(self) -> None:
        self.refresh_calls += 1

    def set_virtual_content_height(self, height: int) -> None:
        self.virtual_heights.append(height)

    def current_scroll_offset_pixels(self) -> int:
        return self.offset

    def set_view_changed_callback(self, callback) -> None:
        self.view_changed_callbacks.append(callback)


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


class _FakeCanvas:
    def __init__(self) -> None:
        self.configure_calls: list[dict[str, object]] = []
        self.itemconfigure_calls: list[tuple[object, dict[str, object]]] = []
        self.yview_moveto_calls: list[float] = []

    def configure(self, **kwargs) -> None:
        self.configure_calls.append(kwargs)

    def itemconfigure(self, item_id, **kwargs) -> None:
        self.itemconfigure_calls.append((item_id, kwargs))

    def yview_moveto(self, fraction: float) -> None:
        self.yview_moveto_calls.append(fraction)

    def yview(self) -> tuple[float, float]:
        return (0.0, 1.0)


class _FakeFrame:
    def __init__(self, *, reqheight: int = 0) -> None:
        self.configure_calls: list[dict[str, object]] = []
        self.reqheight = reqheight

    def configure(self, **kwargs) -> None:
        self.configure_calls.append(kwargs)

    def winfo_reqheight(self) -> int:
        return self.reqheight


class _FakeScrollbar:
    def __init__(self) -> None:
        self.metrics_calls: list[dict[str, int]] = []
        self.view_calls: list[tuple[float, float]] = []

    def set_metrics(self, *, content_height: int, viewport_height: int) -> None:
        self.metrics_calls.append(
            {
                "content_height": content_height,
                "viewport_height": viewport_height,
            }
        )

    def set_view(self, first: float, last: float) -> None:
        self.view_calls.append((first, last))


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


def test_module_four_panel_ensure_song_backfills_passthrough_rows() -> None:
    panel = ModuleFourPanel.__new__(ModuleFourPanel)
    panel.state = SimpleNamespace(
        ordered_groups=[SimpleNamespace(row_id=7, side="A", songs=[])],
        active_group_index=None,
        active_song_index=None,
        current_run_log_lines=[],
    )
    panel.queue_table = _FakeQueueTable()
    panel.queue_scroll = _FakeScroll()
    panel._schedule_queue_refresh = lambda: setattr(panel, "_queue_refresh_scheduled", True)

    ModuleFourPanel.ensure_song(
        panel,
        7,
        "A",
        0,
        ConversionSongProgress(song_label="Alpha Side", queue_index=1, percent=100, status="done", size_label="1.0 MB"),
    )

    assert len(panel.state.ordered_groups[0].songs) == 1
    song = panel.state.ordered_groups[0].songs[0]
    assert song.song_label == "Alpha Side"
    assert song.percent == 100
    assert song.status == "done"
    assert getattr(panel, "_queue_refresh_scheduled", False) is True


def test_module_four_panel_activate_song_updates_existing_planned_row_without_duplication() -> None:
    planned = ConversionSongProgress(song_label="Queued", queue_index=1, percent=0, status="queued", size_label="")
    panel = ModuleFourPanel.__new__(ModuleFourPanel)
    panel.state = SimpleNamespace(
        ordered_groups=[SimpleNamespace(row_id=7, side="A", songs=[planned])],
        active_group_index=None,
        active_song_index=None,
        current_run_log_lines=[],
    )
    panel.queue_table = _FakeQueueTable()
    panel.queue_scroll = _FakeScroll()
    panel._schedule_queue_refresh = lambda: setattr(panel, "_queue_refresh_scheduled", True)

    ModuleFourPanel.activate_song(
        panel,
        7,
        "A",
        0,
        ConversionSongProgress(song_label="Alpha Side", queue_index=1, percent=0, status="converting", size_label=""),
    )

    assert len(panel.state.ordered_groups[0].songs) == 1
    song = panel.state.ordered_groups[0].songs[0]
    assert song.song_label == "Alpha Side"
    assert song.status == "converting"
    assert getattr(panel, "_queue_refresh_scheduled", False) is True


def test_module_four_panel_settle_queue_state_clears_stale_converting_rows() -> None:
    panel = ModuleFourPanel.__new__(ModuleFourPanel)
    panel.state = SimpleNamespace(
        ordered_groups=[
            SimpleNamespace(
                row_id=7,
                side="A",
                songs=[
                    ConversionSongProgress(song_label="Done", queue_index=1, percent=100, status="done", size_label="1 MB"),
                    ConversionSongProgress(song_label="Stale", queue_index=2, percent=0, status="converting", size_label=""),
                ],
            )
        ],
        active_group_index=0,
        active_song_index=1,
        current_run_log_lines=[],
    )
    panel.queue_table = _FakeQueueTable()
    panel.queue_scroll = _FakeScroll()
    panel._schedule_queue_refresh = lambda: setattr(panel, "_queue_refresh_scheduled", True)

    ModuleFourPanel.settle_queue_state(panel)

    songs = panel.state.ordered_groups[0].songs
    assert songs[0].status == "done"
    assert songs[1].status == "queued"
    assert songs[1].percent == 0
    assert getattr(panel, "_queue_refresh_scheduled", False) is True


def test_module_four_panel_queue_view_updates_virtual_height_and_offset() -> None:
    panel = ModuleFourPanel.__new__(ModuleFourPanel)
    panel.state = SimpleNamespace(ordered_groups=[], current_run_log_lines=[], active_group_index=None, active_song_index=None)
    panel.queue_table = _FakeQueueTable()
    panel.queue_scroll = _FakeScroll(offset=96)
    panel._queue_follow_active = False
    panel._queue_internal_scroll_update = False

    ModuleFourPanel._refresh_queue_view(panel)
    ModuleFourPanel._handle_queue_view_changed(panel, 0.0, 1.0)

    assert panel.queue_scroll.virtual_heights[-1] == 1234
    assert panel.queue_scroll.refresh_calls >= 1
    assert panel.queue_table.scroll_offsets[-1] == 96


def test_module_four_panel_refresh_queue_view_follows_active_song() -> None:
    panel = ModuleFourPanel.__new__(ModuleFourPanel)
    panel.state = SimpleNamespace(
        ordered_groups=[SimpleNamespace(songs=[object(), object(), object(), object(), object(), object(), object()])],
        current_run_log_lines=[],
        active_group_index=0,
        active_song_index=6,
    )
    panel.queue_table = _FakeQueueTable()
    panel.queue_scroll = _FakeScroll(offset=0)
    panel._queue_follow_active = True
    panel._queue_internal_scroll_update = False

    ModuleFourPanel._refresh_queue_view(panel)

    assert panel.queue_scroll.virtual_heights[-1] == 1234
    assert panel.queue_scroll.scroll_to_offset_calls


def test_module_four_panel_handle_queue_view_changed_disables_follow_when_active_row_leaves_view() -> None:
    panel = ModuleFourPanel.__new__(ModuleFourPanel)
    panel.state = SimpleNamespace(
        ordered_groups=[SimpleNamespace(songs=[object(), object(), object(), object(), object(), object(), object()])],
        current_run_log_lines=[],
        active_group_index=0,
        active_song_index=6,
    )
    panel.queue_table = _FakeQueueTable()
    panel.queue_scroll = _FakeScroll(offset=0)
    panel._queue_follow_active = True
    panel._queue_internal_scroll_update = False

    ModuleFourPanel._handle_queue_view_changed(panel, 0.0, 1.0)

    assert panel._queue_follow_active is False


def test_module_five_panel_flush_pending_rows_batches_and_virtualizes() -> None:
    panel = ModuleFivePanel.__new__(ModuleFivePanel)
    panel._preview_rows = []
    panel._pending_preview_rows = []
    panel._row_widgets = [_FakePreviewRowWidget(), _FakePreviewRowWidget(), _FakePreviewRowWidget()]
    panel._mode = ModuleFivePanel._MODE_LIVE_LATEST
    panel._export_active = True
    panel.content_scroll = _FakeScroll(near_bottom=True, offset=0)
    panel._ensure_row_widget_pool = lambda: None
    panel._preview_rows = [_preview_row("First"), _preview_row("Second"), _preview_row("Third")]
    panel._active_visible_rows = lambda: panel._preview_rows[-2:]

    ModuleFivePanel._sync_virtual_rows(panel, force_bottom=True)

    assert [row.inventory_cell.label_text for row in panel._preview_rows] == ["First", "Second", "Third"]
    assert panel.content_scroll.virtual_heights[-1] == panel._logical_content_height()
    assert panel.content_scroll.scroll_to_bottom_calls == 1
    assert [widget.row.inventory_cell.label_text for widget in panel._row_widgets[:2]] == ["Second", "Third"]
    assert all(widget.animate_dual_phase is False for widget in panel._row_widgets[:2])
    assert panel._row_widgets[2].row is None


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
    panel._preview_rows = [_preview_row("Queued")]
    panel._pending_preview_rows = []
    panel._row_widgets = [_FakePreviewRowWidget()]
    panel._mode = ModuleFivePanel._MODE_LIVE_LATEST
    panel._export_active = True
    panel.content_scroll = _FakeScroll()
    panel._ensure_row_widget_pool = lambda: None

    ModuleFivePanel.set_export_active(panel, False)

    assert panel._export_active is False
    assert panel._mode == ModuleFivePanel._MODE_HISTORY_VIRTUALIZED
    assert [row.inventory_cell.label_text for row in panel._preview_rows] == ["Queued"]
    assert panel.content_scroll.view_changed_callbacks[-1] == panel._handle_view_changed


def test_module_five_panel_live_mode_limits_visible_rows_to_latest_two() -> None:
    panel = ModuleFivePanel.__new__(ModuleFivePanel)
    panel._preview_rows = [_preview_row("First"), _preview_row("Second"), _preview_row("Third")]
    panel._pending_preview_rows = []
    panel._row_widgets = [_FakePreviewRowWidget(), _FakePreviewRowWidget(), _FakePreviewRowWidget()]
    panel._mode = ModuleFivePanel._MODE_LIVE_LATEST
    panel._export_active = True
    panel.content_scroll = _FakeScroll(offset=0)
    panel._ensure_row_widget_pool = lambda: None

    ModuleFivePanel._refresh_visible_rows(panel)

    assert [widget.row.inventory_cell.label_text for widget in panel._row_widgets[:2]] == ["Second", "Third"]
    assert panel._row_widgets[2].row is None


def test_module_five_panel_live_mode_uses_bounded_logical_height() -> None:
    panel = ModuleFivePanel.__new__(ModuleFivePanel)
    panel._preview_rows = [_preview_row("One"), _preview_row("Two"), _preview_row("Three")]
    panel._pending_preview_rows = []
    panel._row_widgets = []
    panel._mode = ModuleFivePanel._MODE_LIVE_LATEST
    panel._export_active = True
    panel.content_scroll = _FakeScroll()

    row_height = spec.PHASE_THREE_MODULE_FIVE_ROW_SIZE[1]
    viewport_height = spec.PHASE_THREE_MODULE_FIVE_CONTENT_VIEWPORT_SIZE[1]

    assert panel._logical_content_height() == max(viewport_height, row_height * 2)


def test_scroll_viewport_virtual_refresh_uses_logical_height_for_window_and_scrollregion() -> None:
    viewport = ScrollViewport.__new__(ScrollViewport)
    viewport._viewport_size = (400, 180)
    viewport._virtual_content_height = 640
    viewport._content_height = 0
    viewport._viewport_height = 0
    viewport._virtual_scroll_offset = 0.0
    viewport._content_window_id = "window"
    viewport.viewport_canvas = _FakeCanvas()
    viewport.content_frame = _FakeFrame()
    viewport.scrollbar = _FakeScrollbar()
    viewport._view_changed_callback = None

    ScrollViewport.refresh_scroll_region(viewport)

    assert viewport.content_frame.configure_calls[-1]["height"] == 640
    assert viewport.viewport_canvas.itemconfigure_calls[-1] == ("window", {"width": 400, "height": 640})
    assert viewport.viewport_canvas.configure_calls[-1]["scrollregion"] == (0, 0, 400, 640)


def test_scroll_viewport_virtual_refresh_keeps_minimum_window_height_when_content_is_short() -> None:
    viewport = ScrollViewport.__new__(ScrollViewport)
    viewport._viewport_size = (400, 180)
    viewport._virtual_content_height = 80
    viewport._content_height = 0
    viewport._viewport_height = 0
    viewport._virtual_scroll_offset = 0.0
    viewport._content_window_id = "window"
    viewport.viewport_canvas = _FakeCanvas()
    viewport.content_frame = _FakeFrame()
    viewport.scrollbar = _FakeScrollbar()
    viewport._view_changed_callback = None

    ScrollViewport.refresh_scroll_region(viewport)

    assert viewport.content_frame.configure_calls[-1]["height"] == 180
    assert viewport.viewport_canvas.itemconfigure_calls[-1] == ("window", {"width": 400, "height": 180})
    assert viewport.viewport_canvas.configure_calls[-1]["scrollregion"] == (0, 0, 400, 80)
