from __future__ import annotations

from copy import deepcopy
import tkinter as tk

from new_music_builder.domain.models import GeneratedPreviewRow
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.module_five_preview_row import ModuleFivePreviewRow
from new_music_builder.ui.widgets.scroll_area import ScrollViewport


class ModuleFivePanel(tk.Frame):
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
        self._visible_pool_size = 0

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
        self._preview_rows = deepcopy(rows)
        self._sync_virtual_rows(force_bottom=True)

    def append_preview_row(self, row: GeneratedPreviewRow) -> None:
        pinned_to_bottom = self.content_scroll.is_near_bottom()
        row_copy = deepcopy(row)
        self._preview_rows.append(row_copy)
        self._sync_virtual_rows(force_bottom=pinned_to_bottom)

    def reset_preview_rows(self) -> None:
        self._preview_rows = []
        self._sync_virtual_rows(force_bottom=True)

    def _ensure_row_widget_pool(self) -> None:
        target_size = self._target_pool_size()
        while len(self._row_widgets) < target_size:
            row_widget = ModuleFivePreviewRow(self.content_scroll.content_frame)
            self._row_widgets.append(row_widget)
        self._visible_pool_size = target_size

    def _sync_virtual_rows(self, *, force_bottom: bool = False) -> None:
        self._ensure_row_widget_pool()
        self.content_scroll.set_virtual_content_height(self._logical_content_height())
        if force_bottom:
            self.content_scroll.scroll_to_bottom()
        else:
            self.content_scroll.refresh_scroll_region()
        self._refresh_visible_rows()

    def _refresh_visible_rows(self) -> None:
        row_height = spec.PHASE_THREE_MODULE_FIVE_ROW_SIZE[1]
        scroll_offset = self.content_scroll.current_scroll_offset_pixels()
        first_index = max(0, scroll_offset // row_height)
        local_offset = scroll_offset % row_height
        visible_count = min(
            len(self._preview_rows) - first_index if first_index < len(self._preview_rows) else 0,
            self._visible_pool_size,
        )
        for pool_index, row_widget in enumerate(self._row_widgets):
            preview_index = first_index + pool_index
            if pool_index >= visible_count or preview_index >= len(self._preview_rows):
                row_widget.place_forget()
                continue
            row_widget.set_row(self._preview_rows[preview_index])
            row_widget.place(
                x=0,
                y=(pool_index * row_height) - local_offset,
                width=spec.PHASE_THREE_MODULE_FIVE_ROW_SIZE[0],
                height=row_height,
            )

    def _handle_view_changed(self, _first: float, _last: float) -> None:
        self._refresh_visible_rows()

    def _target_pool_size(self) -> int:
        row_height = spec.PHASE_THREE_MODULE_FIVE_ROW_SIZE[1]
        viewport_height = spec.PHASE_THREE_MODULE_FIVE_CONTENT_VIEWPORT_SIZE[1]
        visible_rows = max(1, (viewport_height + row_height - 1) // row_height)
        return visible_rows + 2

    def _logical_content_height(self) -> int:
        row_height = spec.PHASE_THREE_MODULE_FIVE_ROW_SIZE[1]
        viewport_height = spec.PHASE_THREE_MODULE_FIVE_CONTENT_VIEWPORT_SIZE[1]
        return max(viewport_height, len(self._preview_rows) * row_height)
