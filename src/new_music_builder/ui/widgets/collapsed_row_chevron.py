from __future__ import annotations

import tkinter as tk

from new_music_builder.ui import spec


class CollapsedRowChevron(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        size: tuple[int, int] = spec.MEDIA_ROW_COLLAPSED_CHEVRON_SIZE,
        line_color: str = spec.MEDIA_ROW_COLLAPSED_CHEVRON_COLOR,
        line_width: int = spec.MEDIA_ROW_COLLAPSED_CHEVRON_WIDTH,
        bg_color: str | None = None,
    ) -> None:
        resolved_bg = bg_color if bg_color is not None else parent.cget('bg')
        super().__init__(
            parent,
            width=size[0],
            height=size[1],
            bg=resolved_bg,
            bd=0,
            highlightthickness=0,
        )
        self._size = size
        self._line_color = line_color
        self._line_width = line_width
        self._bg_color = resolved_bg
        self._draw()

    def _draw(self) -> None:
        midpoint_y = self._size[1] // 2
        self.create_line(
            0,
            0,
            self._size[0],
            midpoint_y,
            fill=self._line_color,
            width=self._line_width,
        )
        self.create_line(
            0,
            self._size[1],
            self._size[0],
            midpoint_y,
            fill=self._line_color,
            width=self._line_width,
        )

    def set_bg_color(self, bg_color: str) -> None:
        self._bg_color = bg_color
        self.configure(bg=bg_color)
