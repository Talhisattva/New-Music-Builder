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

    def set_preview_rows(self, rows: list[GeneratedPreviewRow]) -> None:
        self._preview_rows = deepcopy(rows)
        self._refresh_rows()

    def append_preview_row(self, row: GeneratedPreviewRow) -> None:
        self._preview_rows.append(deepcopy(row))
        self._refresh_rows()

    def reset_preview_rows(self) -> None:
        self._preview_rows = []
        self._refresh_rows()

    def _refresh_rows(self) -> None:
        for widget in self._row_widgets:
            widget.destroy()
        self._row_widgets.clear()

        for row in self._preview_rows:
            row_widget = ModuleFivePreviewRow(self.content_scroll.content_frame)
            row_widget.set_row(row)
            row_widget.pack(anchor='nw')
            self._row_widgets.append(row_widget)

        self.content_scroll.refresh_scroll_region()
        self.content_scroll.scroll_to_bottom()
