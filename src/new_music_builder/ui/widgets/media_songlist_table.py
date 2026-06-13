from __future__ import annotations

import tkinter as tk

from PIL import Image, ImageTk

from new_music_builder.ui import spec


class MediaSonglistTable(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        bg_color: str,
        ear_icon_path: str | None = None,
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
        self._ear_icon_path = ear_icon_path
        self._ear_icon_image: ImageTk.PhotoImage | None = None
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

        self._draw_header_content()

    def _draw_header_content(self) -> None:
        current_x = 0
        labels = spec.MEDIA_ROW_SONGLIST_TABLE_HEADER_LABELS
        for index, column_width in enumerate(self._column_widths):
            center_x = current_x + (column_width / 2)
            center_y = self._header_height / 2
            if index == 3:
                self._draw_ear_icon(center_x, center_y)
            elif labels[index]:
                self.create_text(
                    center_x,
                    center_y,
                    text=labels[index],
                    fill=spec.MEDIA_ROW_SONGLIST_TABLE_HEADER_TEXT_COLOR,
                    font=(
                        spec.MEDIA_ROW_SONGLIST_TABLE_HEADER_FONT_FAMILY,
                        spec.MEDIA_ROW_SONGLIST_TABLE_HEADER_FONT_SIZE,
                    ),
                    anchor='c',
                )
            current_x += column_width

    def _draw_ear_icon(self, center_x: float, center_y: float) -> None:
        if not self._ear_icon_path:
            return
        try:
            image = Image.open(self._ear_icon_path)
        except OSError:
            return
        self._ear_icon_image = ImageTk.PhotoImage(image)
        self.create_image(center_x, center_y, image=self._ear_icon_image, anchor='c')
