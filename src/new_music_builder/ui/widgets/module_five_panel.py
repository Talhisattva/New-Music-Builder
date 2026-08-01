from __future__ import annotations

from copy import deepcopy
import tkinter as tk

from new_music_builder.domain.models import GeneratedPreviewRow
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.module_five_preview_row import ModuleFivePreviewRow
from new_music_builder.ui.widgets.scroll_area import ScrollViewport


class ModuleFivePanel(tk.Frame):
    _MODE_HISTORY_VIRTUALIZED = "history_virtualized"
    _MODE_LIVE_LATEST = "live_latest"
    _LIVE_VISIBLE_ROWS = 2
    _ROW_OVERSCAN = 2

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(
            parent,
            bg=spec.PHASE_THREE_FOREGROUND_BG,
            bd=0,
            highlightthickness=0,
            width=spec.PHASE_THREE_MODULE_FIVE_SIZE[0],
            height=spec.PHASE_THREE_MODULE_FIVE_SIZE[1],
        )
        self.pack_propagate(False)
        self._preview_rows: list[GeneratedPreviewRow] = []
        self._row_widgets: list[ModuleFivePreviewRow] = []
        self._export_active = False
        self._mode = self._MODE_HISTORY_VIRTUALIZED

        self.header = tk.Frame(
            self,
            bg=spec.PHASE_THREE_MODULE_FIVE_HEADER_BORDER_COLOR,
            bd=0,
            highlightthickness=0,
            width=spec.PHASE_THREE_MODULE_FIVE_HEADER_SIZE[0],
            height=spec.PHASE_THREE_MODULE_FIVE_HEADER_SIZE[1],
        )
        self.header.place(x=0, y=0)
        self.header.pack_propagate(False)
        self.header_fill = tk.Frame(
            self.header,
            bg=spec.PHASE_THREE_MODULE_FIVE_HEADER_BG,
            bd=0,
            highlightthickness=0,
            width=spec.PHASE_THREE_MODULE_FIVE_HEADER_SIZE[0] - (spec.PHASE_THREE_MODULE_FIVE_HEADER_BORDER_WIDTH * 2),
            height=spec.PHASE_THREE_MODULE_FIVE_HEADER_SIZE[1] - (spec.PHASE_THREE_MODULE_FIVE_HEADER_BORDER_WIDTH * 2),
        )
        self.header_fill.place(
            x=spec.PHASE_THREE_MODULE_FIVE_HEADER_BORDER_WIDTH,
            y=spec.PHASE_THREE_MODULE_FIVE_HEADER_BORDER_WIDTH,
        )
        self.header_label = tk.Label(
            self.header_fill,
            text=spec.PHASE_THREE_MODULE_FIVE_HEADER_TEXT,
            bg=spec.PHASE_THREE_MODULE_FIVE_HEADER_BG,
            fg=spec.PHASE_THREE_MODULE_FIVE_HEADER_TEXT_COLOR,
            font=(
                spec.PHASE_THREE_MODULE_FIVE_HEADER_FONT_FAMILY,
                spec.PHASE_THREE_MODULE_FIVE_HEADER_FONT_SIZE,
            ),
            bd=0,
            highlightthickness=0,
            anchor='w',
        )
        self.header_label.place(x=20, y=0, relheight=1.0)

        self.content_scroll = ScrollViewport(
            self,
            size=spec.PHASE_THREE_MODULE_FIVE_CONTENT_PANE_SIZE,
            viewport_size=spec.PHASE_THREE_MODULE_FIVE_CONTENT_VIEWPORT_SIZE,
            scrollbar_size=spec.PHASE_THREE_MODULE_FIVE_SCROLLBAR_SIZE,
            show_top_edge=True,
            content_bottom_padding=0,
            bg_color=spec.PHASE_THREE_FOREGROUND_BG,
        )
        self.content_scroll.place(
            x=spec.PHASE_THREE_MODULE_FIVE_CONTENT_PANE_POS[0],
            y=spec.PHASE_THREE_MODULE_FIVE_CONTENT_PANE_POS[1],
        )
        self.content_scroll.set_view_changed_callback(self._handle_view_changed)
        self.content_scroll.set_virtual_content_height(self._logical_content_height())
        self._ensure_row_widget_pool()

    def set_preview_rows(self, rows: list[GeneratedPreviewRow]) -> None:
        self._mode = self._MODE_HISTORY_VIRTUALIZED
        self._preview_rows = deepcopy(rows)
        self._sync_virtual_rows(force_bottom=True)

    def append_preview_row(self, row: GeneratedPreviewRow) -> None:
        self._preview_rows.append(deepcopy(row))
        self._sync_virtual_rows(force_bottom=True)

    def reset_preview_rows(self) -> None:
        self._mode = self._MODE_HISTORY_VIRTUALIZED
        self._preview_rows = []
        self._sync_virtual_rows(force_bottom=True)

    def set_export_active(self, active: bool) -> None:
        if self._export_active == active:
            return
        self._export_active = active
        self._mode = self._MODE_LIVE_LATEST if active else self._MODE_HISTORY_VIRTUALIZED
        self.content_scroll.set_view_changed_callback(self._handle_view_changed if not active else None)
        self._refresh_visible_rows()
        self._sync_virtual_rows(force_bottom=True)

    def _ensure_row_widget_pool(self) -> None:
        target_size = self._target_pool_size()
        while len(self._row_widgets) < target_size:
            self._row_widgets.append(ModuleFivePreviewRow(self.content_scroll.content_frame))
        while len(self._row_widgets) > target_size:
            widget = self._row_widgets.pop()
            widget.destroy()

    def _sync_virtual_rows(self, *, force_bottom: bool) -> None:
        self._ensure_row_widget_pool()
        self.content_scroll.set_virtual_content_height(self._logical_content_height())
        if force_bottom:
            self.content_scroll.scroll_to_bottom()
        else:
            self.content_scroll.refresh_scroll_region()
        self._refresh_visible_rows()

    def _refresh_visible_rows(self) -> None:
        self._ensure_row_widget_pool()
        row_height = spec.PHASE_THREE_MODULE_FIVE_ROW_SIZE[1]
        visible_rows = self._active_visible_rows()
        mode = getattr(self, '_mode', self._MODE_HISTORY_VIRTUALIZED)
        scroll_offset = 0 if mode == self._MODE_LIVE_LATEST else self.content_scroll.current_scroll_offset_pixels()
        first_index = max(0, scroll_offset // row_height)
        local_offset = scroll_offset % row_height
        visible_count = min(
            len(visible_rows) - first_index if first_index < len(visible_rows) else 0,
            len(self._row_widgets),
        )
        for pool_index, row_widget in enumerate(self._row_widgets):
            preview_index = first_index + pool_index
            if pool_index >= visible_count or preview_index >= len(visible_rows):
                row_widget.clear_row()
                row_widget.place_forget()
                continue
            row_widget.set_row(visible_rows[preview_index], animate_dual_phase=not self._export_active)
            row_widget.place(
                x=0,
                y=(pool_index * row_height) - local_offset,
                width=spec.PHASE_THREE_MODULE_FIVE_ROW_SIZE[0],
                height=row_height,
            )

    def _handle_view_changed(self, _first: float, _last: float) -> None:
        if self._mode == self._MODE_LIVE_LATEST:
            return
        self._refresh_visible_rows()

    def _target_pool_size(self) -> int:
        row_height = spec.PHASE_THREE_MODULE_FIVE_ROW_SIZE[1]
        viewport_height = spec.PHASE_THREE_MODULE_FIVE_CONTENT_VIEWPORT_SIZE[1]
        visible_rows = max(1, (viewport_height + row_height - 1) // row_height)
        return visible_rows + self._ROW_OVERSCAN

    def _logical_content_height(self) -> int:
        row_height = spec.PHASE_THREE_MODULE_FIVE_ROW_SIZE[1]
        viewport_height = spec.PHASE_THREE_MODULE_FIVE_CONTENT_VIEWPORT_SIZE[1]
        visible_row_count = len(self._active_visible_rows())
        return max(viewport_height, visible_row_count * row_height)

    def _active_visible_rows(self) -> list[GeneratedPreviewRow]:
        mode = getattr(self, '_mode', self._MODE_HISTORY_VIRTUALIZED)
        if mode == self._MODE_LIVE_LATEST:
            return self._preview_rows[-self._LIVE_VISIBLE_ROWS:]
        return self._preview_rows
