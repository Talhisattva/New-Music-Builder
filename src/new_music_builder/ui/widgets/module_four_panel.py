from __future__ import annotations

from copy import deepcopy
import tkinter as tk

from new_music_builder.domain.models import ConversionSideGroup, ExportLogLine, ExportRunHistoryEntry, ExportRunState
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.module_four_log_view import ModuleFourLogView
from new_music_builder.ui.widgets.module_four_queue_table import ModuleFourQueueTable
from new_music_builder.ui.widgets.scroll_area import ScrollViewport


class ModuleFourPanel(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        status_check_icon_path: str | None = None,
        status_converting_icon_path: str | None = None,
        status_queued_icon_path: str | None = None,
    ) -> None:
        super().__init__(
            parent,
            bg=spec.PHASE_THREE_FOREGROUND_BG,
            bd=0,
            highlightthickness=0,
            width=spec.PHASE_THREE_MODULE_FOUR_SIZE[0],
            height=spec.PHASE_THREE_MODULE_FOUR_SIZE[1],
        )
        self.pack_propagate(False)
        self.state = ExportRunState()
        self._run_counter = 0
        self._queue_autoscroll = True
        self._log_autoscroll = True

        self.queue_scroll = ScrollViewport(
            self,
            size=spec.PHASE_THREE_MODULE_FOUR_QUEUE_PANE_SIZE,
            viewport_size=spec.PHASE_THREE_MODULE_FOUR_QUEUE_VIEWPORT_SIZE,
            scrollbar_size=spec.PHASE_THREE_MODULE_FOUR_QUEUE_SCROLLBAR_SIZE,
            show_top_edge=True,
            content_bottom_padding=0,
            bg_color=spec.PHASE_THREE_MODULE_FOUR_QUEUE_BG,
        )
        self.queue_scroll.place(x=0, y=0)
        self.queue_table = ModuleFourQueueTable(
            self.queue_scroll.content_frame,
            check_icon_path=status_check_icon_path,
            converting_icon_path=status_converting_icon_path,
            queued_icon_path=status_queued_icon_path,
        )
        self.queue_table.pack(anchor='nw')
        self.queue_scroll.set_view_changed_callback(self._handle_queue_view_changed)
        self.queue_scroll.set_virtual_content_height(self.queue_table.logical_content_height())
        self.queue_table.set_viewport_height(spec.PHASE_THREE_MODULE_FOUR_QUEUE_VIEWPORT_SIZE[1])

        self.log_scroll = ScrollViewport(
            self,
            size=spec.PHASE_THREE_MODULE_FOUR_LOG_PANE_SIZE,
            viewport_size=spec.PHASE_THREE_MODULE_FOUR_LOG_VIEWPORT_SIZE,
            scrollbar_size=spec.PHASE_THREE_MODULE_FOUR_LOG_SCROLLBAR_SIZE,
            show_top_edge=True,
            content_bottom_padding=0,
            bg_color=spec.PHASE_THREE_FOREGROUND_BG,
        )
        self.log_scroll.place(
            x=spec.PHASE_THREE_MODULE_FOUR_LOG_PANE_POS[0],
            y=spec.PHASE_THREE_MODULE_FOUR_LOG_PANE_POS[1],
        )
        self.log_view = ModuleFourLogView(self.log_scroll.content_frame)
        self.log_view.pack(anchor='nw')
        self._last_width = spec.PHASE_THREE_MODULE_FOUR_SIZE[0]
        self._refresh_views(force=True)

    def resize(self, width: int) -> None:
        if self._last_width == width:
            return
        self._last_width = width
        self.configure(width=width, height=spec.PHASE_THREE_MODULE_FOUR_SIZE[1])
        queue_viewport_width = max(1, width - spec.PHASE_THREE_MODULE_FOUR_QUEUE_SCROLLBAR_SIZE[0])
        self.queue_scroll.resize(
            size=(width, spec.PHASE_THREE_MODULE_FOUR_QUEUE_PANE_SIZE[1]),
            viewport_size=(queue_viewport_width, spec.PHASE_THREE_MODULE_FOUR_QUEUE_VIEWPORT_SIZE[1]),
            scrollbar_size=spec.PHASE_THREE_MODULE_FOUR_QUEUE_SCROLLBAR_SIZE,
        )
        self.queue_table.resize(queue_viewport_width)
        self.queue_table.set_viewport_height(spec.PHASE_THREE_MODULE_FOUR_QUEUE_VIEWPORT_SIZE[1])
        self.queue_scroll.set_virtual_content_height(self.queue_table.logical_content_height())
        self._sync_queue_scroll_offset()

        log_viewport_width = max(1, width - spec.PHASE_THREE_MODULE_FOUR_LOG_SCROLLBAR_SIZE[0])
        self.log_scroll.resize(
            size=(width, spec.PHASE_THREE_MODULE_FOUR_LOG_PANE_SIZE[1]),
            viewport_size=(log_viewport_width, spec.PHASE_THREE_MODULE_FOUR_LOG_VIEWPORT_SIZE[1]),
            scrollbar_size=spec.PHASE_THREE_MODULE_FOUR_LOG_SCROLLBAR_SIZE,
        )
        self.log_scroll.place_configure(
            x=spec.PHASE_THREE_MODULE_FOUR_LOG_PANE_POS[0],
            y=spec.PHASE_THREE_MODULE_FOUR_LOG_PANE_POS[1],
            width=width,
            height=spec.PHASE_THREE_MODULE_FOUR_LOG_PANE_SIZE[1],
        )
        self.log_view.resize(log_viewport_width)

    def set_queue_groups(self, groups: list[ConversionSideGroup]) -> None:
        self.state.ordered_groups = deepcopy(groups)
        self._queue_autoscroll = True
        self.queue_table.set_groups(self.state.ordered_groups)
        self._refresh_queue_view(force_bottom=True)

    def append_queue_group(self, group: ConversionSideGroup) -> None:
        self._queue_autoscroll = self.queue_scroll.is_near_bottom()
        group_copy = deepcopy(group)
        self.state.ordered_groups.append(group_copy)
        self.queue_table.append_group(group_copy)
        self._refresh_queue_view(force_bottom=self._queue_autoscroll)

    def append_song_to_group(self, row_id: int, side: str, song) -> None:
        self._queue_autoscroll = self.queue_scroll.is_near_bottom()
        for group in self.state.ordered_groups:
            if group.row_id == row_id and group.side == side:
                group.songs.append(deepcopy(song))
                self.queue_table.set_groups(self.state.ordered_groups)
                self._refresh_queue_view(force_bottom=self._queue_autoscroll)
                return

    def update_song_progress(self, row_id: int, side: str, song_index: int, percent: int, status: str, size_label: str) -> None:
        for group_index, group in enumerate(self.state.ordered_groups):
            if group.row_id != row_id or group.side != side:
                continue
            if 0 <= song_index < len(group.songs):
                song = group.songs[song_index]
                song.percent = percent
                song.status = status  # type: ignore[assignment]
                song.size_label = size_label
                self.state.active_group_index = group_index
                self.state.active_song_index = song_index
                self.queue_table.update_song_progress(row_id, side, song_index, percent, status, size_label)
                self._refresh_queue_view(force_bottom=False)
            return

    def set_output_path(self, path: str) -> None:
        self.state.output_path = path

    def set_log_lines(self, lines: list[ExportLogLine]) -> None:
        self.state.current_run_log_lines = deepcopy(lines)
        self._log_autoscroll = True
        self.log_view.set_lines(self.state.current_run_log_lines)
        self._refresh_log_view(force_bottom=True)

    def append_log_line(self, line: ExportLogLine) -> None:
        self._log_autoscroll = self.log_scroll.is_near_bottom()
        line_copy = deepcopy(line)
        self.state.current_run_log_lines.append(line_copy)
        self.log_view.append_line(line_copy)
        self._refresh_log_view(force_bottom=self._log_autoscroll)

    def update_active_log_line(self, line: ExportLogLine) -> None:
        self._log_autoscroll = self.log_scroll.is_near_bottom()
        line_copy = deepcopy(line)
        if self.state.current_run_log_lines:
            self.state.current_run_log_lines[-1] = line_copy
        else:
            self.state.current_run_log_lines.append(line_copy)
        self.log_view.update_active_line(line_copy)
        self._refresh_log_view(force_bottom=self._log_autoscroll)

    def finalize_active_log_line(self, line: ExportLogLine) -> None:
        self.update_active_log_line(line)

    def archive_current_run(self) -> None:
        if not self.state.current_run_log_lines:
            return
        self._run_counter += 1
        self.state.history_runs.append(
            ExportRunHistoryEntry(
                divider_label=f'EXPORT RUN {self._run_counter}',
                lines=deepcopy(self.state.current_run_log_lines),
            )
        )

    def reset_current_run(self) -> None:
        self.state.ordered_groups = []
        self.state.active_group_index = None
        self.state.active_song_index = None
        self.state.current_run_log_lines = []
        self.state.output_path = ""
        self._queue_autoscroll = True
        self._log_autoscroll = True
        self._refresh_views(force=True)

    def _refresh_views(self, *, force: bool = False) -> None:
        if force:
            self.queue_table.set_groups(self.state.ordered_groups)
            self.log_view.set_lines(self.state.current_run_log_lines)
        self._refresh_queue_view(force_bottom=self._queue_autoscroll)
        self._refresh_log_view(force_bottom=self._log_autoscroll)

    def _refresh_queue_view(self, *, force_bottom: bool) -> None:
        self.queue_scroll.set_virtual_content_height(self.queue_table.logical_content_height())
        self._sync_queue_scroll_offset()
        if force_bottom:
            self.queue_scroll.scroll_to_bottom()
        else:
            self.queue_scroll.refresh_scroll_region()

    def _refresh_log_view(self, *, force_bottom: bool) -> None:
        self.log_scroll.refresh_scroll_region()
        if force_bottom:
            self.log_scroll.scroll_to_bottom()

    def _handle_queue_view_changed(self, _first: float, _last: float) -> None:
        self._sync_queue_scroll_offset()

    def _sync_queue_scroll_offset(self) -> None:
        self.queue_table.set_scroll_offset(self.queue_scroll.current_scroll_offset_pixels())
