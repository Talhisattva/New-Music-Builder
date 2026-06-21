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
        self._refresh_views()

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
        self._refresh_views()

    def append_queue_group(self, group: ConversionSideGroup) -> None:
        self.state.ordered_groups.append(deepcopy(group))
        self._refresh_views()

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
                self._refresh_views()
            return

    def set_output_path(self, path: str) -> None:
        self.state.output_path = path

    def set_log_lines(self, lines: list[ExportLogLine]) -> None:
        self.state.current_run_log_lines = deepcopy(lines)
        self._refresh_views()

    def append_log_line(self, line: ExportLogLine) -> None:
        self.state.current_run_log_lines.append(deepcopy(line))
        self._refresh_views()

    def update_active_log_line(self, line: ExportLogLine) -> None:
        if self.state.current_run_log_lines:
            self.state.current_run_log_lines[-1] = deepcopy(line)
        else:
            self.state.current_run_log_lines.append(deepcopy(line))
        self._refresh_views()

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
        self._refresh_views()

    def _refresh_views(self) -> None:
        self.queue_table.set_groups(self.state.ordered_groups)
        self.log_view.set_lines(self.state.current_run_log_lines)
        self.queue_scroll.scroll_to_bottom()
        self.log_scroll.scroll_to_bottom()
