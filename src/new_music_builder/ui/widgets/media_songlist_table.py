from __future__ import annotations

import tkinter as tk

from new_music_builder.ui import spec


class MediaSonglistTable(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        bg_color: str,
    ) -> None:
        super().__init__(
            parent,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_SONGLIST_TABLE_SIZE[0],
            height=spec.MEDIA_ROW_SONGLIST_TABLE_SIZE[1],
        )
        self._bg_color = bg_color
        self._width = spec.MEDIA_ROW_SONGLIST_TABLE_SIZE[0]
        self._height = spec.MEDIA_ROW_SONGLIST_TABLE_SIZE[1]
        self._header_height = spec.MEDIA_ROW_SONGLIST_TABLE_HEADER_HEIGHT
        self._row_height = spec.MEDIA_ROW_SONGLIST_TABLE_ROW_HEIGHT
        self._row_count = spec.MEDIA_ROW_SONGLIST_TABLE_MIN_ROWS
        self._column_widths = spec.MEDIA_ROW_SONGLIST_TABLE_COLUMN_WIDTHS
        self._divider_color = spec.MEDIA_ROW_SONGLIST_TABLE_DIVIDER_COLOR
        self._divider_width = spec.MEDIA_ROW_SONGLIST_TABLE_DIVIDER_WIDTH
        self._draw()

    def _draw(self) -> None:
        self.create_rectangle(
            0,
            0,
            self._width,
            self._header_height,
            outline='',
            fill=spec.MEDIA_ROW_SONGLIST_TABLE_HEADER_BG,
        )

        body_y = self._header_height
        for row_index in range(self._row_count):
            row_top = body_y + (row_index * self._row_height)
            row_bottom = row_top + self._row_height
            fill = (
                spec.MEDIA_ROW_SONGLIST_TABLE_ROW_BG_ODD
                if row_index % 2 == 0
                else spec.MEDIA_ROW_SONGLIST_TABLE_ROW_BG_EVEN
            )
            self.create_rectangle(
                0,
                row_top,
                self._width,
                row_bottom,
                outline='',
                fill=fill,
            )

        column_x = 0
        for width in self._column_widths[:-1]:
            column_x += width
            self.create_rectangle(
                column_x,
                0,
                column_x + self._divider_width,
                self._height,
                outline='',
                fill=self._divider_color,
            )

        header_divider_y = self._header_height
        self.create_rectangle(
            0,
            header_divider_y,
            self._width,
            header_divider_y + self._divider_width,
            outline='',
            fill=self._divider_color,
        )

        for row_index in range(1, self._row_count):
            row_divider_y = self._header_height + (row_index * self._row_height)
            self.create_rectangle(
                0,
                row_divider_y,
                self._width,
                row_divider_y + self._divider_width,
                outline='',
                fill=self._divider_color,
            )
