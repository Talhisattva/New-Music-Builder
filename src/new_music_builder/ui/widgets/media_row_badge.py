from __future__ import annotations

import tkinter as tk

from new_music_builder.ui import spec


class MediaRowBadge(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        row_number: int,
        size: tuple[int, int] = spec.MEDIA_ROW_BADGE_SIZE,
        bg_color: str = spec.MEDIA_ROW_BADGE_BG,
        outline_color: str = spec.MEDIA_ROW_BADGE_OUTLINE,
        outline_width: int = spec.MEDIA_ROW_BADGE_OUTLINE_WIDTH,
        text_color: str = spec.MEDIA_ROW_BADGE_TEXT_COLOR,
    ) -> None:
        super().__init__(
            parent,
            bg=bg_color,
            width=size[0],
            height=size[1],
            bd=0,
            highlightthickness=0,
        )
        self._size = size
        self._bg_color = bg_color
        self._outline_color = outline_color
        self._outline_width = outline_width
        self._text_color = text_color
        self._row_number = row_number

        self._draw()

    def _font_size_for_number(self, row_number: int) -> int:
        digits = len(str(abs(row_number)))
        if digits >= 4:
            return spec.MEDIA_ROW_BADGE_FONT_SIZE_4_DIGITS
        if digits == 3:
            return spec.MEDIA_ROW_BADGE_FONT_SIZE_3_DIGITS
        return spec.MEDIA_ROW_BADGE_FONT_SIZE

    def _draw(self) -> None:
        inset = self._outline_width
        self.create_rectangle(
            0,
            0,
            self._size[0],
            self._size[1],
            outline='',
            fill=self._outline_color,
        )
        self.create_rectangle(
            inset,
            inset,
            self._size[0] - inset,
            self._size[1] - inset,
            outline='',
            fill=self._bg_color,
        )
        self.create_text(
            self._size[0] // 2,
            self._size[1] // 2,
            text=str(self._row_number),
            fill=self._text_color,
            font=(spec.MEDIA_ROW_BADGE_FONT_FAMILY, self._font_size_for_number(self._row_number)),
            anchor='c',
        )
